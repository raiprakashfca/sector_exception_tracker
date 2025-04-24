# token_utils.py
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

def load_credentials_from_gsheet():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(
            "gcreds.json",
            scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open("ZerodhaTokenStore").sheet1

        # Read row 1 directly and log it
        data = sheet.row_values(1)
        st.write("🔍 Raw row values from Google Sheet:", data)

        if len(data) < 3:
            st.error("❌ Less than 3 items in the first row")
            return None

        api_key = data[0].strip()
        api_secret = data[1].strip()
        access_token = data[2].strip()

        if not all([api_key, api_secret, access_token]):
            st.error("❌ One or more credentials are missing.")
            return None

        return api_key, api_secret, access_token

    except Exception as e:
        st.error(f"❌ Exception in token loader: {e}")
        return None
