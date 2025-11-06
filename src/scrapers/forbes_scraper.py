

# """
# Forbes AI 50 Production Scraper
# Complete solution with Forbes + LinkedIn + Resume + Validation
# """

# import requests
# from bs4 import BeautifulSoup
# import json
# from pathlib import Path
# import time
# import re
# from typing import Dict, List, Optional, Tuple
# from datetime import datetime
# import logging

# # Setup logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('scraper.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)


# class Config:
#     """Scraper configuration."""
#     LINKEDIN_DELAY = 3  # seconds
#     FORBES_DELAY = 2
#     REQUEST_TIMEOUT = 30
#     MAX_RETRIES = 3
#     SAVE_PROGRESS_EVERY = 10
#     VALIDATE_URLS = True
    
#     # All 50 companies
#     FORBES_AI50_2025 = [
#         "Abridge", "Anthropic", "Anysphere", "Baseten", "Captions",
#         "Clay", "Coactive AI", "Cohere", "Crusoe", "Databricks",
#         "Decagon", "DeepL", "ElevenLabs", "Figure AI", "Fireworks AI",
#         "Glean", "Harvey", "Hebbia", "Hugging Face", "Lambda",
#         "LangChain", "Luminance", "Mercor", "Midjourney", "Mistral AI",
#         "Notion", "OpenAI", "OpenEvidence", "Perplexity AI", "Photoroom",
#         "Pika", "Runway", "Sakana AI", "SambaNova", "Scale AI",
#         "Sierra", "Skild AI", "Snorkel AI", "Speak", "StackBlitz",
#         "Suno", "Synthesia", "Thinking Machine Labs", "Together AI",
#         "Vannevar Labs", "VAST Data", "Windsurf", "World Labs", "Writer", "XAI"
#     ]
    
#     # Manual website overrides (edge cases)
#     MANUAL_WEBSITES = {
#         'Anysphere': 'https://www.cursor.com',
#         'Windsurf': 'https://codeium.com',
#         'Pika': 'https://pika.art',
#         'Hugging Face': 'https://huggingface.co',
#         'Mistral AI': 'https://mistral.ai',
#         'DeepL': 'https://www.deepl.com',
#         'ElevenLabs': 'https://elevenlabs.io',
#         'Scale AI': 'https://scale.com',
#         'Anthropic': 'https://www.anthropic.com',
#         'OpenAI': 'https://www.openai.com',
#         'Databricks': 'https://www.databricks.com',
#         'Cohere': 'https://cohere.com',
#         'XAI': 'https://x.ai',
#         'Midjourney': 'https://www.midjourney.com',
#         'Notion': 'https://www.notion.so',
#     }


# class ProgressManager:
#     """Manages scraping progress and resume capability."""
    
#     def __init__(self, data_dir: Path):
#         self.progress_file = data_dir / "scraper_progress.json"
#         self.backup_dir = data_dir / "backups"
#         self.backup_dir.mkdir(exist_ok=True)
    
#     def save_progress(self, profiles: List[Dict], last_index: int):
#         """Save current progress."""
#         progress = {
#             'timestamp': datetime.now().isoformat(),
#             'last_completed_index': last_index,
#             'total_scraped': len(profiles),
#             'profiles': profiles
#         }
        
#         with open(self.progress_file, 'w') as f:
#             json.dump(progress, f, indent=2)
        
#         logger.info(f"💾 Progress saved: {len(profiles)} profiles, last index: {last_index}")
    
#     def load_progress(self) -> Tuple[List[Dict], int]:
#         """Load saved progress if exists."""
#         if not self.progress_file.exists():
#             return [], -1
        
#         try:
#             with open(self.progress_file, 'r') as f:
#                 progress = json.load(f)
            
#             profiles = progress.get('profiles', [])
#             last_index = progress.get('last_completed_index', -1)
            
#             logger.info(f"📂 Resumed from save: {len(profiles)} profiles, starting at index {last_index + 1}")
#             return profiles, last_index
        
#         except Exception as e:
#             logger.error(f"❌ Could not load progress: {e}")
#             return [], -1
    
#     def clear_progress(self):
#         """Clear progress file."""
#         if self.progress_file.exists():
#             # Create backup
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             backup_path = self.backup_dir / f"progress_backup_{timestamp}.json"
#             self.progress_file.rename(backup_path)
#             logger.info(f"🗑️ Progress cleared, backup: {backup_path}")


# class URLValidator:
#     """Validates URLs are reachable."""
    
#     def __init__(self):
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
#         }
    
#     def validate(self, url: str, timeout: int = 5) -> bool:
#         """Check if URL is reachable."""
#         if not url or url == "Not available":
#             return False
        
#         try:
#             response = requests.head(url, headers=self.headers, timeout=timeout, allow_redirects=True)
#             return response.status_code < 400
#         except:
#             # Try GET as fallback (some sites block HEAD)
#             try:
#                 response = requests.get(url, headers=self.headers, timeout=timeout, allow_redirects=True)
#                 return response.status_code < 400
#             except:
#                 return False


# class LinkedInWebsiteScraper:
#     """Scrapes company websites from LinkedIn public pages."""
    
#     def __init__(self):
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.9',
#         }
#         self.blocked = False
    
#     def build_linkedin_url(self, company_name: str) -> str:
#         """Build LinkedIn company URL from name."""
#         slug = company_name.lower()
#         slug = slug.replace(' ', '-').replace('.', '').replace("'", '')
#         slug = re.sub(r'[^a-z0-9-]', '', slug)
        
#         return f"https://www.linkedin.com/company/{slug}/"
    
#     def scrape_website(self, company_name: str, max_retries: int = 3) -> Optional[str]:
#         """
#         Scrape company website from LinkedIn profile.
#         Returns website URL or None.
#         """
#         if self.blocked:
#             logger.warning(f"⚠️ LinkedIn blocked, skipping {company_name}")
#             return None
        
#         linkedin_url = self.build_linkedin_url(company_name)
        
#         for attempt in range(max_retries):
#             try:
#                 logger.info(f"   🔗 LinkedIn: {linkedin_url} (attempt {attempt + 1}/{max_retries})")
                
#                 response = requests.get(linkedin_url, headers=self.headers, timeout=Config.REQUEST_TIMEOUT)
                
#                 # Check for blocking
#                 if response.status_code == 999:  # LinkedIn blocking code
#                     logger.warning(f"⚠️ LinkedIn rate limit detected!")
#                     self.blocked = True
#                     return None
                
#                 if response.status_code == 404:
#                     # Try alternative slug
#                     if attempt == 0 and ' ' in company_name:
#                         # Try without spaces
#                         alt_slug = company_name.lower().replace(' ', '').replace('.', '')
#                         linkedin_url = f"https://www.linkedin.com/company/{alt_slug}/"
#                         continue
                    
#                     logger.warning(f"   ⚠️ LinkedIn profile not found (404)")
#                     return None
                
#                 response.raise_for_status()
                
#                 # Check for auth wall
#                 if 'authwall' in response.text.lower() or 'sign in to see' in response.text.lower():
#                     logger.warning(f"⚠️ LinkedIn auth wall detected")
#                     self.blocked = True
#                     return None
                
#                 soup = BeautifulSoup(response.text, 'html.parser')
                
#                 # Strategy 1: Look for website link in header
#                 # LinkedIn structure: <a class="link-without-visited-state" href="http://company.com">
#                 website_link = soup.find('a', {'class': re.compile(r'link-without-visited')})
#                 if website_link and website_link.get('href'):
#                     website = website_link['href']
#                     if website.startswith('http'):
#                         logger.info(f"   ✅ Found website: {website}")
#                         return website
                
