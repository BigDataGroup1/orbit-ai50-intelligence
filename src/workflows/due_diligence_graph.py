"""
Lab 17-18: Supervisory Workflow Pattern (Graph-based) with HITL Integration
Defines a graph-based workflow for PE Due Diligence analysis.

Nodes:
1. Planner - Constructs plan of actions
2. Data Generator - Invokes MCP dashboard tools
3. Evaluator - Scores dashboards per rubric
4. Risk Detector - Branches to HITL if keywords found
5. HITL - Human-in-the-Loop review with CLI pause (Lab 18)
"""

import asyncio
import json
import os
import uuid
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
    from langgraph.checkpoint.memory import MemorySaver
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
    execution_path: List[Dict]  # Lab 18: Track execution path
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
    node_start = datetime.now()
    
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
    state["metadata"]["planner_timestamp"] = node_start.isoformat()
    
    # Lab 18: Track execution path
    if "execution_path" not in state:
        state["execution_path"] = []
    state["execution_path"].append({
        "node": "planner",
        "start_time": node_start.isoformat(),
        "end_time": datetime.now().isoformat(),
        "status": "completed"
    })
    
    return state


async def data_generator_node(state: WorkflowState) -> WorkflowState:
    """
    Node 2: Data Generator
    Invokes MCP dashboard tools to generate company dashboard.
    """
    company_id = state["company_id"]
    node_start = datetime.now()
    
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
    
    # Lab 18: Track execution path
    state["execution_path"].append({
        "node": "data_generator",
        "start_time": node_start.isoformat(),
        "end_time": datetime.now().isoformat(),
        "status": "completed" if not state.get("error") else "failed"
    })
    
    return state


def evaluator_node(state: WorkflowState) -> WorkflowState:
    """
    Node 3: Evaluator
    Scores dashboards per rubric (completeness, structure, data quality).
    """
    company_id = state["company_id"]
    node_start = datetime.now()
    
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
    
    # Lab 18: Track execution path
    state["execution_path"].append({
        "node": "evaluator",
        "start_time": node_start.isoformat(),
        "end_time": datetime.now().isoformat(),
        "status": "completed",
        "score": state["dashboard_score"]
    })
    
    return state


def risk_detector_node(state: WorkflowState) -> WorkflowState:
    """
    Node 4: Risk Detector
    Branches to HITL if keywords found in dashboard or payload.
    """
    company_id = state["company_id"]
    node_start = datetime.now()
    
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
    
    # Lab 18: Track execution path
    state["execution_path"].append({
        "node": "risk_detector",
        "start_time": node_start.isoformat(),
        "end_time": datetime.now().isoformat(),
        "status": "completed",
        "risks_found": len(found_risks),
        "branch": state["branch_taken"]
    })
    
    return state


