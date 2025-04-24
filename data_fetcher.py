# data_fetcher.py
import requests
import streamlit as st

def fetch_sector_stock_changes():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/"
        }

        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)  # warm-up to get cookies
        response = session.get(url, headers=headers)

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