#                 # Strategy 2: Look for any external link in top card
#                 top_card = soup.find('div', {'class': re.compile(r'org-top-card')})
#                 if top_card:
#                     for link in top_card.find_all('a', href=True):
#                         href = link['href']
#                         if href.startswith('http') and 'linkedin.com' not in href:
#                             logger.info(f"   ✅ Found website in top card: {href}")
#                             return href
                
#                 # Strategy 3: Look for text pattern "Visit website: company.com"
#                 text = soup.get_text()
#                 url_match = re.search(r'(?:website|visit)[\s:]+(?:https?://)?([a-zA-Z0-9.-]+\.(?:com|ai|io|co))', text, re.IGNORECASE)
#                 if url_match:
#                     website = url_match.group(0)
#                     if not website.startswith('http'):
#                         website = 'https://' + website
#                     logger.info(f"   ✅ Found website in text: {website}")
#                     return website
                
#                 logger.warning(f"   ⚠️ No website found on LinkedIn page")
#                 return None
            
#             except requests.exceptions.RequestException as e:
#                 logger.warning(f"   ⚠️ Request failed (attempt {attempt + 1}): {e}")
#                 if attempt < max_retries - 1:
#                     time.sleep(5)  # Wait before retry
            
#             except Exception as e:
#                 logger.error(f"   ❌ Unexpected error: {e}")
#                 return None
        
#         return None


# class ForbesProfileScraper:
#     """Scrapes Forbes company profiles."""
    
#     def __init__(self):
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#         }
    
#     def build_profile_url(self, company_name: str) -> str:
#         """Build Forbes profile URL."""
#         slug = company_name.lower().replace(' ', '-').replace('.', '')
#         slug = re.sub(r'[^a-z0-9-]', '', slug)
#         return f"https://www.forbes.com/companies/{slug}/?list=ai50"
    
#     def scrape(self, company_name: str, save_dir: Path, max_retries: int = 3) -> Dict:
#         """Scrape Forbes profile page."""
#         url = self.build_profile_url(company_name)
        
#         for attempt in range(max_retries):
#             try:
#                 logger.info(f"   📄 Forbes: {url} (attempt {attempt + 1}/{max_retries})")
                
#                 response = requests.get(url, headers=self.headers, timeout=Config.REQUEST_TIMEOUT)
                
#                 if response.status_code == 404:
#                     logger.warning(f"   ⚠️ Forbes profile not found (404)")
#                     return self._empty_profile(company_name, url)
                
#                 response.raise_for_status()
                
#                 # Save HTML
#                 company_dir = save_dir / company_name.replace(' ', '_').replace('/', '_')
#                 company_dir.mkdir(exist_ok=True)
                
#                 with open(company_dir / "forbes_profile.html", 'w', encoding='utf-8') as f:
#                     f.write(response.text)
                
#                 soup = BeautifulSoup(response.text, 'html.parser')
                
#                 with open(company_dir / "forbes_profile.txt", 'w', encoding='utf-8') as f:
#                     f.write(soup.get_text())
                
#                 # Extract data
#                 json_ld = self._extract_json_ld(soup)
                
#                 profile = {
#                     'company_name': company_name,
#                     'forbes_url': url,
#                     'ceo': self._extract_ceo(soup, json_ld),
#                     'founded_year': self._extract_founded(soup, json_ld),
#                     'hq_city': self._extract_hq_city(soup, json_ld),
#                     'hq_country': self._extract_hq_country(soup),
#                     'employees': self._extract_employees(soup, json_ld),
#                     'industry': self._extract_industry(soup),
#                     'description': self._extract_description(soup),
#                     'total_funding': self._extract_total_funding(soup),
#                     'valuation': self._extract_valuation(soup),
#                 }
                
#                 logger.info(f"   ✅ Forbes scraped successfully")
#                 return profile
            
#             except Exception as e:
#                 logger.warning(f"   ⚠️ Forbes scrape failed (attempt {attempt + 1}): {e}")
#                 if attempt < max_retries - 1:
#                     time.sleep(5)
        
#         logger.error(f"   ❌ Forbes scraping failed after {max_retries} attempts")
#         return self._empty_profile(company_name, url)
    
#     def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
#         """Extract JSON-LD structured data."""
#         try:
#             script_tag = soup.find('script', type='application/ld+json')
#             if script_tag and script_tag.string:
#                 return json.loads(script_tag.string)
#         except:
#             pass
#         return None
    
#     def _extract_ceo(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> str:
#         """Extract CEO with validation."""
#         # 1. JSON-LD
#         if json_ld and 'employee' in json_ld:
#             if isinstance(json_ld['employee'], dict):
#                 name = json_ld['employee'].get('name', '')
#                 if name and self._validate_name(name):
#                     return name
        
#         # 2. CSS
#         stats = soup.find_all('dt', class_='profile-stats__title')
#         for stat in stats:
#             if 'CEO' in stat.get_text():
#                 dd = stat.find_next_sibling('dd')
#                 if dd:
#                     name = dd.get_text().strip()
#                     if self._validate_name(name):
#                         return name
        
#         # 3. Description extraction
#         desc = self._extract_description(soup)
#         patterns = [
#             r'CEO\s+(?:and\s+)?(?:co)?founder\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
#             r'(?:Founded|Co-founded)\s+by\s+(?:CEO\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
#             r'CEO\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
#         ]
        
#         for pattern in patterns:
#             match = re.search(pattern, desc)
#             if match:
#                 name = match.group(1).strip()
#                 if self._validate_name(name):
#                     return name
        
#         return "Not available"
    
#     def _validate_name(self, name: str) -> bool:
#         """Validate person name."""
#         if not name:
#             return False
        
#         # Reject bad patterns
#         bad = ['Network', 'Forbes', 'http', 'www', 'Click', 'See All']
#         if any(b in name for b in bad):
#             return False
        
#         words = name.split()
#         return 2 <= len(words) <= 5 and len(name) < 60
    
#     def _extract_founded(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> Optional[int]:
#         """Extract founded year."""
#         if json_ld and 'foundingDate' in json_ld:
#             try:
#                 year = int(json_ld['foundingDate'])
#                 if 1990 <= year <= 2025:
#                     return year
#             except:
#                 pass
        
#         stats = soup.find_all('dt', class_='profile-stats__title')
#         for stat in stats:
#             if 'Founded' in stat.get_text():
#                 dd = stat.find_next_sibling('dd')
#                 if dd:
#                     match = re.search(r'(\d{4})', dd.get_text())
#                     if match:
#                         year = int(match.group(1))
#                         if 1990 <= year <= 2025:
#                             return year
        
#         return None
    
#     def _extract_hq_city(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> str:
#         """Extract HQ city."""
#         if json_ld and 'location' in json_ld:
#             loc = json_ld['location']
#             if ',' in loc:
#                 return loc.split(',')[0].strip()
        
#         stats = soup.find_all('dt', class_='profile-stats__title')
#         for stat in stats:
#             if 'Headquarters' in stat.get_text():
#                 dd = stat.find_next_sibling('dd')
#                 if dd:
#                     hq = dd.get_text().strip()
#                     if ',' in hq:
#                         return hq.split(',')[0].strip()
#                     return hq
        
#         location_div = soup.find(class_='listuser-header__headline--premium-location')
#         if location_div:
#             loc = location_div.get_text().strip()
#             if ',' in loc:
#                 return loc.split(',')[0].strip()
#             return loc
        
#         return "Not available"
    
