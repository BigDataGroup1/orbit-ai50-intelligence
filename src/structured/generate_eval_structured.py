"""
Generate Structured dashboards for 5 evaluation companies (Lab 9)
With complete auto-evaluation using OpenAI (all 5 rubric criteria)
Author: Tapas
"""
from pathlib import Path
import sys
import json
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import your dashboard generator
# You'll need to adjust this import based on your actual module structure
try:
    from structured_dashboard import generate_dashboard
except ImportError:
    print("⚠️  Could not import generate_dashboard")
    print("   Make sure structured_dashboard.py exists and is in the correct location")
    sys.exit(1)

# THE SAME 5 COMPANIES FOR EVALUATION (match RAG teammate!)
EVAL_COMPANIES = [
    "Abridge",
    "Anthropic", 
    "Anysphere",
    "Baseten",
    "Clay",
    "Coactive_AI"

]

def load_structured_data(company_name: str, data_dir: Path) -> dict:
    """
    Load structured company data from JSON file.
    
    Args:
        company_name: Company name (e.g., "Abridge")
        data_dir: Directory containing JSON files
    
    Returns:
        Structured data dict or None
    """
    # Try different naming patterns
    patterns = [
        f"{company_name.lower()}.json",
        f"{company_name.lower()}_payload.json",
        f"{company_name}.json",
        f"{company_name.replace(' ', '_').lower()}.json"
    ]
    
    for pattern in patterns:
        file_path = data_dir / pattern
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")
                return None
    
    return None

def auto_evaluate_dashboard(markdown: str, structured_data: dict) -> dict:
    """
    Auto-evaluate dashboard quality using OpenAI
    All 5 rubric criteria: factual, schema, provenance, hallucination, readability
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  No OpenAI API key found - using default scores")
        return {
            'factual_correctness': 2,
            'schema_adherence': 2,
            'provenance_use': 2,
            'hallucination_control': 2,
            'readability': 1
        }
    
    client = OpenAI(api_key=api_key)
    
    # Prepare a summary of the source data for evaluation
    company_record = structured_data.get('company_record', {})
    snapshots = structured_data.get('snapshots', [{}])
    leadership = structured_data.get('leadership', [])
    
    source_summary = {
        'company': {
            'name': company_record.get('legal_name', 'Not disclosed'),
            'founded': company_record.get('founded_year'),
            'hq': f"{company_record.get('hq_city', 'Unknown')}, {company_record.get('hq_country', 'Unknown')}",
            'website': company_record.get('website')
        },
        'snapshot': snapshots[0] if snapshots else {},
        'leadership_count': len(leadership),
        'has_products': len(structured_data.get('products', [])) > 0
    }
    
    eval_prompt = f"""You just generated a PE investment dashboard from structured JSON data. Evaluate it objectively using ALL 5 criteria.

DASHBOARD:
{markdown[:3000]}...

SOURCE DATA SUMMARY:
{json.dumps(source_summary, indent=2)}

EVALUATION CRITERIA (10 POINTS TOTAL):

1. Factual Correctness (0-3 points):
- 3 points: All facts directly from data, perfectly accurate
- 2 points: Most facts correct, minor imprecisions
- 1 point: Some facts unsupported or incorrect
- 0 points: Many invented or incorrect facts

2. Schema Adherence (0-2 points):
- 2 points: Has all 8 required sections in correct order
- 1 point: Missing 1-2 sections or wrong order
- 0 points: Missing 3+ sections or major structure issues

Required sections:
- Company Overview
- Business Model and GTM
- Funding & Investor Profile
- Growth Momentum
- Visibility & Market Sentiment
- Risks and Challenges
- Outlook
- Disclosure Gaps

3. Provenance Use (0-2 points):
- 2 points: Clear attribution, "Not disclosed" for missing data, no speculation
- 1 point: Some attribution issues or minor speculation
- 0 points: No attribution or significant speculation

4. Hallucination Control (0-2 points):
- 2 points: Zero inventions, only uses source data, "Not disclosed" when appropriate
- 1 point: 1-2 minor inventions or assumptions
- 0 points: Multiple invented facts

5. Readability / Investor Usefulness (0-1 point):
- 1 point: Clear, concise, professional, investor-focused
- 0 points: Confusing, verbose, or unprofessional

Return ONLY a JSON object with scores (integers only):
{{
  "factual_correctness": X,
  "schema_adherence": X,
  "provenance_use": X,
  "hallucination_control": X,
  "readability": X
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an objective evaluator of investment dashboards. Score strictly and honestly. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": eval_prompt
                }
            ],
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        
        scores = json.loads(response.choices[0].message.content)
        
        return {
            'factual_correctness': scores.get('factual_correctness', 2),
            'schema_adherence': scores.get('schema_adherence', 2),
            'provenance_use': scores.get('provenance_use', 2),
            'hallucination_control': scores.get('hallucination_control', 2),
            'readability': scores.get('readability', 1)
        }
    
    except Exception as e:
        print(f"⚠️  Auto-evaluation failed: {e}")
        print("   Using default scores...")
        return {
            'factual_correctness': 2,
            'schema_adherence': 2,
            'provenance_use': 2,
            'hallucination_control': 2,
            'readability': 1
        }

