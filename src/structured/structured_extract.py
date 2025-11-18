"""
Lab 5: Complete Structured Extraction - All-in-One
Author: Tapas
Single file with models, extractor, and runner - SKIP EMPTY VERSION
"""

import instructor
from openai import OpenAI
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Literal
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import time
import sys

load_dotenv()


# ============================================================================
# MODELS (Built-in to avoid import issues)
# ============================================================================

class Provenance(BaseModel):
    source_url: str
    crawled_at: str
    source_folder: Optional[str] = None  # NEW!
    data_files_used: Optional[List[str]] = None  # NEW!
    snippet: Optional[str] = None


class Company(BaseModel):
    company_id: str
    legal_name: str
    brand_name: Optional[str] = None
    website: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    hq_country: Optional[str] = None
    founded_year: Optional[int] = None
    categories: List[str] = Field(default_factory=list)
    related_companies: List[str] = Field(default_factory=list)
    total_raised_usd: Optional[float] = None
    last_disclosed_valuation_usd: Optional[float] = None
    last_round_name: Optional[str] = None
    last_round_date: Optional[str] = None
    schema_version: str = "2.0.0"
    as_of: Optional[str] = None
    provenance: List[Provenance] = Field(default_factory=list)


class Event(BaseModel):
    event_id: str
    company_id: str
    occurred_on: str
    event_type: Literal[
        "funding", "mna", "product_release", "integration", "partnership",
        "customer_win", "leadership_change", "regulatory", "security_incident",
        "pricing_change", "layoff", "hiring_spike", "office_open", "office_close",
        "benchmark", "open_source_release", "contract_award", "other"
    ]
    title: str
    description: Optional[str] = None
    round_name: Optional[str] = None
    investors: List[str] = Field(default_factory=list)
    amount_usd: Optional[float] = None
    valuation_usd: Optional[float] = None
    actors: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = Field(default_factory=list)


class Snapshot(BaseModel):
    company_id: str
    as_of: str
    headcount_total: Optional[int] = None
    job_openings_count: Optional[int] = None
    engineering_openings: Optional[int] = None
    sales_openings: Optional[int] = None
    hiring_focus: List[str] = Field(default_factory=list)
    pricing_tiers: List[str] = Field(default_factory=list)
    active_products: List[str] = Field(default_factory=list)
    geo_presence: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = Field(default_factory=list)


class Product(BaseModel):
    product_id: str
    company_id: str
    name: str
    description: Optional[str] = None
    pricing_model: Optional[str] = None
    pricing_tiers_public: List[str] = Field(default_factory=list)
    integration_partners: List[str] = Field(default_factory=list)
    reference_customers: List[str] = Field(default_factory=list)
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = Field(default_factory=list)


class Leadership(BaseModel):
    person_id: str
    company_id: str
    name: str
    role: str
    is_founder: bool = False
    previous_affiliation: Optional[str] = None
    education: Optional[str] = None
    linkedin: Optional[str] = None
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = Field(default_factory=list)


class Visibility(BaseModel):
    company_id: str
    as_of: str
    news_mentions_30d: Optional[int] = None
    github_stars: Optional[int] = None
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = Field(default_factory=list)


class Payload(BaseModel):
    company_record: Company
    events: List[Event] = Field(default_factory=list)
    snapshots: List[Snapshot] = Field(default_factory=list)
    products: List[Product] = Field(default_factory=list)
    leadership: List[Leadership] = Field(default_factory=list)
    visibility: List[Visibility] = Field(default_factory=list)
    notes: Optional[str] = ""
    provenance_policy: str = "Use only scraped sources. If missing: 'Not disclosed.'"


# ============================================================================
# EXTRACTOR
# ============================================================================