#     def _extract_hq_country(self, soup: BeautifulSoup) -> str:
#         """Extract HQ country."""
#         stats = soup.find_all('dt', class_='profile-stats__title')
#         for stat in stats:
#             if 'Country' in stat.get_text() or 'Territory' in stat.get_text():
#                 dd = stat.find_next_sibling('dd')
#                 if dd:
#                     return dd.get_text().strip()
        
#         return "United States"
    
#     def _extract_employees(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> Optional[int]:
#         """Extract employee count with validation."""
#         # JSON-LD
#         if json_ld and 'numberOfEmployees' in json_ld:
#             try:
#                 count = int(json_ld['numberOfEmployees'])
#                 # Validate (reject obvious placeholders)
#                 if count > 10 and count != 1 and count != 5 and count != 8:
#                     return count
#             except:
#                 pass
        
#         # CSS
#         stats = soup.find_all('dt', class_='profile-stats__title')
#         for stat in stats:
#             if 'Employee' in stat.get_text():
#                 dd = stat.find_next_sibling('dd')
#                 if dd:
#                     text = dd.get_text().replace(',', '')
#                     match = re.search(r'(\d+)', text)
#                     if match:
#                         count = int(match.group(1))
#                         if count > 10:
#                             return count
        
#         return None
    
#     def _extract_industry(self, soup: BeautifulSoup) -> str:
#         """Extract industry."""
#         stats = soup.find_all('dt', class_='profile-stats__title')
#         for stat in stats:
#             if 'Industry' in stat.get_text():
#                 dd = stat.find_next_sibling('dd')
#                 if dd:
#                     return dd.get_text().strip()
#         return "AI Technology"
    
#     def _extract_description(self, soup: BeautifulSoup) -> str:
#         """Extract full description."""
#         bio_div = soup.find(class_='listuser-alternative-bio__content')
#         if bio_div:
#             expanded = bio_div.find(class_='expanded')
#             shortened = bio_div.find(class_='shortened')
            
#             text = (expanded or shortened or bio_div).get_text()
#             text = text.replace('Read More', '').replace('Read Less', '').strip()
#             text = re.sub(r'\s+', ' ', text)
            
#             if len(text) > 100:
#                 return text
        
#         return "Not available"
    
#     def _extract_total_funding(self, soup: BeautifulSoup) -> str:
#         """Extract total funding raised."""
#         text = soup.get_text()
        
#         patterns = [
#             r'raised\s+(?:a\s+)?total\s+(?:of\s+)?\$?([\d.]+)\s*(billion|million|B|M)',
#             r'total\s+(?:of\s+)?\$?([\d.]+)\s*(billion|million|B|M)\s+in\s+funding',
#         ]
        
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 amount = match.group(1)
#                 unit = match.group(2)[0].upper()
#                 return f'${amount}{unit}'
        
#         return "Not available"
    
#     def _extract_valuation(self, soup: BeautifulSoup) -> str:
#         """Extract current valuation."""
#         text = soup.get_text()
        
#         patterns = [
#             r'valued at\s+\$?([\d.]+)\s*(billion|million|B|M)',
#             r'valuation\s+of\s+\$?([\d.]+)\s*(billion|million|B|M)',
#         ]
        
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 amount = match.group(1)
#                 unit = match.group(2)[0].upper()
#                 return f'${amount}{unit}'
        
#         return "Not available"
    
#     def _empty_profile(self, company_name: str, url: str) -> Dict:
#         """Create empty profile."""
#         return {
#             'company_name': company_name,
#             'forbes_url': url,
#             'ceo': "Not available",
#             'founded_year': None,
#             'hq_city': "Not available",
#             'hq_country': "United States",
#             'employees': None,
#             'industry': "AI Technology",
#             'description': "Not available",
#             'total_funding': "Not available",
#             'valuation': "Not available",
#         }


# class ForbesProductionScraper:
#     """Main production scraper orchestrator."""
    
#     def __init__(self, data_dir: Path = None):
#         if data_dir is None:
#             self.data_dir = Path(__file__).resolve().parents[2] / "data"
#         else:
#             self.data_dir = Path(data_dir)
        
#         self.profiles_dir = self.data_dir / "profiles"
#         self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
#         self.progress_mgr = ProgressManager(self.data_dir)
#         self.url_validator = URLValidator()
#         self.linkedin_scraper = LinkedInWebsiteScraper()
#         self.forbes_scraper = ForbesProfileScraper()
    
#     def infer_website(self, company_name: str) -> str:
#         """Infer website from company name."""
#         # Check manual override first
#         if company_name in Config.MANUAL_WEBSITES:
#             return Config.MANUAL_WEBSITES[company_name]
        
#         slug = company_name.lower().replace(' ', '').replace('.', '').replace("'", '')
        
#         # Pattern rules
#         if 'ai' in company_name.lower():
#             # "Mistral AI" -> mistral.ai
#             base = slug.replace('ai', '')
#             return f"https://{base}.ai"
        
#         if 'labs' in company_name.lower():
#             # "World Labs" -> worldlabs.com
#             return f"https://{slug}.com"
        
#         # Default
#         return f"https://{slug}.com"
    
#     def get_website(self, company_name: str) -> Tuple[str, str]:
#         """
#         Get company website with multi-strategy approach.
#         Returns: (website_url, source)
#         """
#         # Strategy 1: Manual override
#         if company_name in Config.MANUAL_WEBSITES:
#             website = Config.MANUAL_WEBSITES[company_name]
#             logger.info(f"   ✅ Website (manual): {website}")
#             return website, "manual"
        
#         # Strategy 2: LinkedIn scraping
#         linkedin_website = self.linkedin_scraper.scrape_website(company_name)
#         if linkedin_website:
#             # Validate
#             if Config.VALIDATE_URLS:
#                 if self.url_validator.validate(linkedin_website):
#                     logger.info(f"   ✅ Website (LinkedIn, validated): {linkedin_website}")
#                     return linkedin_website, "linkedin"
#                 else:
#                     logger.warning(f"   ⚠️ LinkedIn URL not reachable: {linkedin_website}")
#             else:
#                 logger.info(f"   ✅ Website (LinkedIn): {linkedin_website}")
#                 return linkedin_website, "linkedin"
        
#         # Strategy 3: Pattern inference
#         inferred = self.infer_website(company_name)
        
#         if Config.VALIDATE_URLS:
#             if self.url_validator.validate(inferred):
#                 logger.info(f"   ✅ Website (inferred, validated): {inferred}")
#                 return inferred, "inferred"
#             else:
#                 logger.warning(f"   ⚠️ Inferred URL not reachable: {inferred}")
#                 return "Not available", "failed"
        
#         logger.info(f"   ✅ Website (inferred): {inferred}")
#         return inferred, "inferred"
    
#     def infer_category(self, industry: str, description: str) -> str:
#         """Infer AI category."""
#         text = (industry + ' ' + description).lower()
        
#         categories = {
#             'healthcare_ai': ['health', 'medical', 'doctor', 'clinical', 'patient', 'drug'],
#             'legal_ai': ['legal', 'law', 'contract'],
#             'customer_service_ai': ['customer service', 'customer support', 'agent', 'chatbot'],
#             'coding_ai': ['coding', 'code', 'developer', 'software', 'IDE', 'programming'],
#             'search_ai': ['search engine', 'answer engine', 'query'],
#             'voice_ai': ['voice', 'audio', 'speech', 'sound', 'dubbing'],
#             'video_ai': ['video', 'image', 'visual', 'photo', 'generation'],
#             'data_ai': ['data', 'database', 'analytics', 'labeling'],
#             'infrastructure_ai': ['cloud', 'compute', 'chip', 'GPU', 'infrastructure'],
#             'robotics_ai': ['robot', 'humanoid'],
#             'language_ai': ['translation', 'language learning', 'translate'],
#         }
        
