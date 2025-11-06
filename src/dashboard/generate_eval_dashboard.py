"""
Generate RAG dashboards for 5 evaluation companies (Lab 9)
"""
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from vectordb.embedder import VectorStore
from dashboard.rag_generator import RAGDashboardGenerator


# THE 5 COMPANIES FOR EVALUATION
EVAL_COMPANIES = [
    "Abridge",
    "Anthropic", 
    "Anysphere",
    "Baseten",
    "Clay"
]


def main():
    print("="*70)
    print("GENERATING RAG DASHBOARDS - 5 EVALUATION COMPANIES")
    print("="*70)
    
    # Load vector store
    vector_store = VectorStore(use_docker=False)
    
    # Create generator
    generator = RAGDashboardGenerator(vector_store)
    
    print(f"\n📋 Evaluation companies:")
    for company in EVAL_COMPANIES:
        print(f"   - {company}")
    
    print(f"\n{'='*70}")
    
    successful = 0
    
    for i, company in enumerate(EVAL_COMPANIES, 1):
        print(f"\n[{i}/5] Generating: {company}")
        
        result = generator.generate_dashboard(company, max_chunks=20)
        
        if result['success']:
            successful += 1
            print(f"✅ Generated successfully")
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    print(f"\n{'='*70}")
    print(f"COMPLETE: {successful}/5 dashboards generated")
    print(f"{'='*70}")
    
    output_dir = Path(__file__).resolve().parents[2] / "data" / "dashboards" / "rag"
    print(f"\n📁 Output: {output_dir}")
    print(f"\n📋 Files per company:")
    print(f"   - <company>.md (dashboard)")
    print(f"   - <company>_eval.json (evaluation metadata)")
    
    print(f"\n🤝 Coordinate with teammate:")
    print(f"   They should generate structured dashboards for these same 5 companies")


if __name__ == "__main__":
    main()