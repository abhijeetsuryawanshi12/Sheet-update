import pandas as pd
import re
import time
from pinecone import Pinecone
from huggingface_hub import InferenceClient
from typing import List, Dict, Any
import traceback
from sqlalchemy import select, and_, or_

# --- MODIFIED IMPORTS ---
from app.database import database, companies
from app.config import settings

class SearchService:
    def __init__(self):
        # This part remains the same
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
        """
        This function now ONLY syncs the database with the Pinecone vector store.
        It no longer holds a DataFrame in memory for searching.
        """
        print("Loading data from PostgreSQL for Pinecone sync...")

        try:
            query = companies.select()
            records = await database.fetch_all(query)
            
            if not records:
                print("Warning: No records found in the database. Pinecone sync will be skipped.")
                return
            
            df = pd.DataFrame([dict(r) for r in records])
            print(f"--- INFO ---: Successfully loaded {len(df)} records from DB for sync check.")

        except Exception as e:
            print(f"--- FATAL ERROR ---: Could not fetch data from PostgreSQL: {e}")
            traceback.print_exc()
            return

        # Ensure key columns exist and are filled for embedding
        for col in ['name', 'sector', 'website', 'investors', 'latest_funding', 'total_funding', 'overview']:
            if col not in df.columns:
                df[col] = '' # Add missing column
            df[col] = df[col].fillna('') # Fill null values

        df['search_text'] = (
            "Company: " + df['name'] + ". Sector: " + df['sector'] + 
            ". Website: " + df['website'] + ". Investors: " + df['investors'] +
            ". Latest Funding: " + df['latest_funding'] + ". Total Funding: " +
            df['total_funding'] + ". Overview: " + df['overview']
        )
        
        index_stats = self.pinecone_index.describe_index_stats()
        pinecone_count = index_stats['total_vector_count']
        df_count = len(df)

        print(f"Companies in Database: {df_count}")
        print(f"Embeddings in Vector Store: {pinecone_count}")

        if pinecone_count != df_count:
            print("Data mismatch detected. Rebuilding the vector store...")
            
            if pinecone_count > 0:
                print("Clearing existing data from vector store...")
                self.pinecone_index.delete(delete_all=True)

            batch_size = 100 
            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i:i+batch_size]
                
                ids = batch_df['id'].astype(str).tolist()
                metadatas = batch_df.to_dict(orient='records')
                texts_to_embed = batch_df['search_text'].tolist()
                
                try:
                    print(f"Embedding and upserting batch {i//batch_size + 1}/{(len(df) + batch_size - 1)//batch_size}...")
                    embeddings_array = self.inference_client.feature_extraction(text=texts_to_embed)
                    embeddings_list = embeddings_array.tolist()
                    
                    vectors_to_upsert = []
                    for vec_id, embedding, meta in zip(ids, embeddings_list, metadatas):
                        # Metadata for pinecone must have string, number, or boolean values
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
        print(f"Data loading and sync complete. Final vector store count: {final_stats['total_vector_count']}")


    def _parse_monetary_value(self, value_str: str) -> float | None:
        if not isinstance(value_str, str) or not value_str: return None
        # Remove currency symbols and commas, handle 'B' for billion and 'M' for million
        value_str = value_str.strip().replace('$', '').replace(',', '')
        value_str_lower = value_str.lower()
        
        multiplier = 1
        if 'b' in value_str_lower:
            multiplier = 1_000_000_000
            value_str = value_str_lower.replace('b', '')
        elif 'm' in value_str_lower:
            multiplier = 1_000_000
            value_str = value_str_lower.replace('m', '')
        
        try:
            return float(value_str) * multiplier
        except (ValueError, TypeError):
            return None
    
    # --- MODIFIED to fetch fresh data ---
    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
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
            include_metadata=False # We only need the IDs
        )
        
        if not results or not results.get('matches'):
            return []
        
        # Extract IDs from Pinecone results
        result_ids = [int(match['id']) for match in results['matches']]
        if not result_ids:
            return []

        # Fetch the LATEST data from the database for these IDs
        db_query = select(companies).where(companies.c.id.in_(result_ids))
        fresh_records = await database.fetch_all(db_query)

        # Return the records as a list of dicts
        return [dict(record) for record in fresh_records]

    # --- COMPLETELY REWRITTEN to query the database directly ---
    async def advanced_search(
        self, name: str | None = None, sector: str | None = None, valuation: str | None = None,
        website: str | None = None, investors: str | None = None, total_funding: str | None = None,
        sinarmas_interest: str | None = None, share_transfer_allowed: str | None = None
    ) -> List[Dict[str, Any]]:
        
        query = select(companies)
        filters = []

        if name:
            filters.append(companies.c.name.ilike(f"%{name}%"))
        if sector:
            filters.append(companies.c.sector.ilike(f"%{sector}%"))
        if website:
            filters.append(companies.c.website.ilike(f"%{website}%"))
        if investors:
            filters.append(companies.c.investors.ilike(f"%{investors}%"))
        if sinarmas_interest:
            filters.append(companies.c.sinarmas_interest == sinarmas_interest)
        if share_transfer_allowed:
            filters.append(companies.c.share_transfer_allowed == share_transfer_allowed)
        
        if filters:
            query = query.where(and_(*filters))

        records = await database.fetch_all(query)
        
        # Convert to list of dicts for further filtering in Python for complex fields
        results = [dict(r) for r in records]

        # In-memory filtering for monetary values as it's complex for SQL across all DBs
        if valuation:
            min_val = self._parse_monetary_value(valuation)
            if min_val is not None:
                results = [
                    r for r in results 
                    if r.get('valuation') and self._parse_monetary_value(r['valuation']) is not None 
                    and self._parse_monetary_value(r['valuation']) >= min_val
                ]
        
        if total_funding:
            min_funding = self._parse_monetary_value(total_funding)
            if min_funding is not None:
                 results = [
                    r for r in results 
                    if r.get('total_funding') and self._parse_monetary_value(r['total_funding']) is not None
                    and self._parse_monetary_value(r['total_funding']) >= min_funding
                ]
                
        return results

search_service = SearchService()