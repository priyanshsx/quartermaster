#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports Libraries 
import streamlit as st
from paths import ASSET_DIR
from datetime import timedelta
import pandas as pd
from engine import get_asset_date_bounds, fetch_asset, tick_inspector, quant_analyzer, outcome_analyzer
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


        f = outcome_analyzer(result['enriched_data'], result['amount'])

        # entry_date = enriched_data.index[0]
        # entry_price = enriched_data['close'].iloc[0]
        # exit_date = enriched_data.index[-1]
        # exit_price = enriched_data['close'].iloc[-1]

        # final_value = amount * (exit_price / entry_price)

        # month_label = result['month'].strftime("%B %Y")
        # entry_label = entry_date.strftime("%d %b %Y")
        # exit_label = exit_date.strftime("%d %b %Y")

        st.metric(
            label=f"{ccy} {amount:,.0f} in {spec['display']}, {f['entry_date']}",
            value=f"{ccy} {f['final_value']:,.0f}",
            delta=f"{f['gain_pct']:.1%}"
        )

        st.caption(
            f"Bought at {ccy} {f['entry_price']:,.2f} on {f['entry_date']}, the first trading day of the month. Valued at {ccy} {f['exit_price']:,.2f} on the close of {f['exit_date']}, the most recent completed session. Prices are adjusted for splits and dividends."
        )

        r1c1, r1c2, r1c3 = st.columns(3)
        r2c1, r2c2, r2c3 = st.columns(3)

        with r1c1:
            if f['max_loss_pct'] < 0:
                st.metric("Max unrealized loss",
                          f"{ccy} {f['max_loss_amount']:,.0f}",
                          delta=f"{f['max_loss_pct']:.1%} on {f['max_loss_date']: %d %b %Y}",
                          delta_color="off")

            else:
                st.metric("Max unrealized loss", "None", delta="Never fell below what you paid", delta_color="off")

        with r1c2:
            st.metric("Max profit",
                      f"{ccy} {f['max_profit_amount']:,.0f}",
                      delta=f"{f['max_profit_pct']:.1%} on {f['max_profit_date']: %d %b %Y}",
                      delta_color='off')

        with r1c3:
            st.metric("Days at a loss",
                      f"{f['loss_days']:,} of {f['total_days']:,}",
                      delta=f"{f['loss_days'] / f['total_days']:.0%} of the time",
                      delta_color='off')

        with r2c1:
            st.metric("Worst day", f"{f['worst_day_pct']:.1%}",
                      delta=f"{f['worst_day_date']:%d %b %Y}",
                      delta_color='off')

        with r2c2:
            st.metric("Worst week", f"{f['worst_week_pct']:.1%}",
                      delta=f"week ending {f['worst_week_date']:%d %b %Y}", delta_color='off')

        with r2c3:
            st.metric("Worst month", f"{f['worst_month_pct']:.1%}",
                      delta=f"{f['worst_month_date']:%B %Y}",
                      delta_color='off')

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