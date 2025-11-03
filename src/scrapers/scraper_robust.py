"""
Lab 1 Bulletproof: Crash-proof Company Intelligence Scraper
Will NEVER crash - handles all errors gracefully
"""

import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re
from urllib.parse import urljoin
from dotenv import load_dotenv
import os
import traceback
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class BulletproofScraper:
    """Completely crash-proof scraper with comprehensive error handling."""
    
    def __init__(self, seed_file: str):
        self.seed_file = Path(seed_file)
        self.companies = []
        
        # API keys
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')
        
        # Directories
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
        self.raw_dir = self.data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Page patterns
        self.page_patterns = {
            'homepage': ['/', ''],
            'about': ['/about', '/about-us', '/company', '/who-we-are'],
            'pricing': ['/pricing', '/plans', '/buy'],
            'product': ['/product', '/products', '/platform', '/solutions'],
            'careers': ['/careers', '/jobs', '/join-us'],
            'blog': ['/blog', '/news', '/newsroom', '/insights'],
            'customers': ['/customers', '/case-studies', '/success-stories'],
        }
        
        # Session
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.session_name = f"{self.today}_initial"
    
    def safe_load_companies(self) -> List[Dict]:
        """Safely load companies from seed file."""
        try:
            print("\n" + "="*70)
            print("Loading companies")
            print("="*70)
            
            with open(self.seed_file, 'r') as f:
                self.companies = json.load(f)
            
            print(f"✅ Loaded {len(self.companies)} companies")
            return self.companies
            
        except Exception as e:
            logger.error(f"Failed to load seed file: {e}")
            print(f"❌ Error loading seed file: {e}")
            return []
    
    def safe_find_page_url(self, base_url: str, page_type: str) -> Optional[str]:
        """Safely find URL for page type."""
        try:
            if page_type == 'homepage':
                return base_url
            
            patterns = self.page_patterns.get(page_type, [])
            
            for pattern in patterns:
                try:
                    test_url = urljoin(base_url, pattern)
                    
                    response = requests.head(
                        test_url,
                        headers=self.headers,
                        timeout=10,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        return test_url
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding page URL: {e}")
            return None
    
    def safe_scrape_page(self, url: str, page_type: str) -> Tuple[Optional[str], Optional[str], Dict]:
        """Safely scrape a page."""
        metadata = {
            'url': url,
            'page_type': page_type,
            'scraped_at': datetime.now().isoformat(),
            'status_code': None,
            'success': False,
            'error': None
        }
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
                allow_redirects=True
            )
            
            metadata['status_code'] = response.status_code
            
            if response.status_code != 200:
                metadata['error'] = f"HTTP {response.status_code}"
                return None, None, metadata
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove non-content
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            
            # Get text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            metadata['success'] = True
            metadata['content_length'] = len(html)
            
            return html, text, metadata
            
        except Exception as e:
            metadata['error'] = str(e)
            logger.error(f"Error scraping {url}: {e}")
            return None, None, metadata
    
    def safe_extract_pricing(self, html: str, text: str) -> Dict:
        """Safely extract pricing info."""
        try:
            info = {
                'pricing_model': 'Not found',
                'tiers': [],
                'free_tier': False,
                'enterprise_tier': False,
                'pricing_mentioned': False
            }
            
            if not html or not text:
                return info
            
            text_lower = text.lower()
            
            # Check if pricing mentioned
            pricing_indicators = ['pricing', 'plan', 'subscription', 'cost', '/month']
            info['pricing_mentioned'] = any(ind in text_lower for ind in pricing_indicators)
            
            # Detect pricing model
            if any(term in text_lower for term in ['per seat', 'per user', '/seat']):
                info['pricing_model'] = 'Per-seat subscription'
            elif any(term in text_lower for term in ['usage-based', 'pay as you go']):
                info['pricing_model'] = 'Usage-based'
            elif 'token' in text_lower and 'price' in text_lower:
                info['pricing_model'] = 'Token/API-based'
            elif 'contact us' in text_lower and 'enterprise' in text_lower:
                info['pricing_model'] = 'Enterprise/Custom'
            elif 'free' in text_lower and 'paid' in text_lower:
                info['pricing_model'] = 'Freemium'
            elif '/month' in text_lower:
                info['pricing_model'] = 'Monthly subscription'
            
            # Extract tiers
            tier_keywords = [
                'free', 'hobby', 'starter', 'basic', 'plus', 'pro',
                'professional', 'premium', 'team', 'business', 'enterprise', 'scale'
            ]
            
            for keyword in tier_keywords:
                if re.search(rf'\b{keyword}\b', text_lower):
                    tier_name = keyword.capitalize()
                    if tier_name not in info['tiers'] and len(info['tiers']) < 8:
                        info['tiers'].append(tier_name)
            
            info['free_tier'] = any(t.lower() == 'free' for t in info['tiers'])
            info['enterprise_tier'] = any(t.lower() in ['enterprise', 'business'] for t in info['tiers'])
            
            # Infer model from tiers
            if info['tiers'] and info['pricing_model'] == 'Not found':
                if info['free_tier']:
                    info['pricing_model'] = 'Freemium'
                elif info['enterprise_tier']:
                    info['pricing_model'] = 'Tiered subscription'
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting pricing: {e}")
            return {
                'pricing_model': 'Error extracting',
                'tiers': [],
                'free_tier': False,
                'enterprise_tier': False,
                'pricing_mentioned': False
            }
    
    def safe_extract_customers(self, html: str, text: str) -> Dict:
        """Safely extract customer info."""
        try:
            customers = {
                'mentioned_customers': [],
                'has_customer_section': False,
                'customer_count_claim': None
            }
            
            if not html or not text:
                return customers
            
            text_lower = text.lower()
            
            # Check for customer section
            if any(term in text_lower for term in ['our customers', 'trusted by', 'used by']):
                customers['has_customer_section'] = True
            
            # Known companies
            enterprise_names = [
                'google', 'microsoft', 'amazon', 'meta', 'apple', 'netflix',
                'uber', 'airbnb', 'spotify', 'stripe', 'shopify', 'zoom',
                'salesforce', 'adobe', 'oracle', 'ibm', 'nvidia', 'intel',
                'walmart', 'target', 'jpmorgan', 'mit', 'stanford'
            ]
            
            for name in enterprise_names:
                if name in text_lower:
                    customers['mentioned_customers'].append(name.title())
            
            # Customer count
            count_patterns = [
                r'(\d+[\d,]*)\s+(?:customers|companies|organizations)',
                r'trusted by\s+(\d+[\d,]*)',
            ]
            
            for pattern in count_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        count_str = match.group(1).replace(',', '')
                        customers['customer_count_claim'] = int(count_str)
                        break
                    except:
                        pass
            
            customers['mentioned_customers'] = sorted(list(set(customers['mentioned_customers'])))
            return customers
            
        except Exception as e:
            logger.error(f"Error extracting customers: {e}")
            return {
                'mentioned_customers': [],
                'has_customer_section': False,
                'customer_count_claim': None
            }
    
    def safe_extract_integrations(self, text: str) -> List[str]:
        """Safely extract integrations."""
        try:
            if not text:
                return []
            
            integrations = set()
            text_lower = text.lower()
            
            tools = [
                'salesforce', 'snowflake', 'slack', 'microsoft teams', 'teams',
                'google workspace', 'gmail', 'outlook', 'jira', 'confluence',
                'hubspot', 'zendesk', 'intercom', 'stripe', 'zoom',
                'asana', 'notion', 'monday'
            ]
            
            for tool in tools:
                if tool in text_lower:
                    clean = tool.replace('microsoft ', '').title()
                    integrations.add(clean)
            
            return sorted(list(integrations))
            
        except Exception as e:
            logger.error(f"Error extracting integrations: {e}")
            return []
    
    def safe_extract_careers(self, html: str, text: str) -> Dict:
        """Safely extract job opening info."""
        try:
            info = {
                'has_careers_page': True,
                'open_positions': 0,
                'departments': [],
                'locations': [],
                'hiring_focus': [],
                'job_board_detected': None
            }
            
            if not html or not text:
                return info
            
            soup = BeautifulSoup(html, 'html.parser')
            text_lower = text.lower()
            
            # Detect job boards
            boards = {
                'greenhouse': r'greenhouse\.io',
                'lever': r'lever\.co',
                'ashby': r'ashbyhq\.com',
            }
            
            for board, pattern in boards.items():
                if re.search(pattern, html):
                    info['job_board_detected'] = board
                    break
            
            # Count jobs
            count_patterns = [
                r'(\d+)\s+open\s+(?:position|role|job)',
                r'(\d+)\s+(?:position|role|job)s?\s+(?:open|available)',
            ]
            
            for pattern in count_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        count = int(match.group(1))
                        if count < 500:
                            info['open_positions'] = count
                            break
                    except:
                        pass
            
            # Departments
            dept_keywords = {
                'Engineering': ['engineering', 'software', 'backend'],
                'Sales': ['sales', 'account executive'],
                'Marketing': ['marketing', 'growth'],
                'Product': ['product manager', 'product'],
                'Design': ['design', ' ux ', ' ui '],
                'Data Science': ['data scientist', 'ml engineer'],
            }
            
            for dept, keywords in dept_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    info['departments'].append(dept)
            
            # Locations
            if 'remote' in text_lower:
                info['locations'].append('Remote')
            
            # Hiring focus
            if 'ml engineer' in text_lower or 'ai researcher' in text_lower:
                info['hiring_focus'].append('Applied ML/AI')
            if 'enterprise sales' in text_lower:
                info['hiring_focus'].append('Enterprise Sales')
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting careers: {e}")
            return {
                'has_careers_page': True,
                'open_positions': 0,
                'departments': [],
                'locations': [],
                'hiring_focus': [],
                'job_board_detected': None
            }
    
    def safe_extract_features(self, html: str, text: str) -> Dict:
        """Safely extract product features."""
        try:
            features = {
                'mentioned_features': [],
                'use_cases': []
            }
            
            if not text:
                return features
            
            text_lower = text.lower()
            
            feature_keywords = {
                'API': 'API access',
                'real-time': 'Real-time processing',
                'integration': 'Integrations',
                'analytics': 'Analytics',
                'automation': 'Automation',
                'secure': 'Security',
                'compliance': 'Compliance',
            }
            
            for keyword, feature_name in feature_keywords.items():
                if keyword.lower() in text_lower:
                    features['mentioned_features'].append(feature_name)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return {'mentioned_features': [], 'use_cases': []}
    
    def safe_extract_competitors(self, text: str, company_name: str) -> List[str]:
        """Safely extract competitor mentions."""
        try:
            if not text:
                return []
            
            competitors = []
            text_lower = text.lower()
            company_lower = company_name.lower()
            
            ai_companies = [
                'openai', 'anthropic', 'google', 'microsoft', 'meta',
                'cohere', 'databricks', 'scale ai', 'perplexity'
            ]
            
            for company in ai_companies:
                if company in company_lower:
                    continue
                if company in text_lower:
                    competitors.append(company.title())
            
            return sorted(list(set(competitors)))
            
        except Exception as e:
            logger.error(f"Error extracting competitors: {e}")
            return []
    
    def safe_extract_funding(self, html: str, text: str) -> Dict:
        """Safely extract funding signals."""
        try:
            signals = {
                'funding_mentioned': False,
                'latest_round': None,
                'investors_mentioned': []
            }
            
            if not text:
                return signals
            
            text_lower = text.lower()
            
            if any(term in text_lower for term in ['funding', 'raised', 'series']):
                signals['funding_mentioned'] = True
            
            # Round detection
            round_match = re.search(r'(series [a-z]|seed)', text_lower)
            if round_match:
                signals['latest_round'] = round_match.group(1).title()
            
            # Investors
            investors = ['sequoia', 'a16z', 'andreessen', 'accel', 'benchmark']
            for inv in investors:
                if inv in text_lower:
                    signals['investors_mentioned'].append(inv.title())
            
            return signals
            
        except Exception as e:
            logger.error(f"Error extracting funding: {e}")
            return {
                'funding_mentioned': False,
                'latest_round': None,
                'investors_mentioned': []
            }
    
    def safe_get_github_stats(self, github_url: str) -> Dict:
        """Safely get GitHub stats."""
        try:
            if not github_url:
                return {'has_github': False}
            
            match = re.search(r'github\.com/([^/]+)/?$', github_url)
            if not match:
                return {'has_github': False}
            
            org = match.group(1)
            api_url = f"https://api.github.com/orgs/{org}"
            headers = {'Accept': 'application/vnd.github.v3+json'}
            
            if self.github_token:
                headers['Authorization'] = f'token {self.github_token}'
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'has_github': True,
                    'public_repos': data.get('public_repos', 0),
                    'followers': data.get('followers', 0),
                    'url': github_url
                }
            
            return {'has_github': False}
            
        except Exception as e:
            logger.error(f"Error getting GitHub stats: {e}")
            return {'has_github': False, 'error': str(e)}
    
    def safe_search_news(self, company_name: str) -> Dict:
        """Safely search for news."""
        try:
            if not self.news_api_key:
                return {'has_news_api': False}
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'"{company_name}" AI',
                'apiKey': self.news_api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 20,
                'from': (datetime.now() - timedelta(days=30)).isoformat()[:10]
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return {'has_news_api': False, 'error': f"HTTP {response.status_code}"}
            
            data = response.json()
            articles = data.get('articles', [])
            
            # Filter relevant
            filtered = []
            for article in articles:
                title = (article.get('title') or '').lower()
                desc = (article.get('description') or '').lower()
                
                if company_name.lower() in title or company_name.lower() in desc:
                    filtered.append({
                        'title': article.get('title'),
                        'source': (article.get('source') or {}).get('name'),
                        'published_at': article.get('publishedAt'),
                        'url': article.get('url'),
                        'description': (article.get('description') or '')[:200]
                    })
            
            return {
                'has_news_api': True,
                'recent_mentions': len(filtered),
                'timeframe_days': 30,
                'articles': filtered[:10]
            }
            
        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return {'has_news_api': False, 'error': str(e)}
    
    def safe_save_file(self, path: Path, content: str) -> bool:
        """Safely save file."""
        try:
            path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"Error saving {path}: {e}")
            return False
    
    def scrape_company(self, company: Dict) -> Dict:
        """Safely scrape one company - will NOT crash."""
        company_name = company.get('company_name', 'Unknown')
        
        try:
            website = company.get('website', 'Not available')
            
            print(f"\n{'='*70}")
            print(f"🏢 {company_name}")
            print(f"🌐 {website}")
            print(f"{'='*70}")
            
            # Create dirs
            company_dir = self.raw_dir / company_name.replace(' ', '_').replace('/', '_')
            session_dir = company_dir / self.session_name
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Intelligence structure
            intel = {
                'company_name': company_name,
                'website': website,
                'scraped_at': datetime.now().isoformat(),
                'session': self.session_name,
                'seed_data': {k: v for k, v in company.items()},
                'pages': {},
                'extracted_intelligence': {
                    'pricing': None,
                    'customers': None,
                    'integrations': [],
                    'careers': None,
                    'product_features': None,
                    'competitors': [],
                    'funding_signals': None,
                    'github_stats': None,
                    'news': None
                },
                'errors': []
            }
            
            # Skip if no website
            if not website or website == 'Not available':
                print("   ⚠️  No website")
                self.safe_save_file(session_dir / "intelligence.json", json.dumps(intel, indent=2))
                return intel
            
            # Scrape pages
            print("\n📄 Scraping pages...")
            
            all_text = ""
            all_html = ""
            
            for page_type in ['homepage', 'about', 'pricing', 'product', 'careers', 'blog', 'customers']:
                try:
                    page_url = self.safe_find_page_url(website, page_type)
                    
                    if not page_url:
                        print(f"   ⚠️  {page_type}: not found")
                        intel['pages'][page_type] = {'found': False}
                        continue
                    
                    print(f"   🔍 {page_type}: {page_url}")
                    html, text, metadata = self.safe_scrape_page(page_url, page_type)
                    
                    intel['pages'][page_type] = metadata
                    
                    if html and text:
                        self.safe_save_file(session_dir / f"{page_type}.html", html)
                        self.safe_save_file(session_dir / f"{page_type}.txt", text)
                        
                        all_text += "\n\n" + text
                        all_html += html
                        
                        print(f"      ✅ Saved")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error scraping {page_type}: {e}")
                    intel['errors'].append(f"Failed to scrape {page_type}: {str(e)}")
            
            # Extract intelligence
            if all_text:
                print("\n🔬 Extracting intelligence...")
                
                try:
                    # Pricing
                    if intel['pages'].get('pricing', {}).get('success'):
                        html = (session_dir / "pricing.html").read_text(encoding='utf-8')
                        text = (session_dir / "pricing.txt").read_text(encoding='utf-8')
                        intel['extracted_intelligence']['pricing'] = self.safe_extract_pricing(html, text)
                    elif intel['pages'].get('homepage', {}).get('success'):
                        html = (session_dir / "homepage.html").read_text(encoding='utf-8')
                        text = (session_dir / "homepage.txt").read_text(encoding='utf-8')
                        intel['extracted_intelligence']['pricing'] = self.safe_extract_pricing(html, text)
                except Exception as e:
                    logger.error(f"Error in pricing extraction: {e}")
                
                try:
                    # Customers
                    intel['extracted_intelligence']['customers'] = self.safe_extract_customers(all_html, all_text)
                except Exception as e:
                    logger.error(f"Error in customer extraction: {e}")
                
                try:
                    # Integrations
                    intel['extracted_intelligence']['integrations'] = self.safe_extract_integrations(all_text)
                except Exception as e:
                    logger.error(f"Error in integration extraction: {e}")
                
                try:
                    # Careers
                    if intel['pages'].get('careers', {}).get('success'):
                        html = (session_dir / "careers.html").read_text(encoding='utf-8')
                        text = (session_dir / "careers.txt").read_text(encoding='utf-8')
                        intel['extracted_intelligence']['careers'] = self.safe_extract_careers(html, text)
                except Exception as e:
                    logger.error(f"Error in careers extraction: {e}")
                
                try:
                    # Features
                    intel['extracted_intelligence']['product_features'] = self.safe_extract_features(all_html, all_text)
                except Exception as e:
                    logger.error(f"Error in features extraction: {e}")
                
                try:
                    # Competitors
                    intel['extracted_intelligence']['competitors'] = self.safe_extract_competitors(all_text, company_name)
                except Exception as e:
                    logger.error(f"Error in competitor extraction: {e}")
                
                try:
                    # Funding
                    intel['extracted_intelligence']['funding_signals'] = self.safe_extract_funding(all_html, all_text)
                except Exception as e:
                    logger.error(f"Error in funding extraction: {e}")
            
            # GitHub
            try:
                if company.get('github'):
                    print("   🐙 GitHub stats...")
                    intel['extracted_intelligence']['github_stats'] = self.safe_get_github_stats(company['github'])
            except Exception as e:
                logger.error(f"Error getting GitHub stats: {e}")
            
            # News
            try:
                if self.news_api_key:
                    print("   📰 Recent news...")
                    intel['extracted_intelligence']['news'] = self.safe_search_news(company_name)
            except Exception as e:
                logger.error(f"Error searching news: {e}")
            
            # Save intelligence
            self.safe_save_file(session_dir / "intelligence.json", json.dumps(intel, indent=2))
            
            print(f"\n✅ Completed {company_name}")
            
            return intel
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR for {company_name}: {e}")
            traceback.print_exc()
            
            # Return minimal intel on critical failure
            return {
                'company_name': company_name,
                'website': company.get('website'),
                'scraped_at': datetime.now().isoformat(),
                'critical_error': str(e),
                'pages': {},
                'extracted_intelligence': {}
            }
    
    def run(self, limit: Optional[int] = None):
        """Main execution - GUARANTEED to complete."""
        try:
            print("\n" + "="*70)
            print("LAB 1 BULLETPROOF SCRAPER")
            print("="*70)
            
            # Load companies
            companies = self.safe_load_companies()
            
            if not companies:
                print("❌ No companies loaded!")
                return
            
            if limit:
                companies = companies[:limit]
                print(f"\n⚠️  TEST MODE - {limit} companies")
            
            print(f"\n📊 Companies: {len(companies)}")
            print(f"⏱️  Estimated time: ~{len(companies) * 3} minutes")
            
            response = input("\nProceed? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
            
            # Scrape
            all_intel = []
            successful = 0
            
            for i, company in enumerate(companies, 1):
                print(f"\n{'#'*70}")
                print(f"[{i}/{len(companies)}]")
                
                try:
                    intel = self.scrape_company(company)
                    all_intel.append(intel)
                    
                    # Count success if any pages worked
                    if any(p.get('success') for p in intel.get('pages', {}).values()):
                        successful += 1
                    
                except Exception as e:
                    logger.error(f"Failed on company {i}: {e}")
                    print(f"❌ Error (continuing): {e}")
                    
                    # Add minimal entry to keep going
                    all_intel.append({
                        'company_name': company.get('company_name', f'Company_{i}'),
                        'error': str(e),
                        'pages': {},
                        'extracted_intelligence': {}
                    })
                
                # Rate limit
                if i < len(companies):
                    time.sleep(5)
            
            # Generate summary - SAFE version
            print("\n" + "="*70)
            print("GENERATING SUMMARY")
            print("="*70)
            
            try:
                # Safe statistics calculation
                stats = {
                    'total_pages': 0,
                    'with_pricing': 0,
                    'with_customers': 0,
                    'with_careers': 0,
                    'with_news': 0
                }
                
                for r in all_intel:
                    try:
                        # Count pages
                        pages = r.get('pages', {})
                        if pages:
                            stats['total_pages'] += sum(1 for p in pages.values() if isinstance(p, dict) and p.get('success'))
                        
                        # Get extracted intelligence safely
                        intel_data = r.get('extracted_intelligence', {})
                        if not intel_data:
                            continue
                        
                        # Count pricing
                        if intel_data.get('pricing'):
                            stats['with_pricing'] += 1
                        
                        # Count customers
                        customers = intel_data.get('customers')
                        if customers and isinstance(customers, dict):
                            if customers.get('mentioned_customers'):
                                stats['with_customers'] += 1
                        
                        # Count careers
                        if intel_data.get('careers'):
                            stats['with_careers'] += 1
                        
                        # Count news
                        news = intel_data.get('news')
                        if news and isinstance(news, dict):
                            if news.get('recent_mentions', 0) > 0:
                                stats['with_news'] += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing stats for a company: {e}")
                        continue
                
                summary = {
                    'total_companies': len(companies),
                    'successful': successful,
                    'session': self.session_name,
                    'scraped_at': datetime.now().isoformat(),
                    'statistics': stats,
                    'results': all_intel
                }
                
                # Save summary
                summary_path = self.data_dir / f"lab1_bulletproof_summary_{self.today}.json"
                self.safe_save_file(summary_path, json.dumps(summary, indent=2))
                
                print(f"\n📊 FINAL RESULTS:")
                print(f"   Total companies: {summary['total_companies']}")
                print(f"   Successful: {successful}")
                print(f"   Total pages: {stats['total_pages']}")
                print(f"   With pricing: {stats['with_pricing']}")
                print(f"   With customers: {stats['with_customers']}")
                print(f"   With careers: {stats['with_careers']}")
                print(f"   With news: {stats['with_news']}")
                
                print(f"\n📁 Data: {self.raw_dir}")
                print(f"📄 Summary: {summary_path}")
                print("\n✅ LAB 1 COMPLETE - NO CRASHES!")
                
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                print(f"\n⚠️  Summary generation failed, but all data is saved in {self.raw_dir}")
                print("✅ Lab 1 data collection complete!")
        
        except Exception as e:
            logger.critical(f"CRITICAL ERROR: {e}")
            traceback.print_exc()
            print("\n⚠️  Scraper encountered critical error but handled gracefully")


def main():
    """Main execution."""
    try:
        seed_file = Path(__file__).resolve().parents[2] / "data" / "forbes_ai50_seed.json"
        
        if not seed_file.exists():
            print(f"❌ Seed file not found: {seed_file}")
            return
        
        scraper = BulletproofScraper(str(seed_file))
        
        test = input("\nTest with first 5 companies? (y/n): ")
        limit = 5 if test.lower() == 'y' else None
        
        scraper.run(limit=limit)
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        traceback.print_exc()
        print("\n❌ Fatal error occurred")


if __name__ == "__main__":
    main()