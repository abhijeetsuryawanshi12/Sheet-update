# app/services/google_sheets.py
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from app.config import settings
import traceback

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
    
    def get_company_list(self) -> list[str]:
        """
        Fetches a clean list of company names from the 'Company' column in the Google Sheet.

        Returns:
            A list of company names as strings. Returns an empty list on failure.
        """
        print("--- INFO ---: Fetching company list from Google Sheet...")
        df = self.get_all_records_as_df()
        if df.empty or 'Company' not in df.columns:
            print("--- WARNING ---: DataFrame is empty or 'Company' column not found.")
            return []
        
        # Drop any rows where the company name is missing, and get a unique list
        companies = df['Company'].dropna().unique().tolist()
        # Filter out any potential empty strings that might have slipped through
        companies = [name for name in companies if name]

        print(f"--- INFO ---: Found {len(companies)} companies to process.")
        return companies

    def get_all_records_as_df(self) -> pd.DataFrame:
        if not self.client:
            print("--- DEBUG ---: Google Sheets client is not initialized. Returning empty DataFrame.")
            return pd.DataFrame()

        try:
            # print(f"--- DEBUG ---: Attempting to open Google Sheet: '{settings.GOOGLE_SHEET_NAME}'")
            spreadsheet = self.client.open(settings.GOOGLE_SHEET_NAME)
            worksheet = spreadsheet.worksheet(settings.WORKSHEET_NAME)
            records = worksheet.get_all_records()
            
            df = pd.DataFrame(records)
            # print(f"--- DEBUG ---: Successfully fetched data from Google Sheets.")
            # print(f"--- DEBUG ---: DataFrame shape after fetching: {df.shape}")
            if df.empty:
                print("--- WARNING ---: The DataFrame is EMPTY. Check if the worksheet has data and correct headers.")
            # else:
                # print("--- DEBUG ---: First 5 rows of raw data:")
                # print(df.head())
                # print("--- DEBUG ---: Column names from sheet:", df.columns.tolist())
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

    def update_or_add_company_data(self, company_name: str, data: dict) -> bool:
        if not self.client: return False
        try:
            spreadsheet = self.client.open(settings.GOOGLE_SHEET_NAME)
            worksheet = spreadsheet.worksheet(settings.WORKSHEET_NAME)

            key_mapping = {
                'Investors': 'Investors', 'Overview': 'Overview',
                'Highest Qualified Bid': 'Highest Bid Price', 'Total Bid Volume': 'EZ Total Bid Volume',
                'Total Ask Volume': 'EZ Total Ask Volume', 'Funding History': 'Funding History (JSON)'
            }
            
            row_data = {"Company": company_name}
            for scraped_key, value in data.items():
                # Normalize key by removing "Qualified " and title-casing
                normalized_key = scraped_key.title().replace("Qualified ", "")
                if normalized_key in key_mapping:
                    sheet_header = key_mapping[normalized_key]
                    row_data[sheet_header] = value

            headers = worksheet.row_values(1)
            if not headers: # Handle empty sheet
                headers = list(row_data.keys())
                worksheet.update('A1', [headers])

            # Logic for conditional updates
            try:
                cell = worksheet.find(company_name, in_column=1)
                existing_row_values = worksheet.row_values(cell.row)
                existing_row_dict = dict(zip(headers, existing_row_values))

                # Check Investors: if sheet has data, remove from update
                if existing_row_dict.get('Investors', '').strip() and 'Investors' in row_data:
                    del row_data['Investors']
                
                # Check Overview: if sheet has data, remove from update
                if existing_row_dict.get('Overview', '').strip() and 'Overview' in row_data:
                    del row_data['Overview']

                # Now `row_data` only contains fields that should be updated
                update_cells_list = []
                for header, value in row_data.items():
                    if header in headers and header != "Company":
                        col_index = headers.index(header) + 1
                        update_cells_list.append(gspread.Cell(cell.row, col_index, str(value)))
                
                if update_cells_list:
                    worksheet.update_cells(update_cells_list, value_input_option='USER_ENTERED')
                    print(f"   - Sheet: Updated {len(update_cells_list)} cells for {company_name}.")
                
                return True

            except gspread.exceptions.CellNotFound:
                # Company not found, so append a new row with all data
                print(f"   - Sheet: Company '{company_name}' not found. Appending new row.")
                new_row = [row_data.get(header, "") for header in headers]
                worksheet.append_row(new_row, value_input_option='USER_ENTERED')
                return True

        except Exception as e:
            print(f"--- FATAL ERROR ---: Sheet update failed for '{company_name}': {e}")
            traceback.print_exc()
            return False

sheets_client = GoogleSheetsClient()