#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# importing libraries
import streamlit as st 
from pathlib import Path
#--------------------------------------------------------------#
# Imports logo from assets

ASSETS = Path(__file__).parent/"assets"
st.set_page_config(layout="wide", page_title="Quartermaster", page_icon=str(ASSETS/"favicon-32.png"))
st.logo(str(ASSETS / "logo-mark-256.png"), link="https://quartermasterlabs.com")

planner = st.Page("planner.py", title="Planner", default=True)
quant = st.Page("quant_mode.py", title="Quantitative")

st.navigation([planner, quant]).run()
#--------------------------------------------------------------#
#----------------------End-of-code-----------------------------#