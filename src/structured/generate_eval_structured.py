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

from structured_dashboard import generate_dashboard

# THE SAME 5 COMPANIES FOR EVALUATION (match RAG teammate!)
EVAL_COMPANIES = [
    "Abridge",
    "Anthropic", 
    "Anysphere",
    "Baseten",
    "Clay",
    "Coactive_Ai"
]

def auto_evaluate_dashboard(markdown: str, payload: dict) -> dict:
    """
    Auto-evaluate dashboard quality using OpenAI
    All 5 rubric criteria: factual, schema, provenance, hallucination, readability
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {
            'factual_correctness': None,
            'schema_adherence': None,
            'provenance_use': None,
            'hallucination_control': None,
            'readability': None
        }
    
    client = OpenAI(api_key=api_key)
    
    eval_prompt = f"""You just generated a PE investment dashboard from structured JSON data. Evaluate it objectively using ALL 5 criteria.

DASHBOARD:
{markdown}

SOURCE DATA (PAYLOAD):
{json.dumps(payload, indent=2)[:2000]}

EVALUATION CRITERIA (10 POINTS TOTAL):

1. Factual Correctness (0-3 points):
- 3 points: All facts directly from payload, perfectly accurate
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
- 2 points: Zero inventions, only uses payload data, "Not disclosed" when appropriate
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
                    "content": "You are an objective evaluator of investment dashboards. Score strictly and honestly based on the criteria. Return only valid JSON."
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
            'factual_correctness': scores.get('factual_correctness', None),
            'schema_adherence': scores.get('schema_adherence', None),
            'provenance_use': scores.get('provenance_use', None),
            'hallucination_control': scores.get('hallucination_control', None),
            'readability': scores.get('readability', None)
        }
    
    except Exception as e:
        print(f"⚠️  Auto-evaluation failed: {e}")
        return {
            'factual_correctness': None,
            'schema_adherence': None,
            'provenance_use': None,
            'hallucination_control': None,
            'readability': None
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
    payloads_dir = project_root / "data" / "payloads"
    output_dir = project_root / "data" / "dashboards" / "structured"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    total_scores = {
        'factual_correctness': 0,
        'schema_adherence': 0,
        'provenance_use': 0,
        'hallucination_control': 0,
        'readability': 0
    }
    
    for i, company_name in enumerate(EVAL_COMPANIES, 1):
        company_id = company_name.lower()
        print(f"\n[{i}/5] {company_name}")
        print(f"{'='*70}")
        
        # Load payload for evaluation
        payload_file = payloads_dir / f"{company_id}.json"
        if not payload_file.exists():
            print(f"❌ Payload not found!")
            continue
        
        with open(payload_file, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        
        # Generate dashboard
        result = generate_dashboard(company_id)
        
        if result['success']:
            markdown = result['markdown']
            
            print(f"✅ Dashboard generated")
            print(f"🎫 Tokens: {result['tokens_used']}")
            
            # Auto-evaluate with OpenAI
            print(f"🔍 Auto-evaluating...")
            auto_scores = auto_evaluate_dashboard(markdown, payload)
            
            # Display scores
            print(f"\n📊 Auto-Evaluation Scores:")
            print(f"   Factual Correctness:    {auto_scores.get('factual_correctness')}/3")
            print(f"   Schema Adherence:       {auto_scores.get('schema_adherence')}/2")
            print(f"   Provenance Use:         {auto_scores.get('provenance_use')}/2")
            print(f"   Hallucination Control:  {auto_scores.get('hallucination_control')}/2")
            print(f"   Readability:            {auto_scores.get('readability')}/1")
            
            # Calculate total
            total = sum(v for v in auto_scores.values() if v is not None)
            print(f"   TOTAL:                  {total}/10")
            
            # Update running totals
            for key, value in auto_scores.items():
                if value is not None:
                    total_scores[key] += value
            
            successful += 1
            
            # Save markdown
            md_file = output_dir / f"{company_id}.md"
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
            
            # Create evaluation metadata JSON
            eval_metadata = {
                "company_name": company_name,
                "pipeline_type": "Structured",
                "generated_at": datetime.now().isoformat(),
                "metadata": {
                    "source": "GCP cloud storage (structured payload)",
                    "data_approach": "hybrid (intelligence.json from initial + daily content)",
                    "model": "gpt-4o-mini",
                    "prompt_tokens": result.get('tokens_used', 0) - 500,
                    "completion_tokens": 500
                },
                "auto_evaluation": {
                    "has_8_sections": has_8_sections,
                    "uses_not_disclosed": markdown.count("Not disclosed"),
                    "has_disclosure_gaps": "## Disclosure Gaps" in markdown
                },
                "manual_scores": auto_scores
            }
            
            # Save evaluation JSON
            eval_file = output_dir / f"{company_id}_eval.json"
            with open(eval_file, 'w', encoding='utf-8') as f:
                json.dump(eval_metadata, f, indent=2)
            
            print(f"💾 Saved: {company_id}.md + {company_id}_eval.json")
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Successfully generated: {successful}/5 dashboards")
    
    if successful > 0:
        print(f"\n📈 Average Scores (Structured Pipeline):")
        for criterion, total in total_scores.items():
            avg = total / successful
            print(f"   {criterion.replace('_', ' ').title()}: {avg:.2f}")
    
    print(f"\n📁 Output: {output_dir}")
    print(f"\n📋 Files per company:")
    print(f"   - <company>.md (dashboard)")
    print(f"   - <company>_eval.json (auto-evaluation)")
    
    print(f"\n🤝 Next steps for Lab 9:")
    print(f"   1. Review auto-scores and adjust if needed")
    print(f"   2. Compare with RAG teammate's scores")
    print(f"   3. Fill EVAL.md comparison table")
    print(f"   4. Write 1-page reflection on findings")
    print(f"\n💡 Note: Auto-scores are AI-generated. Review dashboards")
    print(f"   manually and adjust scores in _eval.json if needed!")

if __name__ == "__main__":
    main() 