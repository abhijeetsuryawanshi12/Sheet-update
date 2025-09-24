import pandas as pd
import numpy as np
import re  # Import the regex module
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any

from app.services.google_sheets import sheets_client

class SearchService:
    def __init__(self):
        self.df: pd.DataFrame = pd.DataFrame()
        self.embeddings: np.ndarray = np.array([])
        # Use a pre-trained model optimized for semantic search
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._load_and_process_data()

    def _load_and_process_data(self):
        print("Loading and processing data from Google Sheets...")
        self.df = sheets_client.get_all_records_as_df()
        
        if self.df.empty:
            print("Warning: Dataframe is empty. Search will not work.")
            return

        self.df.rename(columns={
            # Existing columns
            "Company": "name",
            "Website": "website",
            "Latest Funding": "latest_funding",
            "Latest Funding Date": "latest_funding_date",
            "Total Funding": "total_funding",
            "Investors": "investors",
            "Valuation": "valuation",
            "Overview (Product, Model & Moat)": "overview",
            "Sector": "sector",
            "Sinarmas Interest": "sinarmas_interest",
            "Implied Valuation": "implied_valuation",
            "Share transfer allowed?": "share_transfer_allowed",
            "Liquidity EZ": "liquidity_ez",
            "Liquidity Forge": "liquidity_forge",
            "Liquidity Nasdaq": "liquidity_nasdaq",
            
            # --- New Columns (guessed names from Google Sheet) ---
            "Summary": "summary",
            "Sellers Ask": "sellers_ask",
            "Buyers Bid": "buyers_bid",
            "Total Bids": "total_bids",
            "Total Asks": "total_asks",
            "Highest Bid Price": "highest_bid_price",
            "Lowest Ask Price": "lowest_ask_price",
            "Price History (JSON)": "price_history",
            "Funding History (JSON)": "funding_history",

        }, inplace=True)

        # Fallback: Use 'overview' for 'summary' if a 'Summary' column doesn't exist
        if 'summary' not in self.df.columns and 'overview' in self.df.columns:
            self.df['summary'] = self.df['overview']

        expected_cols = [
            'name', 'website', 'latest_funding', 'latest_funding_date', 'total_funding',
            'investors', 'valuation', 'overview', 'sector', 'sinarmas_interest',
            'implied_valuation', 'share_transfer_allowed', 'liquidity_ez',
            'liquidity_forge', 'liquidity_nasdaq',
            # New expected columns
            'summary', 'sellers_ask', 'buyers_bid', 'total_bids', 'total_asks',
            'highest_bid_price', 'lowest_ask_price', 'price_history', 'funding_history'
        ]

        for col in expected_cols:
            if col not in self.df.columns:
                print(f"Warning: Column for '{col}' not found after renaming. Creating it as an empty column.")
                self.df[col] = ''
        
        self.df['search_text'] = (
            self.df['name'].fillna('').astype(str) + ". Sector: " + 
            self.df['sector'].fillna('').astype(str) + ". Website: " + 
            self.df['website'].fillna('').astype(str) + ". Investors: " + 
            self.df['investors'].fillna('').astype(str) + ". Latest Funding: " +
            self.df['latest_funding'].fillna('').astype(str) + ". Total Funding: " +
            self.df['total_funding'].fillna('').astype(str) + ". Overview: " +
            self.df['overview'].fillna('').astype(str)
        )

        print("Creating vector embeddings for the data...")
        self.embeddings = self.model.encode(self.df['search_text'].astype(str).tolist(), show_progress_bar=True)
        print("Data loaded and processed successfully.")

    def _parse_monetary_value(self, value_str: str) -> float | None:
        """
        Parse a monetary string like '$4B', '1.2B', or '500M' into a float (in millions).
        Returns None if parsing fails.
        """
        if not isinstance(value_str, str):
            return None
        
        # Make the dollar sign optional and handle potential whitespace
        match = re.match(r'\$?(\d+\.?\d*)\s*([BM])', value_str, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            if unit == 'B':
                return value * 1000  # Convert billions to millions
            elif unit == 'M':
                return value
        return None

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.df.empty or self.embeddings.size == 0:
            return []

        query_embedding = self.model.encode([query])
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results_df = self.df.iloc[top_k_indices].copy()
        results_df = results_df.replace({pd.NaT: None, np.nan: None})
        
        return results_df.to_dict(orient='records')

    def advanced_search(
        self,
        name: str | None = None,
        sector: str | None = None,
        valuation: str | None = None,
        website: str | None = None,
        investors: str | None = None,
        # --- NEW PARAMS ---
        total_funding: str | None = None,
        sinarmas_interest: str | None = None,
        share_transfer_allowed: str | None = None
    ) -> List[Dict[str, Any]]:
        if self.df.empty:
            return []

        results_df = self.df.copy()

        if name:
            results_df = results_df[results_df['name'].str.contains(name, case=False, na=False)]
        
        if sector:
            results_df = results_df[results_df['sector'].str.lower() == sector.lower()]

        if valuation is not None:
            parsed_valuation = self._parse_monetary_value(valuation)
            if parsed_valuation is not None:
                valuations_in_df = results_df['valuation'].apply(self._parse_monetary_value)
                results_df = results_df[valuations_in_df.notna() & (valuations_in_df >= parsed_valuation)]

        if website is not None:
            results_df = results_df[results_df['website'].str.contains(website, case=False, na=False)]
        
        if investors is not None:
            results_df = results_df[results_df['investors'].str.contains(investors, case=False, na=False)]

        # --- NEW FILTER LOGIC ---
        if total_funding is not None:
            parsed_funding = self._parse_monetary_value(total_funding)
            if parsed_funding is not None:
                fundings_in_df = results_df['total_funding'].apply(self._parse_monetary_value)
                results_df = results_df[fundings_in_df.notna() & (fundings_in_df >= parsed_funding)]
        
        if sinarmas_interest:
            results_df = results_df[results_df['sinarmas_interest'].str.lower() == sinarmas_interest.lower()]

        if share_transfer_allowed:
            results_df = results_df[results_df['share_transfer_allowed'].str.lower() == share_transfer_allowed.lower()]
        # ------------------------

        results_df = results_df.replace({pd.NaT: None, np.nan: None})
        return results_df.to_dict(orient='records')

# Create a single instance to be used across the app
search_service = SearchService()
