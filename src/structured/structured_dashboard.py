"""
Lab 8: Structured Pipeline Dashboard
Author: Tapas
Generates investor dashboard from structured payload using LLM
"""

from openai import OpenAI
from pathlib import Path
import json
import os
from dotenv import load_dotenv

load_dotenv()


def generate_dashboard(company_id: str) -> dict:
    """Generate investor dashboard from structured payload"""
    
    # Setup OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {"success": False, "error": "OPENAI_API_KEY not set"}
    
    client = OpenAI(api_key=api_key)
    
    # Build paths from this file location
    # This file is: src/structured/structured_dashboard.py
    this_file = Path(__file__).resolve()
    structured_dir = this_file.parent              # src/structured/
    src_dir = structured_dir.parent                # src/
    project_root = src_dir.parent                  # orbit-ai50-intelligence/
    
    data_dir = project_root / "data"
    payload_file = data_dir / "payloads" / f"{company_id}.json"
    prompt_file = src_dir / "prompts" / "dashboard_system_structured.md"
    
    # Load payload
    if not payload_file.exists():
        return {"success": False, "error": f"Payload not found: {payload_file}"}
    
    with open(payload_file, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    
    # Load prompt
    if not prompt_file.exists():
        return {"success": False, "error": f"Prompt not found: {prompt_file}"}
    
    system_prompt = prompt_file.read_text(encoding='utf-8')
    
    # Build user message
    user_message = f"""Generate an investor dashboard for this company.

**Payload:**
```json
{json.dumps(payload, indent=2)}
```

Remember:
- Use ONLY data from the payload
- If missing, say "Not disclosed."
- Include all 8 required sections
- Always end with "## Disclosure Gaps"
"""
    
    try:
        # Call LLM
        print(f"🤖 Calling OpenAI API for {company_id}...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=2500
        )
        
        markdown = response.choices[0].message.content
        
        return {
            "success": True,
            "company_id": company_id,
            "company_name": payload.get('company_record', {}).get('legal_name', 'Unknown'),
            "markdown": markdown,
            "tokens_used": response.usage.total_tokens
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_lab8():
    """Test dashboard generation"""
    print("\n" + "="*70)
    print("LAB 8: STRUCTURED DASHBOARD TEST")
    print("By: Tapas")
    print("="*70)
    
    # Build paths
    this_file = Path(__file__).resolve()
    structured_dir = this_file.parent              # src/structured/
    src_dir = structured_dir.parent                # src/
    project_root = src_dir.parent                  # orbit-ai50-intelligence/
    
    data_dir = project_root / "data"
    payloads_dir = data_dir / "payloads"
    
    # Debug paths
    print(f"\n🔍 Path Check:")
    print(f"   This file: {this_file}")
    print(f"   Project root: {project_root}")
    print(f"   Payloads dir: {payloads_dir}")
    print(f"   Payloads exists: {payloads_dir.exists()}\n")
    
    # Check if payloads exist
    if not payloads_dir.exists():
        print("❌ Payloads directory not found!")
        print(f"Expected at: {payloads_dir}")
        print("\n💡 Run Lab 6 first to create payloads")
        return
    
    # Get payload files
    payload_files = list(payloads_dir.glob('*.json'))
    
    if not payload_files:
        print("❌ No payload files found!")
        print("💡 Run Lab 6 first")
        return
    
    print(f"✅ Found {len(payload_files)} payload files")
    
    # Test with first company
    test_company = payload_files[0].stem
    print(f"🧪 Testing with: {test_company}\n")
    
    # Generate dashboard
    result = generate_dashboard(test_company)
    
    if result['success']:
        print(f"\n✅ Success!")
        print(f"📊 Company: {result['company_name']}")
        print(f"🎫 Tokens used: {result['tokens_used']}")
        print(f"\n{'='*70}")
        print("GENERATED DASHBOARD:")
        print(f"{'='*70}\n")
        print(result['markdown'])
        
        # Save output
        output_dir = data_dir / "dashboards" / "structured"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{test_company}.md"
        output_file.write_text(result['markdown'], encoding='utf-8')
        print(f"\n💾 Saved to: {output_file}")
        
    else:
        print(f"\n❌ Failed: {result.get('error')}")
    
    print(f"\n✅ LAB 8 TEST COMPLETE!")


if __name__ == "__main__":
    test_lab8()