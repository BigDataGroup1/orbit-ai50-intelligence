"""
Qdrant Client Helper
Queries the existing Qdrant vector database for RAG search
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import List, Dict, Optional
import logging
from pathlib import Path
import os
from dotenv import load_dotenv

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
        
        # Initialize Qdrant client (local mode)
        try:
            self.client = QdrantClient(path=persist_directory)
            self.collection_name = "ai50_companies"  # Your collection name
            logger.info(f"✅ Connected to Qdrant at {persist_directory}")
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
            company_id: Company identifier (e.g., "Anthropic")
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant text chunks with metadata
        """
        try:
            # Search in Qdrant with company filter
            results = self.client.search(
                collection_name=self.collection_name,
                query_text=query,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="company_id",
                            match=MatchValue(value=company_id)
                        )
                    ]
                ),
                limit=limit
            )
            
            # Format results
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    "text": hit.payload.get("text", ""),
                    "page_type": hit.payload.get("page_type", "unknown"),
                    "company_id": hit.payload.get("company_id", company_id),
                    "score": hit.score,
                    "metadata": hit.payload
                })
            
            logger.info(f"✅ Found {len(formatted_results)} results for '{query}' in {company_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error searching Qdrant: {e}")
            return []
    
    def get_all_company_content(self, company_id: str) -> List[Dict]:
        """
        Get all indexed content for a company.
        
        Args:
            company_id: Company identifier
            
        Returns:
            List of all text chunks for the company
        """
        try:
            # Scroll through all points for this company
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="company_id",
                            match=MatchValue(value=company_id)
                        )
                    ]
                ),
                limit=100  # Adjust based on your data size
            )
            
            points, _ = results
            
            formatted_results = []
            for point in points:
                formatted_results.append({
                    "text": point.payload.get("text", ""),
                    "page_type": point.payload.get("page_type", "unknown"),
                    "company_id": point.payload.get("company_id", company_id),
                    "metadata": point.payload
                })
            
            logger.info(f"✅ Retrieved {len(formatted_results)} chunks for {company_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error getting company content: {e}")
            return []
    
    def check_collection_exists(self) -> bool:
        """Check if the collection exists."""
        try:
            collections = self.client.get_collections()
            exists = any(col.name == self.collection_name for col in collections.collections)
            return exists
        except Exception as e:
            logger.error(f"❌ Error checking collection: {e}")
            return False