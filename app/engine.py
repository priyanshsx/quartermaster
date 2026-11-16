#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports Libraries

import streamlit as st 
import pandas as pd 
import numpy as np 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import timedelta
from pathlib import Path
#--------------------------------------------------------------#

# Global Variables 

MAX_MISSING_DATES = 5
#--------------------------------------------------------------#

# Checks for date ranges for which data is available from yfinance
@st.cache_data(ttl=86400, show_spinner="Checking available history")
def get_asset_date_bounds(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='max')

    if df.empty: 
        raise ValueError("No history available for this asset.") 

    return df.index.min().date(), df.index.max().date()
#--------------------------------------------------------------#

# OHLCV downloader: downloads the raw data from yfinance
@st.cache_data(ttl=3600, max_entries=100, show_spinner=False)
def fetch_asset(ui_ticker, ui_start_date, ui_end_date):

    # downloads the raw data 
    asset = yf.download(ui_ticker, start=ui_start_date, end=ui_end_date, auto_adjust=True, progress=False)

    # handles if yf.download did not work/failed 
    if asset.empty:
        raise ValueError("No data found for this ticker and date range.")

    today_utc = pd.Timestamp.utcnow().date()
    asset = asset[asset.index.date < today_utc]

    if asset.empty:
        raise ValueError("Only today's session falls in this range. And it hasn't closed yet.")

    # formats the columns into a standard from the raw downloaded data   
    if isinstance(asset.columns, pd.MultiIndex):
        asset.columns = asset.columns.get_level_values(0)
    asset.columns = asset.columns.str.lower()
    asset.index.name = 'date'
    asset.columns.name = None 
    return asset 
#--------------------------------------------------------------#

# Serializes the analyzed frame for download 
@st.cache_data(show_spinner=False)
def to_csv_bytes(df):
    keep_full = {"open", "high", "low", "close", "sma_20", "sma_50", "volume"}
    rounding = {c: 6 for c in df.columns if c not in keep_full}
    return df.round(rounding).to_csv(index_label="date").encode("utf-8")
#--------------------------------------------------------------#

# Tick Inspector: checks for corrupted highs and lows, negative volume, and high, open, close
def tick_inspector(df, spec):
    # checking for duplicates 
    duplicates = df.index.duplicated().sum()

    # checking for missing dates 
    gaps = df.index.to_series().diff().dt.days
    normal = spec["max_gap_days"]
    excess_days = int((gaps - normal).clip(lower=0).sum())
    suspicious_gaps = gaps[gaps > normal]

    # checking for corrupted highs and lows where low > high 
    corrupted_high_low = df[df['low'] > df['high']]

    # checking for where volume is below 0 
    negative_volume = df[df['volume'] < 0]

    # checking for where high vs. open/close check 
    high_open_close = df[(df['open'] > df['high']) | (df['close'] > df['high'])]

    # doing a global boolean mask check for bad data 
    is_healthy = excess_days <= MAX_MISSING_DATES and len(corrupted_high_low) == 0 and len(negative_volume) == 0 and len(high_open_close) == 0 and duplicates == 0

    return{"is_healthy": is_healthy, 
           "duplicates": duplicates,
           "suspicious_gaps": suspicious_gaps,
           "excess_days": excess_days,
           "corrupted_high_low": corrupted_high_low,
           "negative_volume": negative_volume,
           "high_open_close": high_open_close}
#--------------------------------------------------------------#

# Quant Analyzer: computes the metrics for the charts 
def quant_analyzer(df, ui_ticker, spec):
    # daily returns 
    df['daily_returns'] = df['close'].pct_change()

    # moving averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()

    # calculating the log returns  
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1)) 

    # rolling volatility for a 30-day period (annualized, for 365 trading days for crypto)
    df['rolling_vol_annualized'] = df['log_returns'].rolling(window=30).std() * np.sqrt(spec["trading_days"])

    # calculating the cumulative return 
    df['cumulative_return'] = (1 + df['daily_returns']).cumprod() - 1 

    # calculating the max drawdown 
    df['cum_return_for_drawdown'] = (1 + df['daily_returns'].fillna(0)).cumprod()
    df['running_max'] = df['cum_return_for_drawdown'].cummax()
    df['drawdown'] = ((df['cum_return_for_drawdown'] - df['running_max']) / df['running_max'])
    df['max_drawdown'] = df['drawdown'].min()

    # calculating the tape metrics: skew, kurtosis, sharpe, sortino 
    df['skewness'] = df['log_returns'].skew()
    df['kurtosis'] = df['log_returns'].kurt()
    df['avg_daily_log_return'] = df['log_returns'].mean()
    df['avg_daily_simple_return'] = df['daily_returns'].mean()

    return df
#--------------------------------------------------------------#

