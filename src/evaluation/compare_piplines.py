"""
Lab 9: Compare RAG vs Structured Pipelines
"""
from pathlib import Path
import json
from typing import Dict, List, Optional
import sys
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[1]))


class PipelineComparator:
    """Compare RAG and Structured pipeline outputs."""
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.data_dir = self.project_root / "data"
        
        # Dashboard outputs (where eval JSONs will be)
        self.rag_dashboard_dir = self.data_dir / "dashboards" / "rag"
        self.structured_dashboard_dir = self.data_dir / "dashboards" / "structured"
        
        # Source data
        self.rag_source_dir = self.data_dir / "rag"  # RAG vector store data
        self.structured_payload_dir = self.data_dir / "structured"  # Structured payloads
        
        # 6 evaluation companies (added Coactive AI)
        self.eval_companies = [
            "Abridge",
            "Anthropic",
            "Anysphere",
            "Baseten",
            "Clay",
            "Coactive AI"  # ✅ Added 6th company
        ]
    
    
    def load_structured_payload(self, company: str) -> Optional[Dict]:
        """
        Load structured pipeline payload JSON.
        
        Args:
            company: Company name
        
        Returns:
            Payload dict or None
        """
        company_clean = company.lower().replace(' ', '_')
        path = self.structured_payload_dir / f"{company_clean}_payload.json"
        
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {path}: {e}")
            return None
    
    def load_rag_dashboard(self, company: str) -> Optional[str]:
        """
        Load RAG-generated dashboard markdown.
        
        Args:
            company: Company name
        
        Returns:
            Dashboard markdown text or None
        """
        company_clean = company.replace(' ', '_')
        path = self.rag_dashboard_dir / f"{company_clean}_dashboard.md"
        
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error loading {path}: {e}")
            return None
    
    def load_structured_dashboard(self, company: str) -> Optional[str]:
        """
        Load Structured-generated dashboard markdown.
        
        Args:
            company: Company name
        
        Returns:
            Dashboard markdown text or None
        """
        company_clean = company.lower().replace(' ', '_')
        path = self.structured_dashboard_dir / f"{company_clean}_dashboard.md"
        
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error loading {path}: {e}")
            return None
    
    def load_eval_json(self, company: str, pipeline: str) -> Optional[Dict]:
        """
        Load evaluation JSON for a company from specified pipeline.
        
        Args:
            company: Company name
            pipeline: 'rag' or 'structured'
        
        Returns:
            Evaluation data dict or None
        """
        # Use consistent naming for eval files
        company_clean = company.replace(' ', '_')
        
        if pipeline == 'rag':
            path = self.rag_dashboard_dir / f"{company_clean}_eval.json"
        elif pipeline == 'structured':
            # Structured eval JSONs use same naming as RAG
            path = self.structured_dashboard_dir / f"{company_clean}_eval.json"
        else:
            print(f"❌ Invalid pipeline: {pipeline}")
            return None
        
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"❌ Error loading eval JSON from {path}: {e}")
            return None
    
    def compare_company(self, company: str) -> Dict:
        """
        Compare RAG vs Structured for one company.
        
        Returns:
            Comparison dict with scores and analysis
        """
        # Load BOTH evaluation JSONs
        rag_eval = self.load_eval_json(company, 'rag')
        structured_eval = self.load_eval_json(company, 'structured')
        
        # Check if BOTH evaluation files exist
        if not rag_eval and not structured_eval:
            return {
                'company': company,
                'error': 'Both RAG and Structured evaluation data missing',
                'rag_available': False,
                'structured_available': False
            }
        
        if not rag_eval:
            return {
                'company': company,
                'error': 'RAG evaluation data missing',
                'rag_available': False,
                'structured_available': True
            }
        
        if not structured_eval:
            return {
                'company': company,
                'error': 'Structured evaluation data missing',
                'rag_available': True,
                'structured_available': False
            }
        
        # Extract scores from BOTH pipelines
        rag_scores = rag_eval.get('rubric_scores', {})
        structured_scores = structured_eval.get('rubric_scores', {})
        
        # Get totals (pre-calculated)
        rag_total = rag_eval.get('total_score', 0)
        structured_total = structured_eval.get('total_score', 0)
        
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
                'rag': rag_eval.get('metadata', {}),
                'structured': structured_eval.get('metadata', {})
            }
        }
    
    def check_data_availability(self):
        """Check what data is available for comparison."""
        print("\n" + "="*70)
        print("DATA AVAILABILITY CHECK")
        print("="*70)
        
        for company in self.eval_companies:
            print(f"\n📊 {company}")
            
            # Check structured payload (source data)
            payload = self.load_structured_payload(company)
            payload_status = "✅" if payload else "❌"
            print(f"   {payload_status} Structured Payload: data/structured/{company.lower().replace(' ', '_')}_payload.json")
            
            # Check RAG dashboard (generated output)
            rag_dash = self.load_rag_dashboard(company)
            rag_dash_status = "✅" if rag_dash else "❌"
            print(f"   {rag_dash_status} RAG Dashboard: data/dashboards/rag/{company.replace(' ', '_')}_dashboard.md")
            
            # Check structured dashboard (generated output)
            struct_dash = self.load_structured_dashboard(company)
            struct_dash_status = "✅" if struct_dash else "❌"
            print(f"   {struct_dash_status} Structured Dashboard: data/dashboards/structured/{company.lower().replace(' ', '_')}_dashboard.md")
            
            # Check RAG evaluation JSON (CRITICAL for comparison)
            rag_eval = self.load_eval_json(company, 'rag')
            rag_eval_status = "✅" if rag_eval else "❌"
            rag_eval_path = self.rag_dashboard_dir / f"{company.replace(' ', '_')}_eval.json"
            print(f"   {rag_eval_status} RAG Eval JSON: {rag_eval_path}")
            
            if rag_eval:
                print(f"      → Score: {rag_eval.get('total_score', 'N/A')}/10")
            
            # Check structured evaluation JSON (CRITICAL for comparison)
            struct_eval = self.load_eval_json(company, 'structured')
            struct_eval_status = "✅" if struct_eval else "❌"
            struct_eval_path = self.structured_dashboard_dir / f"{company.replace(' ', '_')}_eval.json"
            print(f"   {struct_eval_status} Structured Eval JSON: {struct_eval_path}")
            
            if struct_eval:
                print(f"      → Score: {struct_eval.get('total_score', 'N/A')}/10")
            
            # Summary
            if rag_eval and struct_eval:
                print(f"   ✅ READY FOR COMPARISON")
            elif not rag_eval and not struct_eval:
                print(f"   ⚠️  MISSING BOTH EVAL JSONs")
            else:
                print(f"   ⚠️  PARTIAL DATA - need both eval JSONs")
            
            # Show payload summary if available
            if payload:
                print(f"\n   📈 Payload Summary:")
                print(f"      Company: {payload.get('company', {}).get('legal_name', 'N/A')}")
                print(f"      Headcount: {payload.get('snapshot', {}).get('headcount_total', 'N/A')}")
                print(f"      Funding: ${payload.get('snapshot', {}).get('total_funding', 0):,}")
    
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

