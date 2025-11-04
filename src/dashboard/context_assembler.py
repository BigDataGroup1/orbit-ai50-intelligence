"""
Context assembly for RAG pipeline (Lab 6-lite)
"""
from typing import List, Dict
import sys
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from vectordb.embedder import VectorStore


class ContextAssembler:
    """Assembles context from vector search for RAG dashboard generation."""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize assembler.
        
        Args:
            vector_store: Loaded VectorStore instance
        """
        self.vector_store = vector_store
    
    def assemble_context(self, company_name: str, max_chunks: int = 20) -> Dict:
        """
        Retrieve and assemble context for a company.
        
        Args:
            company_name: Company to get context for
            max_chunks: Maximum chunks to retrieve
        
        Returns:
            Dict with context string and metadata
        """
        # Multi-query retrieval for comprehensive coverage
        queries = [
            f"{company_name} company overview product",
            f"{company_name} pricing business model revenue",
            f"{company_name} funding investors valuation",
            f"{company_name} CEO leadership team founders",
            f"{company_name} customers growth hiring"
        ]
        
        all_chunks = []
        seen_texts = set()
        
        print(f"\n🔍 Retrieving context for {company_name}...")
        
        for query in queries:
            results = self.vector_store.search(
                query=query,
                k=5,
                company_name=company_name
            )
            
            # Deduplicate by text content
            for result in results:
                text = result['text']
                if text not in seen_texts and len(text) > 50:
                    seen_texts.add(text)
                    all_chunks.append(result)
            
            if len(all_chunks) >= max_chunks:
                break
        
        print(f"   Retrieved {len(all_chunks)} unique chunks")
        
        if not all_chunks:
            return {
                'context': f"No information available for {company_name}.",
                'chunks_used': 0,
                'page_types': [],
                'success': False
            }
        
        # Sort by relevance (score)
        all_chunks = sorted(all_chunks, key=lambda x: x['score'], reverse=True)
        all_chunks = all_chunks[:max_chunks]
        
        # Format context
        context_parts = []
        page_types = set()
        
        for i, chunk in enumerate(all_chunks, 1):
            page_type = chunk['metadata']['page_type']
            page_types.add(page_type)
            
            context_parts.append(
                f"[Source {i}: {page_type} page]\n"
                f"{chunk['text']}\n"
            )
        
        context = "\n\n".join(context_parts)
        
        return {
            'context': context,
            'chunks_used': len(all_chunks),
            'page_types': sorted(list(page_types)),
            'avg_score': sum(c['score'] for c in all_chunks) / len(all_chunks),
            'success': True
        }


def test_assembler():
    """Test context assembly."""
    print("="*70)
    print("TESTING CONTEXT ASSEMBLER")
    print("="*70)
    
    # Load vector store
    from vectordb.embedder import VectorStore
    vector_store = VectorStore(use_docker=False)
    
    # Test assembly
    assembler = ContextAssembler(vector_store)
    
    # Test on Anthropic
    result = assembler.assemble_context("Anthropic", max_chunks=10)
    
    print(f"\n✅ Context assembled:")
    print(f"   Chunks used: {result['chunks_used']}")
    print(f"   Page types: {result['page_types']}")
    print(f"   Avg score: {result.get('avg_score', 0):.3f}")
    print(f"   Context length: {len(result['context'])} chars")
    
    print(f"\n📄 Sample context (first 500 chars):")
    print(result['context'][:500])
    print("...")


if __name__ == "__main__":
    test_assembler()