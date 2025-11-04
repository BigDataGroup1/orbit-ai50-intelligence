"""
Qdrant-based vector store for RAG pipeline
"""
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)
from typing import List, Dict, Optional
from pathlib import Path
import uuid


class VectorStore:
    """Qdrant-based vector store for company documents."""
    
    def __init__(self, 
                 model_name: str = 'all-MiniLM-L6-v2',
                 use_docker: bool = False,
                 data_dir: Optional[Path] = None):
        """
        Initialize vector store with Qdrant.
        
        Args:
            model_name: Sentence transformer model for embeddings
            use_docker: If True, connect to Docker Qdrant. If False, use in-memory
            data_dir: Directory for persistent storage (in-memory mode only)
        """
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        self.collection_name = "pe_companies"
        
        # Initialize Qdrant client
        if use_docker:
            # Connect to Docker instance at localhost:6333
            self.client = QdrantClient(host="localhost", port=6333)
            print("✅ Connected to Qdrant Docker instance")
        else:
            # In-memory mode with persistent storage
            if data_dir is None:
                data_dir = Path(__file__).resolve().parents[2] / "data" / "qdrant_storage"
            
            data_dir.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(data_dir))
            print(f"✅ Using Qdrant in-memory mode")
            print(f"   Storage: {data_dir}")
        
        self.ensure_collection()
    
    def ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created collection: {self.collection_name}")
            else:
                print(f"✅ Collection exists: {self.collection_name}")
        except Exception as e:
            print(f"⚠️  Error ensuring collection: {e}")
    
    def clear_collection(self):
        """Delete and recreate collection (fresh start)."""
        try:
            self.client.delete_collection(self.collection_name)
            print("🗑️  Deleted existing collection")
        except:
            pass
        
        self.ensure_collection()
    
    def add_chunks(self, chunks: List[Dict]):
        """
        Add chunks to vector store.
        
        Args:
            chunks: List of {text, metadata, tokens}
        """
        if not chunks:
            return
        
        print(f"   Embedding {len(chunks)} chunks...", end=" ", flush=True)
        
        # Extract texts
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Prepare points for Qdrant
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={
                    'text': chunk['text'],
                    'company_name': chunk['metadata']['company_name'],
                    'page_type': chunk['metadata']['page_type'],
                    'session': chunk['metadata']['session'],
                    'source_file': chunk['metadata']['source_file'],
                    'tokens': chunk['tokens']
                }
            )
            points.append(point)
        
        # Upload to Qdrant in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
        
        print(f"✅")
    
    def search(self, 
               query: str, 
               k: int = 5, 
               company_name: Optional[str] = None,
               page_type: Optional[str] = None) -> List[Dict]:
        """
        Search for relevant chunks.
        
        Args:
            query: Search query
            k: Number of results to return
            company_name: Optional - filter by specific company
            page_type: Optional - filter by page type (homepage, about, pricing, etc.)
        
        Returns:
            List of results with format:
            {
                'text': str,
                'metadata': dict,
                'score': float,
                'tokens': int
            }
        """
        # Embed query
        query_embedding = self.model.encode([query])[0]
        
        # Build filter conditions
        filter_conditions = []
        
        if company_name:
            filter_conditions.append(
                FieldCondition(
                    key="company_name",
                    match=MatchValue(value=company_name)
                )
            )
        
        if page_type:
            filter_conditions.append(
                FieldCondition(
                    key="page_type",
                    match=MatchValue(value=page_type)
                )
            )
        
        query_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=k,
            query_filter=query_filter
        )
        
        # Format results
        results = []
        for hit in search_results:
            results.append({
                'text': hit.payload['text'],
                'metadata': {
                    'company_name': hit.payload['company_name'],
                    'page_type': hit.payload['page_type'],
                    'session': hit.payload['session'],
                    'source_file': hit.payload['source_file']
                },
                'score': hit.score,
                'tokens': hit.payload['tokens']
            })
        
        return results
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                'total_chunks': collection_info.points_count,
                'vector_dimension': self.dimension,
                'distance_metric': 'COSINE'
            }
        except Exception as e:
            return {
                'total_chunks': 0,
                'vector_dimension': self.dimension,
                'distance_metric': 'COSINE',
                'error': str(e)
            }
    
    def get_companies(self) -> List[str]:
        """Get list of all companies in vector store."""
        try:
            companies = set()
            
            # Scroll through all points
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            for point in scroll_result[0]:
                companies.add(point.payload['company_name'])
            
            return sorted(list(companies))
        except Exception as e:
            print(f"Error getting companies: {e}")
            return []


def main():
    """Test vector store."""
    print("\nTesting VectorStore...")
    
    # Test chunks
    test_chunks = [
        {
            'text': 'Anthropic builds safe AI systems including Claude.',
            'metadata': {
                'company_name': 'Anthropic',
                'page_type': 'homepage',
                'session': 'test',
                'source_file': 'test.txt'
            },
            'tokens': 10
        },
        {
            'text': 'We offer usage-based pricing starting at $10 per million tokens.',
            'metadata': {
                'company_name': 'Anthropic',
                'page_type': 'pricing',
                'session': 'test',
                'source_file': 'test.txt'
            },
            'tokens': 12
        }
    ]
    
    # Initialize
    store = VectorStore(use_docker=False)
    store.clear_collection()
    
    # Add chunks
    print("\nAdding test chunks...")
    store.add_chunks(test_chunks)
    
    # Get stats
    stats = store.get_stats()
    print(f"\nStats: {stats}")
    
    # Test search
    print("\nSearching for 'pricing'...")
    results = store.search('pricing', k=2)
    
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  Company: {result['metadata']['company_name']}")
        print(f"  Page: {result['metadata']['page_type']}")
        print(f"  Score: {result['score']:.4f}")
        print(f"  Text: {result['text']}")
    
    print("\n✅ VectorStore test complete!")


if __name__ == "__main__":
    main()