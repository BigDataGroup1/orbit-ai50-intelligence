"""
Lab 6: Payload Assembly
Author: Tapas
Validates and copies structured files to payloads folder
"""

import shutil
from pathlib import Path
import json


def validate_payload(file_path: Path) -> bool:
    """Validate that payload has required fields"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check required fields
        required = ['company_record', 'snapshots', 'leadership', 'visibility']
        
        for field in required:
            if field not in data:
                print(f"    ⚠️  Missing field: {field}")
                return False
        
        # Check company_record has company_id
        if 'company_id' not in data.get('company_record', {}):
            print(f"    ⚠️  Missing company_id in company_record")
            return False
        
        return True
        
    except json.JSONDecodeError:
        print(f"    ❌ Invalid JSON")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False


def assemble_payloads():
    """Main payload assembly function"""
    
    print("\n" + "="*70)
    print("LAB 6: PAYLOAD ASSEMBLY")
    print("By: Tapas")
    print("="*70)
    
    # Paths
    structured_dir = Path('data/structured')
    payloads_dir = Path('data/payloads')
    
    # Check source exists
    if not structured_dir.exists():
        print("\n❌ Source directory not found: data/structured/")
        print("💡 Run Lab 5 first: python src/structured/structured_extract.py --limit 5")
        return
    
    # Create payloads directory
    payloads_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all structured files
    files = list(structured_dir.glob('*.json'))
    
    if not files:
        print("\n❌ No structured files found!")
        print("💡 Run Lab 5 first to create structured data.")
        return
    
    print(f"\n📊 Found {len(files)} structured files")
    print(f"📁 Source: {structured_dir}")
    print(f"📁 Destination: {payloads_dir}")
    print("\n" + "-"*70)
    
    # Process each file
    results = {
        'total': len(files),
        'valid': 0,
        'invalid': 0,
        'copied': 0
    }
    
    for i, file in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file.name}")
        
        # Validate
        print(f"  🔍 Validating...")
        if validate_payload(file):
            print(f"  ✅ Valid payload")
            results['valid'] += 1
            
            # Copy to payloads
            dest = payloads_dir / file.name
            shutil.copy(file, dest)
            print(f"  📋 Copied to: payloads/{file.name}")
            results['copied'] += 1
            
        else:
            print(f"  ❌ Invalid - skipped")
            results['invalid'] += 1
    
    # Summary
    print("\n" + "="*70)
    print("📊 ASSEMBLY SUMMARY")
    print("="*70)
    print(f"Total files: {results['total']}")
    print(f"✅ Valid: {results['valid']}")
    print(f"❌ Invalid: {results['invalid']}")
    print(f"📋 Copied: {results['copied']}")
    
    print(f"\n📁 Payloads directory: {payloads_dir}")
    
    # List created files
    payload_files = list(payloads_dir.glob('*.json'))
    print(f"\n📄 Created {len(payload_files)} payload files:")
    for pf in payload_files[:15]:
        print(f"  ✅ {pf.name}")
    if len(payload_files) > 15:
        print(f"  ... and {len(payload_files) - 15} more")
    
    print(f"\n✅ LAB 6 COMPLETE!")
    print(f"\n💡 Next Steps:")
    print(f"   - Lab 7: RAG Pipeline Dashboard")
    print(f"   - Lab 8: Structured Pipeline Dashboard")
    print(f"   - Your payloads are ready in: data/payloads/")


if __name__ == "__main__":
    assemble_payloads()