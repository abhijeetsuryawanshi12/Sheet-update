# app/services/google_sheets.py
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from app.config import settings

class GoogleSheetsClient:
    def __init__(self):
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_PATH,
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
        except FileNotFoundError:
            print(f"Error: Credentials file not found at '{settings.GOOGLE_CREDENTIALS_PATH}'.")
            print("Please ensure you have set up your Google API credentials.")
            self.client = None
        except Exception as e:
            print(f"An error occurred during Google Sheets authentication: {e}")
            self.client = None

    def get_all_records_as_df(self) -> pd.DataFrame:
        if not self.client:
            return pd.DataFrame() # Return empty dataframe if client failed to init

        try:
            spreadsheet = self.client.open(settings.GOOGLE_SHEET_NAME)
            worksheet = spreadsheet.worksheet(settings.WORKSHEET_NAME)
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Error: Spreadsheet '{settings.GOOGLE_SHEET_NAME}' not found.")
            return pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            print(f"Error: Worksheet '{settings.WORKSHEET_NAME}' not found.")
            return pd.DataFrame()
        except Exception as e:
            print(f"An error occurred while fetching data: {e}")
            return pd.DataFrame()

# Create a single instance to be used across the app
sheets_client = GoogleSheetsClient()