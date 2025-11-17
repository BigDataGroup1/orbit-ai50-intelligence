"""
Lab 13: Supervisor Agent - PE Due Diligence Agent
Implements ReAct reasoning pattern with structured logging

Usage:
  python src/agents/supervisor_agent.py              # Demo (1 company)
  python src/agents/supervisor_agent.py --all        # All companies
  python src/agents/supervisor_agent.py --batch 10   # First 10 companies
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
from pathlib import Path
import sys
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from openai import OpenAI
from src.agents.react_logger import ReActLogger
from src.agents.tools import (
    get_latest_structured_payload,
    report_layoff_signal,
    PayloadRequest,
    LayoffSignal,
    list_available_companies
)
from src.agents.mcp_integration import get_mcp_integration
from src.agents.advanced_tools import (
    calculate_financial_metrics,
    compare_competitors,
    generate_investment_recommendation,
    analyze_market_trends,
    calculate_risk_score
)

from dotenv import load_dotenv
load_dotenv()


class SupervisorAgent:
    """
    PE Due Diligence Supervisor Agent.
    
    Uses ReAct pattern to:
    1. Think about what to do
    2. Execute actions (call tools)
    3. Observe results
    4. Decide next steps
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the supervisor agent.
        
        Args:
            model: OpenAI model to use
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize MCP integration (Lab 15)
        self.mcp = get_mcp_integration()
        
        # System prompt (includes MCP tools and advanced tools if enabled)
        tools_list = [
            "1. get_latest_structured_payload - Retrieves company data (funding, team, metrics)",
            "2. report_layoff_signal - Logs high-risk events that need human review",
            "3. calculate_financial_metrics - Calculate valuation/funding ratios and efficiency",
            "4. compare_competitors - Compare multiple companies side-by-side",
            "5. generate_investment_recommendation - Get BUY/HOLD/PASS recommendation with score",
            "6. calculate_risk_score - Comprehensive risk assessment (0-100)"
        ]
        
        if self.mcp.is_enabled():
            tools_list.extend([
                "7. generate_structured_dashboard (via MCP) - Generates structured dashboard from payload",
                "8. generate_rag_dashboard (via MCP) - Generates RAG dashboard from vector store"
            ])
        
        self.system_prompt = f"""You are a PE Due Diligence Supervisor Agent.

Your job is to analyze companies and generate insights for private equity investors.

You have access to these tools:
{chr(10).join(tools_list)}

Use ReAct reasoning:
- THINK about what you need to do
- ACT by calling tools
- OBSERVE the results
- Continue until you have enough information

When analyzing a company:
1. Get the company payload
2. Analyze for risks (layoffs, funding issues, leadership changes)
3. Report any critical risks
4. Optionally generate dashboards using MCP tools
5. Provide a concise PE analysis

Be concise and focused on investor-relevant insights."""
        
        print(f"🤖 Supervisor Agent initialized with model: {model}")
    
    async def analyze_company(self, company_id: str, max_steps: int = 5) -> Dict:
        """
        Analyze a company using ReAct reasoning pattern.
        
        Args:
            company_id: Company to analyze
            max_steps: Maximum reasoning steps
            
        Returns:
            Analysis results
        """
        print(f"\n{'='*70}")
        print(f"🎯 ANALYZING: {company_id}")
        print(f"{'='*70}\n")
        
        # Initialize ReAct logger
        react_logger = ReActLogger(company_id=company_id)
        
        # Step 1: Think - What do I need to do?
        thought_1 = f"I need to analyze {company_id} for PE due diligence. First, I should retrieve the company's structured payload to understand their business."
        react_logger.log_thought(thought_1, step_num=1)
        
        # Step 2: Act - Get company payload
        action_input = {"company_id": company_id}
        react_logger.log_action("get_latest_structured_payload", action_input, step_num=1)
        
        payload_req = PayloadRequest(company_id=company_id)
        payload_resp = await get_latest_structured_payload(payload_req)
        
        if not payload_resp.success:
            observation_1 = f"Failed to retrieve payload: {payload_resp.error}"
            react_logger.log_observation(observation_1, success=False, step_num=1)
            
            trace_path = react_logger.save_trace(final_output="Analysis failed - no data available")
            
            return {
                "success": False,
                "company_id": company_id,
                "error": payload_resp.error,
                "trace_file": str(trace_path)
            }
        
        # Step 3: Observe - What did I learn?
        payload = payload_resp.payload
        company = payload.get('company_record', {})
        
        # Safe formatting
        valuation = company.get('last_disclosed_valuation_usd')
        valuation_str = f"${valuation:,.0f}" if valuation else "Not disclosed"
        
        observation_1 = f"Retrieved payload for {company.get('legal_name', 'Unknown')}. Founded: {company.get('founded_year', 'Unknown')}, HQ: {company.get('hq_city', 'Unknown')}, Valuation: {valuation_str}"
        react_logger.log_observation(observation_1, success=True, step_num=1)
        
        # Log complete step
        react_logger.log_step(
            thought=thought_1,
            action_name="get_latest_structured_payload",
            action_input=action_input,
            observation=observation_1,
            success=True
        )
        
        # Step 4: Think - Analyze for risks
        thought_2 = "Now I should perform comprehensive risk analysis across funding, team, market position, and data disclosure gaps."
        react_logger.log_thought(thought_2, step_num=2)
        
        # Extract all data sections
        leadership = payload.get('leadership', [])
        snapshots = payload.get('snapshots', [])
        events = payload.get('events', [])
        
        latest_snapshot = snapshots[0] if snapshots else {}
        
        risks_found = []
        
        # Risk 1: Funding disclosure
        total_raised = company.get('total_raised_usd')
        if not total_raised or total_raised == 0:
            risks_found.append({
                "type": "funding_disclosure",
                "severity": "low",
                "description": "Total funding not publicly disclosed - limits valuation benchmarking"
            })
        
        # Risk 2: Valuation analysis
        if valuation:
            if valuation > 50_000_000_000:  # Over $50B
                risks_found.append({
                    "type": "high_valuation",
                    "severity": "medium",
                    "description": f"Very high valuation (${valuation:,.0f}) - elevated market expectations risk"
                })
            elif valuation > 10_000_000_000:  # $10B-$50B
                risks_found.append({
                    "type": "unicorn_valuation",
                    "severity": "low",
                    "description": f"Decacorn valuation (${valuation:,.0f}) - strong market position but high bar for returns"
                })
        
        # Risk 3: Leadership completeness
        ceo_info = next((l for l in leadership if l.get('role') == 'CEO'), None)
        if not ceo_info:
            risks_found.append({
                "type": "leadership_gap",
                "severity": "medium",
                "description": "CEO information not available - limits team assessment"
            })
        elif not ceo_info.get('is_founder'):
            risks_found.append({
                "type": "non_founder_ceo",
                "severity": "low",
                "description": "CEO is not a founder - may indicate leadership transition"
            })
        
        # Risk 4: Hiring freeze indicator
        job_openings = latest_snapshot.get('job_openings_count', 0)
        if job_openings == 0 and company.get('founded_year', 2025) < 2023:
            risks_found.append({
                "type": "no_hiring",
                "severity": "medium",
                "description": "No public job openings for established company - possible hiring freeze"
            })
        
        # Risk 5: Data completeness
        missing_fields = []
        critical_fields = {
            'legal_name': company.get('legal_name'),
            'founded_year': company.get('founded_year'),
            'website': company.get('website'),
            'categories': company.get('categories')
        }
        for field, value in critical_fields.items():
            if not value or (isinstance(value, list) and len(value) == 0):
                missing_fields.append(field)
        
        if len(missing_fields) >= 3:
            risks_found.append({
                "type": "data_gaps",
                "severity": "medium",
                "description": f"Multiple critical fields missing: {', '.join(missing_fields)} - limits analysis confidence"
            })
        elif len(missing_fields) >= 1:
            risks_found.append({
                "type": "minor_data_gaps",
                "severity": "low",
                "description": f"Some data gaps: {', '.join(missing_fields)}"
            })
        
        # Risk 6: Recent events analysis
        recent_events = events[:5]  # Last 5 events
        for event in recent_events:
            if event.get('event_type') == 'layoff':
                risks_found.append({
                    "type": "layoff_event",
                    "severity": "high",
                    "description": f"Recent layoff event detected: {event.get('title', 'Details unavailable')}"
                })
            elif event.get('event_type') == 'security_incident':
                risks_found.append({
                    "type": "security_incident",
                    "severity": "critical",
                    "description": f"Security incident: {event.get('title', 'Details unavailable')}"
                })
        
        observation_2 = f"Risk analysis complete. Found {len(risks_found)} potential risks."
        react_logger.log_observation(observation_2, success=True, step_num=2)
        
        # Step 5: Act - Report critical risks
        if any(r['severity'] in ['high', 'critical'] for r in risks_found):
            thought_3 = "Found critical risks that require human review. I should log these."
            react_logger.log_thought(thought_3, step_num=3)
            
            for risk in risks_found:
                if risk['severity'] in ['high', 'critical']:
                    signal = LayoffSignal(
                        company_id=company_id,
                        signal_type=risk['type'],
                        severity=risk['severity'],
                        description=risk['description']
                    )
                    
                    signal_resp = await report_layoff_signal(signal)
                    
                    react_logger.log_action(
                        "report_layoff_signal",
                        {"signal_type": risk['type'], "severity": risk['severity']},
                        step_num=3
                    )
                    react_logger.log_observation(
                        signal_resp.message,
                        success=signal_resp.success,
                        step_num=3
                    )
        
        # Step 4: Calculate financial metrics (Advanced Tool)
        thought_4 = "I should calculate financial metrics to understand valuation efficiency and funding health."
        react_logger.log_thought(thought_4, step_num=4)
        
        react_logger.log_action("calculate_financial_metrics", {"company_id": company_id}, step_num=4)
        financial_metrics = await calculate_financial_metrics(company_id)
        
        if financial_metrics.get('error'):
            react_logger.log_observation(
                f"Financial metrics calculation failed: {financial_metrics.get('error')}",
                success=False,
                step_num=4
            )
        else:
            react_logger.log_observation(
                f"Financial metrics: {financial_metrics.get('funding_efficiency', 'N/A')} | Ratio: {financial_metrics.get('valuation_to_funding_ratio', 'N/A')}",
                success=True,
                step_num=4
            )
        
        # Step 5: Calculate risk score (Advanced Tool)
        thought_5 = "I should calculate a comprehensive risk score to assess investment risk."
        react_logger.log_thought(thought_5, step_num=5)
        
        react_logger.log_action("calculate_risk_score", {"company_id": company_id}, step_num=5)
        risk_score_result = await calculate_risk_score(company_id)
        
        if risk_score_result.get('error'):
            react_logger.log_observation(
                f"Risk score calculation failed: {risk_score_result.get('error')}",
                success=False,
                step_num=5
            )
        else:
            react_logger.log_observation(
                f"Risk Score: {risk_score_result.get('risk_score', 'N/A')}/100 - {risk_score_result.get('risk_level', 'N/A')}",
                success=True,
                step_num=5
            )
        
        # Step 6 (Optional): Generate dashboard via MCP if enabled (Lab 15)
        dashboard_info = None
        if self.mcp.is_enabled():
            thought_6 = "I can generate a structured dashboard via MCP to provide comprehensive analysis."
            react_logger.log_thought(thought_6, step_num=6)
            
            react_logger.log_action("generate_structured_dashboard (MCP)", {"company_id": company_id}, step_num=6)
            mcp_result = self.mcp.call_tool("generate_structured_dashboard", {"company_id": company_id})
            
            if mcp_result.get('success'):
                dashboard_info = {
                    'tokens_used': mcp_result.get('tokens_used', 0),
                    'company_name': mcp_result.get('company_name', company_id)
                }
                react_logger.log_observation(
                    f"Generated structured dashboard via MCP ({dashboard_info['tokens_used']} tokens)",
                    success=True,
                    step_num=6
                )
            else:
                react_logger.log_observation(
                    f"MCP dashboard failed: {mcp_result.get('error', 'Unknown error')}",
                    success=False,
                    step_num=6
                )
        
        # Generate final analysis (include financial metrics and risk score)
        analysis = self._generate_analysis(
            payload, 
            risks_found, 
            dashboard_info,
            financial_metrics=financial_metrics if not financial_metrics.get('error') else None,
            risk_score=risk_score_result if not risk_score_result.get('error') else None
        )
        
        # Save trace
        trace_path = react_logger.save_trace(final_output=analysis)
        
        print(f"\n✅ Analysis complete for {company_id}")
        print(f"📊 Risks found: {len(risks_found)}")
        print(f"📝 Trace saved: {trace_path.name}")
        
        return {
            "success": True,
            "company_id": company_id,
            "analysis": analysis,
            "risks": risks_found,
            "trace_file": str(trace_path),
            "run_id": react_logger.run_id
        }
    
    def _generate_analysis(
        self, 
        payload: Dict, 
        risks: List[Dict], 
        dashboard_info: Optional[Dict] = None,
        financial_metrics: Optional[Dict] = None,
        risk_score: Optional[Dict] = None
    ) -> str:
        """
        Generate comprehensive PE analysis summary.
        
        Args:
            payload: Company payload (nested structure)
            risks: Detected risks
            
        Returns:
            Detailed analysis summary
        """
        # Extract all sections
        company = payload.get('company_record', {})
        leadership = payload.get('leadership', [])
        snapshots = payload.get('snapshots', [])
        events = payload.get('events', [])
        products = payload.get('products', [])
        visibility = payload.get('visibility', [])
        
        # Get latest snapshot
        latest_snapshot = snapshots[0] if snapshots else {}
        latest_visibility = visibility[0] if visibility else {}
        
        # Extract CEO
        ceo_info = next((l for l in leadership if l.get('role') == 'CEO'), {})
        ceo_name = ceo_info.get('name', 'Not disclosed')
        is_founder = " (Founder)" if ceo_info.get('is_founder') else ""
        
        # Format funding
        funding_usd = company.get('total_raised_usd')
        funding_str = f"${funding_usd:,.0f}" if funding_usd else "Not disclosed"
        
        # Format valuation
        valuation_usd = company.get('last_disclosed_valuation_usd')
        valuation_str = f"${valuation_usd:,.0f}" if valuation_usd else "Not disclosed"
        
        # Pricing info
        pricing_tiers = latest_snapshot.get('pricing_tiers', [])
        pricing_str = ', '.join(pricing_tiers) if pricing_tiers else "Not disclosed"
        
        # Job openings
        job_count = latest_snapshot.get('job_openings_count', 0)
        hiring_str = f"{job_count} open positions" if job_count else "No public job openings"
        
        analysis = f"""
╔══════════════════════════════════════════════════════════════════╗
║  PE DUE DILIGENCE ANALYSIS - INVESTOR BRIEF                      ║
╚══════════════════════════════════════════════════════════════════╝

COMPANY: {company.get('legal_name', 'Unknown')}
Analyzed: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
Data as of: {company.get('as_of', 'Unknown')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. COMPANY OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Legal Name:     {company.get('legal_name', 'Not disclosed')}
Website:        {company.get('website', 'Not disclosed')}
Founded:        {company.get('founded_year', 'Not disclosed')}
Headquarters:   {company.get('hq_city', 'Not disclosed')}, {company.get('hq_country', 'Not disclosed')}
CEO:            {ceo_name}{is_founder}
Leadership:     {len(leadership)} executives tracked

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. BUSINESS MODEL & GTM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Categories:     {', '.join(company.get('categories', [])) or 'Not disclosed'}
Pricing Model:  {pricing_str}
Product Focus:  {len(products)} products tracked

Competitors/Related:
{chr(10).join(f'  • {comp}' for comp in company.get('related_companies', [])[:5]) or '  • Not disclosed'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. FUNDING & INVESTOR PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Raised:       {funding_str}
Last Valuation:     {valuation_str}
Last Round:         {company.get('last_round_name', 'Not disclosed')}
Last Round Date:    {company.get('last_round_date', 'Not disclosed')}
Funding Events:     {len([e for e in events if e.get('event_type') == 'funding'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. GROWTH MOMENTUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hiring Status:      {hiring_str}
Headcount:          {latest_snapshot.get('headcount_total', 'Not disclosed')}
Recent Events:      {len(events)} tracked events

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. VISIBILITY & MARKET SENTIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
News Mentions (30d): {latest_visibility.get('news_mentions_30d', 'Not tracked')}
GitHub Stars:        {latest_visibility.get('github_stars', 'Not tracked')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. RISKS AND CHALLENGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Risks Identified: {len(risks)}
"""
        
        # Add financial metrics if available
        if financial_metrics and not financial_metrics.get('error'):
            analysis += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. FINANCIAL METRICS ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Valuation to Funding Ratio: {financial_metrics.get('valuation_to_funding_ratio', 'N/A')}
