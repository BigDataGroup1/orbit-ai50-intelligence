"""
FastAPI app for RAG search + Structured dashboards - Cloud Run Deployment
"""
import os
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
from structured.structured_dashboard import generate_dashboard as generate_structured_dashboard

# Initialize FastAPI
app = FastAPI(
    title="ORBIT AI50 Intelligence API",
    description="RAG-powered API for Forbes AI 50 company intelligence",
    version="2.0.0"
)

# CORS - allow all origins for Streamlit
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
async def startup_event():
    """Initialize vector store and dashboard generator on startup."""
    global vector_store, dashboard_generator
    
    try:
        print("\n" + "="*70)
        print("🚀 STARTING ORBIT API ON CLOUD RUN")
        print("="*70)
        
        print("\n📦 Initializing Vector Store...")
        vector_store = VectorStore(use_docker=False)
        
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        print(f"✅ Loaded Qdrant with {stats['total_chunks']} chunks")
        print(f"✅ {len(companies)} companies indexed")
        
        # Initialize RAG dashboard generator
        print("\n🤖 Loading RAG dashboard generator...")
        dashboard_generator = RAGDashboardGenerator(vector_store)
        print(f"✅ RAG generator ready")
        
        print("\n" + "="*70)
        print("✅ API READY AND HEALTHY!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"❌ Startup Error: {e}")
        # Don't fail startup, but log the error


# Pydantic models
class SearchRequest(BaseModel):
    query: str
    k: int = 5
    company_name: Optional[str] = None
    page_type: Optional[str] = None


class SearchResult(BaseModel):
    text: str
    company_name: str
    page_type: str
    score: float
    tokens: int
    session: str
    source_file: str
    is_daily_refresh: bool


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
    """Health check and API info - required for Cloud Run"""
    if vector_store:
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        return {
            "status": "healthy",
            "message": "ORBIT AI50 Intelligence API",
            "version": "2.0.0",
            "environment": "Cloud Run",
            "vector_store": {
                "total_chunks": stats['total_chunks'],
                "total_companies": len(companies),
                "vector_dimension": stats['vector_dimension']
            },
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "search": "/rag/search",
                "companies": "/companies",
                "rag_dashboard": "/dashboard/rag",
                "structured_dashboard": "/dashboard/structured"
            }
        }
    
    return {
        "status": "initializing",
        "message": "Vector store loading..."
    }


@app.get("/health")
async def health_check():
    """Detailed health check for Cloud Run"""
    return {
        "status": "ok",
        "vector_store_initialized": vector_store is not None,
        "dashboard_generator_initialized": dashboard_generator is not None,
        "service": "orbit-api",
        "version": "2.0.0"
    }


@app.post("/rag/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search vector store for relevant chunks.
    
    Example:
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
            detail="Vector store not initialized"
        )
    
    try:
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
                tokens=r['tokens'],
                session=r['metadata']['session'],
                source_file=r['metadata']['source_file'],
                is_daily_refresh=r['metadata'].get('is_daily_refresh', False)
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
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@app.post("/dashboard/rag", response_model=DashboardResponse)
async def generate_rag_dashboard(request: DashboardRequest):
    """
    Generate PE dashboard using RAG pipeline.
    
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
            detail="Dashboard generator not initialized"
        )
    
    try:
        # Generate dashboard
        result = dashboard_generator.generate_dashboard(
            company_name=request.company_name,
            max_chunks=request.max_chunks
        )
        
        return DashboardResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard generation failed: {str(e)}"
        )


@app.post("/dashboard/structured", response_model=DashboardResponse)
async def generate_structured_dashboard_endpoint(request: DashboardRequest):
    """
    Generate PE dashboard using Structured pipeline.
    
    Example:
```json
    {
      "company_name": "anthropic"
    }
```
    """
    try:
        # Call structured pipeline
        result = generate_structured_dashboard(request.company_name)
        
        if result['success']:
            return DashboardResponse(
                company_name=result['company_name'],
                dashboard=result['markdown'],
                success=True,
                metadata={
                    'tokens_used': result.get('tokens_used', 0),
                    'pipeline': 'structured',
                    'source': 'payload_assembly'
                }
            )
        else:
            return DashboardResponse(
                company_name=request.company_name,
                dashboard="",
                success=False,
                error=result.get('error', 'Unknown error')
            )
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Payload not found for {request.company_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Structured dashboard generation failed: {str(e)}"
        )


@app.get("/companies")
async def get_companies():
    """Get list of all companies in vector store."""
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store not initialized"
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
            detail="Vector store not initialized"
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


# For local testing
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     ORBIT API - RAG + STRUCTURED PIPELINES                ║
╚═══════════════════════════════════════════════════════════╝

Starting FastAPI server on port {port}...
API docs: http://localhost:{port}/docs
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)