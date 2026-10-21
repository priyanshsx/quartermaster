#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# importing libraries
import streamlit as st 
from datetime import timedelta
from pathlib import Path
from engine import (
    get_asset_date_bounds,
    fetch_asset,
    tick_inspector,
    MAX_MISSING_DATES,
    available_assets,
    quant_analyzer,
    to_csv_bytes,
)
from charts import visualize 
ASSETS = Path(__file__).parent/"assets"
st.set_page_config(layout="wide", page_title="Quartermaster", page_icon=str(ASSETS/"favicon-32.png"))
st.logo(str(ASSETS / "logo-mark-256.png"), link="https://quartermasterlabs.com")
#--------------------------------------------------------------#

# User Interface 

# managing the sidebar 
st.sidebar.header("Configuration")

# Step 1: request for ticker and dates
ui_ticker = st.sidebar.selectbox(label='select a ticker from the list',
                         options=available_assets, 
                         index=None)

# managing ticker entries
if ui_ticker:
    try: 
        min_date, max_date = get_asset_date_bounds(ui_ticker)
    except ValueError:
        st.sidebar.warning("No history is available for this asset. Please try another asset.")
        ui_start_date, ui_end_date = None, None 
    except Exception: 
        st.sidebar.warning("Couldn't reach Yahoo Finance. Please try again in a minute.")
        ui_start_date, ui_end_date = None, None 
    else:   
        st.sidebar.info(f"Available from {min_date} to {max_date}")

        ui_start_date = st.sidebar.date_input(label='select start date',
                                            value=max(min_date, (max_date - timedelta(days=365))),
                                            min_value=min_date,
                                            max_value=max_date)

        ui_end_date = st.sidebar.date_input(label='select end date',
                                            value=max_date,
                                            min_value=min_date,
                                            max_value=max_date)
else:
    st.sidebar.info("Please select a ticker above to configure dates.")
    ui_start_date, ui_end_date = None, None
#--------------------------------------------------------------#

# letting the user click the run analysis button to continue
if st.sidebar.button("Run analysis", type="primary"):
    st.session_state.pop("result", None)

    # input validation 
    if ui_ticker is None:
        st.error("Please select a ticker before running the analysis.")
        st.stop()
    if ui_start_date is None or ui_end_date is None:
        st.error("Date range unavailable for this asset. Please try another ticker.")
        st.stop()

    if ui_start_date >= ui_end_date:
        st.error("Start date must be before the end date.")
        st.stop()

    # data download
    try: 
        with st.spinner(f"Downloading {ui_ticker} data..."):
            raw_data_df = fetch_asset(ui_ticker, ui_start_date, ui_end_date + timedelta(days=1)) 
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception:
        st.error("Couldn't reach Yahoo Finance. Please try again in a minute.")
        st.stop()
#--------------------------------------------------------------#

    # Step 2: Clean data (if healthy)
    health_report = tick_inspector(raw_data_df)

    if health_report['is_healthy'] == True:
        enriched_data = quant_analyzer(raw_data_df,ui_ticker)
    else:
        enriched_data = None
    
    # storing the session state 
    st.session_state["result"] = {
            "ticker": ui_ticker,
            "start_date": ui_start_date,
            "end_date": ui_end_date,
            "health_report": health_report,
            "enriched_data": enriched_data
        }
    st.toast("Inspection complete.")

result = st.session_state.get("result")

