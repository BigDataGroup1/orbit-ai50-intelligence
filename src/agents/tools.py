"""
Lab 12: Core Agent Tools for PE Due Diligence
Three async tools that integrate with existing ORBIT infrastructure
FIXED: Smart filename matching for all company name variations
"""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Import YOUR existing utilities
from src.utils.qdrant_client import QdrantHelper

logger = logging.getLogger(__name__)


# ============================================================
# Pydantic Models for Tool Inputs/Outputs
# ============================================================

class PayloadRequest(BaseModel):
    """Input model for get_latest_structured_payload."""
    company_id: str = Field(description="Company identifier (e.g., 'Anthropic')")


class PayloadResponse(BaseModel):
    """Output model for get_latest_structured_payload."""
    success: bool
    company_id: str
    payload: Optional[Dict] = None
    error: Optional[str] = None


class RAGSearchRequest(BaseModel):
    """Input model for rag_search_company."""
    company_id: str = Field(description="Company identifier")
    query: str = Field(description="Search query for RAG")


class RAGSearchResponse(BaseModel):
    """Output model for rag_search_company."""
    success: bool
    company_id: str
    query: str
    results: List[Dict] = Field(default_factory=list, description="Relevant text chunks")
    error: Optional[str] = None


class LayoffSignal(BaseModel):
    """Input model for report_layoff_signal."""
    company_id: str
    signal_type: str = Field(description="Type of risk: 'layoff', 'security_breach', 'funding_issue'")
    severity: str = Field(description="Severity: 'low', 'medium', 'high', 'critical'")
    description: str
    detected_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class LayoffSignalResponse(BaseModel):
    """Output model for report_layoff_signal."""
    success: bool
    signal_logged: bool
    message: str


# ============================================================
# Helper: Smart Filename Finder
# ============================================================

def find_payload_file(company_id: str, payloads_dir: Path) -> Optional[Path]:
    """
    Smart filename finder - tries multiple variations.
    
    Args:
        company_id: Company identifier (e.g., "Figure Ai", "Hugging Face")
        payloads_dir: Directory containing payload files
        
    Returns:
        Path to payload file or None
    """
    # Try multiple filename variations
    variations = [
        f"{company_id.lower()}.json",                      # "figure ai.json"
        f"{company_id.lower().replace(' ', '_')}.json",    # "figure_ai.json" ✅
        f"{company_id.lower().replace(' ', '-')}.json",    # "figure-ai.json"
        f"{company_id.lower().replace(' ', '')}.json",     # "figureai.json"
        f"{company_id}.json",                              # "Figure Ai.json"
        f"{company_id.replace(' ', '_')}.json",            # "Figure_Ai.json"
    ]
    
    for variation in variations:
        file_path = payloads_dir / variation
        if file_path.exists():
            return file_path
    
    return None


# ============================================================
# Tool 1: Get Latest Structured Payload
# ============================================================

async def get_latest_structured_payload(request: PayloadRequest) -> PayloadResponse:
    """
    Tool 1: Retrieve the latest assembled payload for a company.
    
    Uses smart filename matching to handle:
    - "Figure Ai" → figure_ai.json
    - "Hugging Face" → hugging_face.json
    - etc.
    
    Args:
        request: PayloadRequest with company_id
        
    Returns:
        PayloadResponse with payload data or error
    """
    try:
        logger.info(f"🔍 Tool 1: Fetching payload for {request.company_id}")
        
        # Path to YOUR payloads directory
        payloads_dir = project_root / "data" / "payloads"
        
        # Smart filename search
        payload_file = find_payload_file(request.company_id, payloads_dir)
        
        if not payload_file:
            logger.warning(f"❌ No payload found for {request.company_id}")
            return PayloadResponse(
                success=False,
                company_id=request.company_id,
                error=f"No payload found for company: {request.company_id}"
            )
        
        # Read payload
        with open(payload_file, 'r') as f:
            payload = json.load(f)
        
        logger.info(f"✅ Tool 1: Found payload at {payload_file.name}")
        return PayloadResponse(
            success=True,
            company_id=request.company_id,
            payload=payload
        )
        
    except Exception as e:
        logger.error(f"❌ Tool 1 Error: {e}")
        return PayloadResponse(
            success=False,
            company_id=request.company_id,
            error=str(e)
        )


# ============================================================
# Tool 2: RAG Search Company Data
# ============================================================

async def rag_search_company(request: RAGSearchRequest) -> RAGSearchResponse:
    """
    Tool 2: Query YOUR Qdrant vector database for relevant context.
    
    Uses YOUR existing Qdrant vector database to perform semantic search.
    
    Args:
        request: RAGSearchRequest with company_id and query
        
    Returns:
        RAGSearchResponse with relevant text chunks
    """
    try:
        logger.info(f"🔍 Tool 2: RAG search for '{request.query}' in {request.company_id}")
        
        # Initialize YOUR Qdrant client
        qdrant = QdrantHelper()
        
        # Check if collection exists
        if not qdrant.check_collection_exists():
            logger.warning(f"⚠️ Qdrant collection doesn't exist yet")
            return RAGSearchResponse(
                success=False,
                company_id=request.company_id,
                query=request.query,
                error="Qdrant collection not found. Run vector indexing first."
            )
        
        # Perform semantic search
        results = qdrant.search_company_context(
            company_id=request.company_id,
            query=request.query,
            limit=5
        )
        
        if not results:
            logger.warning(f"⚠️ No results found for query")
            return RAGSearchResponse(
                success=True,
                company_id=request.company_id,
                query=request.query,
                results=[],
                error="No relevant content found"
            )
        
        logger.info(f"✅ Tool 2: Found {len(results)} results")
        return RAGSearchResponse(
            success=True,
            company_id=request.company_id,
            query=request.query,
            results=results
        )
        
    except Exception as e:
        logger.error(f"❌ Tool 2 Error: {e}")
        return RAGSearchResponse(
            success=False,
            company_id=request.company_id,
            query=request.query,
            error=str(e)
        )