#         for category, keywords in categories.items():
#             if any(kw in text for kw in keywords):
#                 return category
        
#         return 'general_ai'
    
#     def scrape_company(self, company_name: str) -> Dict:
#         """Scrape single company (Forbes + LinkedIn)."""
#         logger.info(f"\n{'='*70}")
#         logger.info(f"🔍 Scraping: {company_name}")
#         logger.info(f"{'='*70}")
        
#         # Step 1: Forbes profile
#         forbes_data = self.forbes_scraper.scrape(company_name, self.profiles_dir)
        
#         time.sleep(Config.FORBES_DELAY)
        
#         # Step 2: LinkedIn website
#         website, source = self.get_website(company_name)
        
#         if source == "linkedin":
#             time.sleep(Config.LINKEDIN_DELAY)
        
#         # Step 3: Build LinkedIn profile URL
#         linkedin_slug = company_name.lower().replace(' ', '-').replace('.', '').replace("'", '')
#         linkedin_url = f"https://www.linkedin.com/company/{linkedin_slug}/"
        
#         # Step 4: Infer category
#         category = self.infer_category(
#             forbes_data.get('industry', ''),
#             forbes_data.get('description', '')
#         )
        
#         # Step 5: Merge data
#         profile = {
#             **forbes_data,
#             'website': website,
#             'website_source': source,
#             'linkedin': linkedin_url,
#             'category': category,
#         }
        
#         # Log summary
#         logger.info(f"   ✅ CEO: {profile['ceo']}")
#         logger.info(f"   ✅ Founded: {profile['founded_year']}")
#         logger.info(f"   ✅ HQ: {profile['hq_city']}, {profile['hq_country']}")
#         logger.info(f"   ✅ Employees: {profile['employees']}")
#         logger.info(f"   ✅ Website: {profile['website']} ({source})")
#         logger.info(f"   ✅ Category: {profile['category']}")
        
#         return profile
    
#     def scrape_all(self, resume: bool = True):
#         """
#         Main scraping function with resume capability.
        
#         Args:
#             resume: If True, resume from last save point
#         """
#         print("\n" + "="*70)
#         print("FORBES AI 50 PRODUCTION SCRAPER")
#         print("="*70)
#         print(f"📊 Total companies: {len(Config.FORBES_AI50_2025)}")
#         print(f"💾 Progress saving: Every {Config.SAVE_PROGRESS_EVERY} companies")
#         print(f"🔗 LinkedIn scraping: Enabled ({Config.LINKEDIN_DELAY}s delay)")
#         print(f"✅ URL validation: {'Enabled' if Config.VALIDATE_URLS else 'Disabled'}")
#         print(f"🔄 Resume: {'Enabled' if resume else 'Disabled'}")
        
#         # Load progress if resuming
#         if resume:
#             all_profiles, last_index = self.progress_mgr.load_progress()
#             start_index = last_index + 1
#         else:
#             all_profiles = []
#             start_index = 0
#             self.progress_mgr.clear_progress()
        
#         companies = Config.FORBES_AI50_2025
        
#         print(f"\n🚀 Starting from company #{start_index + 1}: {companies[start_index] if start_index < len(companies) else 'N/A'}")
#         print("="*70)
        
#         # Scrape companies
#         for i in range(start_index, len(companies)):
#             company_name = companies[i]
            
#             print(f"\n[{i + 1}/{len(companies)}] {company_name}")
            
#             try:
#                 profile = self.scrape_company(company_name)
#                 all_profiles.append(profile)
                
#                 # Save progress periodically
#                 if (i + 1) % Config.SAVE_PROGRESS_EVERY == 0:
#                     self.progress_mgr.save_progress(all_profiles, i)
#                     logger.info(f"💾 Checkpoint saved!")
            
#             except KeyboardInterrupt:
#                 logger.info("\n⚠️ Interrupted by user")
#                 self.progress_mgr.save_progress(all_profiles, i - 1)
#                 logger.info("💾 Progress saved. Run again with resume=True to continue.")
#                 return all_profiles
            
#             except Exception as e:
#                 logger.error(f"❌ Failed to scrape {company_name}: {e}")
#                 # Add empty profile so we don't skip
#                 all_profiles.append(self.forbes_scraper._empty_profile(company_name, ""))
        
#         # Final save
#         print("\n" + "="*70)
#         print("SAVING FINAL RESULTS")
#         print("="*70)
        
#         output_path = self.data_dir / "forbes_ai50_seed.json"
        
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(all_profiles, f, indent=2, ensure_ascii=False)
        
#         logger.info(f"✅ Saved {len(all_profiles)} profiles to {output_path}")
        
#         # Generate report
#         self.generate_report(all_profiles)
        
#         # Clear progress file
#         self.progress_mgr.clear_progress()
        
#         return all_profiles
    
#     def generate_report(self, profiles: List[Dict]):
#         """Generate data quality report."""
#         print("\n" + "="*70)
#         print("DATA QUALITY REPORT")
#         print("="*70)
        
#         total = len(profiles)
        
#         # Completeness metrics
#         with_ceo = sum(1 for p in profiles if p.get('ceo') != 'Not available')
#         with_website = sum(1 for p in profiles if p.get('website') != 'Not available')
#         with_hq = sum(1 for p in profiles if p.get('hq_city') != 'Not available')
#         with_founded = sum(1 for p in profiles if p.get('founded_year') is not None)
#         with_employees = sum(1 for p in profiles if p.get('employees') is not None)
#         with_funding = sum(1 for p in profiles if p.get('total_funding') != 'Not available')
#         with_valuation = sum(1 for p in profiles if p.get('valuation') != 'Not available')
#         with_desc = sum(1 for p in profiles if p.get('description', 'Not available') != 'Not available' and len(p.get('description', '')) > 100)
        
#         print(f"\n📊 Completeness:")
#         print(f"   Companies: {total}/50 ({total/50*100:.0f}%)")
#         print(f"   CEO: {with_ceo}/{total} ({with_ceo/total*100:.0f}%)")
#         print(f"   Website: {with_website}/{total} ({with_website/total*100:.0f}%)")
#         print(f"   HQ: {with_hq}/{total} ({with_hq/total*100:.0f}%)")
#         print(f"   Founded: {with_founded}/{total} ({with_founded/total*100:.0f}%)")
#         print(f"   Employees: {with_employees}/{total} ({with_employees/total*100:.0f}%)")
#         print(f"   Funding: {with_funding}/{total} ({with_funding/total*100:.0f}%)")
#         print(f"   Valuation: {with_valuation}/{total} ({with_valuation/total*100:.0f}%)")
#         print(f"   Description: {with_desc}/{total} ({with_desc/total*100:.0f}%)")
        
#         # Website sources
#         print(f"\n🌐 Website Sources:")
#         sources = {}
#         for p in profiles:
#             source = p.get('website_source', 'unknown')
#             sources[source] = sources.get(source, 0) + 1
        
#         for source, count in sorted(sources.items()):
#             print(f"   {source}: {count}")
        
#         # Category distribution
#         print(f"\n📂 Categories:")
#         categories = {}
#         for p in profiles:
#             cat = p.get('category', 'unknown')
#             categories[cat] = categories.get(cat, 0) + 1
        
#         for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
#             print(f"   {cat}: {count}")
        
