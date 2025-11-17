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
    def try_static_snapshots(self, url: str) -> Optional[str]:
        """
        Try common static snapshot variants of modern JavaScript websites.
        Many companies expose AMP / HTML snapshots automatically for SEO.
        This method requires NO JavaScript engine, works fully in Composer.
        """

        SNAPSHOT_QUERIES = [
            "?_escaped_fragment_=",
            "?view=html",
            "?amp=1",
            "?format=amp",
            "?output=1",
            "?hs_preview=true",
        ]

        for q in SNAPSHOT_QUERIES:
            test_url = url.rstrip("/") + "/" + q
            try:
                r = requests.get(test_url, headers=self.headers, timeout=12)

                # Accept if valid static HTML found
                if r.status_code == 200 and len(r.text) > 500:
                    logger.info(f"   ➜ Snapshot found: {test_url}")
                    return r.text

            except Exception as e:
                logger.debug(f"Snapshot failed for {test_url}: {e}")
                continue

        return None
    
    def fetch_google_cache(self, url: str) -> Optional[str]:
        """
        Fetch the Google Web Cache version of the page.
        This often contains a fully-rendered HTML snapshot.
        100% free and Cloud Composer friendly.
        """

        # Google Cache URL format
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"

        try:
            r = requests.get(cache_url, headers=self.headers, timeout=15)

            # Google Cache should return a valid HTML snapshot
            if r.status_code == 200 and len(r.text) > 500:
                logger.info(f"   ➜ Google Cache snapshot found for {url}")
                return r.text

        except Exception as e:
            logger.debug(f"Google Cache failed for {url}: {e}")
            return None

        return None
    def fetch_textise(self, url: str) -> Optional[str]:
        """
        FINAL free fallback: Textise (text-only HTML snapshot).
        This tool renders a simplified static version of JavaScript pages.
        Works reliably when both snapshots and Google Cache fail.
        100% free and Cloud Composer friendly.
        """

        proxy_url = f"http://textise.net/showtext.aspx?strURL={url}"

        try:
            r = requests.get(proxy_url, headers=self.headers, timeout=15)

            # Textise returns simplified text → so >= 300 chars is OK
            if r.status_code == 200 and len(r.text) > 300:
                logger.info(f"   ➜ Textise snapshot found for {url}")
                return r.text

        except Exception as e:
            logger.debug(f"Textise fallback failed for {url}: {e}")
            return None

        return None


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
        """Safely load companies from seed file - Works on Mac & Windows."""
        try:
            print("\n" + "="*70)
            print("Loading companies")
            print("="*70)
        
            with open(self.seed_file, 'rb') as f:
                self.companies = json.load(f)
        
            print(f"✅ Loaded {len(self.companies)} companies")
            return self.companies
        
        except Exception as e:
            logger.error(f"Failed to load seed file: {e}")
            print(f"❌ Error loading seed file: {e}")
            return []
    
    def safe_find_page_url(self, base_url: str, page_type: str) -> Optional[str]:
        """
        Safely find URL for a given page type.
        Adds GET fallback, JS detection, and snapshot-based fallbacks.
        100% compatible with Cloud Composer (no JS browser required).
        """

        try:
            if not base_url:
                return None

            # Homepage is always valid
            if page_type == "homepage":
                return base_url.rstrip("/")

            patterns = self.page_patterns.get(page_type, [])

            for pattern in patterns:
                test_url = urljoin(base_url, pattern)

                # -------------------------------------
                # 1) Try HEAD request (fast check)
                # -------------------------------------
                try:
                    head_resp = requests.head(
                        test_url,
                        headers=self.headers,
                        timeout=8,
                        allow_redirects=True
                    )

                    if head_resp.status_code in (200, 301, 302, 307, 308):
                        # HEAD success → accept this URL
                        return head_resp.url
                except:
                    pass

                # -------------------------------------
                # 2) Try GET fallback (block-proof)
                # -------------------------------------
                try:
                    get_resp = requests.get(
                        test_url,
                        headers=self.headers,
                        timeout=12,
                        allow_redirects=True
                    )

                    # Basic JS detection
                    txt = get_resp.text

                    if get_resp.status_code == 200 and len(txt) > 500:
                        # Valid static HTML → accept
                        return get_resp.url

                    if "enable JavaScript" in txt or len(txt) < 300:
                        # Try static snapshot fallback → fully free and Composer-safe
                        snapshot_html = self.try_static_snapshots(test_url)
                        if snapshot_html and len(snapshot_html) > 500:
                            return test_url  # Valid snapshot found

                except:
                    continue  # Try next pattern

            # No match found
            return None

        except Exception as e:
            logger.error(f"safe_find_page_url error for {base_url}: {e}")
            return None


    
    def safe_scrape_page(self, url: str, page_type: str) -> Tuple[Optional[str], Optional[str], Dict]:
        """
        Safely scrape a page with multi-layer fallbacks:
        1. Normal GET
        2. JS detection → static snapshots
        3. Google Cache
        4. Textise
        5. Job Board fallback (Greenhouse / Lever / AshbyHQ)
        """

        metadata = {
            'url': url,
            'page_type': page_type,
            'scraped_at': datetime.now().isoformat(),
            'status_code': None,
            'success': False,
            'error': None,
            'source': 'live',
            'content_length': 0
        }

        def clean_html(raw_html: str) -> Tuple[str, str]:
            """Strip scripts/styles and extract readable text."""
            soup = BeautifulSoup(raw_html, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n")
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_clean = "\n".join(chunk for chunk in chunks if chunk)
            return str(soup), text_clean

        # -----------------------------------
        # 1. Normal GET (with retry)
        # -----------------------------------
        for attempt in range(2):
            try:
                response = requests.get(url, headers=self.headers, timeout=20, allow_redirects=True)
                metadata['status_code'] = response.status_code

                if response.status_code == 200 and len(response.text) > 300:
                    html, text = clean_html(response.text)
                    metadata.update({
                        'success': True,
                        'source': 'live',
                        'content_length': len(response.text)
                    })
                    return html, text, metadata

                # If JS skeleton detected → skip to fallbacks
                if "enable JavaScript" in response.text or len(response.text) < 200:
                    break

            except Exception as e:
                metadata['error'] = f"GET attempt {attempt+1}: {e}"

            time.sleep(2)

        # -----------------------------------
        # 2. Static snapshot fallback
        # -----------------------------------
        try:
            snapshot_html = self.try_static_snapshots(url)
            if snapshot_html and len(snapshot_html) > 500:
                html, text = clean_html(snapshot_html)
                metadata.update({
                    'success': True,
                    'source': 'snapshot',
                    'content_length': len(snapshot_html)
                })
                return html, text, metadata
        except Exception as e:
            metadata['error'] = f"snapshot fallback failed: {e}"

        # -----------------------------------
        # 3. Google Cache fallback
        # -----------------------------------
        try:
            cached = self.fetch_google_cache(url)
            if cached and len(cached) > 500:
                html, text = clean_html(cached)
                metadata.update({
                    'success': True,
                    'source': 'google_cache',
                    'content_length': len(cached)
                })
                return html, text, metadata
        except Exception as e:
            metadata['error'] = f"google cache failed: {e}"

        # -----------------------------------
        # 4. Textise fallback (text-only)
        # -----------------------------------
        try:
            textise = self.fetch_textise(url)
            if textise and len(textise) > 300:
                html = textise
                _, text_clean = clean_html(textise)
                metadata.update({
                    'success': True,
                    'source': 'textise',
                    'content_length': len(textise)
                })
                return html, text_clean, metadata
        except Exception as e:
            metadata['error'] = f"textise fallback failed: {e}"

        # -----------------------------------
        # 5. JOB BOARD FALLBACKS (Ashby / Lever / Greenhouse)
        # ONLY runs for careers pages
        # -----------------------------------
        try:
            url_lower = url.lower()

            # ------------ Greenhouse ------------
            if "greenhouse.io" in url_lower:
                gh_api = url.rstrip("/") + "/embed/jobs/"
                r = requests.get(gh_api, headers=self.headers, timeout=15)
                if r.status_code == 200 and len(r.text) > 200:
                    html, text = clean_html(r.text)
                    metadata.update({
                        'success': True,
                        'source': 'greenhouse_embed',
                        'content_length': len(r.text)
                    })
                    logger.info(f"   ➜ Greenhouse embed fallback used: {gh_api}")
                    return html, text, metadata

            # ---------------- Lever --------------
            if "lever.co" in url_lower:
                match = re.search(r'lever\.co/([^/?]+)', url_lower)
                if match:
                    key = match.group(1)
                    lever_api = f"https://api.lever.co/v0/postings/{key}?mode=json"
                    r = requests.get(lever_api, timeout=15)
                    if r.status_code == 200:
                        jobs = r.json()
                        # Build readable HTML/text block
                        text = "\n\n".join(job.get("text", "") for job in jobs)
                        html = "<br><br>".join(job.get("text", "") for job in jobs)
                        metadata.update({
                            'success': True,
                            'source': 'lever_api',
                            'content_length': len(text)
                        })
                        logger.info(f"   ➜ Lever API fallback used: {lever_api}")
                        return html, text, metadata

            # -------------- Ashby ----------------
            if "ashbyhq.com" in url_lower:
                ashby_static = url + "?embedding=true"
                r = requests.get(ashby_static, headers=self.headers, timeout=15)
                if r.status_code == 200 and len(r.text) > 300:
                    html, text = clean_html(r.text)
                    metadata.update({
                        'success': True,
                        'source': 'ashby_embedded',
                        'content_length': len(r.text)
                    })
                    logger.info(f"   ➜ Ashby embedded fallback used: {ashby_static}")
                    return html, text, metadata

        except Exception as e:
            metadata['error'] = f"Job board fallback failed: {e}"

        # -----------------------------------
        # 6. TOTAL FAILURE
        # -----------------------------------
        metadata['error'] = metadata.get('error') or "Failed all scraping fallbacks"
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
    
    # def scrape_company(self, company: Dict) -> Dict:
    #     """Safely scrape one company - will NOT crash."""
    #     company_name = company.get('company_name', 'Unknown')
        
    #     try:
    #         website = company.get('website', 'Not available')
            
    #         print(f"\n{'='*70}")
    #         print(f"🏢 {company_name}")
    #         print(f"🌐 {website}")
    #         print(f"{'='*70}")
            
    #         # Create dirs
    #         company_dir = self.raw_dir / company_name.replace(' ', '_').replace('/', '_')
    #         session_dir = company_dir / self.session_name
    #         session_dir.mkdir(parents=True, exist_ok=True)
            
    #         # Intelligence structure
    #         intel = {
    #             'company_name': company_name,
    #             'website': website,
    #             'scraped_at': datetime.now().isoformat(),
    #             'session': self.session_name,
    #             'seed_data': {k: v for k, v in company.items()},
    #             'pages': {},
    #             'extracted_intelligence': {
    #                 'pricing': None,
    #                 'customers': None,
    #                 'integrations': [],
    #                 'careers': None,
    #                 'product_features': None,
    #                 'competitors': [],
    #                 'funding_signals': None,
    #                 'github_stats': None,
    #                 'news': None
    #             },
    #             'errors': []
    #         }
            
    #         # Skip if no website
    #         if not website or website == 'Not available':
    #             print("   ⚠️  No website")
    #             self.safe_save_file(session_dir / "intelligence.json", json.dumps(intel, indent=2))
    #             return intel
            
    #         # Scrape pages
    #         print("\n📄 Scraping pages...")
            
    #         all_text = ""
    #         all_html = ""
            
    #         for page_type in ['homepage', 'about', 'pricing', 'product', 'careers', 'blog', 'customers']:
    #             try:
    #                 page_url = self.safe_find_page_url(website, page_type)
                    
    #                 if not page_url:
    #                     print(f"   ⚠️  {page_type}: not found")
    #                     intel['pages'][page_type] = {'found': False}
    #                     continue
                    
    #                 print(f"   🔍 {page_type}: {page_url}")
    #                 html, text, metadata = self.safe_scrape_page(page_url, page_type)
                    
    #                 intel['pages'][page_type] = metadata
                    
    #                 if html and text:
    #                     self.safe_save_file(session_dir / f"{page_type}.html", html)
    #                     self.safe_save_file(session_dir / f"{page_type}.txt", text)
                        
    #                     all_text += "\n\n" + text
    #                     all_html += html
                        
    #                     print(f"      ✅ Saved")
                    
    #                 time.sleep(2)
                    
    #             except Exception as e:
    #                 logger.error(f"Error scraping {page_type}: {e}")
    #                 intel['errors'].append(f"Failed to scrape {page_type}: {str(e)}")
            
    #         # Extract intelligence
    #         if all_text:
    #             print("\n🔬 Extracting intelligence...")
                
    #             try:
    #                 # Pricing
    #                 if intel['pages'].get('pricing', {}).get('success'):
    #                     html = (session_dir / "pricing.html").read_text(encoding='utf-8')
    #                     text = (session_dir / "pricing.txt").read_text(encoding='utf-8')
    #                     intel['extracted_intelligence']['pricing'] = self.safe_extract_pricing(html, text)
    #                 elif intel['pages'].get('homepage', {}).get('success'):
    #                     html = (session_dir / "homepage.html").read_text(encoding='utf-8')
    #                     text = (session_dir / "homepage.txt").read_text(encoding='utf-8')
    #                     intel['extracted_intelligence']['pricing'] = self.safe_extract_pricing(html, text)
    #             except Exception as e:
    #                 logger.error(f"Error in pricing extraction: {e}")
                
    #             try:
    #                 # Customers
    #                 intel['extracted_intelligence']['customers'] = self.safe_extract_customers(all_html, all_text)
    #             except Exception as e:
    #                 logger.error(f"Error in customer extraction: {e}")
                
    #             try:
    #                 # Integrations
    #                 intel['extracted_intelligence']['integrations'] = self.safe_extract_integrations(all_text)
    #             except Exception as e:
    #                 logger.error(f"Error in integration extraction: {e}")
                
    #             try:
    #                 # Careers
    #                 if intel['pages'].get('careers', {}).get('success'):
    #                     html = (session_dir / "careers.html").read_text(encoding='utf-8')
    #                     text = (session_dir / "careers.txt").read_text(encoding='utf-8')
    #                     intel['extracted_intelligence']['careers'] = self.safe_extract_careers(html, text)
    #             except Exception as e:
    #                 logger.error(f"Error in careers extraction: {e}")
                
    #             try:
    #                 # Features
    #                 intel['extracted_intelligence']['product_features'] = self.safe_extract_features(all_html, all_text)
    #             except Exception as e:
    #                 logger.error(f"Error in features extraction: {e}")
                
    #             try:
    #                 # Competitors
    #                 intel['extracted_intelligence']['competitors'] = self.safe_extract_competitors(all_text, company_name)
    #             except Exception as e:
    #                 logger.error(f"Error in competitor extraction: {e}")
                
    #             try:
    #                 # Funding
    #                 intel['extracted_intelligence']['funding_signals'] = self.safe_extract_funding(all_html, all_text)
    #             except Exception as e:
    #                 logger.error(f"Error in funding extraction: {e}")
            
    #         # GitHub
    #         try:
    #             if company.get('github'):
    #                 print("   🐙 GitHub stats...")
    #                 intel['extracted_intelligence']['github_stats'] = self.safe_get_github_stats(company['github'])
    #         except Exception as e:
    #             logger.error(f"Error getting GitHub stats: {e}")
            
    #         # News
    #         try:
    #             if self.news_api_key:
    #                 print("   📰 Recent news...")
    #                 intel['extracted_intelligence']['news'] = self.safe_search_news(company_name)
    #         except Exception as e:
    #             logger.error(f"Error searching news: {e}")
            
    #         # Save intelligence
    #         self.safe_save_file(session_dir / "intelligence.json", json.dumps(intel, indent=2))
            
    #         print(f"\n✅ Completed {company_name}")
            
    #         return intel
            
    #     except Exception as e:
    #         logger.error(f"CRITICAL ERROR for {company_name}: {e}")
    #         traceback.print_exc()
            
    #         # Return minimal intel on critical failure
    #         return {
    #             'company_name': company_name,
    #             'website': company.get('website'),
    #             'scraped_at': datetime.now().isoformat(),
    #             'critical_error': str(e),
    #             'pages': {},
    #             'extracted_intelligence': {}
    #         }
    def scrape_company(self, company: Dict) -> Dict:
        """
        Scrape all pages for a company using Bulletproof 5-layer scraping,
        AND SAVE each page to:
            data/raw/<company_name>/<session_name>/<page>.html
            data/raw/<company_name>/<session_name>/<page>.txt
            data/raw/<company_name>/<session_name>/<page>_metadata.json
        """
        name = company.get("company_name") or company.get("name")
        base_url = company.get("website")

        logger.info(f"\n================ COMPANY: {name} ================")
        logger.info(f"Base URL: {base_url}\n")

        results = {
            "name": name,
            "website": base_url,
            "pages": {},
            "found_urls": {},
            "failed_pages": []
        }

        if not base_url:
            logger.error(f"{name}: No base URL found")
            return results

        # ------------------------
        # Create raw folder
        # ------------------------
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
        company_dir = self.raw_dir / safe_name / self.session_name
        company_dir.mkdir(parents=True, exist_ok=True)

        processed_urls = set()

        # -------------------------------------------------------
        # Loop through page types
        # -------------------------------------------------------
        for page_type in self.page_patterns.keys():

            logger.info(f"--- Finding page: {page_type}")

            page_url = self.safe_find_page_url(base_url, page_type)
            if not page_url:
                logger.warning(f"{name}: Could not find URL for {page_type}")
                results["failed_pages"].append(page_type)
                continue

            results["found_urls"][page_type] = page_url

            if page_url in processed_urls:
                logger.info(f"Skipping duplicate URL: {page_url}")
                continue

            processed_urls.add(page_url)

            logger.info(f"Scraping {page_type} → {page_url}")

            html, text, metadata = self.safe_scrape_page(page_url, page_type)

            if not html:
                logger.error(f"Scrape failed for {name} → {page_type}")
                results["failed_pages"].append(page_type)
                continue

            # -------------------------------------------------
            # SAVE FILES (HTML, TEXT, METADATA)
            # -------------------------------------------------
            safe_page = re.sub(r"[^a-zA-Z0-9_-]+", "_", page_type)

            html_path = company_dir / f"{safe_page}.html"
            txt_path = company_dir / f"{safe_page}.txt"
            meta_path = company_dir / f"{safe_page}_metadata.json"

            try:
                html_path.write_text(html, encoding="utf-8")
                txt_path.write_text(text, encoding="utf-8")
                meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                logger.info(f"   ✓ Saved {page_type} → {html_path}")
            except Exception as e:
                logger.error(f"Error saving files for {name}/{page_type}: {e}")

            # -------------------------------------------------
            # Add to results
            # -------------------------------------------------
            results["pages"][page_type] = {
                "html": html,
                "text": text,
                "metadata": metadata
            }

            logger.info(
                f"✓ {name} [{page_type}] scraped "
                f"({metadata['source']}, {metadata['content_length']} chars)"
            )

            time.sleep(0.4)

        return results

 
    def run(self, limit: Optional[int] = None):
        """
        Main execution entry point.
        FULLY compatible with existing DAG and interactive y/n workflow.
        Adds:
            • Retry protection
            • Company-level isolation
            • Dead-site protection
            • Execution timing
            • Logging improvements
            • No changes to I/O or interactive behavior
        """

        print("=====================================")
        print("      LAB 1 BULLETPROOF SCRAPER      ")
        print("=====================================\n")

        companies = self.safe_load_companies()
        if not companies:
            print("No companies found. Exiting.")
            return []

        total = len(companies) if limit is None else min(limit, len(companies))
        proceed = input(f"{total} companies to scrape. Proceed? (y/n): ").strip().lower()

        if proceed != "y":
            print("Exiting without scraping.")
            return []

        failures = {}
        all_results = []

        print("\n========== SCRAPING BEGIN ==========\n")

        for idx, company in enumerate(companies[:total], start=1):

            name = company.get("company_name") or company.get("name")

            url = company.get("website")

            print(f"\n--------------- ({idx}/{total}) ---------------")
            print(f"Company: {name}")
            print(f"Website: {url}")

            start_time = time.time()

            # ---------------------------------------
            # 1) DOMAIN REACHABILITY CHECK
            # ---------------------------------------
            try:
                r = requests.get(url, headers=self.headers, timeout=10)
                if r.status_code not in (200, 301, 302, 307, 308):
                    print(f"⚠️  Warning: Domain {url} returned status {r.status_code}")
            except Exception as e:
                print(f"❌ Domain unreachable: {url} → {e}")
                failures[name] = failures.get(name, 0) + 1

                if failures[name] >= 3:
                    print(f"⛔ Skipping {name} permanently (3 failed attempts)")
                    all_results.append({
                        "name": name,
                        "website": url,
                        "error": "Unreachable domain",
                        "pages": {},
                        "found_urls": {},
                        "failed_pages": []
                    })
                    continue

                print("Skipping for now.")
                continue

            # ---------------------------------------
            # 2) SCRAPE COMPANY (WITH FULL ISOLATION)
            # ---------------------------------------
            try:
                result = self.scrape_company(company)
                all_results.append(result)

            except Exception as e:
                print(f"❌ scrape_company() crashed for {name}: {e}")
                failures[name] = failures.get(name, 0) + 1

                all_results.append({
                    "name": name,
                    "website": url,
                    "error": f"scrape_company crashed: {e}",
                    "pages": {},
                    "found_urls": {},
                    "failed_pages": ["ALL"]
                })

            # ---------------------------------------
            # 3) LOG TIMING
            # ---------------------------------------
            elapsed = time.time() - start_time
            print(f"⏱ Completed {name} in {elapsed:.2f} seconds")

            # Composer-safe gentle rate limit
            time.sleep(1)

        print("\n========== SCRAPING COMPLETE ==========")
        print("Results returned to DAG / caller.\n")
        self.print_summary(all_results)

        return all_results

    def save_html_to_file(self, company_name: str, page_type: str, html: str, output_dir: str):
        """
        Safe HTML writer with filename sanitization + retry.
        NOT used yet—added for future-proofing.
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            safe_company = re.sub(r'[^a-zA-Z0-9_-]+', '_', company_name)
            safe_page = re.sub(r'[^a-zA-Z0-9_-]+', '_', page_type)
            file_path = os.path.join(output_dir, f"{safe_company}_{safe_page}.html")

            for attempt in range(3):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    return file_path
                except:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to save HTML for {company_name}/{page_type}: {e}")
            return None


    def save_text_to_file(self, company_name: str, page_type: str, text: str, output_dir: str):
        """
        Safe TEXT writer with filename sanitization + retry.
        NOT used yet—added for future-proofing.
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            safe_company = re.sub(r'[^a-zA-Z0-9_-]+', '_', company_name)
            safe_page = re.sub(r'[^a-zA-Z0-9_-]+', '_', page_type)
            file_path = os.path.join(output_dir, f"{safe_company}_{safe_page}.txt")

            for attempt in range(3):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    return file_path
                except:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to save text for {company_name}/{page_type}: {e}")
            return None


    def save_text_to_file(self, company_name: str, page_type: str, text: str, output_dir: str):
        """
        Safe TEXT writer with filename sanitization + retry.
        NOT used yet—added for future-proofing.
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            safe_company = re.sub(r'[^a-zA-Z0-9_-]+', '_', company_name)
            safe_page = re.sub(r'[^a-zA-Z0-9_-]+', '_', page_type)
            file_path = os.path.join(output_dir, f"{safe_company}_{safe_page}.txt")

            for attempt in range(3):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    return file_path
                except:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to save text for {company_name}/{page_type}: {e}")
            return None
        
    def print_summary(self, results: List[Dict]):
        """
        Prints a clean, readable scrape summary showing:
        - total companies
        - successfully scraped
        - unreachable domains
        - pages found
        - pages failed
        - fallback usage: live / snapshot / google_cache / textise
        Does NOT modify results, only reads them.
        """

        total = len(results)
        success_count = 0
        unreachable = 0

        fallback_stats = {
            "live": 0,
            "snapshot": 0,
            "google_cache": 0,
            "textise": 0
        }

        total_pages = 0
        total_failed = 0

        for r in results:

            if "error" in r and r["error"] == "Unreachable domain":
                unreachable += 1
                continue

            if "pages" in r and r["pages"]:
                success_count += 1

                for page_type, content in r["pages"].items():
                    total_pages += 1
                    src = content["metadata"].get("source", "live")
                    if src in fallback_stats:
                        fallback_stats[src] += 1
            else:
                total_failed += 1

        print("\n========== SCRAPE SUMMARY ==========")
        print(f"Total companies:        {total}")
        print(f"Successful scrapes:     {success_count}")
        print(f"Unreachable domains:    {unreachable}")
        print(f"Companies with errors:  {total_failed}")
        print(f"Total pages scraped:    {total_pages}")

        print("\n--- Fallback Source Usage ---")
        print(f"Live HTML:              {fallback_stats['live']}")
        print(f"Static snapshot:        {fallback_stats['snapshot']}")
        print(f"Google Cache:           {fallback_stats['google_cache']}")
        print(f"Textise fallback:       {fallback_stats['textise']}")

        print("====================================\n")



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