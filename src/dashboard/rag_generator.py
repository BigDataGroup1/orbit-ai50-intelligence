"""
RAG-based dashboard generator (Lab 7) with auto-evaluation
"""
from pathlib import Path
import sys
from typing import Dict
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

# Add parent to path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from vectordb.embedder import VectorStore
from dashboard.context_assembler import ContextAssembler

# Load environment variables from .env file
load_dotenv()


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
    
    def evaluate_dashboard(self, dashboard: str, context: str) -> Dict:
        """
        Auto-evaluate dashboard quality using LLM.
        
        Args:
            dashboard: Generated dashboard markdown
            context: Original source chunks used
        
        Returns:
            Dict with scores: {'factual': 0-3, 'hallucination': 0-2, 'readability': 0-1}
        """
        eval_prompt = f"""You just generated a PE investment dashboard. Now evaluate it objectively.

DASHBOARD:
{dashboard}

SOURCE DOCUMENTS (what you had available):
{context[:3000]}

EVALUATION CRITERIA:

1. Factual Correctness (0-3 points):
- 3 points: All facts directly supported by sources
- 2 points: Most facts supported, minor unsupported claims
- 1 point: Some facts supported, several unsupported
- 0 points: Many invented facts

2. Hallucination Control (0-2 points):
- 2 points: Used "Not disclosed" for missing data, no inventions
- 1 point: Mostly good, 1-2 minor inventions
- 0 points: Invented multiple facts

3. Readability (0-1 point):
- 1 point: Clear, concise, investor-focused
- 0 points: Confusing or poorly structured

Return ONLY a JSON object with scores:
{{"factual": X, "hallucination": X, "readability": X}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an objective evaluator of investment dashboards. Score strictly."
                    },
                    {
                        "role": "user",
                        "content": eval_prompt
                    }
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            scores = json.loads(response.choices[0].message.content)
            
            return {
                'factual': scores.get('factual', 0),
                'hallucination': scores.get('hallucination', 0),
                'readability': scores.get('readability', 0)
            }
        
        except Exception as e:
            print(f"⚠️  Auto-evaluation failed: {e}")
            return {'factual': None, 'hallucination': None, 'readability': None}
    
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
        print(f"   Daily chunks: {context_result.get('daily_chunks', 0)}")
        print(f"   Initial chunks: {context_result.get('initial_chunks', 0)}")
        
        # Step 2: Fill prompt template
        full_prompt = self.prompt_template.replace('{context}', context)
        
        # Step 3: Call LLM
        print(f"\n🤖 Calling LLM (GPT-4)...")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
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
                temperature=0.3,
                max_tokens=2000
            )
            
            dashboard = response.choices[0].message.content
            
            print(f"✅ Dashboard generated ({len(dashboard)} chars)")
            
            # Step 4: Auto-evaluate the dashboard
            print(f"🔍 Auto-evaluating dashboard...")
            evaluation_scores = self.evaluate_dashboard(dashboard, context)
            print(f"   Factual correctness: {evaluation_scores['factual']}/3")
            print(f"   Hallucination control: {evaluation_scores['hallucination']}/2")
            print(f"   Readability: {evaluation_scores['readability']}/1")
            
            # Step 5: Save evaluation JSON
            output_dir = Path(__file__).resolve().parents[2] / "data" / "dashboards" / "rag"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            eval_data = {
                'company_name': company_name,
                'pipeline_type': 'RAG',
                'generated_at': datetime.now().isoformat(),
                
                'metadata': {
                    'chunks_used': context_result['chunks_used'],
                    'daily_chunks': context_result.get('daily_chunks', 0),
                    'initial_chunks': context_result.get('initial_chunks', 0),
                    'page_types': context_result['page_types'],
                    'avg_score': context_result.get('avg_score', 0),
                    'sources_breakdown': context_result.get('sources_breakdown', {}),
                    'model': 'gpt-4o-mini',
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                },
                
                'auto_evaluation': {
                    'has_8_sections': dashboard.count('## ') >= 8,
                    'uses_not_disclosed': dashboard.count('Not disclosed'),
                    'has_disclosure_gaps': '## 8. Disclosure Gaps' in dashboard
                },

                'rubric_scores': {
                    'factual_correctness': evaluation_scores['factual'],  # 0-3
                    'schema_adherence': 2 if dashboard.count('## ') >= 8 else 1,  # 0-2 (auto-scored)
                    'provenance_use': 2,  # 0-2 (always 2 for RAG - has full source tracking)
                    'hallucination_control': evaluation_scores['hallucination'],  # 0-2
                    'readability': evaluation_scores['readability']  # 0-1
                },

'total_score': evaluation_scores['factual'] + 2 + 2 + evaluation_scores['hallucination'] + evaluation_scores['readability']
            }
            
            eval_file = output_dir / f"{company_name.replace(' ', '_')}_eval.json"
            with open(eval_file, 'w', encoding='utf-8') as f:
                json.dump(eval_data, f, indent=2)
            
            print(f"💾 Evaluation JSON: {eval_file.name}")
            
            # Step 6: Return result
            return {
                'company_name': company_name,
                'dashboard': dashboard,
                'success': True,
                'metadata': {
                    'chunks_used': context_result['chunks_used'],
                    'page_types': context_result['page_types'],
                    'avg_score': context_result.get('avg_score', 0),
                    'daily_chunks': context_result.get('daily_chunks', 0),
                    'initial_chunks': context_result.get('initial_chunks', 0),
                    'data_freshness': f"{context_result.get('daily_chunks', 0)}/{context_result['chunks_used']} from daily refresh",
                    'model': 'gpt-4o-mini',
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'evaluation_scores': evaluation_scores
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
            
            # Show metadata
            print(f"\n📊 Metadata:")
            print(f"   Daily chunks: {result['metadata']['daily_chunks']}")
            print(f"   Initial chunks: {result['metadata']['initial_chunks']}")
            print(f"   Data freshness: {result['metadata']['data_freshness']}")
            print(f"\n🎯 Evaluation Scores:")
            print(f"   Factual: {result['metadata']['evaluation_scores']['factual']}/3")
            print(f"   Hallucination: {result['metadata']['evaluation_scores']['hallucination']}/2")
            print(f"   Readability: {result['metadata']['evaluation_scores']['readability']}/1")
        else:
            print(f"\n❌ Failed to generate dashboard for {company}")
        
        print("\n" + "="*70)
        input("Press Enter to continue to next company...")


if __name__ == "__main__":
    test_generator()