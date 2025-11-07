"""
Lab 9: Compare RAG vs Structured Pipelines
"""
from pathlib import Path
import json
from typing import Dict, List
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))


class PipelineComparator:
    """Compare RAG and Structured pipeline outputs."""
    
    def __init__(self):
        self.data_dir = Path(__file__).resolve().parents[2] / "data" / "dashboards"
        self.rag_dir = self.data_dir / "rag"
        self.structured_dir = self.data_dir / "structured"
        
        # 5 evaluation companies (same as RAG generation)
        self.eval_companies = [
            "Abridge",
            "Anthropic",
            "Anysphere",
            "Baseten",
            "Clay"
        ]
    
    def load_eval_json(self, company: str, pipeline: str) -> Dict:
        """
        Load evaluation JSON for a company.
        
        Args:
            company: Company name
            pipeline: 'rag' or 'structured'
        
        Returns:
            Evaluation data dict or None
        """
        company_clean = company.replace(' ', '_')
        
        if pipeline == 'rag':
            path = self.rag_dir / f"{company_clean}_eval.json"
        else:
            path = self.structured_dir / f"{company_clean}_eval.json"
        
        if not path.exists():
            print(f"⚠️  File not found: {path}")
            return None
        
        with open(path, 'r') as f:
            return json.load(f)
    
    def compare_company(self, company: str) -> Dict:
        """
        Compare RAG vs Structured for one company.
        
        Returns:
            Comparison dict with scores and analysis
        """
        rag_data = self.load_eval_json(company, 'rag')
        structured_data = self.load_eval_json(company, 'structured')
        
        if not rag_data:
            return {
                'company': company,
                'error': 'RAG evaluation data missing',
                'rag_available': False,
                'structured_available': structured_data is not None
            }
        
        if not structured_data:
            return {
                'company': company,
                'error': 'Structured evaluation data missing',
                'rag_available': True,
                'structured_available': False
            }
        
        # Extract scores
        rag_scores = rag_data.get('rubric_scores', {})
        structured_scores = structured_data.get('rubric_scores', {})
        
        # Get totals (pre-calculated)
        rag_total = rag_data.get('total_score', 0)
        structured_total = structured_data.get('total_score', 0)
        
        return {
            'company': company,
            'rag': {
                'factual': rag_scores.get('factual_correctness', 0),
                'schema': rag_scores.get('schema_adherence', 0),
                'provenance': rag_scores.get('provenance_use', 0),
                'hallucination': rag_scores.get('hallucination_control', 0),
                'readability': rag_scores.get('readability', 0),
                'total': rag_total
            },
            'structured': {
                'factual': structured_scores.get('factual_correctness', 0),
                'schema': structured_scores.get('schema_adherence', 0),
                'provenance': structured_scores.get('provenance_use', 0),
                'hallucination': structured_scores.get('hallucination_control', 0),
                'readability': structured_scores.get('readability', 0),
                'total': structured_total
            },
            'winner': 'RAG' if rag_total > structured_total else ('Structured' if structured_total > rag_total else 'Tie'),
            'difference': abs(rag_total - structured_total),
            'metadata': {
                'rag': rag_data.get('metadata', {}),
                'structured': structured_data.get('metadata', {})
            }
        }
    
    def generate_comparison_table(self) -> str:
        """Generate markdown comparison table for all 5 companies."""
        
        print("\n📊 Comparing companies...")
        results = []
        
        for company in self.eval_companies:
            comparison = self.compare_company(company)
            results.append(comparison)
            
            if 'error' not in comparison:
                print(f"   ✅ {company}: RAG={comparison['rag']['total']}, Structured={comparison['structured']['total']}, Winner={comparison['winner']}")
            else:
                print(f"   ⚠️  {company}: {comparison['error']}")
        
        # Build markdown table
        table = """
| Company | RAG Fact | RAG Schema | RAG Prov | RAG Halluc | RAG Read | RAG Total | Struct Fact | Struct Schema | Struct Prov | Struct Halluc | Struct Read | Struct Total | Winner |
|---------|----------|------------|----------|------------|----------|-----------|-------------|---------------|-------------|---------------|-------------|--------------|--------|
"""
        
        for r in results:
            if 'error' in r:
                table += f"| {r['company']} | - | - | - | - | - | - | - | - | - | - | - | - | {r['error']} |\n"
            else:
                rag = r['rag']
                struct = r['structured']
                winner_emoji = "🏆" if r['winner'] != 'Tie' else "🤝"
                table += (
                    f"| {r['company']} "
                    f"| {rag['factual']}/3 "
                    f"| {rag['schema']}/2 "
                    f"| {rag['provenance']}/2 "
                    f"| {rag['hallucination']}/2 "
                    f"| {rag['readability']}/1 "
                    f"| **{rag['total']}/10** "
                    f"| {struct['factual']}/3 "
                    f"| {struct['schema']}/2 "
                    f"| {struct['provenance']}/2 "
                    f"| {struct['hallucination']}/2 "
                    f"| {struct['readability']}/1 "
                    f"| **{struct['total']}/10** "
                    f"| {winner_emoji} {r['winner']} |\n"
                )
        
        # Summary stats
        valid_results = [r for r in results if 'error' not in r]
        
        if valid_results:
            rag_wins = sum(1 for r in valid_results if r['winner'] == 'RAG')
            struct_wins = sum(1 for r in valid_results if r['winner'] == 'Structured')
            ties = sum(1 for r in valid_results if r['winner'] == 'Tie')
            
            rag_avg = sum(r['rag']['total'] for r in valid_results) / len(valid_results)
            struct_avg = sum(r['structured']['total'] for r in valid_results) / len(valid_results)
            
            summary = f"""
## Summary Statistics

**Overall Results:**
- RAG wins: {rag_wins}/{len(valid_results)}
- Structured wins: {struct_wins}/{len(valid_results)}
- Ties: {ties}/{len(valid_results)}

**Average Scores:**
- RAG average: **{rag_avg:.2f}/10**
- Structured average: **{struct_avg:.2f}/10**
- Difference: {abs(rag_avg - struct_avg):.2f} points

**Score Breakdown by Criterion:**

| Criterion | RAG Avg | Structured Avg |
|-----------|---------|----------------|
| Factual Correctness | {sum(r['rag']['factual'] for r in valid_results)/len(valid_results):.2f}/3 | {sum(r['structured']['factual'] for r in valid_results)/len(valid_results):.2f}/3 |
| Schema Adherence | {sum(r['rag']['schema'] for r in valid_results)/len(valid_results):.2f}/2 | {sum(r['structured']['schema'] for r in valid_results)/len(valid_results):.2f}/2 |
| Provenance Use | {sum(r['rag']['provenance'] for r in valid_results)/len(valid_results):.2f}/2 | {sum(r['structured']['provenance'] for r in valid_results)/len(valid_results):.2f}/2 |
| Hallucination Control | {sum(r['rag']['hallucination'] for r in valid_results)/len(valid_results):.2f}/2 | {sum(r['structured']['hallucination'] for r in valid_results)/len(valid_results):.2f}/2 |
| Readability | {sum(r['rag']['readability'] for r in valid_results)/len(valid_results):.2f}/1 | {sum(r['structured']['readability'] for r in valid_results)/len(valid_results):.2f}/1 |
"""
        else:
            summary = "\n## Summary Statistics\n\nNo valid comparisons available.\n"
        
        return table + summary
    
    def generate_eval_md(self, output_path: Path = None):
        """Generate complete EVAL.md report."""
        
        if output_path is None:
            output_path = Path(__file__).resolve().parents[2] / "EVAL.md"
        
        comparison_table = self.generate_comparison_table()
        
        eval_content = f"""# Lab 9: RAG vs Structured Pipeline Evaluation

**Team:** [Your Names]  
**Date:** {datetime.now().strftime('%Y-%m-%d')}

---

## Evaluation Overview

This report compares two approaches for generating PE investment dashboards:
1. **RAG Pipeline (Unstructured):** Vector DB → Retrieval → LLM synthesis
2. **Structured Pipeline:** Pydantic extraction → Payload assembly → LLM generation

**Evaluation Companies:** 5 companies from Forbes AI 50
- Abridge
- Anthropic
- Anysphere
- Baseten
- Clay

---

## Scoring Rubric (10 points total)

| Criterion | Points | Description |
|-----------|--------|-------------|
| **Factual correctness** | 0-3 | Accuracy of claims vs. source documents |
| **Schema adherence** | 0-2 | Follows 8-section dashboard template |
| **Provenance use** | 0-2 | Transparency of sources and citations |
| **Hallucination control** | 0-2 | Avoids inventing facts, uses "Not disclosed" |
| **Readability** | 0-1 | Clarity and investor usefulness |

---

## Comparison Results

{comparison_table}

---

## Detailed Analysis

### RAG Pipeline Strengths

**What RAG did well:**
- [TODO: Analyze where RAG excelled - e.g., synthesis, handling diverse sources, context integration]
- Example: "RAG pipeline effectively synthesized information from multiple page types, providing comprehensive context"

### RAG Pipeline Weaknesses

**What RAG struggled with:**
- [TODO: Analyze RAG limitations - e.g., hallucination risk, dependency on chunk quality]
- Example: "Limited by retrieval quality - low relevance scores led to weaker factual grounding"

### Structured Pipeline Strengths

**What Structured did well:**
- [TODO: Analyze structured advantages - e.g., precision, field extraction, data quality]
- Example: "Structured extraction ensured precise field-level data capture"

### Structured Pipeline Weaknesses

**What Structured struggled with:**
- [TODO: Analyze structured limitations - e.g., brittleness, missing unstructured insights]
- Example: "Struggled with unstructured text that didn't fit Pydantic schemas"

---

## Key Findings

### Factual Accuracy
[TODO: Compare factual correctness scores and analyze why one performed better]

### Schema Compliance
[TODO: Did both pipelines follow the 8-section format? Any differences?]

### Source Transparency
[TODO: Which pipeline better tracked and cited sources?]

### Hallucination Patterns
[TODO: How did each pipeline handle missing data? Compare "Not disclosed" usage]

### Investor Usefulness
[TODO: Which dashboards were more actionable for investors?]

---

## Recommendations

Based on this evaluation, we recommend:

**Use RAG when:**
- [TODO: Scenarios where RAG is better]

**Use Structured when:**
- [TODO: Scenarios where Structured is better]

**Hybrid Approach:**
- [TODO: Could we combine both? How?]

---

## Reflection (1-page)

### What We Learned About RAG

[TODO: Personal insights on building RAG pipeline]
- Chunking strategy impact
- Vector search quality factors
- LLM synthesis capabilities
- Data freshness tracking

### What We Learned About Structured Extraction

[TODO: Insights from teammate on structured approach]
- Pydantic schema design
- Field extraction challenges
- Payload assembly complexity

### The RAG vs Structured Trade-off

**RAG Approach:**
- **Pros:** [TODO: Flexibility, handles diverse formats, good at synthesis]
- **Cons:** [TODO: Retrieval quality dependency, potential hallucination]

**Structured Approach:**
- **Pros:** [TODO: Precision, explicit schemas, type safety]
- **Cons:** [TODO: Brittleness, requires predefined schemas]

### When to Use Each

**RAG is ideal when:**
- Source data is diverse and unstructured
- Need to synthesize across many documents
- Schema is flexible or evolving
- Broader context is valuable

**Structured is ideal when:**
- Data has clear, consistent fields
- Precision is critical
- Type validation is needed
- Schema is well-defined upfront

### Technical Insights

**What worked well:**
- [TODO: GCS integration, daily refresh merge, Qdrant performance]

**What we'd improve:**
- [TODO: Better chunking strategies, hybrid approach, more robust evaluation]

### Future Enhancements

If we had more time:
1. [TODO: Hybrid pipeline combining both approaches]
2. [TODO: Better evaluation metrics beyond GPT self-assessment]
3. [TODO: Incremental updates instead of full rebuilds]
4. [TODO: More sophisticated source attribution]

---

## Conclusion

[TODO: Final verdict - which pipeline performed better overall and why]

---

*Auto-generated comparison table. Analysis sections filled by team.*
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(eval_content)
        
        print(f"\n✅ EVAL.md generated: {output_path}")
        
        return output_path
    
    def print_summary(self):
        """Print summary of available evaluation data."""
        print("\n" + "="*70)
        print("EVALUATION DATA SUMMARY")
        print("="*70)
        
        for company in self.eval_companies:
            rag_file = self.rag_dir / f"{company.replace(' ', '_')}_eval.json"
            struct_file = self.structured_dir / f"{company.replace(' ', '_')}_eval.json"
            
            rag_exists = rag_file.exists()
            struct_exists = struct_file.exists()
            
            status = "✅" if (rag_exists and struct_exists) else "⚠️"
            
            print(f"\n{status} {company}")
            print(f"   RAG: {'✅ Available' if rag_exists else '❌ Missing'}")
            print(f"   Structured: {'✅ Available' if struct_exists else '❌ Missing'}")
            
            if rag_exists and struct_exists:
                comparison = self.compare_company(company)
                if 'error' not in comparison:
                    print(f"   RAG Score: {comparison['rag']['total']}/10")
                    print(f"   Structured Score: {comparison['structured']['total']}/10")
                    print(f"   Winner: {comparison['winner']}")


def main():
    """Test comparison logic."""
    print("="*70)
    print("LAB 9: PIPELINE COMPARISON CHECKER")
    print("="*70)
    
    comparator = PipelineComparator()
    
    # Check which files exist
    comparator.print_summary()
    
    # Try to generate comparison
    print("\n" + "="*70)
    print("GENERATING COMPARISON TABLE")
    print("="*70)
    
    try:
        table = comparator.generate_comparison_table()
        print("\n📊 Comparison Table Preview:")
        print(table[:500])
        print("...")
    except Exception as e:
        print(f"❌ Cannot generate full comparison yet: {e}")
        print("   Waiting for structured pipeline data")


if __name__ == "__main__":
    main()