Funding Efficiency: {financial_metrics.get('funding_efficiency', 'N/A')}
Analysis: {financial_metrics.get('analysis', 'N/A')}
"""
        
        # Add risk score if available
        if risk_score and not risk_score.get('error'):
            analysis += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. RISK SCORE ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{risk_score.get('assessment', 'N/A')}
Risk Factors:
{chr(10).join(f'  • {factor}' for factor in risk_score.get('risk_factors', []))}
"""
        
        if risks:
            for i, risk in enumerate(risks, 1):
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }
                emoji = severity_emoji.get(risk['severity'].lower(), '⚪')
                analysis += f"\n{emoji} Risk {i} [{risk['severity'].upper()}] {risk['type']}"
                analysis += f"\n   └─ {risk['description']}"
        else:
            analysis += "\n✅ No significant risks detected."
        
        analysis += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. INVESTMENT OUTLOOK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Generate recommendation
        critical_risks = sum(1 for r in risks if r['severity'] in ['critical', 'high'])
        data_completeness = self._calculate_data_completeness(payload)
        
        if critical_risks > 0:
            recommendation = "⚠️ CAUTION - Critical risks require HITL review"
        elif data_completeness < 50:
            recommendation = "⚠️ HOLD - Insufficient data for investment decision"
        elif valuation_usd and valuation_usd > 50_000_000_000:
            recommendation = "💎 MONITOR - High valuation, strong market position"
        else:
            recommendation = "✅ PROCEED - Fundamentals support due diligence continuation"
        
        analysis += f"Recommendation: {recommendation}\n"
        analysis += f"Data Completeness: {data_completeness}%\n"
        
        analysis += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. DISCLOSURE GAPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # List missing critical fields
        gaps = []
        if not company.get('legal_name'):
            gaps.append("• Legal name not disclosed")
        if not funding_usd:
            gaps.append("• Total funding not disclosed")
        if not company.get('categories'):
            gaps.append("• Business categories not classified")
        if not latest_snapshot.get('headcount_total'):
            gaps.append("• Employee headcount not disclosed")
        if not events:
            gaps.append("• No recent events tracked")
        if not latest_visibility.get('news_mentions_30d'):
            gaps.append("• News visibility not tracked")
        
        if gaps:
            analysis += "\n".join(gaps)
        else:
            analysis += "✅ All critical data points disclosed"
        
        # Add MCP dashboard info if available (Lab 15)
        if dashboard_info:
            analysis += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            analysis += "\n9. GENERATED DASHBOARDS (via MCP)"
            analysis += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            analysis += f"\n✅ Structured dashboard generated via MCP server"
            analysis += f"\n   Company: {dashboard_info.get('company_name', 'Unknown')}"
            analysis += f"\n   Tokens used: {dashboard_info.get('tokens_used', 0)}"
        
        analysis += "\n\n" + "═"*70
        
        return analysis.strip()
    
    def _calculate_data_completeness(self, payload: Dict) -> int:
        """Calculate percentage of data fields that are populated."""
        company = payload.get('company_record', {})
        leadership = payload.get('leadership', [])
        snapshots = payload.get('snapshots', [])
        events = payload.get('events', [])
        
        total_fields = 10
        filled_fields = 0
        
        if company.get('legal_name'): filled_fields += 1
        if company.get('website'): filled_fields += 1
        if company.get('founded_year'): filled_fields += 1
        if company.get('total_raised_usd'): filled_fields += 1
        if company.get('last_disclosed_valuation_usd'): filled_fields += 1
        if company.get('categories'): filled_fields += 1
        if leadership: filled_fields += 1
        if snapshots: filled_fields += 1
        if events: filled_fields += 1
        if company.get('hq_city'): filled_fields += 1
        
        return int((filled_fields / total_fields) * 100)
    
    async def batch_analyze(self, company_ids: List[str], max_companies: int = None) -> List[Dict]:
        """
        Analyze multiple companies.
        
        Args:
            company_ids: List of company IDs
            max_companies: Maximum companies to analyze (None = all)
            
        Returns:
            List of analysis results with summary
        """
        if max_companies:
            company_ids = company_ids[:max_companies]
        
        total = len(company_ids)
        
        print(f"\n{'='*70}")
        print(f"🚀 BATCH ANALYSIS: {total} companies")
        print(f"{'='*70}\n")
        
        results = []
        successful = 0
        failed = 0
        total_risks = 0
        risk_breakdown = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for i, company_id in enumerate(company_ids, 1):
            print(f"\n[{i}/{total}] Analyzing {company_id}...")
            
            try:
                result = await self.analyze_company(company_id)
                results.append(result)
                
                if result['success']:
                    successful += 1
                    total_risks += len(result['risks'])
                    
                    # Count by severity
                    for risk in result['risks']:
                        severity = risk['severity'].lower()
                        if severity in risk_breakdown:
                            risk_breakdown[severity] += 1
                else:
                    failed += 1
            
            except Exception as e:
                print(f"❌ Error analyzing {company_id}: {e}")
                failed += 1
                results.append({
                    'success': False,
                    'company_id': company_id,
                    'error': str(e)
                })
            
            # Small delay
            await asyncio.sleep(0.5)
        
        # Generate summary
        summary = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_companies": total,
            "successful": successful,
            "failed": failed,
            "total_risks_found": total_risks,
            "risk_breakdown": risk_breakdown,
            "companies": results
        }
        
        # Save to data folder
        summary_file = project_root / "data" / "agent_analysis_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save markdown report
        md_file = project_root / "data" / "agent_analysis_report.md"
        self._save_markdown_report(summary, md_file)
        
        # Print summary
        print(f"\n{'='*70}")
        print("FINAL SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successful: {successful}/{total} ({successful/total*100:.1f}%)")
        print(f"❌ Failed: {failed}/{total}")
        print(f"🚨 Total Risks: {total_risks}")
        print(f"\nRisk Breakdown:")
        print(f"  🔴 Critical: {risk_breakdown['critical']}")
        print(f"  🟠 High: {risk_breakdown['high']}")
        print(f"  🟡 Medium: {risk_breakdown['medium']}")
        print(f"  🟢 Low: {risk_breakdown['low']}")
        print(f"\n📁 JSON Summary: {summary_file}")
        print(f"📁 Markdown Report: {md_file}")
        print(f"📁 Traces: logs/react_traces/ ({successful} files)")
        print(f"{'='*70}\n")
        
        return results
    
    def _save_markdown_report(self, summary: Dict, filepath: Path):
        """Save a markdown report of the analysis."""
        # ✅ FIX: Use UTF-8 encoding to handle any special characters
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# PE Due Diligence - Agent Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}  \n")
            f.write(f"**Total Companies:** {summary['total_companies']}  \n\n")
            f.write("---\n\n")
            
            f.write("## Summary Statistics\n\n")
            total = summary['total_companies']
            success = summary['successful']
            f.write(f"- [OK] Successful: {success}/{total} ({success/total*100:.1f}%)  \n")
            f.write(f"- [FAIL] Failed: {summary['failed']}/{total}  \n")
            f.write(f"- [RISK] Total Risks: {summary['total_risks_found']}  \n\n")
            
            f.write("### Risk Severity Breakdown\n\n")
            rb = summary['risk_breakdown']
            f.write(f"- [CRITICAL] Critical: {rb['critical']}  \n")
            f.write(f"- [HIGH] High: {rb['high']}  \n")
            f.write(f"- [MEDIUM] Medium: {rb['medium']}  \n")
            f.write(f"- [LOW] Low: {rb['low']}  \n\n")
            
            f.write("---\n\n")
            f.write("## Company Analysis\n\n")
            
            for company in summary['companies']:
                if company['success']:
                    f.write(f"### {company['company_id']}\n\n")
                    f.write(f"**Risks Found:** {len(company['risks'])}  \n\n")
                    
                    for risk in company['risks']:
                        severity_label = {'critical': '[CRITICAL]', 'high': '[HIGH]', 'medium': '[MEDIUM]', 'low': '[LOW]'}.get(risk['severity'].lower(), '[UNKNOWN]')
                        f.write(f"{severity_label} **[{risk['severity'].upper()}]** {risk['type']}  \n")
                        f.write(f"  - {risk['description']}  \n\n")
                    
                    f.write(f"**Trace File:** `{Path(company['trace_file']).name}`  \n\n")
                    f.write("---\n\n")


