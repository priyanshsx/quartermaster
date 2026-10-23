#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports Libraries 
import streamlit as st
from paths import ASSET_DIR
#--------------------------------------------------------------#

# Builds the layout and adds the title 

left, mid, right = st.columns([1, 3, 1])

with mid:
    st.markdown("# What you'd have made, and what you'd have sat through")
    st.markdown(" Pick an amount, an asset and a month. You'll get a complete risk analysis of how much you'd have made and other important details.")