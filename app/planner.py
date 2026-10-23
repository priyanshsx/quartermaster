#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports Libraries 
import streamlit as st
from paths import ASSET_DIR
import pandas as pd
from engine import get_asset_date_bounds
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