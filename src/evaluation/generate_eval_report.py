"""
Generate complete EVAL.md report
"""
from pathlib import Path
from compare_pipelines import PipelineComparator


def main():
    print("="*70)
    print("GENERATING EVAL.MD REPORT")
    print("="*70)
    
    comparator = PipelineComparator()
    
    # Check data availability
    print("\n📋 Checking evaluation data...")
    comparator.print_summary()
    
    # Check if we have both pipelines
    rag_count = sum(1 for c in comparator.eval_companies 
                   if (comparator.rag_dir / f"{c.replace(' ', '_')}_eval.json").exists())
    
    struct_count = sum(1 for c in comparator.eval_companies 
                      if (comparator.structured_dir / f"{c.replace(' ', '_')}_eval.json").exists())
    
    print(f"\n📊 Data Status:")
    print(f"   RAG: {rag_count}/5 companies")
    print(f"   Structured: {struct_count}/5 companies")
    
    if rag_count < 5:
        print(f"\n⚠️  Warning: RAG data incomplete")
        print(f"   Run: python src/dashboard/generate_eval_dashboards.py")
    
    if struct_count < 5:
        print(f"\n⚠️  Warning: Structured data incomplete")
        print(f"   Waiting for teammate to complete Labs 5-8")
    
    if rag_count == 5 and struct_count == 5:
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
        print(f"   4. Add team reflection")
        print(f"   5. Review scores and adjust if needed")
        print(f"   6. Commit to repo")
    else:
        print(f"\n⏳ Cannot generate complete report yet")
        print(f"   Need evaluation data from both pipelines")


if __name__ == "__main__":
    main()