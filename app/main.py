from fastapi import FastAPI, Query
from typing import List, Optional
from app.models import Company
from app.services.search import search_service
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Company CRM API",
    description="API for searching company data from a Google Sheet.",
    version="1.0.0"
)

# --- Add this CORS middleware section ---
# This allows your frontend (running on localhost:3000) to communicate with your backend.
origins = [
    "http://localhost",
    "http://localhost:3000", # The default port for React development servers
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)
# ----------------------------------------


@app.on_event("startup")
async def startup_event():
    # This will trigger the data loading and processing when the app starts.
    # The SearchService is already initialized, so this is just for clarity.
    print("Application startup complete. Search service is ready.")

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"status": "API is running"}

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
    investors: Optional[str] = Query(None, description="Investors (case-insensitive, partial match).")
):
    """
    **Perform an advanced filtered search based on specific fields.**
    
    You can combine multiple filters. Only records matching all provided
    filters will be returned.
    
    Example: `?sector=Fintech&valuation=$1B`
    """
    results = search_service.advanced_search(
        name=name,
        sector=sector,
        valuation=valuation,
        website=website,
        investors=investors
    )
    return results