def hitl_node(state: WorkflowState, auto_approve: bool = None) -> WorkflowState:
    """
    Lab 18: HITL Node with CLI pause for human approval.
    
    Args:
        state: Workflow state
        auto_approve: If True, auto-approve without waiting (for testing)
    """
    company_id = state["company_id"]
    node_start = datetime.now()
    
    print(f"\n{'='*70}")
    print(f"👤 HITL NODE: {company_id}")
    print(f"{'='*70}")
    print(f"   ⏸️  Workflow paused for human review")
    print(f"\n   📊 Risk Summary:")
    print(f"      Risk keywords: {', '.join(state.get('risk_keywords', [])[:5])}")
    if len(state.get('risk_keywords', [])) > 5:
        print(f"      ... and {len(state.get('risk_keywords', [])) - 5} more")
    print(f"      Dashboard score: {state.get('dashboard_score', 0):.1f}/100")
    print(f"      Company: {company_id}")
    
    # Lab 18: CLI pause for human approval
    # Check auto_approve from environment variable or parameter
    if auto_approve is None:
        auto_approve = os.getenv('HITL_AUTO_APPROVE', 'false').lower() == 'true'
    
    if auto_approve:
        approval = "y"
        print(f"\n   [AUTO-APPROVE MODE] Continuing automatically...")
    else:
        # CLI mode - interactive input
        print(f"\n   {'─'*70}")
        print(f"   ⚠️  HUMAN REVIEW REQUIRED")
        print(f"   {'─'*70}")
        print(f"   This workflow has detected risks that require human review.")
        print(f"   Please review the information above and decide:")
        print(f"\n   Options:")
        print(f"     [y] Approve - Continue workflow")
        print(f"     [n] Reject - Stop workflow")
        print(f"     [s] Skip HITL - Continue without approval (not recommended)")
        print(f"\n   {'─'*70}")
        
        while True:
            try:
                approval = input("\n   Enter your decision (y/n/s): ").strip().lower()
                if approval in ['y', 'yes', 'n', 'no', 's', 'skip']:
                    break
                print("   ⚠️  Invalid input. Please enter 'y', 'n', or 's'")
            except (EOFError, KeyboardInterrupt):
                print("\n   ⚠️  Input interrupted. Defaulting to rejection.")
                approval = "n"
                break
    
    # Process approval decision
    if auto_approve or approval in ['y', 'yes']:
        state["metadata"]["hitl_approved"] = True
        state["metadata"]["hitl_decision"] = "approved"
        if not auto_approve:
            print(f"\n   ✅ Human approved - continuing workflow")
    elif approval in ['s', 'skip']:
        state["metadata"]["hitl_approved"] = True
        state["metadata"]["hitl_decision"] = "skipped"
        print(f"\n   ⚠️  HITL skipped - continuing workflow (not recommended)")
    else:
        state["metadata"]["hitl_approved"] = False
        state["metadata"]["hitl_decision"] = "rejected"
        state["error"] = "Workflow rejected by human reviewer"
        print(f"\n   ❌ Human rejected - stopping workflow")
    
    state["metadata"]["hitl_timestamp"] = node_start.isoformat()
    state["metadata"]["hitl_decision_timestamp"] = datetime.now().isoformat()
    
    # Lab 18: Track execution path
    state["execution_path"].append({
        "node": "hitl",
        "start_time": node_start.isoformat(),
        "end_time": datetime.now().isoformat(),
        "status": "completed",
        "decision": state["metadata"].get("hitl_decision", "unknown"),
        "approved": state["metadata"].get("hitl_approved", False)
    })
    
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
        
        # Configure checkpointer for state persistence
        checkpointer = MemorySaver()
        compiled = workflow.compile(checkpointer=checkpointer)
        
        return compiled
    
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
                    # Pass auto_approve from workflow context if available
                    auto_approve = getattr(self, '_auto_approve', False)
                    state = hitl_node(state, auto_approve=auto_approve)
                
                return state
            
            def set_auto_approve(self, value: bool):
                """Set auto-approve mode for HITL."""
                self._auto_approve = value
        
        return FallbackWorkflow()


# ============================================================
# Lab 18: Visualization Functions
# ============================================================

def generate_mermaid_diagram(execution_path: List[Dict], branch_taken: str) -> str:
    """
    Generate Mermaid diagram of execution path.
    
    Args:
        execution_path: List of node execution records
        branch_taken: "normal" or "hitl"
        
    Returns:
        Mermaid diagram as string
    """
    nodes = []
    edges = []
    
    # Define node styles
    node_styles = {
        "planner": "style planner fill:#e1f5ff",
        "data_generator": "style data_generator fill:#fff4e1",
        "evaluator": "style evaluator fill:#e8f5e9",
        "risk_detector": "style risk_detector fill:#fff3e0",
        "hitl": "style hitl fill:#fce4ec"
    }
    
    # Add nodes
    for step in execution_path:
        node_name = step["node"]
        status = step.get("status", "completed")
        status_icon = "✅" if status == "completed" else "❌"
        
        # Add node label with status
        label = f"{node_name}\n{status_icon} {status}"
        
        # Add metadata if available
        if node_name == "evaluator" and "score" in step:
            label += f"\nScore: {step['score']:.1f}"
        elif node_name == "risk_detector" and "risks_found" in step:
            label += f"\nRisks: {step['risks_found']}"
        elif node_name == "hitl" and "decision" in step:
            label += f"\nDecision: {step['decision']}"
        
        nodes.append(f'    {node_name}["{label}"]')
    
    # Add edges
    node_names = [step["node"] for step in execution_path]
    for i in range(len(node_names) - 1):
        from_node = node_names[i]
        to_node = node_names[i + 1]
        edges.append(f"    {from_node} --> {to_node}")
    
    # Add branch visualization
    if branch_taken == "hitl" and "risk_detector" in node_names:
        # Add conditional branch note
        edges.append('    risk_detector -->|"Risks detected"| hitl')
    
    # Build diagram
    diagram = "```mermaid\ngraph TD\n"
    diagram += "\n".join(nodes) + "\n"
    diagram += "\n".join(edges) + "\n"
    
    # Add styles
    for style in node_styles.values():
        diagram += f"    {style}\n"
    
    diagram += "```"
    
    return diagram


