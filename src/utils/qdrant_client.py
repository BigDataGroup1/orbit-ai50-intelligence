"""
Qdrant Client Helper
Queries the existing Qdrant vector database for RAG search

⚠️ IMPORTANT: This file should NOT be run directly.
It's a module to be imported by other files.
If you run it directly, you'll get a circular import error.
"""

# ✅ FIX: Import qdrant_client package BEFORE adding current dir to path
# This ensures we import the installed package, not this local file
import importlib.util
import sys
from pathlib import Path

# Temporarily remove current directory from path to avoid circular import
_current_dir = str(Path(__file__).parent)
if _current_dir in sys.path:
    sys.path.remove(_current_dir)

# Now import the qdrant_client PACKAGE (not this file)
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import logging
import os
from dotenv import load_dotenv

# Restore path
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

load_dotenv()

logger = logging.getLogger(__name__)


class QdrantHelper:
    """Helper class for querying Qdrant vector database."""
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize Qdrant client.
        
        Args:
            persist_directory: Path to Qdrant storage (default: data/qdrant_storage)
        """
        if persist_directory is None:
            # Use your existing Qdrant storage location
            project_root = Path(__file__).resolve().parents[2]
            persist_directory = str(project_root / "data" / "qdrant_storage")
        
        self.persist_directory = persist_directory
        
        # ✅ FIX: Initialize embedding model (same as VectorStore)
        model_name = 'all-MiniLM-L6-v2'
        hf_token = os.getenv('HF_TOKEN')
        if hf_token:
            self.model = SentenceTransformer(model_name, token=hf_token)
        else:
            self.model = SentenceTransformer(model_name)
        
        # Initialize Qdrant client (local mode)
        try:
            self.client = QdrantClient(path=persist_directory)
            self.collection_name = "pe_companies"  # ✅ FIX: Match VectorStore collection name
            logger.info(f"[OK] Connected to Qdrant at {persist_directory}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise
    
    def search_company_context(
        self, 
        company_id: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict]:
        """
        Search for relevant context about a company using semantic search.
        
        Args:
            company_id: Company identifier (e.g., "Anthropic" or "anthropic")
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant text chunks with metadata
        """
        try:
            # ✅ FIX: Get actual company name from vector DB (handles case mismatch)
            # First, try to find the correct company name format
            actual_company_name = self._find_company_name(company_id)
            if not actual_company_name:
                logger.warning(f"⚠️ Company '{company_id}' not found in vector DB")
                return []
            
            # ✅ FIX: Embed the query text first (Qdrant needs vectors, not text)
            query_embedding = self.model.encode([query])[0]
            
            # ✅ FIX: Use "company_name" (matches VectorStore metadata)
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="company_name",  # ✅ FIX: Changed from "company_id"
                        match=MatchValue(value=actual_company_name)  # Use actual name from DB
                    )
                ]
            )
            
            # ✅ FIX: Use query_vector instead of query_text
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),  # ✅ FIX: Use vector, not text
                query_filter=query_filter,
                limit=limit
            )
            
            # Format results (match VectorStore format)
            formatted_results = []
            for hit in results:
                payload = hit.payload
                formatted_results.append({
                    "text": payload.get("text", ""),
                    "page_type": payload.get("page_type", "unknown"),
                    "company_name": payload.get("company_name", company_id),  # ✅ FIX: Use company_name
                    "score": hit.score,
                    "metadata": payload
                })
            
            logger.info(f"[OK] Found {len(formatted_results)} results for '{query}' in {actual_company_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error searching Qdrant: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_company_content(self, company_id: str) -> List[Dict]:
        """
        Get all indexed content for a company.
        
        Args:
            company_id: Company identifier (any case)
            
        Returns:
            List of all text chunks for the company
        """
        try:
            # ✅ FIX: Find actual company name (handles case mismatch)
            actual_company_name = self._find_company_name(company_id)
            if not actual_company_name:
                logger.warning(f"⚠️ Company '{company_id}' not found in vector DB")
                return []
            
            # ✅ FIX: Use "company_name" instead of "company_id"
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="company_name",  # ✅ FIX: Changed from "company_id"
                            match=MatchValue(value=actual_company_name)  # Use actual name
                        )
                    ]
                ),
                limit=100  # Adjust based on your data size
            )
            
            points, _ = results
            
            formatted_results = []
            for point in points:
                payload = point.payload
                formatted_results.append({
                    "text": payload.get("text", ""),
                    "page_type": payload.get("page_type", "unknown"),
                    "company_name": payload.get("company_name", company_id),  # ✅ FIX: Use company_name
                    "metadata": payload
                })
            
            logger.info(f"[OK] Retrieved {len(formatted_results)} chunks for {actual_company_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error getting company content: {e}")
            return []
    
    def _find_company_name(self, company_id: str) -> Optional[str]:
        """
        Find the actual company name in the vector DB (handles case-insensitive matching).
        
        Args:
            company_id: Company identifier (any case)
            
        Returns:
            Actual company name from DB, or None if not found
        """
        try:
            # Get all companies from vector DB
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            companies = set()
            for point in scroll_result[0]:
                companies.add(point.payload.get('company_name', ''))
            
            # Try exact match first
            if company_id in companies:
                return company_id
            
            # Try case-insensitive match
            company_id_lower = company_id.lower()
            for company in companies:
                if company.lower() == company_id_lower:
                    return company
            
            # Try with spaces/underscores variations
            company_id_normalized = company_id.replace('_', ' ').replace('-', ' ')
            for company in companies:
                company_normalized = company.replace('_', ' ').replace('-', ' ')
                if company_normalized.lower() == company_id_normalized.lower():
                    return company
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding company name: {e}")
            return None
    
    def check_collection_exists(self) -> bool:
        """Check if the collection exists."""
        try:
            collections = self.client.get_collections()
            exists = any(col.name == self.collection_name for col in collections.collections)
            return exists
        except Exception as e:
            logger.error(f"❌ Error checking collection: {e}")
            return False


# ✅ Prevent running this file directly (it's a module, not a script)
if __name__ == "__main__":
    print("="*70)
    print("ERROR: This file should not be run directly!")
    print("="*70)
    print("\nThis is a module file, not a script.")
    print("Import it in other files like this:")
    print("  from src.utils.qdrant_client import QdrantHelper")
    print("\nTo test the tools, run:")
    print("  python src/agents/tools.py")
    print("="*70)
    sys.exit(1)