if result:
    st.title(f"Visualized quant metrics for {result['ticker']}")
    health_report = result["health_report"]

    if health_report["is_healthy"]:
        enriched_data = result["enriched_data"] 
        missing = health_report['missing_dates']

        # Download csv option 
        start_str = enriched_data.index[0].strftime("%Y-%m-%d")
        end_str = enriched_data.index[-1].strftime("%Y-%m-%d")
        status = "integrity checks passed" if len(missing) == 0 else f"{len(missing)} date(s) missing."

        head_col, d1_col = st.columns([3, 1], vertical_alignment="center")
        with head_col:
            st.caption(f"{start_str} - {end_str} · {len(enriched_data):,} rows · {status}")
        with d1_col:
            st.download_button(
                label="Download CSV",
                data=to_csv_bytes(enriched_data),
                file_name=f"quartermaster_{result['ticker']}_{start_str}_{end_str}.csv",
                mime="text/csv",
                icon=":material/download:",
                width="stretch",
                help="Daily OHLCV plus computed returns, moving averages, rolling volatility, cumulative return and drawdown."
            )


        if len(missing) > 0:
            date_list = ", ".join(missing.strftime('%Y-%m-%d'))
            st.warning(f"{len(missing)} date(s) missing from the source data: {date_list}. "
                       f"The analysis still ran, but volatility and return distribution figures may be slightly affected.")

        # visualizing charts
        charts = visualize(enriched_data)
        candlestick_fig, risk_vs_cum_return_fig, drawdown_fig, returns_histogram_fig = charts

        # Building the columns in streamlit 
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(label="Skew", value=round(enriched_data['skewness'].iloc[-1], 4), help="Asymmetry of daily log returns. Negative means the big moves tend to be drops.")
        m2.metric(label='Excess Kurtosis', value=round(enriched_data['kurtosis'].iloc[-1], 4), help="Tail weight vs a normal distribution. 0 is normal; higher means extreme days are more common.")
        m3.metric(label='Avg. Log Return', value=f"{enriched_data['avg_daily_log_return'].iloc[-1]:.2%}", help="Mean daily log return. Not annualised.")
        m4.metric(label='Avg. Return', value=f"{enriched_data['avg_daily_simple_return'].iloc[-1]:.2%}", help="Mean daily simple return. Not annualised.")
        m5.metric(label="Max Drawdown",value=f"{enriched_data['max_drawdown'].iloc[-1]:.2%}", help="Worst peak-to-trough fall over the selected period.")

        # Step 3: Build the charts  
        top_left, top_right = st.columns(2, gap="medium")

        with top_left:
            st.subheader(f"{result['ticker']} Risk vs. Return")
            st.plotly_chart(risk_vs_cum_return_fig, width="stretch")

        with top_right:
            st.subheader(f"{result['ticker']} Price Action with SMAs")
            st.plotly_chart(candlestick_fig, width="stretch")

        bottom_left, bottom_right = st.columns(2, gap="medium")

        with bottom_left:
            st.subheader(f"{result['ticker']} Drawdown")
            st.plotly_chart(drawdown_fig, width="stretch")

        with bottom_right:
            st.subheader(f"{result['ticker']} Historical Returns")
            st.plotly_chart(returns_histogram_fig, width="stretch")
            st.caption("Each bar groups days by their return. Hover to see the return range "
                       "and how many days fell in it. Axis zoomed to the 1st-99th percentile.")
#--------------------------------------------------------------#

# Dealing with bad data         
    else:
        st.error("Found bad data. Analysis stopped.")

        if health_report['duplicates'] > 0:
            st.warning(f"Found {health_report['duplicates']} duplicate rows.")

        if len(health_report['negative_volume']) > 0:
            st.warning("Negative volume ticks found: ")
            st.dataframe(health_report['negative_volume'])

        if len(health_report['missing_dates']) > MAX_MISSING_DATES:
            missing = health_report['missing_dates']
            date_list = ", ".join(missing[:10].strftime('%Y-%m-%d'))
            st.warning(f"Found {len(health_report['missing_dates'])} missing dates which exceed the allowed missing dates value of {MAX_MISSING_DATES}. Missing: {date_list}.")

        if len(health_report['corrupted_high_low']) > 0:
            st.warning("Rows where low is higher than high: ")
            st.dataframe(health_report['corrupted_high_low'])

        if len(health_report['high_open_close']) > 0:
            st.warning("Rows where open or close is higher than high: ")
            st.dataframe(health_report['high_open_close'])

else:
    # Managing the empty state 

    left, middle, right = st.columns([1, 2, 1])

    with middle:

        st.markdown("# Quantitative risk analysis for crypto assets")
        st.markdown(
            "Pick an asset and a timeframe. Quartermaster audits the data "
            " before it charts anything, then shows what the risk actually "
            " looked like."
        )

        st.markdown(
            "1. **Select a ticker** in the sidebar\n"
            "2. **Choose your timeframe**\n"
            "3. **Run analysis**"
        )

        st.image(str(ASSETS/"sample-dashboard.png"))
        st.caption("Example: BTC-USD over the last year.")

        st.markdown("[Read the methodology](https://quartermasterlabs.com/docs)")
#--------------------------------------------------------------#

#----------------------End-of-code-----------------------------#