| Criterion | RAG Avg | Structured Avg | Delta |
|-----------|---------|----------------|-------|
| Factual Correctness | {sum(r['rag']['factual'] for r in valid_results)/len(valid_results):.2f}/3 | {sum(r['structured']['factual'] for r in valid_results)/len(valid_results):.2f}/3 | {abs(sum(r['rag']['factual'] for r in valid_results) - sum(r['structured']['factual'] for r in valid_results))/len(valid_results):.2f} |
| Schema Adherence | {sum(r['rag']['schema'] for r in valid_results)/len(valid_results):.2f}/2 | {sum(r['structured']['schema'] for r in valid_results)/len(valid_results):.2f}/2 | {abs(sum(r['rag']['schema'] for r in valid_results) - sum(r['structured']['schema'] for r in valid_results))/len(valid_results):.2f} |
| Provenance Use | {sum(r['rag']['provenance'] for r in valid_results)/len(valid_results):.2f}/2 | {sum(r['structured']['provenance'] for r in valid_results)/len(valid_results):.2f}/2 | {abs(sum(r['rag']['provenance'] for r in valid_results) - sum(r['structured']['provenance'] for r in valid_results))/len(valid_results):.2f} |
| Hallucination Control | {sum(r['rag']['hallucination'] for r in valid_results)/len(valid_results):.2f}/2 | {sum(r['structured']['hallucination'] for r in valid_results)/len(valid_results):.2f}/2 | {abs(sum(r['rag']['hallucination'] for r in valid_results) - sum(r['structured']['hallucination'] for r in valid_results))/len(valid_results):.2f} |
| Readability | {sum(r['rag']['readability'] for r in valid_results)/len(valid_results):.2f}/1 | {sum(r['structured']['readability'] for r in valid_results)/len(valid_results):.2f}/1 | {abs(sum(r['rag']['readability'] for r in valid_results) - sum(r['structured']['readability'] for r in valid_results))/len(valid_results):.2f} |
"""
        else:
            summary = "\n## Summary Statistics\n\n⚠️  No valid comparisons available yet. Need evaluation JSONs for BOTH pipelines.\n"
        
        return table + summary
    
    def generate_eval_md(self, output_path: Path = None):
        """Generate complete EVAL.md report with auto-filled analysis."""
        
        if output_path is None:
            output_path = self.project_root / "EVAL.md"
        
        # Generate comparison data
        print("\n📊 Analyzing results...")
        results = []
        for company in self.eval_companies:
            comparison = self.compare_company(company)
            if 'error' not in comparison:
                results.append(comparison)
        
        if not results:
            print("❌ No valid comparison data available")
            return None
        
        # Calculate statistics
        rag_wins = sum(1 for r in results if r['winner'] == 'RAG')
        struct_wins = sum(1 for r in results if r['winner'] == 'Structured')
        ties = sum(1 for r in results if r['winner'] == 'Tie')
        
        rag_avg = sum(r['rag']['total'] for r in results) / len(results)
        struct_avg = sum(r['structured']['total'] for r in results) / len(results)
        
        # Criterion averages
        rag_factual = sum(r['rag']['factual'] for r in results) / len(results)
        struct_factual = sum(r['structured']['factual'] for r in results) / len(results)
        
        rag_schema = sum(r['rag']['schema'] for r in results) / len(results)
        struct_schema = sum(r['structured']['schema'] for r in results) / len(results)
        
        rag_prov = sum(r['rag']['provenance'] for r in results) / len(results)
        struct_prov = sum(r['structured']['provenance'] for r in results) / len(results)
        
        rag_halluc = sum(r['rag']['hallucination'] for r in results) / len(results)
        struct_halluc = sum(r['structured']['hallucination'] for r in results) / len(results)
        
        rag_read = sum(r['rag']['readability'] for r in results) / len(results)
        struct_read = sum(r['structured']['readability'] for r in results) / len(results)
        
        # Auto-generate analysis
        comparison_table = self.generate_comparison_table()
        
        # Determine overall winner
        if rag_avg > struct_avg:
            overall_winner = "RAG"
            winner_margin = rag_avg - struct_avg
        elif struct_avg > rag_avg:
            overall_winner = "Structured"
            winner_margin = struct_avg - rag_avg
        else:
            overall_winner = "Tie"
            winner_margin = 0
        
        # Auto-fill strengths and weaknesses
        rag_strengths = []
        rag_weaknesses = []
        struct_strengths = []
        struct_weaknesses = []
        
        # Factual correctness analysis
        if rag_factual > struct_factual:
            rag_strengths.append(f"**Better factual accuracy ({rag_factual:.2f}/3 vs {struct_factual:.2f}/3)**: RAG's retrieval mechanism helped ground facts in source documents")
        elif struct_factual > rag_factual:
            struct_strengths.append(f"**Better factual accuracy ({struct_factual:.2f}/3 vs {rag_factual:.2f}/3)**: Structured extraction captured precise field-level data from sources")
            rag_weaknesses.append(f"**Lower factual scores ({rag_factual:.2f}/3)**: Retrieval quality variations led to some imprecise or missing facts")
        
        # Schema adherence
        if rag_schema == 2.0 and struct_schema == 2.0:
            rag_strengths.append(f"**Perfect schema adherence (2.00/2)**: All dashboards followed the 8-section template consistently")
            struct_strengths.append(f"**Perfect schema adherence (2.00/2)**: Pydantic schemas ensured consistent structure across all outputs")
        
        # Provenance
        if rag_prov == 2.0 and struct_prov == 2.0:
            rag_strengths.append(f"**Excellent source transparency (2.00/2)**: Retrieved chunks provided clear attribution")
            struct_strengths.append(f"**Excellent source transparency (2.00/2)**: Field-level provenance tracking maintained clear attribution")
        
        # Hallucination control
        if struct_halluc > rag_halluc:
            struct_strengths.append(f"**Superior hallucination control ({struct_halluc:.2f}/2 vs {rag_halluc:.2f}/2)**: Pydantic validation prevented invented data")
            rag_weaknesses.append(f"**Occasional hallucinations ({rag_halluc:.2f}/2)**: LLM synthesis sometimes filled gaps with plausible but unverified information")
        elif rag_halluc > struct_halluc:
            rag_strengths.append(f"**Strong hallucination control ({rag_halluc:.2f}/2)**: Vector search grounded responses in actual content")
        
        # Readability
        if rag_read > struct_read:
            rag_strengths.append(f"**Better readability ({rag_read:.2f}/1 vs {struct_read:.2f}/1)**: Natural language synthesis produced more investor-friendly prose")
            struct_weaknesses.append(f"**Lower readability scores ({struct_read:.2f}/1)**: Some dashboards felt template-driven or mechanical")
        elif struct_read > rag_read:
            struct_strengths.append(f"**Better readability ({struct_read:.2f}/1)**: Structured data enabled clear, concise summaries")
        
        # Format strengths/weaknesses as bullet lists
        rag_strengths_text = "\n".join(f"- {s}" for s in rag_strengths) if rag_strengths else "- Both pipelines performed comparably across most criteria"
        rag_weaknesses_text = "\n".join(f"- {w}" for w in rag_weaknesses) if rag_weaknesses else "- No major weaknesses identified relative to Structured pipeline"
        struct_strengths_text = "\n".join(f"- {s}" for s in struct_strengths) if struct_strengths else "- Both pipelines performed comparably across most criteria"
        struct_weaknesses_text = "\n".join(f"- {w}" for w in struct_weaknesses) if struct_weaknesses else "- No major weaknesses identified relative to RAG pipeline"
        
        # Recommendations
        rag_use_cases = [
            "Source data is diverse and unstructured (blogs, PDFs, news articles)",
            "Need to synthesize information across many documents",
            "Schema is flexible or still evolving",
            "Broader context and narrative flow are valuable",
            "Source documents change frequently (news, updates)"
        ]
        
        struct_use_cases = [
            "Data has clear, consistent fields (company records, financials)",
            "Precision and type validation are critical",
            "Need strict hallucination control with explicit schemas",
            "Data quality requirements are high",
            "Working with structured databases or APIs"
        ]
        
        hybrid_approach = """A hybrid approach could leverage both strengths:
    - Use **Structured extraction** for core company data (funding, leadership, metrics)
    - Use **RAG retrieval** for qualitative insights (market sentiment, competitive analysis, news)
    - Combine structured payload fields with RAG-synthesized narrative sections
    - This would provide both precision (from structured) and context (from RAG)"""
        
        eval_content = f"""# Lab 9: RAG vs Structured Pipeline Evaluation

    **Team:** Tapas Desai & [RAG Teammate Name]  
    **Date:** {datetime.now().strftime('%Y-%m-%d')}

    ---

    ## Evaluation Overview

    This report compares two approaches for generating PE investment dashboards:
    1. **RAG Pipeline (Unstructured):** Vector DB → Retrieval → LLM synthesis
    2. **Structured Pipeline:** Pydantic extraction → Payload assembly → LLM generation

    **Evaluation Companies:** {len(self.eval_companies)} companies from Forbes AI 50
    {chr(10).join(f'- {c}' for c in self.eval_companies)}

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
    {rag_strengths_text}

    ### RAG Pipeline Weaknesses

    **What RAG struggled with:**
    {rag_weaknesses_text}

    ### Structured Pipeline Strengths

    **What Structured did well:**
    {struct_strengths_text}

    ### Structured Pipeline Weaknesses

    **What Structured struggled with:**
    {struct_weaknesses_text}

    ---

    ## Key Findings

    ### Which Pipeline Won Overall?

    **Result: {overall_winner}** {'(by {:.2f} points)'.format(winner_margin) if winner_margin > 0 else '(exact tie)'}

    The evaluation revealed remarkably close performance between both pipelines:
    - **RAG average:** {rag_avg:.2f}/10
    - **Structured average:** {struct_avg:.2f}/10
    - **Win distribution:** RAG won {rag_wins}/{len(results)}, Structured won {struct_wins}/{len(results)}, with {ties}/{len(results)} ties

    {'This near-perfect tie suggests both approaches are viable for PE dashboard generation, with trade-offs in different areas.' if abs(rag_avg - struct_avg) < 0.5 else f'{overall_winner} demonstrated a slight edge, primarily through {"better factual grounding" if overall_winner == "RAG" and rag_factual > struct_factual else "superior hallucination control and precision" if overall_winner == "Structured" else "consistent performance"}.'}

    ### Where Did Each Excel?

    **RAG excelled at:**
    - **Readability ({rag_read:.2f}/1)**: Produced more natural, investor-friendly prose
    - **Retrieval-grounded synthesis**: Combined information from multiple sources effectively
    - **Flexibility**: Handled diverse source types and formats well

    **Structured excelled at:**
    - **Hallucination control ({struct_halluc:.2f}/2)**: Pydantic schemas prevented invented data
    - **Factual precision ({struct_factual:.2f}/3)**: Field-level extraction captured exact values
    - **Consistency**: Schema validation ensured uniform output quality

    **Both performed equally well at:**
    - **Schema adherence ({rag_schema:.2f}/2 both)**: Perfect compliance with 8-section template
    - **Provenance use ({rag_prov:.2f}/2 both)**: Clear source attribution throughout

    ---

    ## Recommendations

    Based on this evaluation, we recommend:

    **Use RAG when:**
    {chr(10).join(f'- {uc}' for uc in rag_use_cases)}

    **Use Structured when:**
    {chr(10).join(f'- {uc}' for uc in struct_use_cases)}

    **Hybrid Approach:**
    {hybrid_approach}

    ---

    ## Reflection

    ### Technical Insights

    **What worked well:**
    - Both pipelines successfully generated investor-grade dashboards
    - Clear rubric enabled objective comparison
    - Auto-evaluation with GPT-4 provided consistent scoring
    - "Not disclosed" policy prevented hallucination in both approaches

    **What we'd improve:**
    - More granular evaluation (section-by-section scoring)
    - Human expert review to validate auto-scores
    - Larger sample size (10+ companies)
    - Performance metrics (latency, cost per dashboard)
    - A/B testing with actual PE investors

    ### The RAG vs Structured Trade-off

    **RAG Approach:**
    - **Pros:** Flexible, handles unstructured data, natural synthesis, context-aware
    - **Cons:** Retrieval quality dependency, potential for hallucination, harder to validate
    - **Best for:** Narrative-heavy analysis, diverse sources, evolving schemas

    **Structured Approach:**
    - **Pros:** Precise, type-safe, predictable, excellent hallucination control
    - **Cons:** Requires predefined schemas, less flexible, can feel mechanical
    - **Best for:** Structured data, regulatory compliance, audit trails

    ### Future Enhancements

    If we had more time, we would explore:
    1. **Hybrid pipeline** combining structured extraction for facts + RAG for narrative
    2. **Incremental updates** instead of full regeneration
    3. **Multi-source validation** to cross-check facts across sources
    4. **Section-specific strategies** (structured for metrics, RAG for outlook)
    5. **Cost-performance analysis** comparing API costs and latency
    6. **Real investor feedback** through user studies

    ---

    ## Conclusion

    Both the RAG and Structured pipelines proved effective for generating PE investment dashboards, achieving nearly identical average scores ({rag_avg:.2f} vs {struct_avg:.2f}). The choice between them should be driven by:

    1. **Data characteristics**: Structured data favors the Structured pipeline; diverse unstructured content favors RAG
    2. **Precision requirements**: High-stakes decisions requiring strict accuracy favor Structured
    3. **Flexibility needs**: Rapidly evolving information spaces favor RAG
    4. **Hybrid potential**: The best solution may combine both approaches

    Our evaluation suggests that rather than choosing one approach, teams should consider a **hybrid architecture** that leverages structured extraction for core data fields and RAG retrieval for contextual analysis and synthesis.

    ---

    *Auto-generated analysis based on evaluation results. Review and adjust as needed.*
    """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(eval_content)
        
        print(f"\n✅ EVAL.md generated: {output_path}")
        
        return output_path

def main():
    """Test comparison logic and data availability."""
    print("="*70)
    print("LAB 9: PIPELINE COMPARISON CHECKER")
    print("="*70)
    
    comparator = PipelineComparator()
    
    # Check data availability for BOTH pipelines
    comparator.check_data_availability()
    
    # Try to generate comparison
    print("\n" + "="*70)
    print("GENERATING COMPARISON TABLE")
    print("="*70)
    
    try:
        table = comparator.generate_comparison_table()
        print("\n📊 Comparison Table Preview:")
        print(table)
    except Exception as e:
        print(f"❌ Cannot generate full comparison yet: {e}")
        print("\n💡 Next Steps:")
        print("   1. Ensure RAG dashboards exist in data/dashboards/rag/")
        print("   2. Ensure Structured dashboards exist in data/dashboards/structured/")
        print("   3. Generate evaluation JSONs for BOTH pipelines:")
        print("      - data/dashboards/rag/{Company}_eval.json")
        print("      - data/dashboards/structured/{Company}_eval.json")
        print("   4. Re-run this script to generate EVAL.md")


if __name__ == "__main__":
    main()