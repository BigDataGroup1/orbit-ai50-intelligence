"""
Generate complete EVAL.md report
"""
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent))

# Import from the actual filename (with typo)
from compare_piplines import PipelineComparator


def main():
    print("="*70)
    print("GENERATING EVAL.MD REPORT")
    print("="*70)
    
    comparator = PipelineComparator()
    
    # Check data availability
    print("\n📋 Checking evaluation data...")
    comparator.check_data_availability()
    
    # Check if we have both pipelines
    rag_count = sum(1 for c in comparator.eval_companies 
                   if (comparator.rag_dashboard_dir / f"{c.replace(' ', '_')}_eval.json").exists())
    
    struct_count = sum(1 for c in comparator.eval_companies 
                      if (comparator.structured_dashboard_dir / f"{c.replace(' ', '_')}_eval.json").exists())
    
    print(f"\n📊 Data Status:")
    print(f"   RAG: {rag_count}/{len(comparator.eval_companies)} companies")
    print(f"   Structured: {struct_count}/{len(comparator.eval_companies)} companies")
    
    if rag_count < len(comparator.eval_companies):
        print(f"\n⚠️  Warning: RAG data incomplete")
        print(f"   Run: python src/rag/generate_eval_dashboards.py")
    
    if struct_count < len(comparator.eval_companies):
        print(f"\n⚠️  Warning: Structured data incomplete")
        print(f"   Run: python src/structured/generate_eval_structured.py")
    
    if rag_count == len(comparator.eval_companies) and struct_count == len(comparator.eval_companies):
        print(f"\n✅ All evaluation data complete!")
        
        # Generate the report
        print("\n📝 Generating EVAL.md...")
        output_path = comparator.generate_eval_md()
        
        print(f"\n✅ EVAL.md created!")
        print(f"   Location: {output_path}")
        print(f"\n📝 Next steps:")
        print(f"   1. Open EVAL.md")
        print(f"   2. Review the auto-generated comparison table")
        print(f"   3. Fill in the [TODO] analysis sections")
        print(f"   4. Add team reflection (1 page)")
        print(f"   5. Review scores and adjust if needed")
        print(f"   6. Commit to repo")
    else:
        print(f"\n⏳ Cannot generate complete report yet")
        print(f"   Need evaluation data from both pipelines")


if __name__ == "__main__":
    main()