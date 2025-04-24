# app.py
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from token_utils import load_credentials_from_gsheet
from data_fetcher import fetch_sector_stock_changes
from sector_logic import identify_exceptions

# Auto-refresh every 5 minutes
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

st.title("📊 Sector-Wise Exception Tracker")

# Load Zerodha API credentials
credentials = load_credentials_from_gsheet()
if not credentials:
    st.stop()
api_key, api_secret, access_token = credentials

# Fetch sector stock changes
raw_result = fetch_sector_stock_changes(api_key, access_token)
st.write("📦 Raw fetch result:", raw_result)

# Convert to DataFrame and prepare for exception detection
sector_df = pd.DataFrame(raw_result)
if not sector_df.empty:
    sector_df = sector_df.rename(columns={"symbol": "Stock", "sector": "Sector", "%change": "Stock % Change"})
    sector_avg_map = sector_df.groupby("Sector")["Stock % Change"].mean().to_dict()
    sector_df["Sector % Change"] = sector_df["Sector"].map(sector_avg_map)
    threshold = st.slider("📈 Exception Threshold (%)", min_value=0.5, max_value=5.0, step=0.5, value=2.0)
    result_df = identify_exceptions(sector_df, threshold=threshold)
    st.dataframe(result_df)
else:
    st.warning("No data received from fetch_sector_stock_changes.")
