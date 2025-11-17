"""
Advanced PE Due Diligence Tools
Additional tools to make your agent more powerful
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Add project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


# ============================================================================
# TOOL 4: Financial Metrics Calculator
# ============================================================================

class FinancialMetrics(BaseModel):
    """Financial analysis results."""
    company_id: str
    valuation: Optional[float] = None
    total_funding: Optional[float] = None
    valuation_to_funding_ratio: Optional[float] = None
    funding_efficiency: Optional[str] = None
    last_round_size: Optional[float] = None
    funding_velocity: Optional[str] = None
    analysis: str


async def calculate_financial_metrics(company_id: str) -> Dict:
    """
    Calculate key financial metrics and ratios.
    
    Args:
        company_id: Company identifier
        
    Returns:
        Dict with financial metrics and analysis
    """
    try:
        # Load payload
        payload_path = project_root / "data" / "payloads" / f"{company_id}.json"
        
        if not payload_path.exists():
            return {"error": f"No payload found for {company_id}"}
        
        with open(payload_path, 'r') as f:
            data = json.load(f)
        
        valuation = data.get('valuation')
        funding = data.get('total_funding')
        
        # Calculate metrics
        metrics = {
            "company_id": company_id,
            "valuation": valuation,
            "total_funding": funding,
            "valuation_to_funding_ratio": None,
            "funding_efficiency": None,
            "analysis": ""
        }
        
        # Ratio analysis
        if valuation and funding and funding > 0:
            ratio = valuation / funding
            metrics["valuation_to_funding_ratio"] = round(ratio, 2)
            
            if ratio > 10:
                metrics["funding_efficiency"] = "🟢 Excellent (10x+ return on funding)"
            elif ratio > 5:
                metrics["funding_efficiency"] = "🟡 Good (5-10x return)"
            elif ratio > 2:
                metrics["funding_efficiency"] = "🟠 Moderate (2-5x return)"
            else:
                metrics["funding_efficiency"] = "🔴 Low (<2x return)"
        
        # Analysis
        analysis_parts = []
        
        if valuation:
            val_billions = valuation / 1_000_000_000
            if val_billions > 10:
                analysis_parts.append(f"Very high valuation (${val_billions:.1f}B) - unicorn status")
            elif val_billions > 1:
                analysis_parts.append(f"Unicorn status (${val_billions:.1f}B)")
            else:
                analysis_parts.append(f"Sub-unicorn valuation (${valuation/1_000_000:.0f}M)")
        
        if funding:
            fund_millions = funding / 1_000_000
            if fund_millions > 1000:
                analysis_parts.append(f"Heavily funded (${fund_millions/1000:.1f}B raised)")
            elif fund_millions > 100:
                analysis_parts.append(f"Well funded (${fund_millions:.0f}M raised)")
        
        metrics["analysis"] = " | ".join(analysis_parts) if analysis_parts else "Limited financial data"
        
        return metrics
        
    except Exception as e:
        return {"error": f"Error calculating metrics: {str(e)}"}


# ============================================================================
# TOOL 5: Competitor Comparison
# ============================================================================

class CompetitorComparison(BaseModel):
    """Comparison of multiple companies."""
    companies: List[str]
    metrics: Dict
    winner: Optional[str] = None
    analysis: str


async def compare_competitors(company_ids: List[str]) -> Dict:
    """
    Compare multiple companies across key metrics.
    
    Args:
        company_ids: List of company identifiers
        
    Returns:
        Dict with comparison results
    """
    try:
        comparison = {
            "companies": company_ids,
            "metrics": {},
            "analysis": ""
        }
        
        # Load all company data
        for company_id in company_ids:
            payload_path = project_root / "data" / "payloads" / f"{company_id}.json"
            
            if not payload_path.exists():
                comparison["metrics"][company_id] = {"error": "No data"}
                continue
            
            with open(payload_path, 'r') as f:
                data = json.load(f)
            
            comparison["metrics"][company_id] = {
                "valuation": data.get('valuation'),
                "funding": data.get('total_funding'),
                "founded": data.get('year_founded'),
                "hq": data.get('headquarters', {}).get('city'),
                "employees": data.get('employee_count')
            }
        
        # Determine winner (by valuation)
        max_val = 0
        winner = None
        for company_id, metrics in comparison["metrics"].items():
            val = metrics.get("valuation", 0)
            if val and val > max_val:
                max_val = val
                winner = company_id
        
        comparison["winner"] = winner
        comparison["analysis"] = f"{winner} leads with ${max_val/1_000_000_000:.1f}B valuation" if winner else "No clear leader"
        
        return comparison
        
    except Exception as e:
        return {"error": f"Error comparing companies: {str(e)}"}


# ============================================================================
# TOOL 6: Investment Recommendation Engine
# ============================================================================

class InvestmentRecommendation(BaseModel):
    """Investment recommendation result."""
    company_id: str
    recommendation: str  # BUY, HOLD, PASS, MONITOR
    confidence: str  # HIGH, MEDIUM, LOW
    score: float  # 0-100
    reasons: List[str]
    risks: List[str]


async def generate_investment_recommendation(company_id: str) -> Dict:
    """
    Generate investment recommendation based on company data.
    
    Args:
        company_id: Company identifier
        
    Returns:
        Dict with recommendation and reasoning
    """
    try:
        # Load payload
        payload_path = project_root / "data" / "payloads" / f"{company_id}.json"
        
        if not payload_path.exists():
            return {"error": f"No payload found for {company_id}"}
        
        with open(payload_path, 'r') as f:
            data = json.load(f)
        
        # Scoring system
        score = 50  # Start neutral
        reasons = []
        risks = []
        
        # Factor 1: Valuation (20 points)
        valuation = data.get('valuation', 0)
        if valuation > 10_000_000_000:
            score += 15
            reasons.append("High valuation indicates market confidence")
        elif valuation > 1_000_000_000:
            score += 10
            reasons.append("Unicorn status achieved")
        
        # Factor 2: Funding (15 points)
        funding = data.get('total_funding', 0)
        if funding > 1_000_000_000:
            score += 15
            reasons.append("Well-capitalized with $1B+ funding")
        elif funding > 100_000_000:
            score += 10
            reasons.append("Adequate funding runway")
        else:
            risks.append("Limited funding may constrain growth")
        
        # Factor 3: Growth indicators (15 points)
        if data.get('job_openings_count', 0) > 0:
            score += 10
            reasons.append("Active hiring indicates growth")
        else:
            score -= 5
            risks.append("No active hiring - possible freeze")
        
        # Factor 4: Market presence (10 points)
        if data.get('github_stars', 0) > 10000:
            score += 10
            reasons.append("Strong developer community")
        
        # Generate recommendation
        if score >= 75:
            recommendation = "🟢 BUY - Strong Investment Opportunity"
            confidence = "HIGH"
        elif score >= 60:
            recommendation = "🟡 MONITOR - Promising with some concerns"
            confidence = "MEDIUM"
        elif score >= 45:
            recommendation = "🟠 HOLD - Wait for more data"
            confidence = "MEDIUM"
        else:
            recommendation = "🔴 PASS - Significant concerns"
            confidence = "LOW"
        
        return {
            "company_id": company_id,
            "recommendation": recommendation,
            "confidence": confidence,
            "score": score,
            "reasons": reasons,
            "risks": risks
        }
        
    except Exception as e:
        return {"error": f"Error generating recommendation: {str(e)}"}


# ============================================================================
# TOOL 7: Market Trend Analyzer
# ============================================================================

async def analyze_market_trends(sector: str = "AI") -> Dict:
    """
    Analyze market trends across Forbes AI 50.
    
    Args:
        sector: Industry sector to analyze
        
    Returns:
        Dict with trend analysis
    """
    try:
        payloads_dir = project_root / "data" / "payloads"
        
        if not payloads_dir.exists():
            return {"error": "No payloads directory found"}
        
        # Aggregate data
        total_companies = 0
        total_valuation = 0
        total_funding = 0
        categories = {}
        hq_locations = {}
        
        for payload_file in payloads_dir.glob("*.json"):
            try:
                with open(payload_file, 'r') as f:
                    data = json.load(f)
                
                total_companies += 1
                
                if val := data.get('valuation'):
                    total_valuation += val
                
                if fund := data.get('total_funding'):
                    total_funding += fund
                
                # Track categories
                for cat in data.get('categories', []):
                    categories[cat] = categories.get(cat, 0) + 1
                
                # Track locations
                if hq := data.get('headquarters', {}).get('city'):
                    hq_locations[hq] = hq_locations.get(hq, 0) + 1
                    
            except:
                continue
        
        # Calculate trends
        avg_valuation = total_valuation / total_companies if total_companies > 0 else 0
        avg_funding = total_funding / total_companies if total_companies > 0 else 0
        
        # Top categories
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Top locations
        top_locations = sorted(hq_locations.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "sector": sector,
            "total_companies": total_companies,
            "total_market_cap": total_valuation,
            "total_funding": total_funding,
            "avg_valuation": avg_valuation,
            "avg_funding": avg_funding,
            "top_categories": dict(top_categories),
            "top_locations": dict(top_locations),
            "analysis": f"${total_valuation/1_000_000_000:.1f}B total market cap across {total_companies} companies"
        }
        
    except Exception as e:
        return {"error": f"Error analyzing trends: {str(e)}"}


# ============================================================================
# TOOL 8: Risk Scoring System
# ============================================================================

async def calculate_risk_score(company_id: str) -> Dict:
    """
    Calculate comprehensive risk score (0-100, lower is better).
    
    Args:
        company_id: Company identifier
        
    Returns:
        Dict with risk score and breakdown
    """
    try:
        # Load payload
        payload_path = project_root / "data" / "payloads" / f"{company_id}.json"
        
        if not payload_path.exists():
            return {"error": f"No payload found for {company_id}"}
        
        with open(payload_path, 'r') as f:
            data = json.load(f)
        
        risk_score = 0
        risk_factors = []
        
        # Factor 1: Funding risk (0-25 points)
        funding = data.get('total_funding', 0)
        if funding == 0:
            risk_score += 25
            risk_factors.append("No disclosed funding (25 pts)")
        elif funding < 10_000_000:
            risk_score += 20
            risk_factors.append("Low funding (<$10M) (20 pts)")
        
        # Factor 2: Hiring risk (0-20 points)
        if data.get('job_openings_count', 0) == 0:
            risk_score += 15
            risk_factors.append("No active hiring (15 pts)")
        
        # Factor 3: Valuation risk (0-25 points)
        valuation = data.get('valuation', 0)
        if valuation > 50_000_000_000:
            risk_score += 20
            risk_factors.append("Very high valuation risk (>$50B) (20 pts)")
        elif valuation == 0:
            risk_score += 10
            risk_factors.append("No valuation disclosed (10 pts)")
        
        # Factor 4: Data completeness (0-15 points)
        required_fields = ['company_name', 'website', 'headquarters', 'ceo']
        missing = sum(1 for field in required_fields if not data.get(field))
        risk_score += missing * 3
        if missing > 0:
            risk_factors.append(f"Missing {missing} key fields ({missing*3} pts)")
        
        # Factor 5: Age risk (0-15 points)
        founded = data.get('year_founded')
        if founded:
            age = 2025 - founded
            if age < 2:
                risk_score += 15
                risk_factors.append("Very young company (<2 years) (15 pts)")
            elif age < 5:
                risk_score += 10
                risk_factors.append("Young company (<5 years) (10 pts)")
        
        # Determine risk level
        if risk_score < 20:
            risk_level = "🟢 LOW RISK"
        elif risk_score < 40:
            risk_level = "🟡 MEDIUM RISK"
        elif risk_score < 60:
            risk_level = "🟠 HIGH RISK"
        else:
            risk_level = "🔴 CRITICAL RISK"
        
        return {
            "company_id": company_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "max_score": 100,
            "risk_factors": risk_factors,
            "assessment": f"{risk_level} - Score: {risk_score}/100"
        }
        
    except Exception as e:
        return {"error": f"Error calculating risk: {str(e)}"}


# ============================================================================
# Tool Registry
# ============================================================================

ADVANCED_TOOLS = {
    "calculate_financial_metrics": calculate_financial_metrics,
    "compare_competitors": compare_competitors,
    "generate_investment_recommendation": generate_investment_recommendation,
    "analyze_market_trends": analyze_market_trends,
    "calculate_risk_score": calculate_risk_score
}


# ============================================================================
# Test Function
# ============================================================================

async def test_advanced_tools():
    """Test all advanced tools."""
    import asyncio
    
    print("=" * 70)
    print("🧪 TESTING ADVANCED TOOLS")
    print("=" * 70)
    
    # Test Tool 4: Financial Metrics
    print("\n[1/5] Testing Financial Metrics...")
    result = await calculate_financial_metrics("anthropic")
    print(json.dumps(result, indent=2))
    
    # Test Tool 5: Competitor Comparison
    print("\n[2/5] Testing Competitor Comparison...")
    result = await compare_competitors(["anthropic", "openai", "cohere"])
    print(json.dumps(result, indent=2))
    
    # Test Tool 6: Investment Recommendation
    print("\n[3/5] Testing Investment Recommendation...")
    result = await generate_investment_recommendation("anthropic")
    print(json.dumps(result, indent=2))
    
    # Test Tool 7: Market Trends
    print("\n[4/5] Testing Market Trend Analysis...")
    result = await analyze_market_trends()
    print(json.dumps(result, indent=2))
    
    # Test Tool 8: Risk Score
    print("\n[5/5] Testing Risk Score Calculator...")
    result = await calculate_risk_score("anthropic")
    print(json.dumps(result, indent=2))
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_advanced_tools())