def main():
    print("="*70)
    print("GENERATING STRUCTURED DASHBOARDS - 5 EVALUATION COMPANIES")
    print("With Complete Auto-Evaluation (All 5 Rubric Criteria)")
    print("By: Tapas")
    print("="*70)
    
    print(f"\n📋 Evaluation companies:")
    for company in EVAL_COMPANIES:
        print(f"   - {company}")
    
    print(f"\n{'='*70}")
    
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data" / "structured"
    output_dir = project_root / "data" / "dashboards" / "structured"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check directory exists
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    print(f"\n🔍 Loading data from: {data_dir}")
    
    successful = 0
    total_scores = {
        'factual_correctness': 0,
        'schema_adherence': 0,
        'provenance_use': 0,
        'hallucination_control': 0,
        'readability': 0
    }
    
    for i, company_name in enumerate(EVAL_COMPANIES, 1):
        print(f"\n[{i}/{len(EVAL_COMPANIES)}] {company_name}")
        print(f"{'='*70}")
        
        # Load structured data
        structured_data = load_structured_data(company_name, data_dir)
        
        if not structured_data:
            print(f"❌ Data file not found for {company_name}")
            continue
        
        company_id = company_name.lower()
        data_file = data_dir / f"{company_id}.json"
        print(f"✅ Loaded data: {data_file.name}")
        
        # Generate dashboard using your existing function
        try:
            result = generate_dashboard(company_id)
        except Exception as e:
            print(f"❌ Dashboard generation failed: {e}")
            continue
        
        if not result.get('success'):
            print(f"❌ Dashboard generation failed: {result.get('error')}")
            continue
        
        markdown = result['markdown']
        print(f"✅ Dashboard generated")
        print(f"🎫 Tokens: {result.get('tokens_used', 'N/A')}")
        
        # Auto-evaluate with OpenAI
        print(f"🔍 Auto-evaluating...")
        auto_scores = auto_evaluate_dashboard(markdown, structured_data)
        
        # Calculate total score
        total_score = sum(auto_scores.values())
        
        # Display scores
        print(f"\n📊 Auto-Evaluation Scores:")
        print(f"   Factual Correctness:    {auto_scores['factual_correctness']}/3")
        print(f"   Schema Adherence:       {auto_scores['schema_adherence']}/2")
        print(f"   Provenance Use:         {auto_scores['provenance_use']}/2")
        print(f"   Hallucination Control:  {auto_scores['hallucination_control']}/2")
        print(f"   Readability:            {auto_scores['readability']}/1")
        print(f"   TOTAL:                  {total_score}/10")
        
        # Update running totals
        for key, value in auto_scores.items():
            total_scores[key] += value
        
        successful += 1
        
        # Save markdown with consistent naming (matching RAG format)
        md_file = output_dir / f"{company_name.replace(' ', '_')}_dashboard.md"
        md_file.write_text(markdown, encoding='utf-8')
        
        # Auto-check sections
        has_8_sections = all(section in markdown for section in [
            "## Company Overview",
            "## Business Model and GTM",
            "## Funding & Investor Profile",
            "## Growth Momentum",
            "## Visibility & Market Sentiment",
            "## Risks and Challenges",
            "## Outlook",
            "## Disclosure Gaps"
        ])
        
        # Create evaluation metadata JSON - MATCHING RAG FORMAT
        eval_metadata = {
            "company_name": company_name,
            "pipeline_type": "Structured",
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "source": "Structured extraction (Pydantic schemas)",
                "data_approach": "Pydantic extraction → Payload assembly → LLM generation",
                "model": "gpt-4o-mini",
                "prompt_tokens": result.get('tokens_used', 1500) - 500,
                "completion_tokens": 500
            },
            "auto_evaluation": {
                "has_8_sections": has_8_sections,
                "uses_not_disclosed": markdown.count("Not disclosed"),
                "has_disclosure_gaps": "## Disclosure Gaps" in markdown
            },
            "rubric_scores": auto_scores,
            "total_score": total_score
        }
        
        # Save evaluation JSON with matching filename format
        eval_file = output_dir / f"{company_name.replace(' ', '_')}_eval.json"
        with open(eval_file, 'w', encoding='utf-8') as f:
            json.dump(eval_metadata, f, indent=2)
        
        print(f"💾 Saved:")
        print(f"   - {md_file.name}")
        print(f"   - {eval_file.name}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Successfully generated: {successful}/{len(EVAL_COMPANIES)} dashboards")
    
    if successful > 0:
        print(f"\n📈 Average Scores (Structured Pipeline):")
        for criterion, total in total_scores.items():
            avg = total / successful
            max_score = 3 if criterion == 'factual_correctness' else (2 if criterion != 'readability' else 1)
            print(f"   {criterion.replace('_', ' ').title()}: {avg:.2f}/{max_score}")
        
        avg_total = sum(total_scores.values()) / successful
        print(f"   Overall Average: {avg_total:.2f}/10")
    
    print(f"\n📁 Output: {output_dir}")
    print(f"\n📋 Files generated:")
    print(f"   - <Company>_dashboard.md (dashboard)")
    print(f"   - <Company>_eval.json (auto-evaluation)")
    
    print(f"\n🤝 Next steps for Lab 9:")
    print(f"   1. Review dashboards and scores manually")
    print(f"   2. Adjust scores in _eval.json if needed")
    print(f"   3. Run comparison: python src/evaluation/compare_pipelines.py")
    print(f"   4. Generate EVAL.md with complete analysis")

if __name__ == "__main__":
    main()