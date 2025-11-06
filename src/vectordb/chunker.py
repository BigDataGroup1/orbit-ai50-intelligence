"""
Text chunking for RAG pipeline with GCS support and initial+daily merge
"""
import tiktoken
from typing import List, Dict, Optional
from pathlib import Path
from google.cloud import storage


class TextChunker:
    """Chunks text from GCS bucket with smart initial+daily merge."""
    
    def __init__(self, 
                 bucket_name: str = "orbit-raw-data-group1-2025",
                 chunk_size: int = 800, 
                 overlap: int = 100,
                 use_gcs: bool = True):
        """
        Initialize chunker.
        
        Args:
            bucket_name: GCS bucket name for raw data
            chunk_size: Target tokens per chunk (default: 800)
            overlap: Overlap tokens between chunks (default: 100)
            use_gcs: If True, read from GCS. If False, read from local files
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.use_gcs = use_gcs
        
        # Page categorization
        self.dynamic_pages = ['blog', 'careers', 'news']
        self.stable_pages = ['homepage', 'about', 'pricing', 'product', 'customers']
        
        # GCS setup
        if use_gcs:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(bucket_name)
            print(f"✅ Connected to GCS bucket: {bucket_name}")
        else:
            self.bucket = None
            print(f"✅ Using local filesystem")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        """Chunk text into overlapping pieces."""
        if not text or len(text.strip()) < 50:
            return []
        
        tokens = self.encoding.encode(text)
        chunks = []
        
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    'text': chunk_text,
                    'metadata': metadata,
                    'tokens': len(chunk_tokens)
                })
            
            start += (self.chunk_size - self.overlap)
        
        return chunks
    
    def list_sessions_gcs(self, company_name: str) -> Dict[str, List[str]]:
        """
        List all sessions for a company in GCS.
        
        Returns:
            {'initial': ['2025-11-03_initial', ...], 'daily': ['2025-11-04_daily', ...]}
        """
        prefix = f"data/raw/{company_name}/"
        
        # List all blobs with prefix
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        
        # Extract unique session folders
        sessions = set()
        for blob in blobs:
            # blob.name = "data/raw/Anthropic/2025-11-03_initial/homepage.txt"
            parts = blob.name.split('/')
            if len(parts) >= 4:
                session = parts[3]  # "2025-11-03_initial"
                sessions.add(session)
        
        # Categorize
        result = {'initial': [], 'daily': []}
        for session in sessions:
            if 'initial' in session.lower():
                result['initial'].append(session)
            elif 'daily' in session.lower():
                result['daily'].append(session)
        
        return result
    
    def read_file_gcs(self, company_name: str, session: str, page_type: str) -> Optional[str]:
        """Read text file from GCS."""
        blob_path = f"data/raw/{company_name}/{session}/{page_type}.txt"
        blob = self.bucket.blob(blob_path)
        
        try:
            if blob.exists():
                content = blob.download_as_bytes()
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"      ⚠️  Error reading {blob_path}: {e}")
        
        return None
    
    def read_file_local(self, company_dir: Path, session: str, page_type: str) -> Optional[str]:
        """Read text file from local filesystem."""
        file_path = company_dir / session / f"{page_type}.txt"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"      ⚠️  Error reading {file_path}: {e}")
            return None
    
    def chunk_company_files_gcs(self, company_name: str) -> List[Dict]:
        """
        Chunk company files from GCS with initial+daily merge.
        
        Strategy:
        - Dynamic pages (blog, careers, news): Prefer daily, fall back to initial
        - Stable pages (homepage, about, pricing, product, customers): Prefer initial, fall back to daily
        
        Args:
            company_name: Company folder name in GCS
        
        Returns:
            List of chunks
        """
        all_chunks = []
        
        # Get sessions from GCS
        sessions = self.list_sessions_gcs(company_name)
        
        latest_initial = sorted(sessions['initial'])[-1] if sessions['initial'] else None
        latest_daily = sorted(sessions['daily'])[-1] if sessions['daily'] else None
        
        if not latest_initial and not latest_daily:
            return []
        
        # Process each page type
        all_page_types = self.dynamic_pages + self.stable_pages
        
        for page_type in all_page_types:
            text = None
            session_used = None
            
            # Smart selection based on page type
            prefer_daily = page_type in self.dynamic_pages
            
            if prefer_daily:
                # Try daily first for dynamic pages
                if latest_daily:
                    text = self.read_file_gcs(company_name, latest_daily, page_type)
                    if text:
                        session_used = latest_daily
                
                # Fall back to initial
                if not text and latest_initial:
                    text = self.read_file_gcs(company_name, latest_initial, page_type)
                    if text:
                        session_used = latest_initial
            else:
                # Try initial first for stable pages
                if latest_initial:
                    text = self.read_file_gcs(company_name, latest_initial, page_type)
                    if text:
                        session_used = latest_initial
                
                # Fall back to daily
                if not text and latest_daily:
                    text = self.read_file_gcs(company_name, latest_daily, page_type)
                    if text:
                        session_used = latest_daily
            
            if not text or len(text.strip()) < 100:
                continue
            
            # Create metadata
            metadata = {
                'company_name': company_name,
                'page_type': page_type,
                'session': session_used,
                'source': 'gcs',
                'is_daily_refresh': 'daily' in session_used.lower()  # ← MISSING THIS!
            }
            
            # Chunk the text
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def chunk_company_files_local(self, company_dir: Path, company_name: str) -> List[Dict]:
        """
        Chunk company files from local filesystem with initial+daily merge.
        
        Same strategy as GCS version but reads from local disk.
        """
        all_chunks = []
        
        # Find all sessions locally
        sessions = [d for d in company_dir.iterdir() if d.is_dir()]
        if not sessions:
            return []
        
        # Separate by type
        initial_sessions = sorted([s for s in sessions if 'initial' in s.name.lower()])
        daily_sessions = sorted([s for s in sessions if 'daily' in s.name.lower()])
        
        latest_initial = initial_sessions[-1] if initial_sessions else None
        latest_daily = daily_sessions[-1] if daily_sessions else None
        
        # Process each page type
        all_page_types = self.dynamic_pages + self.stable_pages
        
        for page_type in all_page_types:
            text = None
            session_used = None
            
            prefer_daily = page_type in self.dynamic_pages
            
            if prefer_daily:
                # Try daily first
                if latest_daily:
                    text = self.read_file_local(company_dir, latest_daily.name, page_type)
                    if text:
                        session_used = latest_daily.name
                
                # Fall back to initial
                if not text and latest_initial:
                    text = self.read_file_local(company_dir, latest_initial.name, page_type)
                    if text:
                        session_used = latest_initial.name
            else:
                # Try initial first
                if latest_initial:
                    text = self.read_file_local(company_dir, latest_initial.name, page_type)
                    if text:
                        session_used = latest_initial.name
                
                # Fall back to daily
                if not text and latest_daily:
                    text = self.read_file_local(company_dir, latest_daily.name, page_type)
                    if text:
                        session_used = latest_daily.name
            
            if not text or len(text.strip()) < 100:
                continue
            metadata = {
            'company_name': company_name,
            'page_type': page_type,
            'session': session_used,
            'source': f'gcs:{company_name}/{session_used}/{page_type}.txt',
            'is_daily_refresh': 'daily' in session_used.lower()  #to dentify if it is daily or not
             }
            
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def chunk_company_files(self, company_name_or_dir, company_name: str = None) -> List[Dict]:
        """
        Universal method that works with both GCS and local.
        
        Args:
            company_name_or_dir: Company name (str) for GCS, Path for local
            company_name: Display name (optional, inferred if not provided)
        
        Returns:
            List of chunks
        """
        if self.use_gcs:
            # GCS mode - company_name_or_dir is a string
            return self.chunk_company_files_gcs(company_name_or_dir)
        else:
            # Local mode - company_name_or_dir is a Path
            if company_name is None:
                company_name = company_name_or_dir.name.replace('_', ' ')
            return self.chunk_company_files_local(company_name_or_dir, company_name)


def main():
    """Test chunking."""
    import sys
    
    use_gcs = '--gcs' in sys.argv
    
    if use_gcs:
        print("="*70)
        print("TESTING CHUNKER - GCS MODE")
        print("="*70)
        
        chunker = TextChunker(
            bucket_name="orbit-raw-data-group1-2025",
            use_gcs=True
        )
        
        # Test on Anthropic
        chunks = chunker.chunk_company_files("Anthropic")
        
        print(f"\nGenerated {len(chunks)} chunks for Anthropic")
        
        if chunks:
            # Show session distribution
            session_counts = {}
            for chunk in chunks:
                session = chunk['metadata']['session']
                session_counts[session] = session_counts.get(session, 0) + 1
            
            print(f"\nChunks by session:")
            for session, count in sorted(session_counts.items()):
                print(f"  {session}: {count} chunks")
            
            print(f"\nSample chunk:")
            print(f"  Company: {chunks[0]['metadata']['company_name']}")
            print(f"  Page: {chunks[0]['metadata']['page_type']}")
            print(f"  Session: {chunks[0]['metadata']['session']}")
            print(f"  Text: {chunks[0]['text'][:200]}...")
    
    else:
        print("="*70)
        print("TESTING CHUNKER - LOCAL MODE")
        print("="*70)
        
        data_dir = Path(__file__).resolve().parents[2] / "data"
        raw_dir = data_dir / "raw"
        
        if not raw_dir.exists():
            print(f"❌ Raw data directory not found: {raw_dir}")
            print("   Use --gcs flag to test GCS mode")
            return
        
        chunker = TextChunker(use_gcs=False)
        
        companies = sorted([d for d in raw_dir.iterdir() if d.is_dir()])
        if not companies:
            print("❌ No companies found")
            return
        
        test_company = companies[0]
        company_name = test_company.name.replace('_', ' ')
        
        print(f"Testing on: {company_name}")
        
        chunks = chunker.chunk_company_files(test_company, company_name)
        
        print(f"\nGenerated {len(chunks)} chunks")
        
        if chunks:
            session_counts = {}
            for chunk in chunks:
                session = chunk['metadata']['session']
                session_counts[session] = session_counts.get(session, 0) + 1
            
            print(f"\nChunks by session:")
            for session, count in sorted(session_counts.items()):
                print(f"  {session}: {count} chunks")


if __name__ == "__main__":
    main()