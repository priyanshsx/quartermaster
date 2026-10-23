#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# importing libraries
import streamlit as st 
from pathlib import Path
from paths import ASSET_DIR
#--------------------------------------------------------------#
# Imports logo from assets

st.set_page_config(layout="wide", page_title="Quartermaster", page_icon=str(ASSET_DIR/"favicon-32.png"))
st.logo(str(ASSET_DIR / "logo-mark-256.png"), link="https://quartermasterlabs.com")

planner = st.Page("planner.py", title="Planner", default=True)
quant = st.Page("quant_mode.py", title="Quantitative Metrics")

st.navigation([planner, quant]).run()
#--------------------------------------------------------------#
#----------------------End-of-code-----------------------------#