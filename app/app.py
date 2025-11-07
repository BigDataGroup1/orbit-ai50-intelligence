"""
FastAPI Backend for PE Dashboard - Lab 8
Author: Tapas
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.structured.structured_dashboard import generate_dashboard

app = FastAPI(title="PE Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@app.get("/")
def root():
    return {
        "message": "PE Dashboard API - Lab 8 Complete",
        "author": "Tapas",
        "endpoints": {
            "health": "/health",
            "list_companies": "/companies", 
            "structured_dashboard": "/dashboard/structured?company_id=<id>"
        }
    }


@app.get("/health")
def health():
    return {"status": "ok", "lab": "Lab 8 - Structured Dashboard"}


@app.get("/companies")
def list_companies():
    """List all 39 companies with payloads"""
    payloads_dir = DATA_DIR / "payloads"
    
    if not payloads_dir.exists():
        return []
    
    companies = []
    for payload_file in sorted(payloads_dir.glob('*.json')):
        with open(payload_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            companies.append({
                "company_id": payload_file.stem,
                "legal_name": data.get('company_record', {}).get('legal_name', 'Unknown'),
                "website": data.get('company_record', {}).get('website', 'N/A')
            })
    
    return companies


@app.post("/dashboard/structured")
def dashboard_structured(company_id: str):
    """
    Generate structured pipeline dashboard
    Example: POST /dashboard/structured?company_id=anthropic
    """
    print(f"\n📊 Generating dashboard for: {company_id}")
    
    result = generate_dashboard(company_id)
    
    if not result['success']:
        raise HTTPException(
            status_code=404, 
            detail=result.get('error', 'Dashboard generation failed')
        )
    
    return {
        "company_id": result['company_id'],
        "company_name": result['company_name'],
        "markdown": result['markdown'],
        "tokens_used": result.get('tokens_used', 0),
        "pipeline": "structured"
    }


@app.post("/dashboard/rag")
def dashboard_rag(company_name: str):
    """
    RAG pipeline dashboard - Lab 7 (placeholder)
    Example: POST /dashboard/rag?company_name=Anthropic
    """
    return {
        "company_name": company_name,
        "markdown": (
            f"## Company Overview\n{company_name}\n\n"
            "## Business Model and GTM\nNot disclosed.\n\n"
            "## Funding & Investor Profile\nNot disclosed.\n\n"
            "## Growth Momentum\nNot disclosed.\n\n"
            "## Visibility & Market Sentiment\nNot disclosed.\n\n"
            "## Risks and Challenges\nNot disclosed.\n\n"
            "## Outlook\nNot disclosed.\n\n"
            "## Disclosure Gaps\n- RAG pipeline not implemented (Lab 7).\n"
        ),
        "pipeline": "rag"
    }