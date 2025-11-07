"""
Utility functions for Streamlit dashboard app
"""
from pathlib import Path
import json
from typing import Dict, List, Optional, Tuple


class DashboardLoader:
    """Loads dashboards and metadata from disk."""
    
    def __init__(self):
        # Get project root (go up 2 levels from src/app/)
        self.project_root = Path(__file__).resolve().parents[2]
        self.data_dir = self.project_root / "data"
        self.dashboards_dir = self.data_dir / "dashboards"
        self.rag_dir = self.dashboards_dir / "rag"
        self.structured_dir = self.dashboards_dir / "structured"
        self.payloads_dir = self.data_dir / "payloads"
    
    def get_all_companies(self) -> List[str]:
        """Get list of all companies with any dashboard data."""
        companies = set()
        
        # From RAG dashboards
        if self.rag_dir.exists():
            for file in self.rag_dir.glob("*.md"):
                company = file.stem.replace('_', ' ')
                companies.add(company)
        
        # From Structured dashboards
        if self.structured_dir.exists():
            for file in self.structured_dir.glob("*.md"):
                company = file.stem.replace('_', ' ')
                companies.add(company)
        
        return sorted(list(companies))
    
    def get_company_id(self, company_name: str) -> str:
        """Convert company name to file ID."""
        return company_name.replace(' ', '_')
    
    def load_dashboard(self, company_name: str, pipeline: str) -> Optional[str]:
        """
        Load dashboard markdown.
        
        Args:
            company_name: Display name (e.g., "Anthropic")
            pipeline: 'rag' or 'structured'
        
        Returns:
            Markdown content or None
        """
        company_id = self.get_company_id(company_name)
        
        if pipeline == 'rag':
            file_path = self.rag_dir / f"{company_id}.md"
        else:
            file_path = self.structured_dir / f"{company_id}.md"
        
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        
        return None
    
    def load_evaluation(self, company_name: str, pipeline: str) -> Optional[Dict]:
        """
        Load evaluation JSON.
        
        Args:
            company_name: Display name
            pipeline: 'rag' or 'structured'
        
        Returns:
            Evaluation data dict or None
        """
        company_id = self.get_company_id(company_name)
        
        if pipeline == 'rag':
            file_path = self.rag_dir / f"{company_id}_eval.json"
        else:
            file_path = self.structured_dir / f"{company_id}_eval.json"
        
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def check_availability(self, company_name: str) -> Dict[str, bool]:
        """
        Check which pipelines have data for a company.
        
        Returns:
            {'rag': bool, 'structured': bool}
        """
        company_id = self.get_company_id(company_name)
        
        return {
            'rag': (self.rag_dir / f"{company_id}.md").exists(),
            'structured': (self.structured_dir / f"{company_id}.md").exists()
        }
    
    def get_statistics(self) -> Dict:
        """Get overall statistics."""
        rag_count = len(list(self.rag_dir.glob("*.md"))) if self.rag_dir.exists() else 0
        structured_count = len(list(self.structured_dir.glob("*.md"))) if self.structured_dir.exists() else 0
        
        # Get evaluation companies
        rag_eval_count = len(list(self.rag_dir.glob("*_eval.json"))) if self.rag_dir.exists() else 0
        struct_eval_count = len(list(self.structured_dir.glob("*_eval.json"))) if self.structured_dir.exists() else 0
        
        return {
            'total_companies': len(self.get_all_companies()),
            'rag_dashboards': rag_count,
            'structured_dashboards': structured_count,
            'rag_evaluated': rag_eval_count,
            'structured_evaluated': struct_eval_count
        }


def format_score_display(score: Optional[int], max_score: int) -> str:
    """
    Format score for display with progress bar.
    
    Args:
        score: Actual score or None
        max_score: Maximum possible score
    
    Returns:
        Formatted string with emoji progress bar
    """
    if score is None:
        return "Not evaluated"
    
    # Calculate percentage
    percentage = (score / max_score) * 100
    
    # Create progress bar (10 blocks)
    filled = int(percentage / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    # Color coding
    if percentage >= 80:
        emoji = "🟢"
    elif percentage >= 60:
        emoji = "🟡"
    else:
        emoji = "🔴"
    
    return f"{emoji} {bar} {score}/{max_score}"


def extract_sections(markdown: str) -> Dict[str, str]:
    """
    Extract sections from dashboard markdown.
    
    Returns:
        Dict mapping section names to content
    """
    sections = {}
    current_section = None
    current_content = []
    
    for line in markdown.split('\n'):
        if line.startswith('## '):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def compare_dashboards(rag_md: str, struct_md: str) -> Dict:
    """
    Compare two dashboards and extract differences.
    
    Returns:
        Comparison metadata
    """
    rag_sections = extract_sections(rag_md)
    struct_sections = extract_sections(struct_md)
    
    return {
        'rag_sections': len(rag_sections),
        'structured_sections': len(struct_sections),
        'rag_length': len(rag_md),
        'structured_length': len(struct_md),
        'rag_not_disclosed': rag_md.count('Not disclosed'),
        'structured_not_disclosed': struct_md.count('Not disclosed'),
        'common_sections': set(rag_sections.keys()) & set(struct_sections.keys()),
        'rag_only_sections': set(rag_sections.keys()) - set(struct_sections.keys()),
        'structured_only_sections': set(struct_sections.keys()) - set(rag_sections.keys())
    }