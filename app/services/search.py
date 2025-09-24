import pandas as pd
import numpy as np
import re
import time
# --- REMOVE GOOGLE AI ---
# import google.generativeai as genai 
# +++ ADD HUGGING FACE CLIENT +++
from huggingface_hub import InferenceClient
import chromadb
from typing import List, Dict, Any

from app.services.google_sheets import sheets_client
from app.config import settings

class SearchService:
    def __init__(self):
        self.df: pd.DataFrame = pd.DataFrame()
        # +++ UPDATE TO THE SENTENCE TRANSFORMER MODEL +++
        self.embedding_model_id = 'sentence-transformers/all-MiniLM-L6-v2'
        self.embedding_dimension = 384 # This model's dimension size

        # --- REMOVE GOOGLE AI CLIENT CONFIGURATION ---
        # try:
        #     if not settings.GOOGLE_API_KEY:
        #         raise ValueError("GOOGLE_API_KEY is not set in the environment.")
        #     genai.configure(api_key=settings.GOOGLE_API_KEY)
        #     print("Google AI client configured successfully.")
        # except Exception as e:
        #     print(f"Error configuring Google AI client: {e}")

        # +++ CONFIGURE THE HUGGING FACE CLIENT +++
        try:
            if not settings.HF_API_TOKEN:
                raise ValueError("HF_API_TOKEN is not set in the environment.")
            # UPDATED: Use the more modern and robust InferenceClient
            self.inference_client = InferenceClient(
                model=self.embedding_model_id, 
                token=settings.HF_API_TOKEN
            )
            print("Hugging Face InferenceClient configured successfully.")
        except Exception as e:
            print(f"Error configuring Hugging Face client: {e}")
            self.inference_client = None

        # Initialize ChromaDB client
        print("Initializing ChromaDB client...")
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_PATH)
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )
        print(f"Vector store collection '{settings.CHROMA_COLLECTION_NAME}' loaded/created.")
        
        self._load_and_sync_data()

    def _load_and_sync_data(self):
        print("Loading and processing data from Google Sheets...")
        self.df = sheets_client.get_all_records_as_df()
        
        if self.df.empty:
            print("Warning: Dataframe is empty. Search will not work. Check Google Sheets connection and sheet/worksheet names.")
            return

        self.df.rename(columns={
            "Company": "name", "Website": "website", "Latest Funding ": "latest_funding",
            "Latest Funding Date ": "latest_funding_date", "Total Funding": "total_funding",
            "Investors": "investors", "Valuation": "valuation", "Overview (Product, Model & Moat)": "overview",
            "Sector": "sector", "Sinarmas Interest": "sinarmas_interest", "Implied Valuation": "implied_valuation",
            "Share transfer allowed ?": "share_transfer_allowed", "Liquidity EZ": "liquidity_ez",
            "Liquidity Forge": "liquidity_forge", "Liquidity Nasdaq": "liquidity_nasdaq",
            "Summary": "summary", "Sellers Ask": "sellers_ask", "Buyers Bid": "buyers_bid",
            "Total Bids": "total_bids", "Total Asks": "total_asks", "Highest Bid Price": "highest_bid_price",
            "Lowest Ask Price": "lowest_ask_price", "Price History (JSON)": "price_history",
            "Funding History (JSON)": "funding_history",
        }, inplace=True)

        if 'summary' not in self.df.columns and 'overview' in self.df.columns:
            self.df['summary'] = self.df['overview']

        all_expected_columns = [
            'name', 'website', 'latest_funding', 'latest_funding_date', 'total_funding',
            'investors', 'valuation', 'overview', 'sector', 'sinarmas_interest', 'implied_valuation',
            'share_transfer_allowed', 'liquidity_ez', 'liquidity_forge', 'liquidity_nasdaq',
            'summary', 'sellers_ask', 'buyers_bid', 'total_bids', 'total_asks',
            'highest_bid_price', 'lowest_ask_price', 'price_history', 'funding_history'
        ]
        for col in all_expected_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna('').astype(str)
            else:
                self.df[col] = ''
        
        self.df['search_text'] = (
            "Company: " + self.df['name'] + ". Sector: " + self.df['sector'] + 
            ". Website: " + self.df['website'] + ". Investors: " + self.df['investors'] +
            ". Latest Funding: " + self.df['latest_funding'] + ". Total Funding: " +
            self.df['total_funding'] + ". Overview: " + self.df['overview']
        )
        
        collection_count = self.collection.count()
        df_count = len(self.df)

        print(f"Companies in Google Sheet: {df_count}")
        print(f"Embeddings in Vector Store: {collection_count}")

        if collection_count != df_count:
            print("Data mismatch detected. Rebuilding the vector store...")
            
            if collection_count > 0:
                self.chroma_client.delete_collection(name=settings.CHROMA_COLLECTION_NAME)
            
            self.collection = self.chroma_client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)

            texts_to_embed = self.df['search_text'].tolist()
            batch_size = 50 # Smaller batch size is safer for free inference APIs
            all_embeddings = []

            for i in range(0, len(texts_to_embed), batch_size):
                batch_texts = texts_to_embed[i:i+batch_size]
                try:
                    print(f"Embedding batch {i//batch_size + 1}/{(len(texts_to_embed) + batch_size - 1)//batch_size}...")
                    # +++ USE HUGGING FACE CLIENT FOR EMBEDDING +++
                    # CORRECTED: The argument is 'text', not 'sentences'
                    embeddings_array = self.inference_client.feature_extraction(text=batch_texts)
                    all_embeddings.extend(embeddings_array.tolist())
                    time.sleep(1)
                except Exception as e:
                    print(f"An error occurred during batch embedding: {e}")
                    # +++ UPDATE PLACEHOLDER DIMENSION TO 384 +++
                    all_embeddings.extend([[0.0] * self.embedding_dimension] * len(batch_texts))

            ids = [str(i) for i in self.df.index]
            metadatas = self.df.to_dict(orient='records')

            self.collection.add(
                 embeddings=all_embeddings,
                 documents=texts_to_embed,
                 metadatas=metadatas,
                 ids=ids
            )
            print("Vector store rebuild complete.")
        else:
            print("Data is in sync with the vector store.")
        
        print(f"Data loading complete. Final vector store count: {self.collection.count()}")

    def _parse_monetary_value(self, value_str: str) -> float | None:
        if not isinstance(value_str, str) or not value_str: return None
        value_str = value_str.strip()
        match = re.search(r'(\d+\.?\d*)\s*([BM])', value_str, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            return value * 1000 if unit == 'B' else value
        return None

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.collection.count() == 0 or not self.inference_client:
            print("Semantic search attempted but collection is empty or client is not configured.")
            return []

        try:
            # +++ USE HUGGING FACE CLIENT FOR QUERY EMBEDDING +++
            # CORRECTED: The argument is 'text', not 'sentences'
            # For a single string, it returns an array of shape (1, embedding_dim)
            query_embedding_array = self.inference_client.feature_extraction(text=query)
            # Convert to a list of lists for ChromaDB: e.g., [[0.1, 0.2, ...]]
            query_embedding_list = query_embedding_array.tolist()
        except Exception as e:
            print(f"Error embedding search query '{query}': {e}")
            return []

        results = self.collection.query(
            query_embeddings=query_embedding_list,
            n_results=top_k
        )
        
        if not results or not results.get('metadatas') or not results['metadatas'][0]:
            return []
        
        return results['metadatas'][0]

    def advanced_search(
        self, name: str | None = None, sector: str | None = None, valuation: str | None = None,
        website: str | None = None, investors: str | None = None, total_funding: str | None = None,
        sinarmas_interest: str | None = None, share_transfer_allowed: str | None = None
    ) -> List[Dict[str, Any]]:
        if self.df.empty:
            print("Advanced search attempted but dataframe is empty.")
            return []
        results_df = self.df.copy()
        if name: results_df = results_df[results_df['name'].str.contains(name, case=False, na=False)]
        if sector: results_df = results_df[results_df['sector'].str.lower() == sector.lower()]
        if website: results_df = results_df[results_df['website'].str.contains(website, case=False, na=False)]
        if investors: results_df = results_df[results_df['investors'].str.contains(investors, case=False, na=False)]
        if sinarmas_interest: results_df = results_df[results_df['sinarmas_interest'].str.lower() == sinarmas_interest.lower()]
        if share_transfer_allowed: results_df = results_df[results_df['share_transfer_allowed'].str.lower() == share_transfer_allowed.lower()]

        if valuation:
            min_val = self._parse_monetary_value(valuation)
            if min_val is not None:
                df_vals = results_df['valuation'].apply(self._parse_monetary_value)
                results_df = results_df[df_vals.notna() & (df_vals >= min_val)]
        if total_funding:
            min_funding = self._parse_monetary_value(total_funding)
            if min_funding is not None:
                df_vals = results_df['total_funding'].apply(self._parse_monetary_value)
                results_df = results_df[df_vals.notna() & (df_vals >= min_funding)]

        return results_df.to_dict(orient='records')

search_service = SearchService()