#         # Geographic distribution
#         print(f"\n🌍 Countries:")
#         countries = {}
#         for p in profiles:
#             country = p.get('hq_country', 'Unknown')
#             countries[country] = countries.get(country, 0) + 1
        
#         for country, count in sorted(countries.items(), key=lambda x: -x[1]):
#             print(f"   {country}: {count}")
        
#         print(f"\n📂 Profile HTMLs saved in: {self.profiles_dir}")
#         print(f"📄 Final JSON: {self.data_dir / 'forbes_ai50_seed.json'}")
#         print(f"📝 Log file: scraper.log")
#         print("\n✅ Scraping Complete!")


# def main():
#     """Main entry point."""
#     import sys
    
#     print("""
#     ╔════════════════════════════════════════════════════════════════╗
#     ║          FORBES AI 50 PRODUCTION SCRAPER v3.0                  ║
#     ║                                                                ║
#     ║  Features:                                                     ║
#     ║  ✅ Forbes profiles for main data                             ║
#     ║  ✅ LinkedIn scraping for websites                            ║
#     ║  ✅ Manual overrides for edge cases                           ║
#     ║  ✅ Resume from save point                                    ║
#     ║  ✅ URL validation                                            ║
#     ║  ✅ Retry logic                                               ║
#     ║                                                                ║
#     ║  Usage:                                                        ║
#     ║    python forbes_scraper.py                  (normal run)      ║
#     ║    python forbes_scraper.py --fresh          (start fresh)     ║
#     ║    python forbes_scraper.py --no-validate    (skip URL check)  ║
#     ╚════════════════════════════════════════════════════════════════╝
#     """)
    
#     # Parse args
#     resume = '--fresh' not in sys.argv
#     Config.VALIDATE_URLS = '--no-validate' not in sys.argv
    
#     if resume:
#         print("🔄 Resume mode: Will continue from last save point\n")
#     else:
#         print("🆕 Fresh start: Starting from scratch\n")
    
#     # Create scraper
#     scraper = ForbesProductionScraper()
    
#     # Run
#     try:
#         scraper.scrape_all(resume=resume)
#     except KeyboardInterrupt:
#         print("\n⚠️ Interrupted! Progress saved. Run again to resume.")
#     except Exception as e:
#         logger.error(f"❌ Fatal error: {e}")
#         import traceback
#         traceback.print_exc()


# if __name__ == "__main__":
#     main()

"""
Forbes AI 50 Production Scraper
Complete solution with Forbes + LinkedIn + Resume + Validation
FIXED: All 50 companies now have correct websites
"""

import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Scraper configuration."""
    LINKEDIN_DELAY = 3  # seconds
    FORBES_DELAY = 2
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    SAVE_PROGRESS_EVERY = 10
    VALIDATE_URLS = True
    
    # All 50 companies
    FORBES_AI50_2025 = [
        "Abridge", "Anthropic", "Anysphere", "Baseten", "Captions",
        "Clay", "Coactive AI", "Cohere", "Crusoe", "Databricks",
        "Decagon", "DeepL", "ElevenLabs", "Figure AI", "Fireworks AI",
        "Glean", "Harvey", "Hebbia", "Hugging Face", "Lambda",
        "LangChain", "Luminance", "Mercor", "Midjourney", "Mistral AI",
        "Notion", "OpenAI", "OpenEvidence", "Perplexity AI", "Photoroom",
        "Pika", "Runway", "Sakana AI", "SambaNova", "Scale AI",
        "Sierra", "Skild AI", "Snorkel AI", "Speak", "StackBlitz",
        "Suno", "Synthesia", "Thinking Machine Labs", "Together AI",
        "Vannevar Labs", "VAST Data", "Windsurf", "World Labs", "Writer", "XAI"
    ]
    
    # COMPLETE manual website overrides - ALL 50 companies
    MANUAL_WEBSITES = {
        'Abridge': 'https://abridge.com',
        'Anthropic': 'https://www.anthropic.com',
        'Anysphere': 'https://www.cursor.com',
        'Baseten': 'https://baseten.com',
        'Captions': 'https://captions.com',
        'Clay': 'https://clay.com',
        'Coactive AI': 'https://coactive.ai',
        'Cohere': 'https://cohere.com',
        'Crusoe': 'https://crusoe.com',
        'Databricks': 'https://www.databricks.com',
        'Decagon': 'https://decagon.ai',
        'DeepL': 'https://www.deepl.com',
        'ElevenLabs': 'https://elevenlabs.io',
        'Figure AI': 'https://figure.ai',
        'Fireworks AI': 'https://fireworks.ai',
        'Glean': 'https://glean.com',
        'Harvey': 'https://harvey.ai',
        'Hebbia': 'https://hebbia.com',
        'Hugging Face': 'https://huggingface.co',
        'Lambda': 'https://lambdalabs.com',
        'LangChain': 'https://langchain.com',
        'Luminance': 'https://luminance.com',
        'Mercor': 'https://mercor.com',
        'Midjourney': 'https://www.midjourney.com',
        'Mistral AI': 'https://mistral.ai',
        'Notion': 'https://www.notion.so',
        'OpenAI': 'https://www.openai.com',
        'OpenEvidence': 'https://openevidence.com',
        'Perplexity AI': 'https://perplexity.ai',
        'Photoroom': 'https://photoroom.com',
        'Pika': 'https://pika.art',
        'Runway': 'https://runway.com',
        'Sakana AI': 'https://sakana.ai',
        'SambaNova': 'https://sambanova.ai',
        'Scale AI': 'https://scale.com',
        'Sierra': 'https://sierra.ai',
        'Skild AI': 'https://skild.ai',
        'Snorkel AI': 'https://snorkel.ai',
        'Speak': 'https://speak.com',
        'StackBlitz': 'https://stackblitz.com',
        'Suno': 'https://suno.com',
        'Synthesia': 'https://synthesia.com',
        'Thinking Machine Labs': 'Not available',  # Stealth startup
        'Together AI': 'https://together.ai',
        'Vannevar Labs': 'https://vannevarlabs.com',
        'VAST Data': 'https://vastdata.com',
        'Windsurf': 'https://codeium.com',
        'World Labs': 'https://worldlabs.com',
        'Writer': 'https://writer.com',
        'XAI': 'https://x.ai',
    }


class ProgressManager:
    """Manages scraping progress and resume capability."""
    
    def __init__(self, data_dir: Path):
        self.progress_file = data_dir / "scraper_progress.json"
        self.backup_dir = data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def save_progress(self, profiles: List[Dict], last_index: int):
        """Save current progress."""
        progress = {
            'timestamp': datetime.now().isoformat(),
            'last_completed_index': last_index,
            'total_scraped': len(profiles),
            'profiles': profiles
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        
        logger.info(f"💾 Progress saved: {len(profiles)} profiles, last index: {last_index}")
    
    def load_progress(self) -> Tuple[List[Dict], int]:
        """Load saved progress if exists."""
        if not self.progress_file.exists():
            return [], -1
        
        try:
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
            
            profiles = progress.get('profiles', [])
            last_index = progress.get('last_completed_index', -1)
            
            logger.info(f"📂 Resumed from save: {len(profiles)} profiles, starting at index {last_index + 1}")
            return profiles, last_index
        
        except Exception as e:
            logger.error(f"❌ Could not load progress: {e}")
            return [], -1
    
    def clear_progress(self):
        """Clear progress file."""
        if self.progress_file.exists():
            # Create backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = self.backup_dir / f"progress_backup_{timestamp}.json"
            self.progress_file.rename(backup_path)
            logger.info(f"🗑️ Progress cleared, backup: {backup_path}")


class URLValidator:
    """Validates URLs are reachable."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def validate(self, url: str, timeout: int = 10) -> bool:
        """Check if URL is reachable."""
        if not url or url == "Not available":
            return False
        
        try:
            # Try GET directly (some sites block HEAD)
            response = requests.get(url, headers=self.headers, timeout=timeout, allow_redirects=True)
            return response.status_code < 400
        except:
            return False


