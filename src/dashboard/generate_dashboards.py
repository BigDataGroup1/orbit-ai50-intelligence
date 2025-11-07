"""
Generate RAG dashboards for all companies
"""
from pathlib import Path
import sys
import json

# We're in src/dashboard/, so add src/ to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from vectordb.embedder import VectorStore
from dashboard.rag_generator import RAGDashboardGenerator


def main():
    print("="*70)
    print("GENERATING RAG DASHBOARDS FOR ALL COMPANIES")
    print("="*70)
    
    # Load vector store
    vector_store = VectorStore(use_docker=False)
    companies = vector_store.get_companies()
    
    print(f"\n📊 Found {len(companies)} companies")
    
    # Create generator
    generator = RAGDashboardGenerator(vector_store)
    
    # Output directory (go up 2 levels from src/dashboard/)
    output_dir = Path(__file__).resolve().parents[2] / "data" / "dashboards" / "rag"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate dashboards
    results = []
    successful = 0
    
    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] Generating: {company}")
        
        result = generator.generate_dashboard(company, max_chunks=20)
        results.append(result)
        
        if result['success']:
            # Save dashboard
            filename = company.replace(' ', '_').replace('/', '_') + '.md'
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result['dashboard'])
            
            successful += 1
            print(f"   ✅ Saved to {filename}")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
    
    # Save summary
    summary = {
        'total_companies': len(companies),
        'successful': successful,
        'failed': len(companies) - successful,
        'results': results
    }
    
    summary_file = output_dir / "_generation_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"DASHBOARD GENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"Successful: {successful}/{len(companies)}")
    print(f"Output: {output_dir}")
    print(f"Summary: {summary_file}")


if __name__ == "__main__":
    main()