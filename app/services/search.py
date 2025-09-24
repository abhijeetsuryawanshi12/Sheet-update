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

        # IMPORTANT: Ensure your Google Sheet column names EXACTLY match the keys here.
        # e.g., "Latest Funding", not "Latest funding" or "Latest Funding "
        self.df.rename(columns={
            "Company": "name",
            "Sector": "sector",
            "Valuation": "valuation",
            "Website": "website",
            "Investors": "investors",
            "Latest Funding": "latest_funding",
            "Latest Funding Date": "latest_funding_date",
            "Total Funding": "total_funding",
            "Overview (Product, Model & Moat)": "overview",
        }, inplace=True)

        expected_cols = [
            'name', 'sector', 'valuation', 'website', 'investors', 
            'latest_funding', 'latest_funding_date', 'total_funding', 'overview'
        ]

        # Ensure all expected columns exist, creating them if they don't.
        for col in expected_cols:
            if col not in self.df.columns:
                print(f"Warning: Column '{col}' not found after renaming. Creating it as an empty column.")
                self.df[col] = ''
        
        # Create a combined text field for better semantic search context.
        # This new method is more robust: it explicitly fills empty cells and converts
        # each column to a string BEFORE concatenation. This prevents errors from
        # mixed data types (e.g., numbers, dates, text) and empty cells (NaNs).
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
        self.embeddings = self.model.encode(self.df['search_text'].tolist(), show_progress_bar=True)
        print("Data loaded and processed successfully.")

    def _parse_valuation(self, valuation_str: str) -> float | None:
        """
        Parse a valuation string like '$4B' or '$3.4M' into a float (in millions).
        Returns None if parsing fails.
        """
        if not isinstance(valuation_str, str):
            return None

        match = re.match(r'\$(\d+\.?\d*)([BM])', valuation_str, re.IGNORECASE)
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
        
        # Get the indices of the top_k most similar results
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results_df = self.df.iloc[top_k_indices].copy()

        # Replace any lingering NaN/NaT with None for JSON compatibility
        results_df = results_df.replace({np.nan: None})
        
        return results_df.to_dict(orient='records')

    def advanced_search(
        self,
        name: str | None = None,
        sector: str | None = None,
        valuation: str | None = None, # Expect valuation as string now
        website: str | None = None,
        investors: str | None = None
    ) -> List[Dict[str, Any]]:
        if self.df.empty:
            return []

        results_df = self.df.copy()

        if name:
            # Use the 'name' column to match the Pydantic model
            results_df = results_df[results_df['name'].str.contains(name, case=False, na=False)]
        
        if sector:
            results_df = results_df[results_df['sector'].str.lower() == sector.lower()]

        if valuation is not None:
            # Parse the valuation string to a float
            parsed_valuation = self._parse_valuation(valuation)
            if parsed_valuation is not None:
                # Create a boolean mask where valuation is greater or equal than the parsed value
                valuations = results_df['valuation'].apply(self._parse_valuation)
                results_df = results_df[valuations >= parsed_valuation]

        if website is not None:
            results_df = results_df[results_df['website'].str.contains(website, case=False, na=False)]
        
        if investors is not None:
            results_df = results_df[results_df['investors'].str.contains(investors, case=False, na=False)]

        # Replace any lingering NaN/NaT with None for JSON compatibility
        results_df = results_df.replace({np.nan: None})

        return results_df.to_dict(orient='records')

# Create a single instance to be used across the app
search_service = SearchService()
