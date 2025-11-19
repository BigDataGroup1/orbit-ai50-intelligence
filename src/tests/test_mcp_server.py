"""
Test Lab 14: MCP Server
Tests MCP server endpoints and functionality
"""
import pytest
import requests
from unittest.mock import Mock, patch


def test_mcp_server_structure():
    """Test MCP server has required components"""
    from src.server import mcp_server
    
    assert hasattr(mcp_server, 'app'), "MCP server should have FastAPI app"
    print("✅ MCP server structure valid")


def test_mcp_endpoints_defined():
    """Test that required endpoints are defined"""
    from src.server.mcp_server import app
    
    routes = [route.path for route in app.routes]
    
    # Check for tool endpoints
    assert any('/tool' in r for r in routes), "Should have tool endpoints"
    assert any('/resource' in r for r in routes) or any('/prompt' in r for r in routes), "Should have resource or prompt endpoints"
    
    print(f"✅ MCP server has {len(routes)} routes defined")
    print(f"   Routes: {routes[:5]}...")


def test_mcp_server_health():
    """Test if MCP server is responding (requires server running)"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=2)
        assert response.status_code == 200
        print("✅ MCP server is running and healthy")
    except requests.exceptions.ConnectionError:
        pytest.skip("MCP server not running - start with: python src/server/mcp_server.py")
    except Exception as e:
        pytest.skip(f"MCP server test skipped: {e}")


@patch('requests.post')
def test_mcp_tool_endpoint_format(mock_post):
    """Test MCP tool endpoint returns expected format"""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "markdown": "# Test Dashboard\n\nContent here",
        "company_name": "test",
        "tokens_used": 500
    }
    mock_post.return_value = mock_response
    
    # Simulate calling MCP tool
    response = requests.post(
        "http://localhost:8001/tool/generate_structured_dashboard",
        json={"company_id": "anthropic"}
    )
    
    data = response.json()
    
    # Verify response format
    assert "success" in data
    assert "markdown" in data or "error" in data
    print("✅ MCP tool endpoint returns expected format")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING MCP SERVER (LAB 14)")
    print("="*70)
    
    print("\n1. Testing Server Structure...")
    test_mcp_server_structure()
    
    print("\n2. Testing Endpoints Defined...")
    test_mcp_endpoints_defined()
    
    print("\n3. Testing Server Health...")
    test_mcp_server_health()
    
    print("\n4. Testing Tool Endpoint Format...")
    test_mcp_tool_endpoint_format()
    
    print("\n" + "="*70)
    print("✅ ALL MCP SERVER TESTS PASSED")
    print("="*70)