"""
Build Qdrant vector index from scraped data (GCS or Local)
"""
from pathlib import Path
from chunker import TextChunker 

from embedder import VectorStore
import sys
from typing import List 

def build_vector_index(use_docker: bool = False, 
                      clear_existing: bool = True,
                      use_gcs: bool = True,
                      bucket_name: str = "orbit-raw-data-g1-2025"):
    """
    Build complete vector index for all companies.
    
    Args:
        use_docker: Use Docker Qdrant (else in-memory with persistence)
        clear_existing: Clear existing data before building
        use_gcs: Read from GCS bucket (else read from local data/raw/)
        bucket_name: GCS bucket name for raw data
    """
    
    print("="*70)
    print("BUILDING QDRANT VECTOR INDEX - LAB 4")
    print("="*70)
    print(f"Mode: {'Docker' if use_docker else 'In-memory (persistent)'}")
    print(f"Data source: {'GCS' if use_gcs else 'Local filesystem'}")
    print(f"Clear existing: {clear_existing}")
    
    # Initialize
    print("\nInitializing...")
    chunker = TextChunker(
        bucket_name=bucket_name,
        chunk_size=800, 
        overlap=100,
        use_gcs=use_gcs
    )
    vector_store = VectorStore(use_docker=use_docker)
    
    # Clear existing data if requested
    if clear_existing:
        vector_store.clear_collection()
    
    # Get company list
    if use_gcs:
        companies = get_companies_from_gcs(chunker.bucket)
    else:
        data_dir = Path(__file__).resolve().parents[2] / "data"
        raw_dir = data_dir / "raw"
        
        if not raw_dir.exists():
            print(f"❌ Raw data directory not found: {raw_dir}")
            return
        
        companies = sorted([d.name for d in raw_dir.iterdir() if d.is_dir()])
    
    print(f"\nFound {len(companies)} companies")
    print(f"\n{'='*70}")
    print("PROCESSING COMPANIES")
    print(f"{'='*70}\n")
    
    total_chunks = 0
    successful = 0
    
    # Process each company
    for i, company in enumerate(companies, 1):
        if use_gcs:
            # Company is string name
            company_name = company
            display_name = company.replace('_', ' ')
        else:
            # Company is Path object
            company_dir = Path(__file__).resolve().parents[2] / "data" / "raw" / company
            company_name = company
            display_name = company.replace('_', ' ')
        
        print(f"[{i:2d}/{len(companies)}] {display_name:30s}", end=" ")
        
        try:
            # Chunk files
            if use_gcs:
                chunks = chunker.chunk_company_files(company_name)
            else:
                chunks = chunker.chunk_company_files(company_dir, display_name)
            
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
            import traceback
            traceback.print_exc()
    
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
                print(f"      Score: {result['score']:.4f} | Session: {result['metadata']['session']}")
                print(f"      Text: {result['text'][:100]}...")
        else:
            print("   No results found")
    
    # Final message
    print(f"\n{'='*70}")
    print("✅ VECTOR INDEX BUILT SUCCESSFULLY!")
    print(f"{'='*70}")
    
    data_dir = Path(__file__).resolve().parents[2] / "data"
    print(f"\n📁 Storage location: {data_dir / 'qdrant_storage'}")
    print(f"   This directory will persist across runs")
    
    if use_gcs:
        print(f"\n☁️  Data source: gs://{bucket_name}/data/raw/")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. cd ../api")
    print(f"   2. python main.py")
    print(f"   3. Test: http://localhost:8000/docs")


def get_companies_from_gcs(bucket) -> List[str]:
    """Get list of all company folders in GCS bucket."""
    prefix = "data/raw/"
    
    # List all blobs
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    # Extract unique company names
    companies = set()
    for blob in blobs:
        # blob.name = "data/raw/Anthropic/2025-11-03_initial/homepage.txt"
        parts = blob.name.split('/')
        if len(parts) >= 3:
            company = parts[2]  # "Anthropic"
            companies.add(company)
    
    return sorted(list(companies))


if __name__ == "__main__":
    # Parse arguments
    use_docker = '--docker' in sys.argv
    no_clear = '--no-clear' in sys.argv
    use_local = '--local' in sys.argv  # Only use local if explicitly requested
    
    # ✅ DEFAULT TO GCS (production mode)
    use_gcs = not use_local  # Changed: Default to GCS unless --local is specified
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Usage: python build_index.py [OPTIONS]

Options:
  --local       Read from local data/raw/ folder (DEVELOPMENT ONLY)
  --gcs         Read from GCS bucket (DEFAULT - production mode)
  --docker      Use Docker Qdrant instance (default: in-memory)
  --no-clear    Don't clear existing data (default: clear and rebuild)
  -h, --help    Show this help message

Examples:
  python build_index.py                # DEFAULT: Read from GCS, build locally
  python build_index.py --local        # DEV: Read from local files
  python build_index.py --gcs --docker # GCS + Docker Qdrant
  
NOTE: GCS mode requires GOOGLE_APPLICATION_CREDENTIALS in .env
        """)
        sys.exit(0)
    
    # Show what mode we're using
    print(f"\n{'='*70}")
    print(f"DATA SOURCE: {'GCS (Production)' if use_gcs else 'Local (Development)'}")
    print(f"{'='*70}\n")
    
    build_vector_index(
        use_docker=use_docker, 
        clear_existing=not no_clear,
        use_gcs=use_gcs
    )