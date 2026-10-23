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