class StructuredExtractor:
    """Extract structured data using Instructor + OpenAI"""
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("❌ Set OPENAI_API_KEY in .env file!")
        
        self.client = instructor.from_openai(OpenAI(api_key=api_key))
        
        # Paths
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
        self.raw_dir = self.data_dir / "raw"
        self.structured_dir = self.data_dir / "structured"
        self.structured_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Extractor ready")
        print(f"📂 Input: {self.raw_dir}")
        print(f"📂 Output: {self.structured_dir}")
    
    def load_company_data(self, company_name: str):
        """Load scraped data for a company"""
        company_folder = company_name.replace(' ', '_')
        company_dir = self.raw_dir / company_folder
        
        if not company_dir.exists():
            raise FileNotFoundError(f"Not found: {company_dir}")
        
        # Get latest session
        sessions = [d for d in company_dir.iterdir() if d.is_dir()]
        session_dir = max(sessions, key=lambda x: x.name)
        
        print(f"  📂 {session_dir.name}")
        
        # Load text files
        texts = {}
        for txt in session_dir.glob("*.txt"):
            content = txt.read_text(encoding='utf-8')
            if content.strip():
                texts[txt.stem] = content
                print(f"    ✅ {txt.stem} ({len(content)} chars)")
        
        # Load intelligence
        intel_file = session_dir / "intelligence.json"
        intel = {}
        if intel_file.exists():
            with open(intel_file, 'r', encoding='utf-8') as f:
                intel = json.load(f)
        
        return {'texts': texts, 'intelligence': intel, 'company_name': company_name}
    
    def extract_company(self, data: dict) -> Company:
        """Extract Company using LLM"""
        combined = ""
        for page in ['homepage', 'about', 'product']:
            if page in data['texts']:
                combined += f"\n{data['texts'][page][:1500]}"
        
        seed = data['intelligence'].get('seed_data', {})
        company_id = data['company_name'].lower().replace(' ', '_')
        
        prompt = f"""Extract company data for {data['company_name']}.

Seed: CEO={seed.get('ceo')}, Founded={seed.get('founded_year')}, HQ={seed.get('hq_city')}, Funding={seed.get('total_funding')}, Valuation={seed.get('valuation')}

Content: {combined[:3000]}

Extract: company_id="{company_id}", legal_name, website, hq_city, hq_country, founded_year, total_raised_usd (convert $100M→100000000.0, $1B→1000000000.0), last_disclosed_valuation_usd

If missing: None. Don't invent."""
        
        company = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=Company,
            messages=[{"role": "user", "content": prompt}],
            max_retries=2
        )
        
        company.as_of = datetime.now().strftime('%Y-%m-%d')
        
        # Fill important fields from seed data
        company.website = seed.get('website', 'Not available')
        company.hq_country = seed.get('hq_country', 'United States')
        
        # Convert funding string to USD
        funding_str = seed.get('total_funding', 'Not available')
        if funding_str and funding_str != 'Not available':
            try:
                if 'B' in funding_str:
                    num = float(''.join(c for c in funding_str if c.isdigit() or c == '.'))
                    company.total_raised_usd = num * 1000000000
                elif 'M' in funding_str:
                    num = float(''.join(c for c in funding_str if c.isdigit() or c == '.'))
                    company.total_raised_usd = num * 1000000
            except:
                pass
        
        # Convert valuation string to USD
        valuation_str = seed.get('valuation', 'Not available')
        if valuation_str and valuation_str != 'Not available':
            try:
                if 'B' in valuation_str:
                    num = float(''.join(c for c in valuation_str if c.isdigit() or c == '.'))
                    company.last_disclosed_valuation_usd = num * 1000000000
                elif 'M' in valuation_str:
                    num = float(''.join(c for c in valuation_str if c.isdigit() or c == '.'))
                    company.last_disclosed_valuation_usd = num * 1000000
            except:
                pass
        
        # UPDATED: Include metadata in provenance
        company.provenance = [Provenance(
            source_url=seed.get('website', 'Not available'),
            crawled_at=datetime.now().isoformat(),
            source_folder=getattr(self, 'source_folder', 'local'),
            data_files_used=getattr(self, 'data_files_used', []),
            snippet=f"Extracted from {getattr(self, 'source_folder', 'scraped')} data"
        )]
        
        return company
    
    def extract_snapshot(self, data: dict, company_id: str) -> Snapshot:
        """Extract snapshot - NULL SAFE VERSION"""
        
        # Get intelligence safely
        intel = data.get('intelligence', {})
        extracted = intel.get('extracted_intelligence', {})
        
        # Check if extracted_intelligence exists and is not None
        if not extracted or not isinstance(extracted, dict):
            # No extracted intelligence - return minimal snapshot
            return Snapshot(
                company_id=company_id,
                as_of=datetime.now().strftime('%Y-%m-%d'),
                job_openings_count=0,
                pricing_tiers=[]
            )
        
        # Safe access to careers (might be null)
        careers_intel = extracted.get('careers')
        pricing_intel = extracted.get('pricing')
        
        # Get job count - handle None
        job_count = 0
        if careers_intel and isinstance(careers_intel, dict):
            job_count = careers_intel.get('open_positions', 0)
        
        # Get pricing tiers - handle None
        pricing_tiers = []
        if pricing_intel and isinstance(pricing_intel, dict):
            pricing_tiers = pricing_intel.get('tiers', [])
        
        return Snapshot(
            company_id=company_id,
            as_of=datetime.now().strftime('%Y-%m-%d'),
            job_openings_count=job_count,
            pricing_tiers=pricing_tiers
        )
    
    def extract_leadership(self, data: dict, company_id: str) -> List[Leadership]:
        """Extract leadership with education"""
        leaders = []
        seed = data['intelligence'].get('seed_data', {})
        ceo = seed.get('ceo')
        
        if ceo and ceo != 'Not available':
            # Get text for extraction
            about_text = data['texts'].get('about', '') + data['texts'].get('homepage', '')
            
            # Extract education from about page
            education = None
            universities = [
                'Stanford', 'MIT', 'Harvard', 'Berkeley', 'Yale', 
                'Princeton', 'Carnegie Mellon', 'Oxford', 'Cambridge',
                'Cornell', 'Columbia', 'University of Pennsylvania',
                'Caltech', 'ETH Zurich', 'Imperial College'
            ]
            
            for uni in universities:
                if uni in about_text:
                    education = uni
                    break
            
            leaders.append(Leadership(
                person_id=f"person_{company_id}_ceo",
                company_id=company_id,
                name=ceo,
                role="CEO",
                is_founder=True,
                education=education,
                linkedin=None
            ))
        
        return leaders
    
    def extract_all(self, company_name: str) -> Payload:
        """Extract complete payload for one company - SKIP IF NO DATA"""
        print(f"\n{'='*70}")
        print(f"🔬 EXTRACTING: {company_name}")
        print(f"{'='*70}\n")
        
        # Load data
        data = self.load_company_data(company_name)
        company_id = company_name.lower().replace(' ', '_')
        
        file_count = len(data['texts'])
        print(f"📊 Loaded {file_count} files\n")
        
        # ⚠️ SKIP if no meaningful data
        if file_count == 0:
            print("⚠️  SKIPPING: No scraped content available")
            raise ValueError(f"No data files for {company_name}")
        
        # Extract components (only if we have data)
        print("1️⃣ Company...")
        company = self.extract_company(data)
        print(f"   ✅ {company.legal_name}")
        
        print("\n2️⃣ Snapshot...")
        snapshot = self.extract_snapshot(data, company_id)
        print(f"   ✅ Jobs: {snapshot.job_openings_count}")
        
        print("\n3️⃣ Leadership...")
        leadership = self.extract_leadership(data, company_id)
        print(f"   ✅ {len(leadership)} leaders")
        
        print("\n4️⃣ Visibility...")
        visibility = Visibility(company_id=company_id, as_of=datetime.now().strftime('%Y-%m-%d'))
        
        # Create payload
        payload = Payload(
            company_record=company,
            snapshots=[snapshot],
            leadership=leadership,
            visibility=[visibility],
            notes=f"Extracted {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        # Save
        output = self.structured_dir / f"{company_id}.json"
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(payload.model_dump(mode='json'), f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n💾 SAVED: {output}")
        
        return payload


# ============================================================================
# MAIN RUNNER
# ============================================================================

def get_companies(extractor):
    """Get list of companies with data"""
    companies = []
    for d in extractor.raw_dir.iterdir():
        if d.is_dir():
            sessions = [s for s in d.iterdir() if s.is_dir()]
            if sessions:
                companies.append(d.name.replace('_', ' '))
    return companies


def main():
    print("\n" + "="*70)
    print("LAB 5: STRUCTURED EXTRACTION - SKIP EMPTY")
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
    print("\n🔧 Initializing...")
    extractor = StructuredExtractor()
    
    # Get companies
    print("\n📊 Scanning companies...")
    companies = get_companies(extractor)
    print(f"✅ Found {len(companies)} companies\n")
    
    # Determine what to process
    if test_mode:
        companies = companies[:1]
        print(f"🧪 TEST MODE: 1 company")
    elif limit:
        companies = companies[:limit]
        print(f"⚠️  LIMITED: {limit} companies")
    elif not all_mode:
        print("Usage:")
        print("  python structured_extract.py --test          (1 company)")
        print("  python structured_extract.py --limit 5       (5 companies)")
        print("  python structured_extract.py --all           (all companies)")
        return
    
    print(f"⏱️  Time: ~{len(companies) * 2} min")
    print(f"💰 Cost: ~${len(companies) * 0.05:.2f}")
    
    response = input("\nProceed? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return
    
    # Extract
    results = {'successful': 0, 'failed': 0, 'skipped': 0, 'companies': []}
    
    for i, company in enumerate(companies, 1):
        print(f"\n{'#'*70}")
        print(f"[{i}/{len(companies)}] {company}")
        print(f"{'#'*70}")
        
        try:
            start = time.time()
            payload = extractor.extract_all(company)
            elapsed = time.time() - start
            
            results['successful'] += 1
            results['companies'].append({
                'name': company,
                'status': 'success',
                'time': f"{elapsed:.1f}s"
            })
            
            print(f"\n✅ SUCCESS ({elapsed:.1f}s)")
            
        except ValueError as e:
            # Expected error for companies with no data
            print(f"\n⚠️  SKIPPED: {e}")
            results['skipped'] += 1
            results['companies'].append({
                'name': company,
                'status': 'skipped',
                'reason': str(e)
            })
            
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            results['failed'] += 1
            results['companies'].append({
                'name': company,
                'status': 'failed',
                'error': str(e)
            })
        
        if i < len(companies):
            time.sleep(1)
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Total: {len(companies)}")
    print(f"✅ Success: {results['successful']}")
    print(f"⚠️  Skipped: {results['skipped']} (no data)")
    print(f"❌ Failed: {results['failed']}")
    print(f"\n📁 Output: data/structured/")
    print(f"\n✅ LAB 5 COMPLETE!")


if __name__ == "__main__":
    main()