# data_fetcher.py
import requests
import streamlit as st

def fetch_nse_stock_watch():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        }
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            st.error(f"❌ NSE API returned status code {response.status_code}")
            st.stop()

        try:
            data = response.json()
        except Exception as e:
            st.error(f"❌ Failed to parse JSON: {e}")
            st.text(response.text)
            st.stop()

        return data

    except Exception as e:
        st.error(f"❌ Exception during NSE fetch: {e}")
        st.stop()
# data_fetcher.py
import pandas as pd
import requests
from kiteconnect import KiteConnect
from datetime import datetime
from bs4 import BeautifulSoup

def fetch_nse_sector_constituents():
    url = "https://www1.nseindia.com/live_market/dynaContent/live_watch/stock_watch/niftyStockWatch.json"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    data = response.json()

    sector_map = {}
    for item in data['data']:
        symbol = item['symbol']
        index_name = item['index']
        if index_name == "NIFTY 50":
            continue  # Ignore NIFTY 50 as a sector
        if index_name not in sector_map:
            sector_map[index_name] = []
        sector_map[index_name].append(symbol)

    return sector_map

def fetch_sector_stock_changes(api_key, access_token):
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    # Dynamically pull sector constituents from NSE
    sectors = fetch_nse_sector_constituents()

    sector_tokens = {
        "NIFTY BANK": "NSE:NIFTY_BANK",
        "NIFTY IT": "NSE:NIFTY_IT",
        "NIFTY FMCG": "NSE:NIFTY_FMCG",
        "NIFTY AUTO": "NSE:NIFTY_AUTO",
        "NIFTY METAL": "NSE:NIFTY_METAL",
        "NIFTY PHARMA": "NSE:NIFTY_PHARMA",
        "NIFTY FINANCIAL SERVICES": "NSE:NIFTY_FIN_SERVICE",
        "NIFTY ENERGY": "NSE:NIFTY_ENERGY",
    }

    symbols = [f"NSE:{sym}" for sec in sectors for sym in sectors[sec]]
    sector_indices = list(sector_tokens.values())
    all_tokens = list(set(symbols + sector_indices))

    ltp_data = kite.ltp(all_tokens)

    result = []
    for sector, stocks in sectors.items():
        sector_token = sector_tokens.get(sector)
        if not sector_token:
            continue
        sector_info = ltp_data.get(sector_token, {})
        sector_ltp = sector_info.get("last_price")
        sector_open = sector_info.get("ohlc", {}).get("open")
        if not sector_ltp or not sector_open:
            continue
        sector_change = ((sector_ltp - sector_open) / sector_open) * 100

        for stock in stocks:
            token = f"NSE:{stock}"
            data = ltp_data.get(token, {})
            ltp = data.get("last_price")
            open_price = data.get("ohlc", {}).get("open")
            if not ltp or not open_price:
                continue
            stock_change = ((ltp - open_price) / open_price) * 100

            result.append({
                "Stock": stock,
                "Sector": sector,
                "Stock % Change": round(stock_change, 2),
                "Sector % Change": round(sector_change, 2)
            })

    return pd.DataFrame(result)
