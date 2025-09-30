# sync_sheet_to_db.py
from app.services.google_sheets import GoogleSheetsClient
from app.services.database import DatabaseClient

def main():
    """
    This script performs a one-way sync from the Google Sheet to the Postgres database.
    It reads all records from the sheet and uses an UPSERT command to either
    insert new companies or update existing ones in the database.
    """
    print("Starting sync from Google Sheet to Database...")
    
    # 1. Initialize clients
    sheets_client = GoogleSheetsClient()
    db_client = DatabaseClient()

    # 2. Fetch data from Google Sheets
    company_df = sheets_client.get_all_records_as_df()

    if company_df.empty:
        print("No data found in Google Sheet. Exiting.")
        return

    # 3. Sync data to the database
    db_client.sync_sheet_data(company_df)

    # 4. Close the database connection
    db_client.close()
    
    print("Sync complete.")

if __name__ == "__main__":
    main()