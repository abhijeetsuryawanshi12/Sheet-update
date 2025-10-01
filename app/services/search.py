import pandas as pd
import re
import time
from pinecone import Pinecone
from huggingface_hub import InferenceClient
from typing import List, Dict, Any
import traceback

# --- MODIFIED IMPORTS ---
from app.database import database, companies # ADDED
from app.config import settings

class SearchService:
    def __init__(self):
        # This part remains the same
        self.df: pd.DataFrame = pd.DataFrame()
        self.embedding_model_id = 'sentence-transformers/all-MiniLM-L6-v2'
        self.embedding_dimension = 384

        try:
            if not settings.HF_API_TOKEN:
                raise ValueError("HF_API_TOKEN is not set in the environment.")
            self.inference_client = InferenceClient(model=self.embedding_model_id, token=settings.HF_API_TOKEN)
        except Exception as e:
            print(f"--- [FATAL DEBUG] Error configuring Hugging Face client: {e} ---")
            self.inference_client = None

        self.pinecone_index = None
        try:
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            if settings.PINECONE_INDEX_NAME not in pc.list_indexes().names():
                 raise ValueError(f"Pinecone index '{settings.PINECONE_INDEX_NAME}' not found.")
            self.pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
        except Exception as e:
            print(f"--- [FATAL DEBUG] Could not initialize Pinecone: {e} ---")
            traceback.print_exc()
        
        if not self.pinecone_index or not self.inference_client:
            print("--- Halting data sync due to initialization failure. ---")

    async def _load_and_sync_data(self):
        print("Loading and processing data from PostgreSQL database...")

        try:
            query = companies.select()
            records = await database.fetch_all(query)
            
            if not records:
                print("Warning: No records found in the database. Search will not work.")
                return
            
            # --- THIS IS THE FIX ---
            # The 'Record' object from the database library is not a dict,
            # but it can be converted to one by calling dict(r). It does not have an .items() method.
            self.df = pd.DataFrame([dict(r) for r in records])
            # -----------------------
            
            print(f"--- INFO ---: Successfully loaded {len(self.df)} records from the database.")

        except Exception as e:
            print(f"--- FATAL ERROR ---: Could not fetch data from PostgreSQL: {e}")
            traceback.print_exc()
            self.df = pd.DataFrame() 
            return

        if self.df.empty or self.pinecone_index is None:
            print("Warning: Dataframe is empty or Pinecone index is not available. Search will not work.")
            return

        if 'summary' not in self.df.columns and 'overview' in self.df.columns:
            self.df['summary'] = self.df['overview']
        
        all_expected_columns = [
            'name', 'website', 'latest_funding', 'latest_funding_date', 'total_funding', 'investors', 
            'valuation', 'overview', 'sector', 'sinarmas_interest', 'implied_valuation', 'share_transfer_allowed', 
            'liquidity_ez', 'liquidity_forge', 'liquidity_nasdaq', 'summary', 'sellers_ask', 'buyers_bid', 
            'total_bids', 'total_asks', 'highest_bid_price', 'lowest_ask_price', 'price_history', 'funding_history'
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
        
        index_stats = self.pinecone_index.describe_index_stats()
        pinecone_count = index_stats['total_vector_count']
        df_count = len(self.df)

        print(f"Companies in Database: {df_count}")
        print(f"Embeddings in Vector Store: {pinecone_count}")

        if pinecone_count != df_count:
            print("Data mismatch detected. Rebuilding the vector store...")
            
            if pinecone_count > 0:
                print("Clearing existing data from vector store...")
                self.pinecone_index.delete(delete_all=True)

            batch_size = 100 
            for i in range(0, len(self.df), batch_size):
                batch_df = self.df.iloc[i:i+batch_size]
                
                ids = batch_df['id'].astype(str).tolist()
                metadatas = batch_df.to_dict(orient='records')
                texts_to_embed = batch_df['search_text'].tolist()
                
                try:
                    print(f"Embedding and upserting batch {i//batch_size + 1}/{(len(self.df) + batch_size - 1)//batch_size}...")
                    embeddings_array = self.inference_client.feature_extraction(text=texts_to_embed)
                    embeddings_list = embeddings_array.tolist()
                    
                    vectors_to_upsert = []
                    for vec_id, embedding, meta in zip(ids, embeddings_list, metadatas):
                        clean_meta = {k: (v if v is not None else "") for k, v in meta.items()}
                        vectors_to_upsert.append({
                            "id": vec_id,
                            "values": embedding,
                            "metadata": clean_meta
                        })

                    self.pinecone_index.upsert(vectors=vectors_to_upsert)
                    
                except Exception as e:
                    print(f"An error occurred during batch upsert: {e}")
                    traceback.print_exc()

            print("Vector store rebuild complete.")
        else:
            print("Data is in sync with the vector store.")
        
        final_stats = self.pinecone_index.describe_index_stats()
        print(f"Data loading complete. Final vector store count: {final_stats['total_vector_count']}")


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
        if self.pinecone_index is None or not self.inference_client:
            print("Semantic search attempted but index or client is not configured.")
            return []

        try:
            query_embedding_array = self.inference_client.feature_extraction(text=query)
            query_embedding_list = query_embedding_array.tolist()
        except Exception as e:
            print(f"Error embedding search query '{query}': {e}")
            return []

        results = self.pinecone_index.query(
            vector=query_embedding_list,
            top_k=top_k,
            include_metadata=True
        )
        
        if not results or not results.get('matches'):
            return []
        
        return [match['metadata'] for match in results['matches']]

    def advanced_search(
        self, name: str | None = None, sector: str | None = None, valuation: str | None = None,
        website: str | None = None, investors: str | None = None, total_funding: str | None = None,
        sinarmas_interest: str | None = None, share_transfer_allowed: str | None = None
    ) -> List[Dict[str, Any]]:
        if self.df.empty:
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