# Computes the numbers displayed on the performance calculator page
def outcome_analyzer(df, amount):
    cr = df['cumulative_return']
    r = df['daily_returns']

    # Entries and exits 
    entry_price = df['close'].iloc[0]
    entry_date = df.index[0]
    exit_price = df['close'].iloc[-1]
    exit_date = df.index[-1]

    # Final Value    
    final_value = amount * (1 + cr.iloc[-1])

    # Max unrealized loss 
    max_loss_pct = cr.min()
    max_profit_pct = cr.max()

    # Worst week, worst month 
    weekly = (1 + r).resample("W").prod() - 1
    monthly = (1 + r).resample("ME").prod() - 1

    # Position value over time, and how much it moved each period 
    V = amount * (1 + cr.fillna(0))
    Vw = V.resample("W").last()
    Vm = V.resample("ME").last()

    wk_change = Vw.diff()
    wk_change.iloc[0] = Vw.iloc[0] - amount 
    mo_change = Vm.diff()
    mo_change.iloc[0] = Vm.iloc[0] - amount 

    return {

        # Computes basic details 
        "entry_price": entry_price,
        "entry_date": entry_date,
        "exit_price": exit_price,
        "exit_date": exit_date,
        "final_value": final_value,
        "gain_amount": amount * cr.iloc[-1],
        "gain_pct": cr.iloc[-1],

        # Computes max loss amounts
        "max_loss_amount": amount * max_loss_pct,
        "max_loss_pct": max_loss_pct,
        "max_loss_date": cr.idxmin(),

        # Computes max profit amounts 
        "max_profit_amount": amount * max_profit_pct,
        "max_profit_pct": max_profit_pct,
        "max_profit_date": cr.idxmax(),
        
        # Computes loss days 
        "loss_days": int((cr < 0).sum()),
        "total_days": len(df),

        # Computes worst performance returns, date(s), and week(s)
        "worst_day_pct": r.min(),
        "worst_day_date": r.idxmin(),
        "worst_week_pct": weekly.min(),
        "worst_week_date": weekly.idxmin(),
        "worst_month_pct": monthly.min(),
        "worst_month_date": monthly.idxmin(),
        "low_value": amount * (1 + max_loss_pct),
        "high_value": amount * (1 + max_profit_pct),
        "worst_day_amount": V.diff().loc[r.idxmin()],
        "worst_week_amount": wk_change.loc[weekly.idxmin()],
        "worst_month_amount": mo_change.loc[monthly.idxmin()]
    }
#--------------------------------------------------------------#

# Returns the default return frequency for a pair of assets: daily when both
# trade on the same market, weekly when they do not
def default_freq(spec_a, spec_b):
    return "D" if spec_a["market"] == spec_b["market"] else "W"
#--------------------------------------------------------------#

# Pair Aligner: puts two assets onto a shared calendar before comparing them
def align_pair(df_a, df_b, freq="W"):
    # keeps only the days on which both assets traded
    common = df_a.index.intersection(df_b.index).sort_values()

    if len(common) == 0:
        raise ValueError("These two assets share no trading days in this range.")

    # reindexes PRICES, not returns. A move on a day that only one asset traded
    # is then compounded into the next shared observation instead of being
    # thrown away: a Bitcoin weekend is carried into Monday.
    price_a = df_a['close'].reindex(common)
    price_b = df_b['close'].reindex(common)

    # weekly resampling happens AFTER reindexing, so both series end their week
    # on the same shared trading day rather than on their own calendars
    if freq == "W":
        price_a = price_a.resample("W").last()
        price_b = price_b.resample("W").last()

    aligned = pd.concat([price_a.pct_change(), price_b.pct_change()], axis=1, keys=["a", "b"])

    return aligned.dropna()
#--------------------------------------------------------------#

# Pair Analyzer: computes how two aligned return series relate to each other
def pair_analyzer(aligned, window):
    a = aligned['a']
    b = aligned['b']

    # rolling correlation, and rolling beta of a measured against b
    rolling_corr = a.rolling(window).corr(b)
    rolling_beta = a.rolling(window).cov(b) / b.rolling(window).var()
    rolling_beta = rolling_beta.replace([np.inf, -np.inf], np.nan)

    # whole-period figures. var_b guards a flat series such as a stablecoin,
    # where dividing by zero variance would return infinity.
    full_corr = a.corr(b)
    var_b = b.var()
    full_beta = a.cov(b) / var_b if var_b else np.nan

    # share of periods where both moved the same way. Flat periods are left out
    # because np.sign(0) is 0, so two flat periods would otherwise count as
    # agreeing with each other.
    moved = (a != 0) & (b != 0)
    same = np.sign(a[moved]) == np.sign(b[moved])
    n_moved = int(moved.sum())

    return {

        # Rolling series, for the chart
        "rolling_corr": rolling_corr,
        "rolling_beta": rolling_beta,

        # Whole-period figures, for the table
        "full_corr": full_corr,
        "full_beta": full_beta,
        "r_squared": full_corr ** 2,

        # Direction agreement, with the counts behind it
        "same_direction_pct": same.mean() if n_moved else np.nan,
        "same_direction_periods": int(same.sum()),
        "n_moved": n_moved,

        # Lead and lag. corr_b_leads pairs today's a against yesterday's b, so a
        # high value there means b moved first.
        "corr_b_leads": a.corr(b.shift(1)),
        "corr_same": full_corr,
        "corr_a_leads": a.shift(1).corr(b),

        # Context for the caller
        "n_obs": len(aligned),
        "window": window
    }
#--------------------------------------------------------------#
#----------------------End-of-code-----------------------------#