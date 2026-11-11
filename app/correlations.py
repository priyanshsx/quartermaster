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
    default_freq
)
#--------------------------------------------------------------#

# Global variables 
WINDOW = {"D": 90, "W": 26}
left, mid, right = st.columns([1, 6, 1])
#--------------------------------------------------------------#

with mid:
    st.markdown("# Correlations")
    st.markdown(
        "How two assets moved together - correlation, beta, and timing."
    )

    c1, c2 = st.columns([1, 2])

    # User inputs for primary and comparison assets 
    with c1:
        ui_primary = st.selectbox(
            label="Primary asset",
            options=list(ASSET_SPECS.keys()),
            format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})",
            key="correlations_primary"
        )
    primary_spec = get_spec(ui_primary)

    # Comparison assets
    with c2: 
        ui_compare = st.multiselect(
            label="Compare against (upto 5)",
            options=[t for t in ASSET_SPECS if t != ui_primary],
            format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})",
            max_selections=5
        )

    if not ui_compare:
        st.info("Pick at least one asset to compare against.")
        st.stop()

    # Date bounds 
    try:
        bounds = [get_asset_date_bounds(t) for t in [ui_primary] + ui_compare]
    except ValueError:
        st.warning("No history available for one of these assets.")
        st.stop()
    except Exception:
        st.warning("Couldn't reach Yahoo Finance. Please try again in a minute.")
        st.stop()

    min_date = max(b[0] for b in bounds)
    max_date = min(b[0] for b in bounds)

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
            default=freq_default
        )

    with f2:
        ui_start = st.date_input(
            "From", value=min_date, min_value=min_date, max_value=max_date
        )
        



#--------------------------------------------------------------#
#----------------------End-of-code-----------------------------#