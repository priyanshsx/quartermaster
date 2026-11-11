#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports libraries
import streamlit as st
import pandas as pd
from datetime import timedelta
from assets import ASSET_SPECS, get_spec
from engine import (
    get_asset_date_bounds,
    fetch_asset,
    tick_inspector,
    quant_analyzer,
    align_pair,
    pair_analyzer,
    default_freq,
)
#--------------------------------------------------------------#

# Global variables 
WINDOW = {"D": 90, "W": 26}
left, mid, right = st.columns([1, 6, 1])
#--------------------------------------------------------------#

with mid:
    st.markdown("# Correlations")
    st.markdown(
        "How two assets moved together — correlation, beta, and timing."
    )

    c1, c2 = st.columns([1, 2])

    with c1:
        ui_primary = st.selectbox(
            label="Primary asset",
            options=list(ASSET_SPECS.keys()),
            format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})",
            key="correlations_primary",
        )

    primary_spec = get_spec(ui_primary)

    with c2:
        ui_compare = st.multiselect(
            label="Compare against (up to 5)",
            options=[t for t in ASSET_SPECS if t != ui_primary],
            format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})",
            max_selections=5,
        )

    if not ui_compare:
        st.info("Pick at least one asset to compare against.")
        st.stop()

    # Date bounds are the overlap across every selected asset.
    try:
        bounds = [get_asset_date_bounds(t) for t in [ui_primary] + ui_compare]
    except ValueError:
        st.warning("No history available for one of these assets.")
        st.stop()
    except Exception:
        st.warning("Couldn't reach Yahoo Finance. Please try again in a minute.")
        st.stop()

    min_date = max(b[0] for b in bounds)
    max_date = min(b[1] for b in bounds)

    if min_date >= max_date:
        st.error("These assets have no overlapping price history.")
        st.stop()

    f1, f2, f3 = st.columns(3)

    with f1:
        freq_default = "W" if any(
            default_freq(primary_spec, get_spec(t)) == "W" for t in ui_compare
        ) else "D"

        ui_freq = st.segmented_control(
            label="Return frequency",
            options=["W", "D"],
            format_func=lambda f: {"W": "Weekly", "D": "Daily"}[f],
            default=freq_default,
        )

    with f2:
        ui_start = st.date_input(
            "From", value=min_date, min_value=min_date, max_value=max_date
        )

    with f3:
        ui_end = st.date_input(
            "To", value=max_date, min_value=min_date, max_value=max_date
        )

    if freq_default == "W":
        st.caption(
            "Weekly is the default because these assets trade on different "
            "markets, which close at different times. Daily is available but "
            "understates how closely they move."
        )

    run = st.button("Run comparison", type="primary")

    if run:
        st.session_state.pop("correlations_result", None)

        frames, failed = {}, []
        for t in [ui_primary] + ui_compare:
            try:
                with st.spinner(f"Fetching {t}..."):
                    raw = fetch_asset(t, ui_start, ui_end + timedelta(days=1))
            except Exception:
                failed.append(t)
                continue

            spec = get_spec(t)
            health = tick_inspector(raw, spec)
            if not health["is_healthy"]:
                failed.append(t)
                continue

            frames[t] = quant_analyzer(raw, t, spec)

        if ui_primary in failed or len(frames) < 2:
            st.error(
                "Couldn't build a clean comparison from these assets. "
                "Try a different selection or a shorter period."
            )
            st.stop()

        window = WINDOW[ui_freq]
        pairs = {}
        for t in ui_compare:
            if t not in frames:
                continue
            aligned = align_pair(frames[ui_primary], frames[t], ui_freq)
            if len(aligned) < window:
                failed.append(t)
                continue
            pairs[t] = pair_analyzer(aligned, window)

        st.session_state["correlations_result"] = {
            "primary": ui_primary,
            "freq": ui_freq,
            "window": window,
            "pairs": pairs,
            "failed": failed,
        }

    result = st.session_state.get("correlations_result")

    if result:
        # Step 3: statement, table, rolling chart, lag table, methodology.
        st.write(result["pairs"])

        if result["failed"]:
            names = ", ".join(ASSET_SPECS[t]["display"] for t in result["failed"])
            st.warning(
                f"Left out of the comparison: {names}. Either the price "
                f"history failed its integrity checks or there weren't enough "
                f"shared trading days for the window."
            )
#--------------------------------------------------------------#
#---------------------end-of-code------------------------------#