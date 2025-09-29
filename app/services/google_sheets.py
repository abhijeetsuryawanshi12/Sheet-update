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
        if not self.client:
            print("--- ERROR ---: Google Sheets client not initialized. Cannot update data.")
            return False

        try:
            # print(f"--- INFO ---: Opening Google Sheet '{settings.GOOGLE_SHEET_NAME}' to update data for '{company_name}'.")
            spreadsheet = self.client.open(settings.GOOGLE_SHEET_NAME)
            worksheet = spreadsheet.worksheet(settings.WORKSHEET_NAME)

            key_mapping = {
                # Hiive Fields
                "Highest Bid": "Highest Bid Price", "Lowest Ask": "Lowest Ask Price",
                "Hiive Price": "Hiive Price", "Implied Valuation": "Implied Valuation",
                "Total Bids": "Total Bids", "Total Asks": "Total Asks",
                "Sellers Ask": "Sellers Ask", "Buyers Bid": "Buyers Bid",
                # EquityZen Fields
                "Total Bid Volume": "EZ Total Bid Volume", "Total Ask Volume": "EZ Total Ask Volume",
                # EquityZen Funding Table
                "Funding History": "Funding History (JSON)",
            }
            
            row_data = {"Company": company_name}
            for scraped_key, value in data.items():
                normalized_key = scraped_key.title()
                if normalized_key in key_mapping:
                    sheet_header = key_mapping[normalized_key]
                    row_data[sheet_header] = value

            # print(f"--- DEBUG ---: Prepared data for sheet: {row_data}")
            
            headers = worksheet.row_values(1)
            if not headers:
                print("--- INFO ---: Worksheet is empty. Creating headers from scratch.")
                headers = list(row_data.keys())
                worksheet.update('A1', [headers], value_input_option='USER_ENTERED')
            else:
                new_headers_to_add = [h for h in row_data.keys() if h not in headers]
                if new_headers_to_add:
                    print(f"--- INFO ---: Adding new columns to the sheet: {new_headers_to_add}")
                    start_col_index = len(headers) + 1
                    header_update_cells = []
                    for i, header_name in enumerate(new_headers_to_add):
                        header_update_cells.append(gspread.Cell(row=1, col=start_col_index + i, value=header_name))
                    
                    if header_update_cells:
                        worksheet.update_cells(header_update_cells, value_input_option='USER_ENTERED')
                        # print(f"--- SUCCESS ---: Added {len(new_headers_to_add)} new columns.")
                        headers = worksheet.row_values(1)

            try:
                cell = worksheet.find(company_name, in_column=1)
            except gspread.exceptions.CellNotFound:
                cell = None

            if cell:
                # print(f"--- INFO ---: Found '{company_name}' at row {cell.row}. Preparing update.")
                update_cells_list = []
                for header, value in row_data.items():
                    if header != "Company" and header in headers:
                        col_index = headers.index(header) + 1
                        update_cells_list.append(gspread.Cell(cell.row, col_index, str(value)))
                
                if update_cells_list:
                    worksheet.update_cells(update_cells_list, value_input_option='USER_ENTERED')
                    print(f"--- SUCCESS ---: Successfully updated {len(update_cells_list)} cells for '{company_name}'.")
                else:
                    print(f"--- INFO ---: No new data to update for '{company_name}'.")
                return True
            else:
                # This logic is less likely to be hit now, but is good for new companies
                print(f"--- INFO ---: Company '{company_name}' not found. Appending a new row.")
                new_row = [row_data.get(header, "") for header in headers]
                worksheet.append_row(new_row, value_input_option='USER_ENTERED')
                print(f"--- SUCCESS ---: Successfully added a new row for '{company_name}'.")
                return True

        except Exception as e:
            print(f"--- FATAL ERROR ---: An error occurred while updating the sheet for '{company_name}': {e}")
            traceback.print_exc()
            return False

sheets_client = GoogleSheetsClient()