"""
Lab 5 GCP Version: Extract from Cloud Storage
Author: Tapas
Same as structured_extract.py but reads from GCP bucket
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.gcp_storage import list_companies_in_bucket, download_company_files
from src.structured.structured_extract import StructuredExtractor
import time
import os
from dotenv import load_dotenv

load_dotenv()


class GCPStructuredExtractor(StructuredExtractor):
    """Extract structured data from GCP bucket"""
    
    def __init__(self):
        super().__init__()
        self.bucket_name = os.getenv('GCP_BUCKET_NAME')
        if not self.bucket_name:
            raise ValueError("GCP_BUCKET_NAME not set in .env!")
    
    def load_company_data(self, company_name: str):
        """Load scraped data from GCP bucket"""
        return download_company_files(self.bucket_name, company_name)
    
    def extract_all(self, company_name: str):
        """Extract from GCP (same logic as parent class)"""
        return super().extract_all(company_name)


def main():
    print("\n" + "="*70)
    print("LAB 5 GCP: STRUCTURED EXTRACTION FROM CLOUD")
    print("By: Tapas")
    print("="*70)
    
    # Parse arguments
    test_mode = '--test' in sys.argv
    limit = None
    
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    
    all_mode = '--all' in sys.argv
    
    # Initialize
    print("\n🔧 Initializing GCP extractor...")
    extractor = GCPStructuredExtractor()
    
    # Get companies from GCP
    print("\n📊 Scanning GCP bucket...")
    companies = list_companies_in_bucket(extractor.bucket_name)
    print(f"✅ Found {len(companies)} companies in GCP\n")
    
    # Determine what to process
    if test_mode:
        companies = companies[:1]
        print(f"🧪 TEST MODE: 1 company")
    elif limit:
        companies = companies[:limit]
        print(f"⚠️  LIMITED: {limit} companies")
    elif not all_mode:
        print("Usage:")
        print("  python structured_extract_gcp.py --test          (1 company)")
        print("  python structured_extract_gcp.py --limit 5       (5 companies)")
        print("  python structured_extract_gcp.py --all           (all companies)")
        return
    
    print(f"⏱️  Time: ~{len(companies) * 2} min")
    print(f"💰 Cost: ~${len(companies) * 0.05:.2f}")
    
    response = input("\nProceed? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return
    
    # Extract
    results = {'successful': 0, 'failed': 0, 'skipped': 0}
    
    for i, company in enumerate(companies, 1):
        print(f"\n{'#'*70}")
        print(f"[{i}/{len(companies)}] {company}")
        print(f"{'#'*70}")
        
        try:
            start = time.time()
            payload = extractor.extract_all(company)
            elapsed = time.time() - start
            
            results['successful'] += 1
            print(f"\n✅ SUCCESS ({elapsed:.1f}s)")
            
        except ValueError as e:
            print(f"\n⚠️  SKIPPED: {e}")
            results['skipped'] += 1
            
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            results['failed'] += 1
        
        if i < len(companies):
            time.sleep(1)
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Total: {len(companies)}")
    print(f"✅ Success: {results['successful']}")
    print(f"⚠️  Skipped: {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"\n📁 Output: data/structured/")
    print(f"\n✅ LAB 5 GCP COMPLETE!")


if __name__ == "__main__":
    main()