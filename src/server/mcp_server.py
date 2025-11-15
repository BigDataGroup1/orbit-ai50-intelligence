"""
Lab 14: Model Context Protocol (MCP) Server
Exposes Tools, Resources, and Prompts for PE Due Diligence
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List, Dict
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import dashboard generators
from dashboard.rag_generator import RAGDashboardGenerator
from structured.structured_dashboard import generate_dashboard as generate_structured_dashboard
from vectordb.embedder import VectorStore
from agents.tools import list_available_companies

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="ORBIT MCP Server",
    description="Model Context Protocol server for PE Due Diligence tools, resources, and prompts",
    version="1.0.0"
)

# CORS - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
vector_store = None
rag_generator = None


@app.on_event("startup")
async def startup_event():
    """Initialize vector store and RAG generator on startup."""
    global vector_store, rag_generator
    
    print("\n" + "="*70)
    print("🚀 STARTING MCP SERVER")
    print("="*70)
    
    try:
        # Initialize vector store (local mode with data directory)
        print("\n📦 Loading vector store...")
        
        # Use local data directory for vector store
        data_dir = Path(__file__).resolve().parents[2] / "data" / "qdrant_storage"
        if data_dir.exists():
            vector_store = VectorStore(use_docker=False, data_dir=data_dir)
        else:
            # Fallback to default location
            vector_store = VectorStore(use_docker=False)
        
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        print(f"✅ Loaded {stats['total_chunks']} chunks")
        print(f"✅ {len(companies)} companies")
        
        # Initialize RAG dashboard generator
        print("\n🤖 Initializing RAG generator...")
        rag_generator = RAGDashboardGenerator(vector_store)
        
        print("\n✅ MCP SERVER READY!")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# Pydantic Models
# ============================================================

class StructuredDashboardRequest(BaseModel):
    """Request model for structured dashboard generation."""
    company_id: str
    

class StructuredDashboardResponse(BaseModel):
    """Response model for structured dashboard."""
    success: bool
    company_id: str
    company_name: Optional[str] = None
    markdown: Optional[str] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None


class RAGDashboardRequest(BaseModel):
    """Request model for RAG dashboard generation."""
    company_name: str
    max_chunks: Optional[int] = 20


class RAGDashboardResponse(BaseModel):
    """Response model for RAG dashboard."""
    success: bool
    company_name: str
    dashboard: Optional[str] = None
    chunks_used: Optional[int] = None
    page_types: Optional[List[str]] = None
    error: Optional[str] = None


class CompaniesResponse(BaseModel):
    """Response model for companies list."""
    success: bool
    companies: List[str]
    total: int
    error: Optional[str] = None


class PromptResponse(BaseModel):
    """Response model for prompt template."""
    success: bool
    prompt_type: str
    content: Optional[str] = None
    error: Optional[str] = None


# ============================================================
# MCP Endpoints
# ============================================================

@app.get("/")
async def root():
    """Root endpoint - MCP server info."""
    return {
        "name": "ORBIT MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for PE Due Diligence",
        "endpoints": {
            "tools": [
                "/tool/generate_structured_dashboard",
                "/tool/generate_rag_dashboard"
            ],
            "resources": [
                "/resource/ai50/companies"
            ],
            "prompts": [
                "/prompt/pe-dashboard"
            ]
        }
    }


@app.post("/tool/generate_structured_dashboard", response_model=StructuredDashboardResponse)
async def tool_generate_structured_dashboard(request: StructuredDashboardRequest):
    """
    MCP Tool: Generate structured dashboard from payload.
    
    Args:
        request: Company ID to generate dashboard for
        
    Returns:
        Dashboard markdown and metadata
    """
    try:
        print(f"\n🔧 MCP Tool: generate_structured_dashboard({request.company_id})")
        
        result = generate_structured_dashboard(request.company_id)
        
        if result.get('success'):
            return StructuredDashboardResponse(
                success=True,
                company_id=result.get('company_id', request.company_id),
                company_name=result.get('company_name'),
                markdown=result.get('markdown'),
                tokens_used=result.get('tokens_used')
            )
        else:
            return StructuredDashboardResponse(
                success=False,
                company_id=request.company_id,
                error=result.get('error', 'Unknown error')
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating structured dashboard: {str(e)}"
        )


@app.post("/tool/generate_rag_dashboard", response_model=RAGDashboardResponse)
async def tool_generate_rag_dashboard(request: RAGDashboardRequest):
    """
    MCP Tool: Generate RAG dashboard from vector store.
    
    Args:
        request: Company name and optional max_chunks
        
    Returns:
        Dashboard markdown and metadata
    """
    try:
        print(f"\n🔧 MCP Tool: generate_rag_dashboard({request.company_name})")
        
        if not rag_generator:
            raise HTTPException(
                status_code=503,
                detail="RAG generator not initialized. Check server startup logs."
            )
        
        result = rag_generator.generate_dashboard(
            company_name=request.company_name,
            max_chunks=request.max_chunks or 20
        )
        
        if result.get('success'):
            return RAGDashboardResponse(
                success=True,
                company_name=result.get('company_name', request.company_name),
                dashboard=result.get('dashboard'),
                chunks_used=result.get('chunks_used'),
                page_types=result.get('page_types')
            )
        else:
            return RAGDashboardResponse(
                success=False,
                company_name=request.company_name,
                error=result.get('error', 'Unknown error')
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating RAG dashboard: {str(e)}"
        )


@app.get("/resource/ai50/companies", response_model=CompaniesResponse)
async def resource_ai50_companies():
    """
    MCP Resource: List all available AI50 company IDs.
    
    Returns:
        List of company IDs
    """
    try:
        print("\n📚 MCP Resource: ai50/companies")
        
        # Get companies from both sources
        companies = list_available_companies()
        
        return CompaniesResponse(
            success=True,
            companies=companies,
            total=len(companies)
        )
        
    except Exception as e:
        return CompaniesResponse(
            success=False,
            companies=[],
            total=0,
            error=str(e)
        )


@app.get("/prompt/pe-dashboard", response_model=PromptResponse)
async def prompt_pe_dashboard(prompt_type: str = "rag"):
    """
    MCP Prompt: Get PE dashboard generation prompt template.
    
    Args:
        prompt_type: "rag" (default) or "structured"
        
    Returns:
        Prompt template content
    """
    try:
        print(f"\n💬 MCP Prompt: pe-dashboard (type={prompt_type})")
        
        # Determine which prompt file to load
        if prompt_type.lower() == "structured":
            prompt_file = Path(__file__).resolve().parents[1] / "prompts" / "dashboard_system_structured.md"
            prompt_type_name = "structured"
        else:
            prompt_file = Path(__file__).resolve().parents[1] / "prompts" / "dashboard_system.md"
            prompt_type_name = "rag"
        
        if not prompt_file.exists():
            return PromptResponse(
                success=False,
                prompt_type=prompt_type_name,
                error=f"Prompt file not found: {prompt_file}"
            )
        
        content = prompt_file.read_text(encoding='utf-8')
        
        return PromptResponse(
            success=True,
            prompt_type=prompt_type_name,
            content=content
        )
        
    except Exception as e:
        return PromptResponse(
            success=False,
            prompt_type=prompt_type or "unknown",
            error=str(e)
        )


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "vector_store_loaded": vector_store is not None,
        "rag_generator_loaded": rag_generator is not None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)

