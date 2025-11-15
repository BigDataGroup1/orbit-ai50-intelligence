"""
Lab 17: Supervisory Workflow Pattern (Graph-based)
Defines a graph-based workflow for PE Due Diligence analysis.

Nodes:
1. Planner - Constructs plan of actions
2. Data Generator - Invokes MCP dashboard tools
3. Evaluator - Scores dashboards per rubric
4. Risk Detector - Branches to HITL if keywords found
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Literal, TypedDict
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️  LangGraph not available. Using fallback workflow builder.")

from src.agents.mcp_integration import get_mcp_integration
from src.agents.tools import get_latest_structured_payload, PayloadRequest
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# State Definition
# ============================================================

class WorkflowState(TypedDict):
    """State passed between workflow nodes."""
    company_id: str
    plan: Optional[List[str]]
    payload: Optional[Dict]
    dashboard_markdown: Optional[str]
    dashboard_score: Optional[float]
    risk_keywords: List[str]
    requires_hitl: bool
    branch_taken: Optional[str]  # "normal" or "hitl"
    error: Optional[str]
    metadata: Dict


# ============================================================
# Node Implementations
# ============================================================

def planner_node(state: WorkflowState) -> WorkflowState:
    """
    Node 1: Planner
    Constructs a plan of actions for the due diligence workflow.
    """
    company_id = state["company_id"]
    print(f"\n{'='*70}")
    print(f"📋 PLANNER NODE: {company_id}")
    print(f"{'='*70}")
    
    plan = [
        "1. Retrieve company structured payload",
        "2. Generate dashboard via MCP",
        "3. Evaluate dashboard quality",
        "4. Detect risks and determine if HITL needed"
    ]
    
    print(f"✅ Plan constructed: {len(plan)} steps")
    for step in plan:
        print(f"   {step}")
    
    state["plan"] = plan
    state["metadata"]["planner_timestamp"] = datetime.now().isoformat()
    
    return state


async def data_generator_node(state: WorkflowState) -> WorkflowState:
    """
    Node 2: Data Generator
    Invokes MCP dashboard tools to generate company dashboard.
    """
    company_id = state["company_id"]
    print(f"\n{'='*70}")
    print(f"📊 DATA GENERATOR NODE: {company_id}")
    print(f"{'='*70}")
    
    try:
        # Step 1: Get payload
        print("   Step 1: Retrieving structured payload...")
        payload_req = PayloadRequest(company_id=company_id)
        payload_resp = await get_latest_structured_payload(payload_req)
        
        if not payload_resp.success:
            state["error"] = f"Failed to retrieve payload: {payload_resp.error}"
            return state
        
        state["payload"] = payload_resp.payload
        print(f"   ✅ Payload retrieved: {len(json.dumps(payload_resp.payload))} bytes")
        
        # Step 2: Generate dashboard via MCP
        print("   Step 2: Generating dashboard via MCP...")
        mcp = get_mcp_integration()
        
        if not mcp.is_enabled():
            state["error"] = "MCP server not enabled"
            return state
        
        mcp_result = mcp.call_tool("generate_structured_dashboard", {
            "company_id": company_id
        })
        
        if mcp_result.get("success"):
            state["dashboard_markdown"] = mcp_result.get("markdown", "")
            print(f"   ✅ Dashboard generated: {len(state['dashboard_markdown'])} chars")
            state["metadata"]["tokens_used"] = mcp_result.get("tokens_used", 0)
        else:
            state["error"] = f"MCP dashboard generation failed: {mcp_result.get('error')}"
            print(f"   ❌ Dashboard generation failed: {mcp_result.get('error')}")
        
    except Exception as e:
        state["error"] = f"Data generator error: {str(e)}"
        print(f"   ❌ Error: {e}")
    
    return state


def evaluator_node(state: WorkflowState) -> WorkflowState:
    """
    Node 3: Evaluator
    Scores dashboards per rubric (completeness, structure, data quality).
    """
    company_id = state["company_id"]
    print(f"\n{'='*70}")
    print(f"📝 EVALUATOR NODE: {company_id}")
    print(f"{'='*70}")
    
    dashboard = state.get("dashboard_markdown", "")
    
    if not dashboard:
        state["dashboard_score"] = 0.0
        state["error"] = "No dashboard to evaluate"
        print("   ❌ No dashboard available for evaluation")
        return state
    
    # Scoring rubric (0-100 scale)
    score = 0.0
    max_score = 100.0
    
    # Criteria 1: Dashboard length (20 points)
    if len(dashboard) > 1000:
        score += 20
    elif len(dashboard) > 500:
        score += 15
    elif len(dashboard) > 200:
        score += 10
    print(f"   Length score: {min(20, score)}/20")
    
    # Criteria 2: Structure completeness (30 points)
    structure_keywords = [
        "company", "funding", "valuation", "team", "product",
        "revenue", "customers", "competitors"
    ]
    found_keywords = sum(1 for kw in structure_keywords if kw.lower() in dashboard.lower())
    structure_score = min(30, (found_keywords / len(structure_keywords)) * 30)
    score += structure_score
    print(f"   Structure score: {structure_score:.1f}/30 ({found_keywords}/{len(structure_keywords)} keywords)")
    
    # Criteria 3: Data quality indicators (30 points)
    quality_indicators = [
        "founded", "headquarters", "ceo", "employees",
        "funding", "valuation", "revenue"
    ]
    found_indicators = sum(1 for ind in quality_indicators if ind.lower() in dashboard.lower())
    quality_score = min(30, (found_indicators / len(quality_indicators)) * 30)
    score += quality_score
    print(f"   Quality score: {quality_score:.1f}/30 ({found_indicators}/{len(quality_indicators)} indicators)")
    
    # Criteria 4: Formatting (20 points)
    formatting_score = 0.0
    if "##" in dashboard or "#" in dashboard:  # Has headers
        formatting_score += 10
    if "-" in dashboard or "*" in dashboard:  # Has lists
        formatting_score += 5
    if ":" in dashboard:  # Has structured data
        formatting_score += 5
    score += formatting_score
    print(f"   Formatting score: {formatting_score:.1f}/20")
    
    state["dashboard_score"] = min(100.0, score)
    state["metadata"]["evaluation_timestamp"] = datetime.now().isoformat()
    
    print(f"   ✅ Total score: {state['dashboard_score']:.1f}/100")
    
    return state


def risk_detector_node(state: WorkflowState) -> WorkflowState:
    """
    Node 4: Risk Detector
    Branches to HITL if keywords found in dashboard or payload.
    """
    company_id = state["company_id"]
    print(f"\n{'='*70}")
    print(f"🚨 RISK DETECTOR NODE: {company_id}")
    print(f"{'='*70}")
    
    # Risk keywords that trigger HITL
    risk_keywords = [
        "layoff", "layoffs", "firing", "termination", "downsizing",
        "bankruptcy", "insolvency", "default", "foreclosure",
        "lawsuit", "litigation", "legal action", "breach",
        "security incident", "data breach", "hack", "cyber attack",
        "funding round failed", "investor pullout", "valuation drop",
        "ceo resignation", "executive departure", "leadership change"
    ]
    
    # Handle None values safely
    dashboard = state.get("dashboard_markdown") or ""
    dashboard = dashboard.lower() if dashboard else ""
    
    payload = state.get("payload") or {}
    payload_str = json.dumps(payload).lower()
    combined_text = dashboard + " " + payload_str
    
    # Detect risk keywords
    found_risks = [kw for kw in risk_keywords if kw in combined_text]
    state["risk_keywords"] = found_risks
    
    # Determine if HITL required
    requires_hitl = len(found_risks) > 0
    
    if requires_hitl:
        state["requires_hitl"] = True
        state["branch_taken"] = "hitl"
        print(f"   ⚠️  RISK DETECTED: {len(found_risks)} risk keywords found")
        print(f"   Keywords: {', '.join(found_risks[:5])}")
        print(f"   → Branch: HITL (Human-in-the-Loop)")
    else:
        state["requires_hitl"] = False
        state["branch_taken"] = "normal"
        print(f"   ✅ No risks detected")
        print(f"   → Branch: Normal flow")
    
    state["metadata"]["risk_detection_timestamp"] = datetime.now().isoformat()
    state["metadata"]["risk_count"] = len(found_risks)
    
    return state


def hitl_node(state: WorkflowState) -> WorkflowState:
    """
    HITL Node: Human-in-the-Loop review point.
    In production, this would pause and wait for human approval.
    """
    company_id = state["company_id"]
    print(f"\n{'='*70}")
    print(f"👤 HITL NODE: {company_id}")
    print(f"{'='*70}")
    print(f"   ⏸️  Workflow paused for human review")
    print(f"   Risk keywords: {', '.join(state.get('risk_keywords', []))}")
    print(f"   Dashboard score: {state.get('dashboard_score', 0):.1f}/100")
    print(f"   → Waiting for human approval...")
    print(f"   [SIMULATED] Human approved - continuing workflow")
    
    state["metadata"]["hitl_timestamp"] = datetime.now().isoformat()
    state["metadata"]["hitl_approved"] = True
    
    return state


# ============================================================
# Workflow Graph Builder
# ============================================================

def build_workflow_graph():
    """
    Build the due diligence workflow graph.
    
    Flow:
    START → Planner → Data Generator → Evaluator → Risk Detector
                                                      ↓
                                                   [Branch]
                                                   /      \
                                            HITL (if risks)  Normal (if no risks)
                                                   ↓              ↓
                                                  END            END
    """
    if LANGGRAPH_AVAILABLE:
        # Use LangGraph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("planner", planner_node)
        workflow.add_node("data_generator", data_generator_node)
        workflow.add_node("evaluator", evaluator_node)
        workflow.add_node("risk_detector", risk_detector_node)
        workflow.add_node("hitl", hitl_node)
        
        # Define edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "data_generator")
        workflow.add_edge("data_generator", "evaluator")
        workflow.add_edge("evaluator", "risk_detector")
        
        # Conditional edge: Risk Detector → HITL or END
        def should_go_to_hitl(state: WorkflowState) -> Literal["hitl", "end"]:
            if state.get("requires_hitl", False):
                return "hitl"
            return "end"
        
        workflow.add_conditional_edges(
            "risk_detector",
            should_go_to_hitl,
            {
                "hitl": "hitl",
                "end": END
            }
        )
        
        workflow.add_edge("hitl", END)
        
        return workflow.compile()
    
    else:
        # Fallback: Simple sequential workflow
        print("⚠️  Using fallback sequential workflow (LangGraph not available)")
        
        class FallbackWorkflow:
            async def ainvoke(self, initial_state: WorkflowState) -> WorkflowState:
                """Execute workflow sequentially."""
                state = initial_state.copy()
                
                # Execute nodes in order
                state = planner_node(state)
                state = await data_generator_node(state)
                state = evaluator_node(state)
                state = risk_detector_node(state)
                
                # Branch based on risk detection
                if state.get("requires_hitl", False):
                    state = hitl_node(state)
                
                return state
        
        return FallbackWorkflow()


# ============================================================
# Main Execution
# ============================================================

async def run_workflow(company_id: str) -> Dict:
    """
    Run the due diligence workflow for a company.
    
    Args:
        company_id: Company identifier
        
    Returns:
        Final workflow state
    """
    print("\n" + "="*70)
    print("🚀 DUE DILIGENCE WORKFLOW")
    print("="*70)
    print(f"Company: {company_id}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    
    # Initialize state
    initial_state: WorkflowState = {
        "company_id": company_id,
        "plan": None,
        "payload": None,
        "dashboard_markdown": None,
        "dashboard_score": None,
        "risk_keywords": [],
        "requires_hitl": False,
        "branch_taken": None,
        "error": None,
        "metadata": {}
    }
    
    # Build and run workflow
    workflow = build_workflow_graph()
    final_state = await workflow.ainvoke(initial_state)
    
    # Print summary
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETE")
    print("="*70)
    print(f"Company: {final_state['company_id']}")
    print(f"Branch taken: {final_state.get('branch_taken', 'unknown')}")
    print(f"Dashboard score: {final_state.get('dashboard_score', 0):.1f}/100")
    print(f"Risks detected: {len(final_state.get('risk_keywords', []))}")
    print(f"Requires HITL: {final_state.get('requires_hitl', False)}")
    if final_state.get("error"):
        print(f"Error: {final_state['error']}")
    print("="*70 + "\n")
    
    return final_state


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run due diligence workflow")
    parser.add_argument("--company", type=str, default="anthropic", help="Company ID to analyze")
    args = parser.parse_args()
    
    result = asyncio.run(run_workflow(args.company))
    
    # Print branch taken (checkpoint requirement)
    print(f"\n{'='*70}")
    print(f"✅ CHECKPOINT: Branch taken = {result.get('branch_taken', 'unknown')}")
    print(f"{'='*70}\n")

