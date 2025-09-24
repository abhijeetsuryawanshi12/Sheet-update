# test_sheet_loading.py
import pandas as pd

# This test script assumes it's run from the project's root directory.
# It uses the exact same client and configuration as your FastAPI application.
from app.services.google_sheets import sheets_client

def run_loading_test():
    """
    Connects to Google Sheets, fetches data, and prints diagnostic information
    about specific columns to help debug loading issues.
    """
    print("--- Starting Google Sheets Data Loading Test ---")
    
    # 1. Fetch data using the application's client
    # Any authentication or connection errors will be printed by the client itself.
    print("\nStep 1: Fetching data from Google Sheets...")
    df = sheets_client.get_all_records_as_df()

    # 2. Check if the DataFrame was loaded successfully
    if df.empty:
        print("\n[FAIL] The DataFrame is empty. The test cannot proceed.")
        print("Please check the error messages above from the GoogleSheetsClient.")
        print("--- Test Finished ---")
        return

    print(f"\n[SUCCESS] DataFrame created with {df.shape[0]} rows and {df.shape[1]} columns.")
    
    # 3. Display general information about the DataFrame
    print("\nStep 2: Displaying all column names found in the sheet...")
    print("Columns:", df.columns.tolist())
    print("-" * 30)

    # 4. Perform a detailed check on the columns of interest
    print("\nStep 3: Checking specific columns of interest...")
    columns_to_check = ["Latest Funding ", "Latest Funding Date "]

    for col_name in columns_to_check:
        print(f"\n--- Checking Column: '{col_name}' ---")
        
        # Check if the column exists in the DataFrame
        if col_name in df.columns:
            print(f"[OK] Column '{col_name}' exists.")
            
            # Print the data type (dtype) of the column
            # 'object' usually means it's being treated as a string.
            print(f"   - Data Type (dtype): {df[col_name].dtype}")
            
            # Print the first 5 non-empty values to see the format
            print("   - First 5 non-empty values:")
            # .dropna() removes empty cells, .head() gets the first 5
            non_empty_values = df[col_name].dropna().head()
            if not non_empty_values.empty:
                print(non_empty_values.to_string(index=False))
            else:
                print("     (This column appears to be empty)")
        else:
            print(f"[FAIL] Column '{col_name}' was NOT FOUND in the DataFrame.")
            print("       Please check for typos or extra spaces in your Google Sheet header.")
    
    print("\n--- Test Finished ---")
    print("\nReview the output above. Pay close attention to:")
    print("1. Whether the columns were found.")
    print("2. The 'Data Type' (is it a number, a date, or just a generic 'object'/string?).")
    print("3. The actual values being loaded.")

if __name__ == "__main__":
    run_loading_test()