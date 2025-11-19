"""
Unit tests for Due Diligence Workflow Graph (Lab 17)
Tests both normal and HITL branches.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.workflows.due_diligence_graph import (
    planner_node,
    data_generator_node,
    evaluator_node,
    risk_detector_node,
    hitl_node,
    run_workflow,
    WorkflowState
)


class TestPlannerNode:
    """Test Planner node."""
    
    def test_planner_creates_plan(self):
        """Test that planner creates a structured plan."""
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": None,
            "payload": None,
            "dashboard_markdown": None,
            "dashboard_score": None,
            "risk_keywords": [],
            "requires_hitl": False,
            "branch_taken": None,
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = planner_node(state)
        
        assert result["plan"] is not None
        assert len(result["plan"]) > 0
        assert "Retrieve company structured payload" in result["plan"][0]
        assert "metadata" in result
        assert "planner_timestamp" in result["metadata"]


class TestDataGeneratorNode:
    """Test Data Generator node."""
    
    @pytest.mark.asyncio
    @patch('src.workflows.due_diligence_graph.get_latest_structured_payload')
    @patch('src.workflows.due_diligence_graph.get_mcp_integration')
    async def test_data_generator_success(self, mock_mcp_class, mock_get_payload):
        """Test successful data generation."""
        # Mock payload response
        mock_payload_resp = Mock()
        mock_payload_resp.success = True
        mock_payload_resp.payload = {"company": "test", "funding": 1000000}
        mock_get_payload.return_value = mock_payload_resp
        
        # Mock MCP integration
        mock_mcp = Mock()
        mock_mcp.is_enabled.return_value = True
        mock_mcp.call_tool.return_value = {
            "success": True,
            "markdown": "# Test Dashboard\n\nContent here",
            "tokens_used": 500
        }
        mock_mcp_class.return_value = mock_mcp
        
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": ["Step 1", "Step 2"],
            "payload": None,
            "dashboard_markdown": None,
            "dashboard_score": None,
            "risk_keywords": [],
            "requires_hitl": False,
            "branch_taken": None,
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = await data_generator_node(state)
        
        assert result["payload"] is not None
        assert result["dashboard_markdown"] is not None
        assert result["error"] is None
        assert "tokens_used" in result["metadata"]


class TestEvaluatorNode:
    """Test Evaluator node."""
    
    def test_evaluator_scores_dashboard(self):
        """Test dashboard scoring."""
        dashboard = """
        # Company Dashboard
        
        ## Company Overview
        Company: Test Corp
        Founded: 2020
        Headquarters: San Francisco
        
        ## Funding
        Total Raised: $10M
        Valuation: $50M
        
        ## Team
        CEO: John Doe
        Employees: 50
        
        ## Products
        - Product A
        - Product B
        
        ## Revenue
        Annual Revenue: $5M
        """
        
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": ["Step 1"],
            "payload": {},
            "dashboard_markdown": dashboard,
            "dashboard_score": None,
            "risk_keywords": [],
            "requires_hitl": False,
            "branch_taken": None,
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = evaluator_node(state)
        
        assert result["dashboard_score"] is not None
        assert 0 <= result["dashboard_score"] <= 100
        assert result["dashboard_score"] > 0  # Should score something
        assert "evaluation_timestamp" in result["metadata"]
    
    def test_evaluator_handles_empty_dashboard(self):
        """Test evaluator handles missing dashboard."""
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": ["Step 1"],
            "payload": {},
            "dashboard_markdown": None,
            "dashboard_score": None,
            "risk_keywords": [],
            "requires_hitl": False,
            "branch_taken": None,
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = evaluator_node(state)
        
        assert result["dashboard_score"] == 0.0
        assert result["error"] is not None


class TestRiskDetectorNode:
    """Test Risk Detector node - covers both branches."""
    
    def test_risk_detector_normal_branch(self):
        """Test normal branch when no risks detected."""
        dashboard = """
        # Company Dashboard
        
        Company is doing well.
        Strong growth and positive outlook.
        """
        
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": ["Step 1"],
            "payload": {"status": "healthy"},
            "dashboard_markdown": dashboard,
            "dashboard_score": 75.0,
            "risk_keywords": [],
            "requires_hitl": False,
            "branch_taken": None,
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = risk_detector_node(state)
        
        assert result["requires_hitl"] is False
        assert result["branch_taken"] == "normal"
        assert len(result["risk_keywords"]) == 0
        assert "risk_detection_timestamp" in result["metadata"]
    
    def test_risk_detector_hitl_branch(self):
        """Test HITL branch when risks detected."""
        dashboard = """
        # Company Dashboard
        
        Company announced layoffs affecting 20% of workforce.
        Recent security breach reported.
        """
        
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": ["Step 1"],
            "payload": {"events": [{"type": "layoff", "title": "Mass layoffs"}]},
            "dashboard_markdown": dashboard,
            "dashboard_score": 60.0,
            "risk_keywords": [],
            "requires_hitl": False,
            "branch_taken": None,
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = risk_detector_node(state)
        
        assert result["requires_hitl"] is True
        assert result["branch_taken"] == "hitl"
        assert len(result["risk_keywords"]) > 0
        assert "layoff" in " ".join(result["risk_keywords"]).lower() or "security" in " ".join(result["risk_keywords"]).lower()
        assert "risk_detection_timestamp" in result["metadata"]
        assert result["metadata"]["risk_count"] > 0


class TestHITLNode:
    """Test HITL node."""
    
    @patch('builtins.input', return_value='y')  # Mock user input
    def test_hitl_node_executes(self, mock_input):
        """Test HITL node execution."""
        state: WorkflowState = {
            "company_id": "test_company",
            "plan": ["Step 1"],
            "payload": {},
            "dashboard_markdown": "Dashboard content",
            "dashboard_score": 60.0,
            "risk_keywords": ["layoff", "downsizing"],
            "requires_hitl": True,
            "branch_taken": "hitl",
            "error": None,
            "metadata": {},
            "execution_path": []
        }
        
        result = hitl_node(state)
        
        assert "hitl_timestamp" in result["metadata"]
        assert result["metadata"]["hitl_approved"] is True


class TestWorkflowIntegration:
    """Integration tests for full workflow."""
    
    @pytest.mark.asyncio
    @patch('src.workflows.due_diligence_graph.get_latest_structured_payload')
    @patch('src.workflows.due_diligence_graph.get_mcp_integration')
    async def test_normal_flow(self, mock_mcp_class, mock_get_payload):
        """Test complete workflow with normal branch (no risks)."""
        # Mock payload
        mock_payload_resp = Mock()
        mock_payload_resp.success = True
        mock_payload_resp.payload = {"company": "test", "status": "healthy"}
        mock_get_payload.return_value = mock_payload_resp
        
        # Mock MCP - return clean dashboard
        mock_mcp = Mock()
        mock_mcp.is_enabled.return_value = True
        mock_mcp.call_tool.return_value = {
            "success": True,
            "markdown": "# Test Company\n\nStrong growth and positive outlook.",
            "tokens_used": 500
        }
        mock_mcp_class.return_value = mock_mcp
        
        result = await run_workflow("test_company", auto_approve=True)
        
        assert result["branch_taken"] == "normal"
        assert result["requires_hitl"] is False
        assert result["dashboard_score"] is not None
        assert result["plan"] is not None
    
    @pytest.mark.asyncio
    @patch('src.workflows.due_diligence_graph.get_latest_structured_payload')
    @patch('src.workflows.due_diligence_graph.get_mcp_integration')
    async def test_hitl_flow(self, mock_mcp_class, mock_get_payload):
        """Test complete workflow with HITL branch (risks detected)."""
        # Mock payload with risk indicators
        mock_payload_resp = Mock()
        mock_payload_resp.success = True
        mock_payload_resp.payload = {
            "company": "test",
            "events": [{"type": "layoff", "title": "Mass layoffs announced"}]
        }
        mock_get_payload.return_value = mock_payload_resp
        
        # Mock MCP - return dashboard with risk keywords
        mock_mcp = Mock()
        mock_mcp.is_enabled.return_value = True
        mock_mcp.call_tool.return_value = {
            "success": True,
            "markdown": "# Test Company\n\nCompany announced layoffs affecting 20% of workforce.",
            "tokens_used": 500
        }
        mock_mcp_class.return_value = mock_mcp
        
        result = await run_workflow("test_company", auto_approve=True)
        
        assert result["branch_taken"] == "hitl"
        assert result["requires_hitl"] is True
        assert len(result["risk_keywords"]) > 0
        assert result["dashboard_score"] is not None
        assert result["plan"] is not None


def run_tests():
    """Run all tests."""
    print("="*70)
    print("TESTING DUE DILIGENCE WORKFLOW GRAPH")
    print("="*70)
    
    # Test Planner
    print("\n1. Testing Planner Node...")
    test_planner = TestPlannerNode()
    test_planner.test_planner_creates_plan()
    print("   ✅ Planner node test passed")
    
    # Test Evaluator
    print("\n2. Testing Evaluator Node...")
    test_evaluator = TestEvaluatorNode()
    test_evaluator.test_evaluator_scores_dashboard()
    test_evaluator.test_evaluator_handles_empty_dashboard()
    print("   ✅ Evaluator node test passed")
    
    # Test Risk Detector (both branches)
    print("\n3. Testing Risk Detector Node (Normal Branch)...")
    test_risk = TestRiskDetectorNode()
    test_risk.test_risk_detector_normal_branch()
    print("   ✅ Normal branch test passed")
    
    print("\n4. Testing Risk Detector Node (HITL Branch)...")
    test_risk.test_risk_detector_hitl_branch()
    print("   ✅ HITL branch test passed")
    
    # Test HITL Node
    print("\n5. Testing HITL Node...")
    test_hitl = TestHITLNode()
    test_hitl.test_hitl_node_executes()
    print("   ✅ HITL node test passed")
    
    # Integration tests
    print("\n6. Testing Workflow Integration (Normal Flow)...")
    test_workflow = TestWorkflowIntegration()
    asyncio.run(test_workflow.test_normal_flow())
    print("   ✅ Normal flow integration test passed")
    
    print("\n7. Testing Workflow Integration (HITL Flow)...")
    asyncio.run(test_workflow.test_hitl_flow())
    print("   ✅ HITL flow integration test passed")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)


if __name__ == "__main__":
    run_tests()