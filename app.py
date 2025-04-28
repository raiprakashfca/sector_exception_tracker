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

# Fetch instrument list for suggestions
import gspread
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

instruments = kite.instruments("NSE")
all_symbols = sorted({inst['tradingsymbol'] for inst in instruments if inst['segment'] == 'NSE'})

# Load existing watchlist from Google Sheet
try:
    gc = gspread.service_account_from_dict(eval(st.secrets["gcreds"]))
    sh = gc.open("SectorWatchlist")
    watchlist_sheet = sh.sheet1
    existing_watchlist = watchlist_sheet.col_values(1)[1:]  # skip header
except Exception as e:
    st.error(f"❌ Failed to load watchlist: {e}")
    existing_watchlist = []

# Allow multi-select
selected_scripts = st.multiselect("🔎 Search and Add Scripts to Watchlist:", options=all_symbols, default=existing_watchlist)

# Save updated watchlist
if st.button("💾 Save Watchlist"):
    try:
        watchlist_sheet.update([['Script']] + [[script] for script in selected_scripts])
        st.success("✅ Watchlist saved successfully!")
    except Exception as e:
        st.error(f"❌ Failed to save watchlist: {e}")

selected_scripts = st.multiselect("🔎 Search and Add Scripts to Watchlist:", options=all_symbols)

# Display current watchlist
if selected_scripts:
    st.success(f"📋 Current Watchlist: {', '.join(selected_scripts)}")

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
