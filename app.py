import streamlit as st
import pandas as pd
import time
from datetime import datetime

from token_utils import load_credentials_from_gsheet
from data_fetcher import fetch_sector_stock_changes
from sector_logic import identify_exceptions
from logger import log_exceptions_to_sheet

st.set_page_config(page_title="📊 Sector Exception Tracker", layout="wide")

st.title("📊 Sector-Wise Exception Tracker")

# Adjustable threshold
threshold = st.slider("Set Divergence Threshold (%)", min_value=0.1, max_value=3.0, value=1.0, step=0.1)

# Load Zerodha credentials
token_data = load_credentials_from_gsheet()

if not token_data:
    st.error("❌ Failed to load Zerodha credentials from Google Sheet.")
    st.stop()

api_key, api_secret, access_token = token_data

with st.spinner("Fetching live market data..."):
    try:
        sector_df = fetch_sector_stock_changes(api_key, access_token)
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")
        st.stop()

# Apply logic to find exceptions
result_df = identify_exceptions(sector_df, threshold=threshold)

# Display exceptions only
exception_df = result_df[result_df['Exception'] == True]

if exception_df.empty:
    st.success("✅ No sector-wise exceptions found as per current threshold.")
else:
    st.subheader("🔍 Exceptions Detected")
    st.dataframe(exception_df, use_container_width=True)
    log_exceptions_to_sheet(exception_df)

# Auto-refresh every 5 minutes
st.caption("⏱️ This dashboard auto-refreshes every 5 minutes.")
st.experimental_rerun() if int(time.time()) % 300 < 5 else None
