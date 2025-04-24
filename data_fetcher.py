# data_fetcher.py
import streamlit as st
from kiteconnect import KiteConnect

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

def fetch_sector_stock_changes(api_key, access_token):
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        instruments = list(SECTOR_MAP.keys())
        ltp_data = kite.ltp([f"NSE:{symbol}" for symbol in instruments])

        result = []
        for symbol in instruments:
            try:
                ltp_info = ltp_data[f"NSE:{symbol}"]
                last_price = ltp_info['last_price']
                change_pct = ltp_info['net_change'] / (last_price - ltp_info['net_change']) * 100
                result.append({
                    "symbol": symbol,
                    "sector": SECTOR_MAP[symbol],
                    "last_price": last_price,
                    "%change": round(change_pct, 2)
                })
            except Exception as e:
                st.warning(f"⚠️ Could not fetch LTP for {symbol}: {e}")

        return result

    except Exception as e:
        st.error(f"❌ Error fetching sector stock changes: {e}")
        st.stop()
