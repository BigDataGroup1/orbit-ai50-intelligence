"""
Text chunking for RAG pipeline
"""
import tiktoken
from typing import List, Dict
from pathlib import Path
import json


class TextChunker:
    """Chunks text into token-sized pieces for embedding."""
    
    def __init__(self, chunk_size: int = 800, overlap: int = 100):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target tokens per chunk (default: 800)
            overlap: Overlap tokens between chunks (default: 100)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        """
        Chunk text into overlapping pieces.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
        
        Returns:
            List of chunks with format:
            {
                'text': str,
                'metadata': dict,
                'tokens': int
            }
        """
        if not text or len(text.strip()) < 50:
            return []
        
        tokens = self.encoding.encode(text)
        chunks = []
        
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Skip very short chunks
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    'text': chunk_text,
                    'metadata': metadata,
                    'tokens': len(chunk_tokens)
                })
            
            start += (self.chunk_size - self.overlap)
        
        return chunks
    
    def chunk_company_files(self, company_dir: Path, company_name: str) -> List[Dict]:
        """
        Chunk all text files for a company.
        
        Args:
            company_dir: Path to company directory (e.g., data/raw/Anthropic)
            company_name: Display name of company
        
        Returns:
            List of all chunks for this company
        """
        all_chunks = []
        
        # Find latest session directory
        sessions = [d for d in company_dir.iterdir() if d.is_dir()]
        if not sessions:
            return []
        
        # Get most recent session
        latest_session = sorted(sessions)[-1]
        
        # Page types to process
        page_types = ['homepage', 'about', 'pricing', 'product', 'careers', 'blog', 'customers']
        
        for page_type in page_types:
            txt_file = latest_session / f"{page_type}.txt"
            
            if not txt_file.exists():
                continue
            
            try:
                # Read file with cross-platform encoding
                with open(txt_file, 'rb') as f:
                    text = f.read().decode('utf-8', errors='ignore')
                
                # Skip if too short
                if len(text.strip()) < 100:
                    continue
                
                # Create metadata
                metadata = {
                    'company_name': company_name,
                    'page_type': page_type,
                    'session': latest_session.name,
                    'source_file': str(txt_file)
                }
                
                # Chunk the text
                chunks = self.chunk_text(text, metadata)
                all_chunks.extend(chunks)
                
            except Exception as e:
                print(f"      ⚠️  Error reading {txt_file.name}: {e}")
                continue
        
        return all_chunks


def main():
    """Test chunking on sample company."""
    from pathlib import Path
    
    data_dir = Path(__file__).resolve().parents[2] / "data"
    raw_dir = data_dir / "raw"
    
    if not raw_dir.exists():
        print(f"❌ Raw data directory not found: {raw_dir}")
        return
    
    chunker = TextChunker(chunk_size=800, overlap=100)
    
    # Test on first company
    companies = [d for d in raw_dir.iterdir() if d.is_dir()]
    if not companies:
        print("❌ No companies found in raw directory")
        return
    
    test_company = companies[0]
    company_name = test_company.name.replace('_', ' ')
    
    print(f"\n{'='*70}")
    print(f"Testing chunker on: {company_name}")
    print(f"{'='*70}\n")
    
    chunks = chunker.chunk_company_files(test_company, company_name)
    
    print(f"Generated {len(chunks)} chunks\n")
    
    if chunks:
        print("Sample chunk:")
        print(f"  Company: {chunks[0]['metadata']['company_name']}")
        print(f"  Page: {chunks[0]['metadata']['page_type']}")
        print(f"  Tokens: {chunks[0]['tokens']}")
        print(f"  Text preview: {chunks[0]['text'][:200]}...")
    
    # Token statistics
    total_tokens = sum(c['tokens'] for c in chunks)
    avg_tokens = total_tokens / len(chunks) if chunks else 0
    
    print(f"\nStatistics:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Avg tokens/chunk: {avg_tokens:.0f}")


if __name__ == "__main__":
    main()