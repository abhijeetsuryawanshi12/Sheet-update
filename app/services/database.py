import psycopg2
import pandas as pd
from app.config import settings
import json

class DatabaseClient:
    def __init__(self):
        self.conn = None
        try:
            self.conn = psycopg2.connect(settings.DATABASE_URL)
            print("✅ Successfully connected to the database.")
        except Exception as e:
            print(f"❌ Could not connect to the database: {e}")

    def get_field_value(self, company_name: str, field_name: str):
        """
        Retrieves the value of a specific field for a given company.
        
        Args:
            company_name: The name of the company
            field_name: The database column name (e.g., 'overview', 'investors')
        
        Returns:
            The field value if found, None otherwise
        """
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor() as cur:
                # Use parameterized query to prevent SQL injection
                # Note: We can't use %s for column names, so we validate the field_name
                allowed_fields = [
                    'name', 'website', 'latest_funding', 'latest_funding_date', 
                    'total_funding', 'investors', 'valuation', 'overview', 'sector',
                    'sinarmas_interest', 'implied_valuation', 'share_transfer_allowed',
                    'liquidity_ez', 'liquidity_forge', 'liquidity_nasdaq', 'summary',
                    'sellers_ask', 'buyers_bid', 'ez_total_bid_volume', 'ez_total_ask_volume',
                    'highest_bid_price', 'lowest_ask_price', 'price_history',
                    'funding_history'
                ]
                
                if field_name not in allowed_fields:
                    print(f"⚠️ Invalid field name: {field_name}")
                    return None
                
                sql = f"SELECT {field_name} FROM companies WHERE name = %s"
                cur.execute(sql, (company_name,))
                result = cur.fetchone()
                
                if result:
                    return result[0]
                return None
                
        except Exception as e:
            print(f"⚠️ Error retrieving field '{field_name}' for {company_name}: {e}")
            return None

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
            'Sellers Ask': 'sellers_ask', 'Buyers Bid': 'buyers_bid', 
            'Highest Bid Price': 'highest_bid_price', 'Lowest Ask Price': 'lowest_ask_price',
            'Price History (JSON)': 'price_history', 'Funding History (JSON)': 'funding_history',
            'EZ Total Bid Volume': 'ez_total_bid_volume', 'EZ Total Ask Volume': 'ez_total_ask_volume'
        }
        df.rename(columns=column_mapping, inplace=True)

        table_columns = list(column_mapping.values())
        df_filtered = df[[col for col in df.columns if col in table_columns]]
        
        records = df_filtered.to_dict(orient='records')

        with self.conn.cursor() as cur:
            for record in records:
                # --- JSON VALIDATION LOGIC ---
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
                # --- END OF JSON VALIDATION ---

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
                    self.conn.rollback()
            
            self.conn.commit()
            print(f"✅ Sync process finished.")

    def update_scraped_data(self, company_name: str, data: dict):
        """
        Updates a company record with scraped data using conditional logic.
        - Investors/Overview are only updated if they are currently NULL or empty.
        - Other fields are updated unconditionally.
        """
        if not self.conn: 
            return

        # Map scraped keys to DB columns
        key_to_col_map = {
            'Overview': 'overview',
            'Investors': 'investors',
            'Highest Qualified Bid': 'highest_bid_price',
            'Total Bid Volume': 'ez_total_bid_volume',
            'Total Ask Volume': 'ez_total_ask_volume',
            'Funding History': 'funding_history',
            # Additional mappings for other market activity fields
            'EquityZen Reference Price': 'ez_reference_price',

        }
        
        unconditional_data = {}
        conditional_data = {}

        for key, value in data.items():
            # Try direct mapping first
            col = key_to_col_map.get(key)
            
            # If not found, try normalized key
            if not col:
                normalized_key = key.title().replace("Qualified ", "")
                col = key_to_col_map.get(normalized_key)
            
            if col:
                if col in ['overview', 'investors']:
                    conditional_data[col] = value
                else:
                    unconditional_data[col] = value

        with self.conn.cursor() as cur:
            # 1. Unconditional updates (Market Activity, Funding)
            if unconditional_data:
                set_clause = ", ".join([f"{key} = %s" for key in unconditional_data.keys()])
                sql = f"UPDATE companies SET {set_clause} WHERE name = %s"
                try:
                    cur.execute(sql, list(unconditional_data.values()) + [company_name])
                    if cur.rowcount > 0:
                        print(f"   - DB: Updated {len(unconditional_data)} unconditional field(s) for {company_name}.")
                    else:
                        print(f"   - DB: No rows updated (company may not exist): {company_name}")
                except Exception as e:
                    print(f"   - ❌ DB Error (unconditional) for {company_name}: {e}")
                    self.conn.rollback()
            
            # 2. Conditional updates (Overview, Investors) - only if currently empty
            if conditional_data:
                for col, value in conditional_data.items():
                    sql = f"UPDATE companies SET {col} = %s WHERE name = %s AND ({col} IS NULL OR {col} = '')"
                    try:
                        cur.execute(sql, (value, company_name))
                        if cur.rowcount > 0:
                            print(f"   - DB: Updated empty '{col}' for {company_name}.")
                        else:
                            print(f"   - DB: '{col}' already has data for {company_name}, skipped.")
                    except Exception as e:
                        print(f"   - ❌ DB Error (conditional '{col}') for {company_name}: {e}")
                        self.conn.rollback()
            
            self.conn.commit()
    
    def get_all_company_names(self):
        """
        Fetches a list of all unique company names from the database.
        """
        if not self.conn:
            return []
        
        query = "SELECT DISTINCT name FROM companies WHERE name IS NOT NULL"
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                results = [item[0] for item in cursor.fetchall()]
                return results
        except Exception as e:
            print(f"❌ Error fetching company names from database: {e}")
            return []

    # --- NEW METHOD for Hiive Scraper ---
    def update_hiive_prices(self, company_name: str, highest_bid: str, lowest_ask: str):
        """
        Updates the highest bid and lowest ask prices for a specific company.
        """
        if not self.conn:
            return

        update_data = {}
        if highest_bid:
            update_data["highest_bid_price"] = highest_bid
        if lowest_ask:
            update_data["lowest_ask_price"] = lowest_ask

        if not update_data:
            print(f"   - DB: No Hiive price data provided for {company_name}.")
            return

        set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
        sql = f"UPDATE companies SET {set_clause} WHERE name = %s"
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, list(update_data.values()) + [company_name])
                if cur.rowcount > 0:
                    print(f"   - ✅ DB: Successfully updated Hiive prices for {company_name}.")
                else:
                    # This is not an error, the company might not exist in the DB.
                    print(f"   - ⚠️ DB: Company '{company_name}' not found. No update performed.")
                self.conn.commit()
        except Exception as e:
            print(f"   - ❌ DB Error updating Hiive prices for {company_name}: {e}")
            self.conn.rollback()
    # --- END NEW METHOD ---

    def close(self):
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed.")

db_client = DatabaseClient()
