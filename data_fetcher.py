# data_fetcher.py
import streamlit as st
from kiteconnect import KiteConnect
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SECTOR_MAP = {
    "RELIANCE": "ENERGY",
    "ONGC": "ENERGY",
    "COALINDIA": "ENERGY",
    "HDFCBANK": "FINANCIAL SERVICES",
    "ICICIBANK": "FINANCIAL SERVICES",
    "KOTAKBANK": "FINANCIAL SERVICES",
    "SBIN": "FINANCIAL SERVICES",
    "AXISBANK": "FINANCIAL SERVICES",
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "LTIM": "IT",
    "ULTRACEMCO": "CEMENT & CONSTRUCTION",
    "GRASIM": "CEMENT & CONSTRUCTION",
    "SHREECEM": "CEMENT & CONSTRUCTION",
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "BRITANNIA": "FMCG",
    "NESTLEIND": "FMCG",
    "TITAN": "CONSUMER GOODS",
    "BAJFINANCE": "FINANCIAL SERVICES",
    "ASIANPAINT": "CONSUMER GOODS",
    "EICHERMOT": "AUTO",
    "M&M": "AUTO",
    "HEROMOTOCO": "AUTO",
    "TATAMOTORS": "AUTO",
    "MARUTI": "AUTO",
    "DRREDDY": "PHARMA",
    "CIPLA": "PHARMA",
    "SUNPHARMA": "PHARMA",
    "DIVISLAB": "PHARMA",
    "ADANIENT": "INDUSTRIALS",
    "ADANIPORTS": "INDUSTRIALS",
    "TATASTEEL": "METALS",
    "JSWSTEEL": "METALS",
    "HINDALCO": "METALS",
    "BPCL": "ENERGY",
    "NTPC": "ENERGY",
    "POWERGRID": "ENERGY",
    "UPL": "CHEMICALS",
    "HCLTECH": "IT",
    "LT": "CONSTRUCTION",
    "BAJAJFINSV": "FINANCIAL SERVICES",
    "SBILIFE": "INSURANCE",
    "HDFCLIFE": "INSURANCE",
    "ICICIPRULI": "INSURANCE",
    "INDUSINDBK": "FINANCIAL SERVICES",
    "APOLLOHOSP": "HEALTHCARE",
    "BAJAJ-AUTO": "AUTO"
}

def log_to_google_sheet(rows):
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcreds"], scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        sheet = client.open("SectorExceptionLog").sheet1
        for row in rows:
            sheet.append_row(row)
    except Exception as e:
        st.error(f"❌ Failed to log to Google Sheet: {e}")

def fetch_sector_stock_changes(api_key, access_token):
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        instruments = list(SECTOR_MAP.keys())
        ltp_input = [f"NSE:{symbol}" for symbol in instruments]
        st.write("📤 Instruments sent to kite.ltp():", ltp_input)
        ltp_data = kite.ltp(ltp_input)

        result = []
        sector_averages = {}
        sector_counts = {}

        # Aggregate sector % changes
        for symbol in instruments:
            try:
                ltp_info = ltp_data[f"NSE:{symbol}"]
                last_price = ltp_info['last_price']
                prev_close = ltp_info['ohlc']['close']
                change_pct = (last_price - prev_close) / prev_close * 100
                sector = SECTOR_MAP[symbol]

                result.append({
                    "symbol": symbol,
                    "sector": sector,
                    "last_price": last_price,
                    "%change": round(change_pct, 2)
                })

                if sector not in sector_averages:
                    sector_averages[sector] = 0
                    sector_counts[sector] = 0

                sector_averages[sector] += change_pct
                sector_counts[sector] += 1

            except Exception as e:
                st.warning(f"⚠️ Could not fetch LTP for {symbol}: {e}")

        # Calculate sector averages
        for sector in sector_averages:
            sector_averages[sector] /= sector_counts[sector]

        # Identify exceptions and log
        exceptions = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for stock in result:
            sector_avg = sector_averages[stock["sector"]]
            diff = stock["%change"] - sector_avg
            if abs(diff) >= 2:  # configurable threshold
                exceptions.append([
                    now.split()[0], now.split()[1],
                    stock["symbol"], stock["sector"],
                    stock["%change"], round(sector_avg, 2)
                ])

        if exceptions:
            log_to_google_sheet(exceptions)

        if not result:
            st.warning("⚠️ No valid LTP data fetched. The result list is empty.")

        return result

    except Exception as e:
        st.error(f"❌ Error fetching sector stock changes: {e}")
        st.stop()