def save_execution_trace(state: Dict, output_dir: Path = None) -> Path:
    """
    Save execution trace with Mermaid diagram.
    
    Args:
        state: Final workflow state
        output_dir: Directory to save trace (default: docs/)
        
    Returns:
        Path to saved trace file
    """
    if output_dir is None:
        output_dir = project_root / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    execution_path = state.get("execution_path", [])
    branch_taken = state.get("branch_taken", "unknown")
    
    # Generate Mermaid diagram
    mermaid_diagram = generate_mermaid_diagram(execution_path, branch_taken)
    
    # Create trace document
    trace_content = f"""# Execution Trace - {state.get('company_id', 'unknown')}

**Run ID:** {state.get('metadata', {}).get('run_id', 'N/A')}  
**Company:** {state.get('company_id', 'unknown')}  
**Branch Taken:** {branch_taken}  
**Timestamp:** {datetime.now().isoformat()}

## Execution Path

### Nodes Executed

"""
    
    for i, step in enumerate(execution_path, 1):
        trace_content += f"### {i}. {step['node'].replace('_', ' ').title()}\n\n"
        trace_content += f"- **Status:** {step.get('status', 'unknown')}\n"
        trace_content += f"- **Start Time:** {step.get('start_time', 'N/A')}\n"
        trace_content += f"- **End Time:** {step.get('end_time', 'N/A')}\n"
        
        if 'score' in step:
            trace_content += f"- **Dashboard Score:** {step['score']:.1f}/100\n"
        if 'risks_found' in step:
            trace_content += f"- **Risks Found:** {step['risks_found']}\n"
        if 'branch' in step:
            trace_content += f"- **Branch:** {step['branch']}\n"
        if 'decision' in step:
            trace_content += f"- **HITL Decision:** {step['decision']}\n"
            trace_content += f"- **Approved:** {step.get('approved', False)}\n"
        
        trace_content += "\n"
    
    trace_content += f"""
## Decision Path

**Branch Taken:** `{branch_taken}`

"""
    
    if branch_taken == "hitl":
        hitl_decision = state.get('metadata', {}).get('hitl_decision', 'unknown')
        trace_content += f"""
### HITL Review

- **Decision:** {hitl_decision}
- **Approved:** {state.get('metadata', {}).get('hitl_approved', False)}
- **Risk Keywords:** {', '.join(state.get('risk_keywords', []))}
- **Dashboard Score:** {state.get('dashboard_score', 0):.1f}/100

"""
    else:
        trace_content += """
### Normal Flow

No risks detected. Workflow completed without HITL intervention.

"""
    
    trace_content += f"""
## Visualization

{mermaid_diagram}

## Complete State

```json
{json.dumps(state, indent=2, default=str)}
```
"""
    
    # Save trace file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"execution_trace_{state.get('company_id', 'unknown')}_{timestamp}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(trace_content)
    
    print(f"\n📊 Execution trace saved: {filepath}")
    
    return filepath


# ============================================================
# Main Execution
# ============================================================

async def run_workflow(company_id: str, auto_approve: bool = False) -> Dict:
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
        "execution_path": [],  # Lab 18: Initialize execution path
        "metadata": {
            "run_id": str(uuid.uuid4())
        }
    }
    
    # Build and run workflow
    workflow = build_workflow_graph()
    
    # Set auto-approve for fallback workflow
    if hasattr(workflow, 'set_auto_approve'):
        workflow.set_auto_approve(auto_approve)
    
    # Set auto_approve environment variable for hitl_node
    os.environ['HITL_AUTO_APPROVE'] = str(auto_approve).lower()
    
    # LangGraph checkpointer requires thread_id in config
    config = {"configurable": {"thread_id": f"workflow_{company_id}_{initial_state['metadata']['run_id']}"}}
    
    final_state = await workflow.ainvoke(initial_state, config=config)
    
    # Lab 18: Save execution trace
    if final_state.get("execution_path"):
        trace_path = save_execution_trace(final_state)
        final_state["metadata"]["trace_file"] = str(trace_path)
    
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
    import uuid as uuid_module
    
    parser = argparse.ArgumentParser(description="Run due diligence workflow")
    parser.add_argument("--company", type=str, default="anthropic", help="Company ID to analyze")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve HITL without waiting (for testing)")
    args = parser.parse_args()
    
    result = asyncio.run(run_workflow(args.company, auto_approve=args.auto_approve))
    
    # Print branch taken (checkpoint requirement)
    print(f"\n{'='*70}")
    print(f"✅ CHECKPOINT: Branch taken = {result.get('branch_taken', 'unknown')}")
    if result.get('execution_path'):
        print(f"📊 Execution path: {len(result['execution_path'])} nodes")
    if result.get('metadata', {}).get('trace_file'):
        print(f"📝 Trace saved: {result['metadata']['trace_file']}")
    print(f"{'='*70}\n")

