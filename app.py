# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from token_utils import load_credentials_from_gsheet
from data_fetcher import fetch_sector_stock_changes
from sector_logic import identify_exceptions

# Page configuration
st.set_page_config(page_title="📊 Sector-Wise Exception Tracker", layout="wide")

# Auto-refresh every 1 minute
st_autorefresh(interval=60 * 1000, key="auto_refresh")

# Page title and last updated time
st.title("📊 Sector-Wise Exception Tracker")
ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
st.caption(f"🕒 Last Updated (IST): {ist_now.strftime('%Y-%m-%d %H:%M:%S')}")

# Load credentials
credentials = load_credentials_from_gsheet()
if not credentials:
    st.error("❌ Failed to load Zerodha credentials.")
    st.stop()
api_key, api_secret, access_token = credentials

# Fetch data
raw_result = fetch_sector_stock_changes(api_key, access_token)

# Threshold slider
threshold = st.slider("📈 Exception Threshold (%)", min_value=0.5, max_value=5.0, step=0.5, value=2.0)

# Process data
sector_df = pd.DataFrame(raw_result)
if not sector_df.empty:
    sector_df = sector_df.rename(columns={"symbol": "Stock", "sector": "Sector", "%change": "Stock % Change"})
    sector_avg_map = sector_df.groupby("Sector")["Stock % Change"].mean().to_dict()
    sector_df["Sector % Change"] = sector_df["Sector"].map(sector_avg_map)

    result_df = identify_exceptions(sector_df, threshold=threshold)

    st.subheader("📋 Sector Divergence Summary")
    st.dataframe(result_df.style.format({"Stock % Change": "{:.2f}", "Sector % Change": "{:.2f}"}))
else:
    st.info("✅ Market data fetched but no exceptions identified at the current threshold.")
