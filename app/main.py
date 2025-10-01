from fastapi import FastAPI, Query
from typing import List, Optional
from app.models import Company
from app.services.search import search_service
from fastapi.middleware.cors import CORSMiddleware
# --- ADDED IMPORTS ---
from app.database import database

app = FastAPI(
    title="Company CRM API",
    description="API for searching company data from a PostgreSQL database.",
    version="1.1.0"
)

# This CORS section remains the same
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",
    "https://company-search-ui7v.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODIFIED LIFECYCLE EVENTS ---
@app.on_event("startup")
async def startup_event():
    """
    On startup, connect to the database and trigger the data loading and syncing process.
    """
    print("--- INFO ---: Connecting to the database...")
    await database.connect()
    print("--- INFO ---: Database connection established.")
    # Now, trigger the async data loading function in the search service
    print("--- INFO ---: Initializing search service and syncing data...")
    await search_service._load_and_sync_data()
    print("--- INFO ---: Application startup complete. Search service is ready.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    On shutdown, disconnect from the database.
    """
    print("--- INFO ---: Disconnecting from the database...")
    await database.disconnect()
    print("--- INFO ---: Database connection closed.")
# ---------------------------------

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"status": "API is running"}

# --- The search endpoints remain exactly the same, no changes needed ---
@app.get("/search", response_model=List[Company], tags=["Search"])
async def semantic_search_endpoint(
    q: str = Query(..., description="The natural language search query."),
    limit: int = Query(5, ge=1, le=50, description="Number of results to return.")
):
    """
    **Perform a semantic (NLP-based) search.**
    
    This endpoint converts your query into a vector and finds the most
    semantically similar companies in the database.
    
    Example: `?q=innovative tech company in renewable energy`
    """
    results = search_service.semantic_search(query=q, top_k=limit)
    return results

@app.get("/advanced-search", response_model=List[Company], tags=["Search"])
async def advanced_search_endpoint(
    name: Optional[str] = Query(None, description="Filter by company name (case-insensitive, partial match)."),
    sector: Optional[str] = Query(None, description="Filter by an exact sector name."),
    valuation: Optional[str] = Query(None, description="Minimum valuation (e.g., '$500M', '$1.2B')."),
    website: Optional[str] = Query(None, description="Website URL (case-insensitive, partial match)."),
    investors: Optional[str] = Query(None, description="Investors (case-insensitive, partial match)."),
    total_funding: Optional[str] = Query(None, description="Minimum total funding (e.g., '100M', '$2B')."),
    sinarmas_interest: Optional[str] = Query(None, description="Filter by Sinarmas Interest level (High, Medium, Low)."),
    share_transfer_allowed: Optional[str] = Query(None, description="Filter by share transfer permission (Yes, No).")
):
    """
    **Perform an advanced filtered search based on specific fields.**
    
    You can combine multiple filters. Only records matching all provided
    filters will be returned.
    
    Example: `?sector=Fintech&valuation=$1B&sinarmas_interest=High`
    """
    results = search_service.advanced_search(
        name=name,
        sector=sector,
        valuation=valuation,
        website=website,
        investors=investors,
        total_funding=total_funding,
        sinarmas_interest=sinarmas_interest,
        share_transfer_allowed=share_transfer_allowed
    )
    return results
