# logger.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

def log_exceptions_to_sheet(df):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(
            "gcreds.json",  # Ensure this file is present in your working directory
            scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open("SectorExceptionLog").sheet1

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        for _, row in df.iterrows():
            sheet.append_row([
                date_str,
                time_str,
                row['Stock'],
                row['Sector'],
                row['Stock % Change'],
                row['Sector % Change']
            ])
    except Exception as e:
        print(f"Logging to Google Sheet failed: {e}")
