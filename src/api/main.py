"""
FastAPI app for RAG search - Lab 4 + Lab 7
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from vectordb.embedder import VectorStore
from dashboard.rag_generator import RAGDashboardGenerator

app = FastAPI(
    title="PE Dashboard RAG API",
    description="Vector search API for Forbes AI 50 companies",
    version="1.0.0"
)

# Enable CORS (for Streamlit later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
vector_store = None
dashboard_generator = None


@app.on_event("startup")
async def load_vector_store():
    """Load Qdrant vector store and dashboard generator on startup."""
    global vector_store, dashboard_generator
    
    try:
        print("\nLoading vector store...")
        vector_store = VectorStore(use_docker=False)
        
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        print(f"✅ Loaded Qdrant with {stats['total_chunks']} chunks")
        print(f"✅ {len(companies)} companies indexed")
        
        # Initialize dashboard generator
        print("Loading dashboard generator...")
        dashboard_generator = RAGDashboardGenerator(vector_store)
        print(f"✅ Dashboard generator ready")
        print(f"✅ API ready at http://localhost:8000\n")
        
    except Exception as e:
        print(f"❌ Error loading: {e}")
        print("   Make sure you've run: python src/vectordb/build_index.py")


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    company_name: Optional[str] = None
    page_type: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the pricing model?",
                "k": 5,
                "company_name": "Anthropic",
                "page_type": "pricing"
            }
        }


class SearchResult(BaseModel):
    text: str
    company_name: str
    page_type: str
    score: float
    tokens: int


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    num_results: int
    filters: dict


class DashboardRequest(BaseModel):
    company_name: str
    max_chunks: int = 20


class DashboardResponse(BaseModel):
    company_name: str
    dashboard: str
    success: bool
    metadata: Optional[dict] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Health check and API info."""
    if vector_store:
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        return {
            "status": "ok",
            "message": "PE Dashboard RAG API",
            "version": "1.0.0",
            "vector_store": {
                "total_chunks": stats['total_chunks'],
                "total_companies": len(companies),
                "vector_dimension": stats['vector_dimension'],
                "distance_metric": stats['distance_metric']
            },
            "endpoints": {
                "search": "POST /rag/search",
                "companies": "GET /companies",
                "stats": "GET /stats",
                "dashboard": "POST /dashboard/rag"
            }
        }
    
    return {
        "status": "error",
        "message": "Vector store not loaded. Run build_index.py first."
    }


@app.post("/rag/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search vector store for relevant chunks.
    
    **Query Parameters:**
    - `query`: Search query text
    - `k`: Number of results (default: 5)
    - `company_name`: Optional filter by company
    - `page_type`: Optional filter by page type
    
    **Page Types:**
    - homepage, about, pricing, product, careers, blog, customers
    
    **Example:**
```json
    {
      "query": "What is the pricing?",
      "k": 5,
      "company_name": "Anthropic",
      "page_type": "pricing"
    }
```
    """
    if vector_store is None:
        raise HTTPException(
            status_code=503, 
            detail="Vector store not loaded. Run build_index.py first."
        )
    
    # Search
    results = vector_store.search(
        query=request.query,
        k=request.k,
        company_name=request.company_name,
        page_type=request.page_type
    )
    
    # Format results
    formatted_results = [
        SearchResult(
            text=r['text'],
            company_name=r['metadata']['company_name'],
            page_type=r['metadata']['page_type'],
            score=r['score'],
            tokens=r['tokens']
        )
        for r in results
    ]
    
    return SearchResponse(
        results=formatted_results,
        query=request.query,
        num_results=len(formatted_results),
        filters={
            "company_name": request.company_name,
            "page_type": request.page_type
        }
    )


@app.post("/dashboard/rag", response_model=DashboardResponse)
async def generate_rag_dashboard(request: DashboardRequest):
    """
    Generate PE dashboard using RAG pipeline.
    
    **Lab 7 Endpoint**
    
    Args:
        company_name: Company to generate dashboard for
        max_chunks: Maximum context chunks to use (default: 20)
    
    Returns:
        Markdown dashboard with 8 sections
    
    Example:
```json
    {
      "company_name": "Anthropic",
      "max_chunks": 20
    }
```
    """
    if dashboard_generator is None:
        raise HTTPException(
            status_code=503,
            detail="Dashboard generator not loaded. Check API startup logs."
        )
    
    # Generate dashboard
    result = dashboard_generator.generate_dashboard(
        company_name=request.company_name,
        max_chunks=request.max_chunks
    )
    
    return DashboardResponse(**result)


@app.get("/companies")
async def get_companies():
    """Get list of all companies in vector store."""
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store not loaded"
        )
    
    companies = vector_store.get_companies()
    
    return {
        "companies": companies,
        "total": len(companies),
        "page_types": [
            "homepage", "about", "pricing", 
            "product", "careers", "blog", "customers"
        ]
    }


@app.get("/stats")
async def get_stats():
    """Get vector store statistics."""
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store not loaded"
        )
    
    stats = vector_store.get_stats()
    companies = vector_store.get_companies()
    
    return {
        "total_chunks": stats['total_chunks'],
        "total_companies": len(companies),
        "vector_dimension": stats['vector_dimension'],
        "distance_metric": stats['distance_metric'],
        "companies": companies
    }


if __name__ == "__main__":
    import uvicorn
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║         PE DASHBOARD RAG API - LAB 4 + LAB 7                   ║
╚════════════════════════════════════════════════════════════════╝

Starting FastAPI server...
API docs: http://localhost:8000/docs
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)