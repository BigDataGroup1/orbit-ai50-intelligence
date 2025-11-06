"""
Generate dashboards for all 39 companies
Author: Tapas
"""

from pathlib import Path
from structured_dashboard import generate_dashboard
import time

def generate_all():
    print("\n" + "="*70)
    print("GENERATING ALL 39 DASHBOARDS")
    print("By: Tapas")
    print("="*70)
    
    # Get paths
    this_file = Path(__file__).resolve()
    structured_dir = this_file.parent
    src_dir = structured_dir.parent
    project_root = src_dir.parent
    
    payloads_dir = project_root / "data" / "payloads"
    output_dir = project_root / "data" / "dashboards" / "structured"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all payloads
    payload_files = sorted(payloads_dir.glob('*.json'))
    
    print(f"\n📊 Found {len(payload_files)} companies")
    print(f"⏱️  Estimated time: ~{len(payload_files) * 10} seconds (~{len(payload_files) * 10 / 60:.1f} minutes)")
    print(f"💰 Estimated cost: ~${len(payload_files) * 0.02:.2f}")
    
    response = input("\n▶️  Press Enter to start (or Ctrl+C to cancel)...")
    
    results = {'success': 0, 'failed': 0, 'total_tokens': 0}
    
    for i, payload_file in enumerate(payload_files, 1):
        company_id = payload_file.stem
        print(f"\n{'='*70}")
        print(f"[{i}/{len(payload_files)}] {company_id}")
        print(f"{'='*70}")
        
        result = generate_dashboard(company_id)
        
        if result['success']:
            print(f"✅ Success!")
            print(f"📊 Company: {result['company_name']}")
            print(f"🎫 Tokens: {result['tokens_used']}")
            
            results['success'] += 1
            results['total_tokens'] += result['tokens_used']
            
            # Save
            output_file = output_dir / f"{company_id}.md"
            output_file.write_text(result['markdown'], encoding='utf-8')
            print(f"💾 Saved: {output_file.name}")
        else:
            print(f"❌ Failed: {result.get('error')}")
            results['failed'] += 1
        
        # Rate limiting (1 second between requests)
        if i < len(payload_files):
            time.sleep(1)
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Total companies: {len(payload_files)}")
    print(f"✅ Success: {results['success']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"🎫 Total tokens used: {results['total_tokens']:,}")
    print(f"💰 Estimated cost: ${results['total_tokens'] * 0.000002:.4f}")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n✅ ALL DASHBOARDS GENERATED!")


if __name__ == "__main__":
    generate_all()