# ============================================================
# Tool 3: Report Layoff/Risk Signal
# ============================================================

async def report_layoff_signal(signal: LayoffSignal) -> LayoffSignalResponse:
    """
    Tool 3: Log or flag high-risk events (layoffs, breaches, etc.).
    
    Creates a log entry for risk signals that require human review.
    
    Args:
        signal: LayoffSignal with risk details
        
    Returns:
        LayoffSignalResponse indicating success
    """
    try:
        logger.info(f"🚨 Tool 3: Risk signal for {signal.company_id}: {signal.signal_type} ({signal.severity})")
        
        # Create risk log entry
        risk_log = {
            "company_id": signal.company_id,
            "signal_type": signal.signal_type,
            "severity": signal.severity,
            "description": signal.description,
            "detected_at": signal.detected_at,
            "requires_hitl": signal.severity in ["high", "critical"]
        }
        
        # Save to logs directory
        log_dir = project_root / "logs" / "risk_signals"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{signal.company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump(risk_log, f, indent=2)
        
        message = f"Risk signal logged: {signal.signal_type} for {signal.company_id}"
        logger.info(f"✅ Tool 3: {message}")
        
        return LayoffSignalResponse(
            success=True,
            signal_logged=True,
            message=message
        )
        
    except Exception as e:
        logger.error(f"❌ Tool 3 Error: {e}")
        return LayoffSignalResponse(
            success=False,
            signal_logged=False,
            message=f"Failed to log signal: {str(e)}"
        )


# ============================================================
# Helper Function: List All Companies
# ============================================================

def list_available_companies() -> List[str]:
    """
    Helper: List all companies with available payloads.
    Returns proper names (not filenames).
    
    Returns:
        List of company IDs
    """
    try:
        payloads_dir = project_root / "data" / "payloads"
        
        if not payloads_dir.exists():
            return []
        
        companies = []
        for file in payloads_dir.glob("*.json"):
            if file.stem != "forbes_ai50_seed":
                # Keep the filename AS-IS (with underscores)
                # The smart finder will handle the matching
                companies.append(file.stem)
        
        return sorted(companies)
        
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        return []


# ============================================================
# Test Runner (for quick testing)
# ============================================================

if __name__ == "__main__":
    import asyncio
    
    print("\n" + "="*70)
    print("TESTING AGENT TOOLS")
    print("="*70 + "\n")
    
    async def test_tools():
        """Quick test of all three tools."""
        
        # Test Tool 1: Get Payload
        print("🧪 Testing Tool 1: Get Payload...")
        
        # Test with underscore filename
        payload_req = PayloadRequest(company_id="anthropic")
        payload_resp = await get_latest_structured_payload(payload_req)
        print(f"   anthropic: {payload_resp.success}")
        
        # Test with space in name (should still work!)
        payload_req2 = PayloadRequest(company_id="Figure Ai")
        payload_resp2 = await get_latest_structured_payload(payload_req2)
        print(f"   Figure Ai: {payload_resp2.success}")
        
        # Test with exact underscore name
        payload_req3 = PayloadRequest(company_id="figure_ai")
        payload_resp3 = await get_latest_structured_payload(payload_req3)
        print(f"   figure_ai: {payload_resp3.success}")
        
        print()
        
        # Test Tool 2: RAG Search
        print("🧪 Testing Tool 2: RAG Search...")
        try:
            rag_req = RAGSearchRequest(
                company_id="anthropic",
                query="What does this company do?"
            )
            rag_resp = await rag_search_company(rag_req)
            if rag_resp.success:
                print(f"   ✅ RAG search successful: {len(rag_resp.results)} results")
            else:
                print(f"   ⚠️  RAG search: {rag_resp.error}")
        except Exception as e:
            print(f"   ⚠️  RAG search not available: {e}")
        
        print()
        
        # Test Tool 3: Report Risk
        print("🧪 Testing Tool 3: Report Risk...")
        signal = LayoffSignal(
            company_id="TestCompany",
            signal_type="layoff",
            severity="high",
            description="Test risk signal"
        )
        signal_resp = await report_layoff_signal(signal)
        print(f"   Result: {signal_resp.success}")
        print(f"   {signal_resp.message}")
        
        print()
        
        # Test Helper: List Companies
        print("🧪 Testing Helper: List Companies...")
        companies = list_available_companies()
        print(f"   Found {len(companies)} companies")
        print(f"   Sample: {companies[:5]}")
    
    # Run async tests
    asyncio.run(test_tools())
    
    print("\n" + "="*70)
    print("✅ TOOL TESTING COMPLETE")
    print("="*70)