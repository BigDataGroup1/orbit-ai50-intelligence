"""
Build Qdrant vector index from scraped data
"""
from pathlib import Path
from chunker import TextChunker
from embedder import VectorStore
import sys


def build_vector_index(use_docker: bool = False, clear_existing: bool = True):
    """
    Build complete vector index for all companies.
    
    Args:
        use_docker: Use Docker Qdrant (else in-memory with persistence)
        clear_existing: Clear existing data before building
    """
    
    # Paths
    data_dir = Path(__file__).resolve().parents[2] / "data"
    raw_dir = data_dir / "raw"
    
    if not raw_dir.exists():
        print(f"❌ Raw data directory not found: {raw_dir}")
        print("   Run Lab 1 scraper first!")
        return
    
    print("="*70)
    print("BUILDING QDRANT VECTOR INDEX - LAB 4")
    print("="*70)
    print(f"Mode: {'Docker' if use_docker else 'In-memory (persistent)'}")
    print(f"Clear existing: {clear_existing}")
    
    # Initialize
    print("\nInitializing...")
    chunker = TextChunker(chunk_size=800, overlap=100)
    vector_store = VectorStore(use_docker=use_docker)  # Remove data_dir parameter
    
    # Clear existing data if requested
    if clear_existing:
        vector_store.clear_collection()
    
    # Get all companies
    companies = sorted([d for d in raw_dir.iterdir() if d.is_dir()])
    print(f"\nFound {len(companies)} companies in {raw_dir}")
    print(f"\n{'='*70}")
    print("PROCESSING COMPANIES")
    print(f"{'='*70}\n")
    
    total_chunks = 0
    successful = 0
    
    # Process each company
    for i, company_dir in enumerate(companies, 1):
        company_name = company_dir.name.replace('_', ' ')
        
        print(f"[{i:2d}/{len(companies)}] {company_name:30s}", end=" ")
        
        try:
            # Chunk files
            chunks = chunker.chunk_company_files(company_dir, company_name)
            
            if chunks:
                # Add to vector store
                vector_store.add_chunks(chunks)
                total_chunks += len(chunks)
                successful += 1
                print(f"({len(chunks)} chunks)")
            else:
                print(f"⚠️  No data")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Final statistics
    print(f"\n{'='*70}")
    print("INDEX COMPLETE")
    print(f"{'='*70}")
    
    stats = vector_store.get_stats()
    companies_in_index = vector_store.get_companies()
    
    print(f"\n📊 Statistics:")
    print(f"   Companies processed: {len(companies)}")
    print(f"   Companies successful: {successful}")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Companies in index: {len(companies_in_index)}")
    print(f"   Vector dimension: {stats['vector_dimension']}")
    print(f"   Distance metric: {stats['distance_metric']}")
    
    # Test searches
    print(f"\n{'='*70}")
    print("TEST SEARCHES")
    print(f"{'='*70}")
    
    test_queries = [
        ("What is the pricing model?", None, None),
        ("leadership team and CEO", None, None),
        ("funding and investors", None, None),
    ]
    
    # Add company-specific test if Anthropic exists
    if 'Anthropic' in companies_in_index:
        test_queries.append(("Claude AI assistant", "Anthropic", None))
    
    for query, company, page_type in test_queries:
        filters = []
        if company:
            filters.append(f"company={company}")
        if page_type:
            filters.append(f"page_type={page_type}")
        
        filter_str = f" [{', '.join(filters)}]" if filters else ""
        print(f"\n🔍 Query: \"{query}\"{filter_str}")
        
        results = vector_store.search(
            query=query, 
            k=3,
            company_name=company,
            page_type=page_type
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['metadata']['company_name']} - {result['metadata']['page_type']}")
                print(f"      Score: {result['score']:.4f} | Tokens: {result['tokens']}")
                print(f"      Text: {result['text'][:120]}...")
        else:
            print("   No results found")
    
    # Final message
    print(f"\n{'='*70}")
    print("✅ VECTOR INDEX BUILT SUCCESSFULLY!")
    print(f"{'='*70}")
    
    if not use_docker:
        print(f"\n📁 Storage location: {data_dir / 'qdrant_storage'}")
        print(f"   This directory will persist across runs")
    else:
        print(f"\n🐳 Qdrant Dashboard: http://localhost:6333/dashboard")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. cd ../api")
    print(f"   2. python main.py")
    print(f"   3. Test endpoint: curl -X POST http://localhost:8000/rag/search \\")
    print(f"        -H 'Content-Type: application/json' \\")
    print(f"        -d '{{\"query\": \"pricing model\", \"k\": 5}}'")


if __name__ == "__main__":
    # Check for flags
    use_docker = '--docker' in sys.argv
    no_clear = '--no-clear' in sys.argv
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Usage: python build_index.py [OPTIONS]

Options:
  --docker      Use Docker Qdrant instance (default: in-memory)
  --no-clear    Don't clear existing data (default: clear and rebuild)
  -h, --help    Show this help message

Examples:
  python build_index.py              # In-memory, clear existing
  python build_index.py --docker     # Docker, clear existing
  python build_index.py --no-clear   # In-memory, append to existing
        """)
        sys.exit(0)
    
    build_vector_index(use_docker=use_docker, clear_existing=not no_clear)