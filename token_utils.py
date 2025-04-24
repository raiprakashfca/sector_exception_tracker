# token_utils.py
import gspread
from google.oauth2.service_account import Credentials

def load_credentials_from_gsheet():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(
            "gcreds.json",  # Make sure this file is present in root directory
            scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open("ZerodhaTokenStore").sheet1

        # Read the first row without headers
        data = sheet.row_values(1)

        if len(data) < 3:
            raise ValueError("❌ Sheet does not contain enough values in the first row (expected 3)")

        api_key = data[0].strip()
        api_secret = data[1].strip()
        access_token = data[2].strip()

        if not all([api_key, api_secret, access_token]):
            raise ValueError("❌ Missing credentials in Google Sheet")

        return api_key, api_secret, access_token

    except Exception as e:
        print(f"❌ Error loading credentials from Google Sheet: {e}")
        return None
