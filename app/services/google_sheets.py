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
            print(f"--- FATAL ERROR ---: Credentials file not found at '{settings.GOOGLE_CREDENTIALS_PATH}'.")
            self.client = None
        except Exception as e:
            print(f"--- FATAL ERROR ---: An error occurred during Google Sheets authentication: {e}")
            self.client = None

    def get_all_records_as_df(self) -> pd.DataFrame:
        if not self.client:
            print("--- DEBUG ---: Google Sheets client is not initialized. Returning empty DataFrame.")
            return pd.DataFrame()

        try:
            print(f"--- DEBUG ---: Attempting to open Google Sheet: '{settings.GOOGLE_SHEET_NAME}'")
            spreadsheet = self.client.open(settings.GOOGLE_SHEET_NAME)
            worksheet = spreadsheet.worksheet(settings.WORKSHEET_NAME)
            records = worksheet.get_all_records()
            
            df = pd.DataFrame(records)
            # --- CRITICAL DEBUGGING STEP ---
            print(f"--- DEBUG ---: Successfully fetched data from Google Sheets.")
            print(f"--- DEBUG ---: DataFrame shape after fetching: {df.shape}")
            if df.empty:
                print("--- WARNING ---: The DataFrame is EMPTY. Check if the worksheet has data and correct headers.")
            else:
                print("--- DEBUG ---: First 5 rows of raw data:")
                print(df.head())
                print("--- DEBUG ---: Column names from sheet:", df.columns.tolist())
            # --------------------------------
            return df

        except gspread.exceptions.SpreadsheetNotFound:
            print(f"--- FATAL ERROR ---: Spreadsheet '{settings.GOOGLE_SHEET_NAME}' not found.")
            return pd.DataFrame()
        except gspread.exceptions.WorksheetNotFound:
            print(f"--- FATAL ERROR ---: Worksheet '{settings.WORKSHEET_NAME}' not found.")
            return pd.DataFrame()
        except Exception as e:
            print(f"--- FATAL ERROR ---: An error occurred while fetching data: {e}")
            return pd.DataFrame()

sheets_client = GoogleSheetsClient()