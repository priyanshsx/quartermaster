#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports Libraries 
import streamlit as st
from paths import ASSET_DIR
from datetime import timedelta
import pandas as pd
from engine import get_asset_date_bounds, fetch_asset, tick_inspector, quant_analyzer
from assets import ASSET_SPECS, get_spec
#--------------------------------------------------------------#

# Builds the layout and adds the title 
left, mid, right = st.columns([1, 3, 1])

with mid:
    st.markdown("# What you'd have made, and what you'd have sat through")
    st.markdown(" Pick an amount, an asset and a month. You'll get a complete risk analysis of how much you'd have made and other important details.")
#--------------------------------------------------------------#

# Defines the three input columns 
c1, c2, c3 = st.columns(3)

with c2:
    ui_ticker = st.selectbox(label="Asset",
                             options=list(ASSET_SPECS.keys()),
                             format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})"
                             )

# Defines the month and year for user selection
# the month selection here assumes the first trading day of the chosen month 
try:
    min_date, max_date = get_asset_date_bounds(ui_ticker)
except ValueError:
    st.warning("No history is available for this asset. Please try another.")
    months = []
except Exception:
    st.warning("Couldn't reach Yahoo Finance. Please try again in a minute.")
    months = []
else:
    months = pd.date_range(min_date, max_date, freq="MS")[::-1]

spec = get_spec(ui_ticker)

with c1: 
    amount = st.number_input(f"Amount ({spec['currency']})",
                             value=10000,
                             min_value=1000,
                             step=1000,
                             format="%d")

with c3:
    ui_month = st.selectbox("Month/Year", options=months,
                            format_func=lambda d: d.strftime("%B %Y"))

_, b, _ = st.columns([1, 1, 1])

with b:
    run = st.button("Run Analysis", type="primary", width="stretch")

if run:
    st.session_state.pop("planner_result", None)

    if ui_month is None:
        st.error("No months available for this asset. Please try another.")
        st.stop()

    try:
        with st.spinner(f"Fetching {ui_ticker}..."):
            raw = fetch_asset(ui_ticker, ui_month, max_date + timedelta(days=1))
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception:
        st.error("Couldn't reach Yahoo Finance. Please try again in a minute.")
        st.stop()

    health_report = tick_inspector(raw, spec)
    enriched_data = quant_analyzer(raw, ui_ticker, spec) if health_report["is_healthy"] else None

    st.session_state['planner_result'] = {
        "ticker": ui_ticker, 
        "amount": amount,
        "month": ui_month, 
        "health_report": health_report, 
        "enriched_data": enriched_data
    }

    result = st.session_state.get('planner_result')

    if result:
        health_report = result['health_report']

        if health_report['is_healthy']:
            enriched_data = result['enriched_data']
            amount = result['amount']
            spec = get_spec(result['ticker'])
            ccy = spec["currency"]

            entry_date = enriched_data.index[0]
            entry_price = enriched_data['close'].iloc[0]
            exit_date = enriched_data.index[-1]
            exit_price = enriched_data['close'].iloc[-1]

            final_value = amount * (exit_price / entry_price)

            month_label = result['month'].strftime("%B %Y")
            entry_label = entry_date.strftime("%d %b %Y")
            exit_label = exit_date.strftime("%d %b %Y")

            st.metric(
                label=f"{ccy} {amount:,.0f} in {spec['display']}, {month_label}",
                value=f"{ccy} {final_value:,.0f}"
            )

            st.caption(
                f"Bought at {ccy} {entry_price:,.2f} on {entry_label}, the first trading day of the month. Valued at {ccy} {exit_price:,.2f} on {exit_label}. Prices are adjusted for splits and dividends."
            )

            excess = health_report['excess_days']
            if excess > 0:
                st.warning(
                    f"{excess} day(s) of price history are missing beyond what's normal for this market. The figures still ran, but treat them as approximate."
                )
            else:
                st.error(
                    "The price history for this asset didn't pass its integrity checks, so nothing was calculated. Try a different asset or a later start month."
                )

#--------------------------------------------------------------#
#---------------------end-of-code------------------------------#