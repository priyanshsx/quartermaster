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
    st.markdown("# Check your asset's historical performance")
    st.markdown(" Check how much you made, how your asset performed, your worst and best days.")
#--------------------------------------------------------------#

    # Defines the three input columns 
    c1, c2, c3 = st.columns(3)

    with c2:
        ui_ticker = st.selectbox(label="In asset",
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
        amount = st.number_input(f"If I had invested ({spec['currency']})",
                                value=10000,
                                min_value=1000,
                                step=1000,
                                format="%d")

    with c3:
        ui_month = st.selectbox("In Month/Year", options=months,
                                format_func=lambda d: d.strftime("%B %Y"))

    _, b, _ = st.columns([1, 1, 1])

    with b:
        run = st.button("Check My Asset's Performance", type="primary", width="stretch")

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

            month_label = result['month'].strftime("%B %Y")
            entry_label = f['entry_date'].strftime("%d %b %Y")
            exit_label = f['exit_date'].strftime("%d %b %Y")

            st.metric(
                label="Worth today",
                value=f"{ccy} {f['final_value']:,.0f}",
                delta=f"{f['gain_pct']:.1%}"
            )

            if f["max_loss_pct"] < 0:
                st.markdown(
                    f"Your **{ccy} {amount:,.0f}** would be worth **{ccy} {f['final_value']:,.0f}** today. "
                    f"Along the way it reached **{ccy} {f['high_value']:,.0f}**, "
                    f"and fell as low as **{ccy} {f['low_value']:,.0f}**."
                )
            else:
                st.markdown(
                    f"Your **{ccy} {amount:,.0f}** would be worth **{ccy} {f['final_value']:,.0f}** today. "
                    f"It reached **{ccy} {f['high_value']:,.0f}** along the way, "
                    f"and never fell below what you put in."
                )

            r1c1, r1c2, r1c3 = st.columns(3)
            

            with r1c1:
                if f["max_loss_pct"] < 0:
                    st.metric("The worst it got", f"{ccy} {f['low_value']:,.0f}",
                            help="The least your investment was ever worth. You'd have to hold through this.")
                    st.caption(f"Down {abs(f['max_loss_pct']):.1%} on {f['max_loss_date']:%d %b %Y}")
                else:
                    st.metric("The worst it got", f"{ccy} {f['low_value']:,.0f}",
                            help="The least your investment was ever worth. You'd have to hold through this.")
                    st.caption("Never fell below what you put in")

            with r1c2:
                st.metric("The best it got", f"{ccy} {f['high_value']:,.0f}",
                        help="The most it was ever worth. You'd only have got this by selling on that exact day.")
                st.caption(f"Up {f['max_profit_pct']:.1%} on {f['max_profit_date']:%d %b %Y}")

            with r1c3:
                st.metric("Time spent underwater", f"{f['loss_days']:,} of {f['total_days']:,} days",
                        help="Days when it was worth less than what you put in.")
                st.caption(f"{f['loss_days'] / f['total_days']:.0%} of the time")

            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

            r2c1, r2c2, r2c3 = st.columns(3)

            with st.expander("How this is calculated"):
                st.markdown(
                    f"- Bought at the close of **{f['entry_date']:%d %b %Y}**, the first trading "
                    f"day of {month_label}.\n"
                    f"- Valued at the close of **{f['exit_date']:%d %b %Y}**. The current session "
                    f"is excluded because it hasn't finished.\n"
                    f"- Prices are adjusted for splits and dividends, so this is a total return.\n"
                    f"- Figures are in {ccy}, the currency the asset trades in."
                )

            with r2c1:
                st.metric("Worst single day", f"-{ccy} {abs(f['worst_day_amount']):,.0f}",
                        help="The largest one-day fall in value.")
                st.caption(f"{f['worst_day_date']:%d %b %Y}, down {abs(f['worst_day_pct']):.1%}")

            with r2c2:
                st.metric("Worst week", f"-{ccy} {abs(f['worst_week_amount']):,.0f}",
                        help="The largest fall across a single week.")
                st.caption(f"Week ending {f['worst_week_date']:%d %b %Y}, down {abs(f['worst_week_pct']):.1%}")

            with r2c3:
                st.metric("Worst month", f"-{ccy} {abs(f['worst_month_amount']):,.0f}",
                        help="The largest fall across a single calendar month.")
                st.caption(f"{f['worst_month_date']:%B %Y}, down {abs(f['worst_month_pct']):.1%}")

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