# app/services/database.py
import psycopg2
import pandas as pd
from app.config import settings
import json # Import the json library

class DatabaseClient:
    def __init__(self):
        self.conn = None
        try:
            self.conn = psycopg2.connect(settings.DATABASE_URL)
            print("✅ Successfully connected to the database.")
        except Exception as e:
            print(f"❌ Could not connect to the database: {e}")

    def sync_sheet_data(self, df: pd.DataFrame):
        """
        Synchronizes a DataFrame from Google Sheets into the 'companies' table.
        It uses an UPSERT operation: inserts new companies and updates existing ones.
        It also validates data for JSONB columns before syncing.
        """
        if not self.conn:
            return
        
        column_mapping = {
            'Company': 'name', 'Website': 'website', 'Latest Funding ': 'latest_funding',
            'Latest Funding Date ': 'latest_funding_date', 'Total Funding': 'total_funding',
            'Investors': 'investors', 'Valuation': 'valuation', 'Overview (Product, Model & Moat)': 'overview',
            'Sector': 'sector', 'Sinarmas Interest': 'sinarmas_interest', 'Implied Valuation': 'implied_valuation',
            'Share transfer allowed ?': 'share_transfer_allowed', 'Liquidity EZ': 'liquidity_ez',
            'Liquidity Forge': 'liquidity_forge', 'Liquidity Nasdaq': 'liquidity_nasdaq', 'Summary': 'summary',
            'Sellers Ask': 'sellers_ask', 'Buyers Bid': 'buyers_bid', 'Total Bids': 'total_bids',
            'Total Asks': 'total_asks', 'Highest Bid Price': 'highest_bid_price', 'Lowest Ask Price': 'lowest_ask_price',
            'Price History (JSON)': 'price_history', 'Funding History (JSON)': 'funding_history', 'Hiive Price': 'hiive_price',
            'EZ Total Bid Volume': 'ez_total_bid_volume', 'EZ Total Ask Volume': 'ez_total_ask_volume'
        }
        df.rename(columns=column_mapping, inplace=True)

        table_columns = list(column_mapping.values())
        df_filtered = df[[col for col in df.columns if col in table_columns]]
        
        records = df_filtered.to_dict(orient='records')

        with self.conn.cursor() as cur:
            for record in records:
                # --- NEW JSON VALIDATION LOGIC ---
                json_columns = ['price_history', 'funding_history']
                for col in json_columns:
                    if col in record:
                        value = record[col]
                        # Check if it's a string-like value before trying to parse
                        if isinstance(value, str) and value.strip():
                            try:
                                # Test if it's valid JSON. If not, this will raise an error.
                                json.loads(value)
                            except (json.JSONDecodeError, TypeError):
                                # If it's not valid JSON, set it to None to store as NULL
                                print(f"Warning: Invalid JSON for {record.get('name')} in column '{col}'. Setting to NULL.")
                                record[col] = None
                        else:
                            # If it's empty, NaN, or None, set it to None for the DB
                            record[col] = None
                # --- END OF NEW LOGIC ---

                # Prepare for UPSERT
                record = {k: v for k, v in record.items() if pd.notna(v)} # Remove any remaining NaN values
                
                if 'name' not in record or not record['name']:
                    print("Skipping record with no name.")
                    continue

                cols = ', '.join(record.keys())
                placeholders = ', '.join(['%s'] * len(record))
                update_placeholders = ', '.join([f"{col} = EXCLUDED.{col}" for col in record.keys() if col != 'name'])

                upsert_sql = f"""
                INSERT INTO companies ({cols}) VALUES ({placeholders})
                ON CONFLICT (name) DO UPDATE SET {update_placeholders};
                """
                
                try:
                    cur.execute(upsert_sql, list(record.values()))
                except Exception as e:
                    print(f"Error on record '{record.get('name')}': {e}. Rolling back this record.")
                    self.conn.rollback() # Rollback the single failed command
                    # In a simple script, we might have to restart the transaction or handle it.
                    # For now, we'll just report the error and continue. The main issue is the JSON validation.
            
            self.conn.commit()
            print(f"✅ Sync process finished.")


    def update_scraped_data(self, company_name: str, data: dict):
        """
        Updates a company record with scraped data using conditional logic.
        - Investors/Overview are only updated if they are currently NULL or empty.
        - Other fields are updated unconditionally.
        """
        if not self.conn: return

        # Map scraped keys to DB columns
        key_to_col_map = {
            'Overview': 'overview', 'Investors': 'investors',
            'Highest Qualified Bid': 'highest_bid_price', 'Total Bid Volume': 'ez_total_bid_volume',
            'Total Ask Volume': 'ez_total_ask_volume', 'Funding History': 'funding_history'
        }
        
        unconditional_data = {}
        conditional_data = {}

        for key, value in data.items():
            col = key_to_col_map.get(key.title().replace("Qualified ", "")) # Normalize key
            if col in ['overview', 'investors']:
                conditional_data[col] = value
            elif col:
                unconditional_data[col] = value

        with self.conn.cursor() as cur:
            # 1. Unconditional updates (Market Activity, Funding)
            if unconditional_data:
                set_clause = ", ".join([f"{key} = %s" for key in unconditional_data.keys()])
                sql = f"UPDATE companies SET {set_clause} WHERE name = %s"
                try:
                    cur.execute(sql, list(unconditional_data.values()) + [company_name])
                    print(f"   - DB: Updated unconditional data for {company_name}.")
                except Exception as e:
                    print(f"   - ❌ DB Error (unconditional) for {company_name}: {e}")
                    self.conn.rollback()
            
            # 2. Conditional updates (Overview, Investors)
            if conditional_data:
                for col, value in conditional_data.items():
                    sql = f"UPDATE companies SET {col} = %s WHERE name = %s AND ({col} IS NULL OR {col} = '')"
                    try:
                        cur.execute(sql, (value, company_name))
                        if cur.rowcount > 0:
                            print(f"   - DB: Updated empty '{col}' for {company_name}.")
                    except Exception as e:
                        print(f"   - ❌ DB Error (conditional) for {company_name}: {e}")
                        self.conn.rollback()
            
            self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

db_client = DatabaseClient()