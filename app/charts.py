#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports libraries
import plotly.graph_objects as go 
from plotly.subplots import make_subplots
#--------------------------------------------------------------#

# Percent Format Function for low-volatility assets 
def pct_format(span):
    if span >= 0.10:
        return ".0%"
    if span >= 0.01:
        return ".1%"
    if span >= 0.001:
        return ".2%"
    return ".3%"
#--------------------------------------------------------------#

# Styling function for all the figures 
def style_fig(fig, height=380):
    fig.update_layout(
        height=height,
        margin=dict(t=40, b=30, l=50, r=20),
        legend=dict(orientation="h", y=1.12),
        template="plotly_dark",
        paper_bgcolor="#101010", plot_bgcolor="#101010",
        font=dict(family="Inter, sans-serif", color="#9498A0", size=12),
    )

    fig.update_xaxes(gridcolor="#1e1e1e")
    fig.update_yaxes(gridcolor="#1e1e1e")
    
    return fig
#--------------------------------------------------------------#

# Visualisation Function: builds the charts for the metrics computed above 
def visualize(df):

    # Global variables for function 
    log_rets = df['log_returns'].dropna()
    lo = log_rets.quantile(0.01)
    hi = log_rets.quantile(0.99)
    span = hi - lo 
    bin_size = span / 50 if span > 0 else 0.001
    ret_fmt = pct_format(span)

    cum_ret = df['cumulative_return'].dropna()
    vol = df['rolling_vol_annualized'].dropna()

    cum_fmt = pct_format(cum_ret.max() - cum_ret.min()) if len(cum_ret) else ".1%"
    vol_fmt = pct_format(vol.max() - vol.min()) if len(vol) else ".1%"

    # visualizations 
    candlestick_fig = go.Figure()

    # adding the candlestick trace 
    candlestick_fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price'
    ))

    # adding the sma traces 
    # sma 20
    candlestick_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['sma_20'],
        mode='lines',
        name='20-day SMA',
        line=dict(color='#60A5FA', width=1.5)
    ))

    # sma 50
    candlestick_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['sma_50'],
        mode='lines',
        name='50-day SMA',
        line=dict(color='#FBBF24', width=1.5)
    ))

    candlestick_fig.update_layout(xaxis_rangeslider_visible=False)

    # making subplots for quant charts 
    risk_vs_cum_return_fig = make_subplots(specs=[[{"secondary_y": True}]])

    # risk vs. return 
    risk_vs_cum_return_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['cumulative_return'],
        mode='lines',
        name='Return',
        line=dict(color='#34D399', width=1.5)
    ), secondary_y=False)

    risk_vs_cum_return_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['rolling_vol_annualized'],
        mode='lines',
        name='Annualized Risk',
        line=dict(color='#A78BFA', width=1.5)
    ), secondary_y=True)

    # underwater drawdown chart 
    drawdown_fig = go.Figure()
    drawdown_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['drawdown'],
        mode='lines',
        name='Drawdown',
        line=dict(color='#EF4444', width=1.5),
        fill='tozeroy', fillcolor="rgba(239,68,68,0.22)"
    ))

    drawdown_fig.update_yaxes(title_text="Drawdown", tickformat=pct_format(abs(df['drawdown'].min())))

    # returns distribution histogram 
    returns_histogram_fig = go.Figure(go.Histogram(
    x=log_rets,
    xbins=dict(size=bin_size),
    name='Returns Distribution',
    marker_color="#60A5FA",
    hovertemplate=f"Daily return near %{{x:{ret_fmt}}}<br>Days: %{{y}}<extra></extra>"
    ))

    risk_vs_cum_return_fig.update_yaxes(
    title_text="Cumulative Return",
    tickformat=cum_fmt,
    title_font_color="#34D399",
    secondary_y=False)

    risk_vs_cum_return_fig.update_yaxes(
    title_text="Annualized Volatility",
    tickformat=vol_fmt,
    title_font_color="#A78BFA",
    secondary_y=True)

    returns_histogram_fig.update_xaxes(range=[lo, hi], 
                          title_text="Daily log returns",
                          tickformat=ret_fmt)
    returns_histogram_fig.update_yaxes(title_text="Number of days")

    return (
        style_fig(candlestick_fig), 
        style_fig(risk_vs_cum_return_fig), 
        style_fig(drawdown_fig), 
        style_fig(returns_histogram_fig)
    )
#--------------------------------------------------------------#

