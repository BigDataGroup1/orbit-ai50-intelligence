"""
RAG-based dashboard generator (Lab 7)
"""
from pathlib import Path
import sys
from typing import Dict
import os
from openai import OpenAI
from dotenv import load_dotenv  # ✅ ADD THIS

# Add parent to path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from vectordb.embedder import VectorStore
from dashboard.context_assembler import ContextAssembler

# Load environment variables from .env file
load_dotenv()  # ✅ ADD THIS


class RAGDashboardGenerator:
    """Generates PE dashboards using RAG pipeline."""
    
    def __init__(self, vector_store: VectorStore, llm_api_key: str = None):
        """
        Initialize generator.
        
        Args:
            vector_store: Loaded VectorStore instance
            llm_api_key: OpenAI API key (or use OPENAI_API_KEY env var)
        """
        self.vector_store = vector_store
        self.context_assembler = ContextAssembler(vector_store)
        
        # Initialize LLM client
        self.llm_api_key = llm_api_key or os.getenv('OPENAI_API_KEY')
        if not self.llm_api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass llm_api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.llm_api_key)
        
        # Load prompt template
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "dashboard_system.md"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        
        print(f"✅ RAG Dashboard Generator initialized")
        print(f"   Prompt template: {prompt_path}")
    
    def generate_dashboard(self, company_name: str, max_chunks: int = 20) -> Dict:
        """
        Generate PE dashboard for a company.
        
        Args:
            company_name: Company to generate dashboard for
            max_chunks: Max context chunks to use
        
        Returns:
            Dict with dashboard markdown and metadata
        """
        print(f"\n{'='*70}")
        print(f"GENERATING RAG DASHBOARD: {company_name}")
        print(f"{'='*70}")
        
        # Step 1: Assemble context
        context_result = self.context_assembler.assemble_context(
            company_name=company_name,
            max_chunks=max_chunks
        )
        
        if not context_result['success']:
            return {
                'company_name': company_name,
                'dashboard': f"# {company_name}\n\n**Error:** No data available for this company.",
                'success': False,
                'error': 'No context retrieved'
            }
        
        context = context_result['context']
        
        print(f"\n📝 Context prepared:")
        print(f"   Chunks: {context_result['chunks_used']}")
        print(f"   Page types: {', '.join(context_result['page_types'])}")
        print(f"   Avg relevance: {context_result.get('avg_score', 0):.3f}")
        
        # Step 2: Fill prompt template
        full_prompt = self.prompt_template.replace('{context}', context)
        
        # Step 3: Call LLM
        print(f"\n🤖 Calling LLM (GPT-4)...")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-4o" for better quality
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert private equity analyst. Generate precise, factual investment dashboards."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                temperature=0.3,  # Low temperature for factual output
                max_tokens=2000
            )
            
            dashboard = response.choices[0].message.content
            
            print(f"✅ Dashboard generated ({len(dashboard)} chars)")
            
            return {
                'company_name': company_name,
                'dashboard': dashboard,
                'success': True,
                'metadata': {
                    'chunks_used': context_result['chunks_used'],
                    'page_types': context_result['page_types'],
                    'avg_score': context_result.get('avg_score', 0),
                    'model': 'gpt-4o-mini',
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                }
            }
        
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            return {
                'company_name': company_name,
                'dashboard': f"# {company_name}\n\n**Error:** Dashboard generation failed: {str(e)}",
                'success': False,
                'error': str(e)
            }


def test_generator():
    """Test dashboard generation."""
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("   Set it with: $env:OPENAI_API_KEY='your-key-here'")
        return
    
    print("="*70)
    print("TESTING RAG DASHBOARD GENERATOR")
    print("="*70)
    
    # Load vector store
    from vectordb.embedder import VectorStore
    vector_store = VectorStore(use_docker=False)
    
    # Create generator
    generator = RAGDashboardGenerator(vector_store)
    
    # Test companies
    test_companies = ["Anthropic", "Cohere", "Together AI"]
    
    for company in test_companies:
        result = generator.generate_dashboard(company, max_chunks=15)
        
        if result['success']:
            print(f"\n{'='*70}")
            print(f"DASHBOARD: {company}")
            print(f"{'='*70}")
            print(result['dashboard'])
            
            # Save to file
            output_dir = Path(__file__).resolve().parents[2] / "data" / "dashboards" / "rag"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"{company.replace(' ', '_')}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result['dashboard'])
            
            print(f"\n💾 Saved to: {output_file}")
        else:
            print(f"\n❌ Failed to generate dashboard for {company}")
        
        print("\n" + "="*70)
        input("Press Enter to continue to next company...")


if __name__ == "__main__":
    test_generator()