class LinkedInWebsiteScraper:
    """Scrapes company websites from LinkedIn public pages."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.blocked = False
    
    def build_linkedin_url(self, company_name: str) -> str:
        """Build LinkedIn company URL from name."""
        slug = company_name.lower()
        slug = slug.replace(' ', '-').replace('.', '').replace("'", '')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        return f"https://www.linkedin.com/company/{slug}/"
    
    def scrape_website(self, company_name: str, max_retries: int = 2) -> Optional[str]:
        """
        Scrape company website from LinkedIn profile.
        Returns website URL or None.
        """
        if self.blocked:
            logger.warning(f"⚠️ LinkedIn blocked, skipping {company_name}")
            return None
        
        linkedin_url = self.build_linkedin_url(company_name)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"   🔗 LinkedIn: {linkedin_url} (attempt {attempt + 1}/{max_retries})")
                
                response = requests.get(linkedin_url, headers=self.headers, timeout=Config.REQUEST_TIMEOUT)
                
                # Check for blocking
                if response.status_code == 999:  # LinkedIn blocking code
                    logger.warning(f"⚠️ LinkedIn rate limit detected!")
                    self.blocked = True
                    return None
                
                if response.status_code == 404:
                    logger.warning(f"   ⚠️ LinkedIn profile not found (404)")
                    return None
                
                response.raise_for_status()
                
                # Check for auth wall
                if 'authwall' in response.text.lower() or 'sign in to see' in response.text.lower():
                    logger.warning(f"⚠️ LinkedIn auth wall detected")
                    self.blocked = True
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Strategy 1: Look for website link
                website_link = soup.find('a', {'class': re.compile(r'link-without-visited')})
                if website_link and website_link.get('href'):
                    website = website_link['href']
                    if website.startswith('http'):
                        logger.info(f"   ✅ Found website: {website}")
                        return website
                
                # Strategy 2: Look in top card
                top_card = soup.find('div', {'class': re.compile(r'org-top-card')})
                if top_card:
                    for link in top_card.find_all('a', href=True):
                        href = link['href']
                        if href.startswith('http') and 'linkedin.com' not in href:
                            logger.info(f"   ✅ Found website in top card: {href}")
                            return href
                
                logger.warning(f"   ⚠️ No website found on LinkedIn page")
                return None
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"   ⚠️ Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
            
            except Exception as e:
                logger.error(f"   ❌ Unexpected error: {e}")
                return None
        
        return None


class ForbesProfileScraper:
    """Scrapes Forbes company profiles."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def build_profile_url(self, company_name: str) -> str:
        """Build Forbes profile URL."""
        slug = company_name.lower().replace(' ', '-').replace('.', '')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        return f"https://www.forbes.com/companies/{slug}/?list=ai50"
    
    def scrape(self, company_name: str, save_dir: Path, max_retries: int = 3) -> Dict:
        """Scrape Forbes profile page."""
        url = self.build_profile_url(company_name)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"   📄 Forbes: {url} (attempt {attempt + 1}/{max_retries})")
                
                response = requests.get(url, headers=self.headers, timeout=Config.REQUEST_TIMEOUT)
                
                if response.status_code == 404:
                    logger.warning(f"   ⚠️ Forbes profile not found (404)")
                    return self._empty_profile(company_name, url)
                
                response.raise_for_status()
                
                # Save HTML
                company_dir = save_dir / company_name.replace(' ', '_').replace('/', '_')
                company_dir.mkdir(exist_ok=True)
                
                with open(company_dir / "forbes_profile.html", 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                with open(company_dir / "forbes_profile.txt", 'w', encoding='utf-8') as f:
                    f.write(soup.get_text())
                
                # Extract data
                json_ld = self._extract_json_ld(soup)
                
                profile = {
                    'company_name': company_name,
                    'forbes_url': url,
                    'ceo': self._extract_ceo(soup, json_ld),
                    'founded_year': self._extract_founded(soup, json_ld),
                    'hq_city': self._extract_hq_city(soup, json_ld),
                    'hq_country': self._extract_hq_country(soup),
                    'employees': self._extract_employees(soup, json_ld),
                    'industry': self._extract_industry(soup),
                    'description': self._extract_description(soup),
                    'total_funding': self._extract_total_funding(soup),
                    'valuation': self._extract_valuation(soup),
                }
                
                logger.info(f"   ✅ Forbes scraped successfully")
                return profile
            
            except Exception as e:
                logger.warning(f"   ⚠️ Forbes scrape failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
        
        logger.error(f"   ❌ Forbes scraping failed after {max_retries} attempts")
        return self._empty_profile(company_name, url)
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract JSON-LD structured data."""
        try:
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag and script_tag.string:
                return json.loads(script_tag.string)
        except:
            pass
        return None
    
    def _extract_ceo(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> str:
        """Extract CEO with validation."""
        # 1. JSON-LD
        if json_ld and 'employee' in json_ld:
            if isinstance(json_ld['employee'], dict):
                name = json_ld['employee'].get('name', '')
                if name and self._validate_name(name):
                    return name
        
        # 2. CSS
        stats = soup.find_all('dt', class_='profile-stats__title')
        for stat in stats:
            if 'CEO' in stat.get_text():
                dd = stat.find_next_sibling('dd')
                if dd:
                    name = dd.get_text().strip()
                    if self._validate_name(name):
                        return name
        
        # 3. Description extraction
        desc = self._extract_description(soup)
        patterns = [
            r'CEO\s+(?:and\s+)?(?:co)?founder\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'(?:Founded|Co-founded)\s+by\s+(?:CEO\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'CEO\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, desc)
            if match:
                name = match.group(1).strip()
                if self._validate_name(name):
                    return name
        
        return "Not available"
    
    def _validate_name(self, name: str) -> bool:
        """Validate person name."""
        if not name:
            return False
        
        # Reject bad patterns
        bad = ['Network', 'Forbes', 'http', 'www', 'Click', 'See All']
        if any(b in name for b in bad):
            return False
        
        words = name.split()
        return 2 <= len(words) <= 5 and len(name) < 60
    
    def _extract_founded(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> Optional[int]:
        """Extract founded year."""
        if json_ld and 'foundingDate' in json_ld:
            try:
                year = int(json_ld['foundingDate'])
                if 1990 <= year <= 2025:
                    return year
            except:
                pass
        
        stats = soup.find_all('dt', class_='profile-stats__title')
        for stat in stats:
            if 'Founded' in stat.get_text():
                dd = stat.find_next_sibling('dd')
                if dd:
                    match = re.search(r'(\d{4})', dd.get_text())
                    if match:
                        year = int(match.group(1))
                        if 1990 <= year <= 2025:
                            return year
        
        return None
    
    def _extract_hq_city(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> str:
        """Extract HQ city."""
        if json_ld and 'location' in json_ld:
            loc = json_ld['location']
            if ',' in loc:
                return loc.split(',')[0].strip()
        
        stats = soup.find_all('dt', class_='profile-stats__title')
        for stat in stats:
            if 'Headquarters' in stat.get_text():
                dd = stat.find_next_sibling('dd')
                if dd:
                    hq = dd.get_text().strip()
                    if ',' in hq:
                        return hq.split(',')[0].strip()
                    return hq
        
        location_div = soup.find(class_='listuser-header__headline--premium-location')
        if location_div:
            loc = location_div.get_text().strip()
            if ',' in loc:
                return loc.split(',')[0].strip()
            return loc
        
        return "Not available"
    
    def _extract_hq_country(self, soup: BeautifulSoup) -> str:
        """Extract HQ country."""
        stats = soup.find_all('dt', class_='profile-stats__title')
        for stat in stats:
            if 'Country' in stat.get_text() or 'Territory' in stat.get_text():
                dd = stat.find_next_sibling('dd')
                if dd:
                    return dd.get_text().strip()
        
        return "United States"
    
    def _extract_employees(self, soup: BeautifulSoup, json_ld: Optional[Dict]) -> Optional[int]:
        """Extract employee count with validation."""
        # JSON-LD
        if json_ld and 'numberOfEmployees' in json_ld:
            try:
                count = int(json_ld['numberOfEmployees'])
                # Validate (reject obvious placeholders)
                if count > 10 and count != 1 and count != 5 and count != 8:
                    return count
            except:
                pass
        
        # CSS
        stats = soup.find_all('dt', class_='profile-stats__title')
        for stat in stats:
            if 'Employee' in stat.get_text():
                dd = stat.find_next_sibling('dd')
                if dd:
                    text = dd.get_text().replace(',', '')
                    match = re.search(r'(\d+)', text)
                    if match:
                        count = int(match.group(1))
                        if count > 10:
                            return count
        
        return None
    
    def _extract_industry(self, soup: BeautifulSoup) -> str:
        """Extract industry."""
        stats = soup.find_all('dt', class_='profile-stats__title')
        for stat in stats:
            if 'Industry' in stat.get_text():
                dd = stat.find_next_sibling('dd')
                if dd:
                    return dd.get_text().strip()
        return "AI Technology"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract full description."""
        bio_div = soup.find(class_='listuser-alternative-bio__content')
        if bio_div:
            expanded = bio_div.find(class_='expanded')
            shortened = bio_div.find(class_='shortened')
            
            text = (expanded or shortened or bio_div).get_text()
            text = text.replace('Read More', '').replace('Read Less', '').strip()
            text = re.sub(r'\s+', ' ', text)
            
            if len(text) > 100:
                return text
        
        return "Not available"
    
    def _extract_total_funding(self, soup: BeautifulSoup) -> str:
        """Extract total funding raised."""
        text = soup.get_text()
        
        patterns = [
            r'raised\s+(?:a\s+)?total\s+(?:of\s+)?\$?([\d.]+)\s*(billion|million|B|M)',
            r'total\s+(?:of\s+)?\$?([\d.]+)\s*(billion|million|B|M)\s+in\s+funding',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1)
                unit = match.group(2)[0].upper()
                return f'${amount}{unit}'
        
        return "Not available"
    
    def _extract_valuation(self, soup: BeautifulSoup) -> str:
        """Extract current valuation."""
        text = soup.get_text()
        
        patterns = [
            r'valued at\s+\$?([\d.]+)\s*(billion|million|B|M)',
            r'valuation\s+of\s+\$?([\d.]+)\s*(billion|million|B|M)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1)
                unit = match.group(2)[0].upper()
                return f'${amount}{unit}'
        
        return "Not available"
    
    def _empty_profile(self, company_name: str, url: str) -> Dict:
        """Create empty profile."""
        return {
            'company_name': company_name,
            'forbes_url': url,
            'ceo': "Not available",
            'founded_year': None,
            'hq_city': "Not available",
            'hq_country': "United States",
            'employees': None,
            'industry': "AI Technology",
            'description': "Not available",
            'total_funding': "Not available",
            'valuation': "Not available",
        }


class ForbesProductionScraper:
    """Main production scraper orchestrator."""
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parents[2] / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.profiles_dir = self.data_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress_mgr = ProgressManager(self.data_dir)
        self.url_validator = URLValidator()
        self.linkedin_scraper = LinkedInWebsiteScraper()
        self.forbes_scraper = ForbesProfileScraper()
    
    def get_website(self, company_name: str) -> Tuple[str, str]:
        """
        Get company website with multi-strategy approach.
        Returns: (website_url, source)
        
        Priority:
        1. Manual override (100% reliable)
        2. LinkedIn scraping (if not blocked)
        3. Pattern inference (fallback)
        """
        # Strategy 1: Manual override (BEST - always use if available)
        if company_name in Config.MANUAL_WEBSITES:
            website = Config.MANUAL_WEBSITES[company_name]
            logger.info(f"   ✅ Website (manual): {website}")
            return website, "manual"
        
        # Strategy 2: LinkedIn scraping (GOOD - but can be blocked)
        linkedin_website = self.linkedin_scraper.scrape_website(company_name)
        if linkedin_website:
            # Validate
            if Config.VALIDATE_URLS:
                if self.url_validator.validate(linkedin_website):
                    logger.info(f"   ✅ Website (LinkedIn, validated): {linkedin_website}")
                    return linkedin_website, "linkedin"
                else:
                    logger.warning(f"   ⚠️ LinkedIn URL not reachable: {linkedin_website}")
            else:
                logger.info(f"   ✅ Website (LinkedIn): {linkedin_website}")
                return linkedin_website, "linkedin"
        
        # Strategy 3: Should never reach here since all companies have manual overrides
        logger.warning(f"   ⚠️ No website strategy worked for {company_name}")
        return "Not available", "failed"
    
    def infer_category(self, industry: str, description: str) -> str:
        """Infer AI category."""
        text = (industry + ' ' + description).lower()
        
        categories = {
            'healthcare_ai': ['health', 'medical', 'doctor', 'clinical', 'patient', 'drug'],
            'legal_ai': ['legal', 'law', 'contract'],
            'customer_service_ai': ['customer service', 'customer support', 'agent', 'chatbot'],
            'coding_ai': ['coding', 'code', 'developer', 'software', 'IDE', 'programming'],
            'search_ai': ['search engine', 'answer engine', 'query'],
            'voice_ai': ['voice', 'audio', 'speech', 'sound', 'dubbing'],
            'video_ai': ['video', 'image', 'visual', 'photo', 'generation'],
            'data_ai': ['data', 'database', 'analytics', 'labeling'],
            'infrastructure_ai': ['cloud', 'compute', 'chip', 'GPU', 'infrastructure'],
            'robotics_ai': ['robot', 'humanoid'],
            'language_ai': ['translation', 'language learning', 'translate'],
        }
        
        for category, keywords in categories.items():
            if any(kw in text for kw in keywords):
                return category
        
        return 'general_ai'
    
    def scrape_company(self, company_name: str) -> Dict:
        """Scrape single company (Forbes + LinkedIn)."""
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 Scraping: {company_name}")
        logger.info(f"{'='*70}")
        
        # Step 1: Forbes profile
        forbes_data = self.forbes_scraper.scrape(company_name, self.profiles_dir)
        
        time.sleep(Config.FORBES_DELAY)
        
        # Step 2: Website (prioritizes manual overrides)
        website, source = self.get_website(company_name)
        
        if source == "linkedin":
            time.sleep(Config.LINKEDIN_DELAY)
        
        # Step 3: Build LinkedIn profile URL
        linkedin_slug = company_name.lower().replace(' ', '-').replace('.', '').replace("'", '')
        linkedin_url = f"https://www.linkedin.com/company/{linkedin_slug}/"
        
        # Step 4: Infer category
        category = self.infer_category(
            forbes_data.get('industry', ''),
            forbes_data.get('description', '')
        )
        
        # Step 5: Merge data
        profile = {
            **forbes_data,
            'website': website,
            'website_source': source,
            'linkedin': linkedin_url,
            'category': category,
        }
        
        # Log summary
        logger.info(f"   ✅ CEO: {profile['ceo']}")
        logger.info(f"   ✅ Founded: {profile['founded_year']}")
        logger.info(f"   ✅ HQ: {profile['hq_city']}, {profile['hq_country']}")
        logger.info(f"   ✅ Employees: {profile['employees']}")
        logger.info(f"   ✅ Website: {profile['website']} ({source})")
        logger.info(f"   ✅ Category: {profile['category']}")
        
        return profile
    
    def scrape_all(self, resume: bool = True):
        """
        Main scraping function with resume capability.
        
        Args:
            resume: If True, resume from last save point
        """
        print("\n" + "="*70)
        print("FORBES AI 50 PRODUCTION SCRAPER")
        print("="*70)
        print(f"📊 Total companies: {len(Config.FORBES_AI50_2025)}")
        print(f"💾 Progress saving: Every {Config.SAVE_PROGRESS_EVERY} companies")
        print(f"🔗 LinkedIn scraping: Enabled ({Config.LINKEDIN_DELAY}s delay)")
        print(f"✅ URL validation: {'Enabled' if Config.VALIDATE_URLS else 'Disabled'}")
        print(f"📋 Manual overrides: {len(Config.MANUAL_WEBSITES)}/50 companies")
        print(f"🔄 Resume: {'Enabled' if resume else 'Disabled'}")
        
        # Load progress if resuming
        if resume:
            all_profiles, last_index = self.progress_mgr.load_progress()
            start_index = last_index + 1
        else:
            all_profiles = []
            start_index = 0
            self.progress_mgr.clear_progress()
        
        companies = Config.FORBES_AI50_2025
        
        print(f"\n🚀 Starting from company #{start_index + 1}: {companies[start_index] if start_index < len(companies) else 'N/A'}")
        print("="*70)
        
        # Scrape companies
        for i in range(start_index, len(companies)):
            company_name = companies[i]
            
            print(f"\n[{i + 1}/{len(companies)}] {company_name}")
            
            try:
                profile = self.scrape_company(company_name)
                all_profiles.append(profile)
                
                # Save progress periodically
                if (i + 1) % Config.SAVE_PROGRESS_EVERY == 0:
                    self.progress_mgr.save_progress(all_profiles, i)
                    logger.info(f"💾 Checkpoint saved!")
            
            except KeyboardInterrupt:
                logger.info("\n⚠️ Interrupted by user")
                self.progress_mgr.save_progress(all_profiles, i - 1)
                logger.info("💾 Progress saved. Run again with resume=True to continue.")
                return all_profiles
            
            except Exception as e:
                logger.error(f"❌ Failed to scrape {company_name}: {e}")
                # Add empty profile so we don't skip
                all_profiles.append(self.forbes_scraper._empty_profile(company_name, ""))
        
        # Final save
        print("\n" + "="*70)
        print("SAVING FINAL RESULTS")
        print("="*70)
        
        output_path = self.data_dir / "forbes_ai50_seed.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_profiles, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved {len(all_profiles)} profiles to {output_path}")
        
        # Generate report
        self.generate_report(all_profiles)
        
        # Clear progress file
        self.progress_mgr.clear_progress()
        
        return all_profiles
    
    def generate_report(self, profiles: List[Dict]):
        """Generate data quality report."""
        print("\n" + "="*70)
        print("DATA QUALITY REPORT")
        print("="*70)
        
        total = len(profiles)
        
        # Completeness metrics
        with_ceo = sum(1 for p in profiles if p.get('ceo') != 'Not available')
        with_website = sum(1 for p in profiles if p.get('website') != 'Not available')
        with_hq = sum(1 for p in profiles if p.get('hq_city') != 'Not available')
        with_founded = sum(1 for p in profiles if p.get('founded_year') is not None)
        with_employees = sum(1 for p in profiles if p.get('employees') is not None)
        with_funding = sum(1 for p in profiles if p.get('total_funding') != 'Not available')
        with_valuation = sum(1 for p in profiles if p.get('valuation') != 'Not available')
        with_desc = sum(1 for p in profiles if p.get('description', 'Not available') != 'Not available' and len(p.get('description', '')) > 100)
        
        print(f"\n📊 Completeness:")
        print(f"   Companies: {total}/50 ({total/50*100:.0f}%)")
        print(f"   CEO: {with_ceo}/{total} ({with_ceo/total*100:.0f}%)")
        print(f"   Website: {with_website}/{total} ({with_website/total*100:.0f}%)")
        print(f"   HQ: {with_hq}/{total} ({with_hq/total*100:.0f}%)")
        print(f"   Founded: {with_founded}/{total} ({with_founded/total*100:.0f}%)")
        print(f"   Employees: {with_employees}/{total} ({with_employees/total*100:.0f}%)")
        print(f"   Funding: {with_funding}/{total} ({with_funding/total*100:.0f}%)")
        print(f"   Valuation: {with_valuation}/{total} ({with_valuation/total*100:.0f}%)")
        print(f"   Description: {with_desc}/{total} ({with_desc/total*100:.0f}%)")
        
        # Website sources
        print(f"\n🌐 Website Sources:")
        sources = {}
        for p in profiles:
            source = p.get('website_source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        for source, count in sorted(sources.items()):
            print(f"   {source}: {count}")
        
        # Category distribution
        print(f"\n📂 Categories:")
        categories = {}
        for p in profiles:
            cat = p.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"   {cat}: {count}")
        
        # Geographic distribution
        print(f"\n🌍 Countries:")
        countries = {}
        for p in profiles:
            country = p.get('hq_country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        for country, count in sorted(countries.items(), key=lambda x: -x[1]):
            print(f"   {country}: {count}")
        
        print(f"\n📂 Profile HTMLs saved in: {self.profiles_dir}")
        print(f"📄 Final JSON: {self.data_dir / 'forbes_ai50_seed.json'}")
        print(f"📝 Log file: scraper.log")
        print("\n✅ Scraping Complete!")


def main():
    """Main entry point."""
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║          FORBES AI 50 PRODUCTION SCRAPER v4.0 FIXED             ║
    ║                                                                  ║
    ║  Features:                                                       ║
    ║  ✅ Forbes profiles for main data                               ║
    ║  ✅ Complete manual website overrides (ALL 50 companies)        ║
    ║  ✅ LinkedIn scraping as fallback                               ║
    ║  ✅ Resume from save point                                      ║
    ║  ✅ URL validation                                              ║
    ║  ✅ Retry logic                                                 ║
    ║                                                                  ║
    ║  Usage:                                                          ║
    ║    python forbes_scraper.py                  (normal run)        ║
    ║    python forbes_scraper.py --fresh          (start fresh)       ║
    ║    python forbes_scraper.py --no-validate    (skip URL check)    ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Parse args
    resume = '--fresh' not in sys.argv
    Config.VALIDATE_URLS = '--no-validate' not in sys.argv
    
    if resume:
        print("🔄 Resume mode: Will continue from last save point\n")
    else:
        print("🆕 Fresh start: Starting from scratch\n")
    
    # Create scraper
    scraper = ForbesProductionScraper()
    
    # Run
    try:
        scraper.scrape_all(resume=resume)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted! Progress saved. Run again to resume.")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()