# ============================================================
# Main Execution
# ============================================================

async def main():
    """Main execution with command-line arguments."""
    
    parser = argparse.ArgumentParser(description='PE Due Diligence Supervisor Agent')
    parser.add_argument('--all', action='store_true', help='Analyze all companies')
    parser.add_argument('--batch', type=int, help='Analyze first N companies')
    parser.add_argument('--company', type=str, help='Analyze specific company')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("LAB 13: SUPERVISOR AGENT - PE DUE DILIGENCE")
    print("="*70 + "\n")
    
    # Initialize agent
    agent = SupervisorAgent(model="gpt-4o-mini")
    
    # Get available companies
    companies = list_available_companies()
    print(f"📊 Available companies: {len(companies)}")
    print(f"   Sample: {companies[:5]}\n")
    
    if args.all:
        # Analyze ALL companies
        print(f"🎯 MODE: Analyzing ALL {len(companies)} companies")
        print(f"⏱️  Estimated time: ~{len(companies) * 2} seconds")
        print()
        
        await agent.batch_analyze(companies)
    
    elif args.batch:
        # Analyze first N companies
        n = args.batch
        print(f"🎯 MODE: Analyzing first {n} companies")
        print()
        
        await agent.batch_analyze(companies[:n], max_companies=n)
    
    elif args.company:
        # Analyze specific company
        company = args.company
        print(f"🎯 MODE: Single company analysis - {company}")
        print()
        
        result = await agent.analyze_company(company)
        
        print("\n" + "="*70)
        print("ANALYSIS RESULT")
        print("="*70)
        print(result['analysis'])
        print(f"\n📁 Trace: {result['trace_file']}")
    
    else:
        # Default: Demo mode (1 company + small batch)
        print("🎯 MODE: Demo (1 company + 3 company batch)")
        print()
        
        # Single analysis
        result = await agent.analyze_company("anthropic")
        
        print("\n" + "="*70)
        print("ANALYSIS RESULT")
        print("="*70)
        print(result['analysis'])
        print(f"\n📁 Trace: {result['trace_file']}")
        
        # Batch
        print("\n\n🎯 Batch Analysis (3 companies):")
        await agent.batch_analyze(companies[:3], max_companies=3)


if __name__ == "__main__":
    asyncio.run(main())