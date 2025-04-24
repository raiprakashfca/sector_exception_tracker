# data_fetcher.py
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime

def fetch_sector_stock_changes(api_key, access_token):
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    # Define sectors and their constituents (basic example, can be fetched from NSE later)
    sectors = {
        "NIFTY BANK": ["AXISBANK", "HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN"],
        "NIFTY IT": ["TCS", "INFY", "WIPRO", "TECHM", "LTIM"]
    }

    symbols = [f"NSE:{sym}" for sec in sectors for sym in sectors[sec]]
    sector_indices = ["NSE:NIFTY_BANK", "NSE:NIFTY_IT"]
    all_tokens = sector_indices + symbols

    # Get LTP
    ltp_data = kite.ltp(all_tokens)

    # Extract opening price and last traded price (using ltp call)
    result = []
    for sector, stocks in sectors.items():
        sector_token = f"NSE:{sector.split()[-1]}"  # e.g., NIFTY_BANK
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
