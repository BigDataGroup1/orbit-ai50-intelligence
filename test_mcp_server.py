"""
Test script for MCP Server (Lab 14)
Tests all MCP endpoints
"""
import requests
import json
from pathlib import Path

# MCP Server URL (local)
MCP_URL = "http://localhost:8001"

def test_root():
    """Test root endpoint."""
    print("\n" + "="*70)
    print("TEST 1: Root Endpoint")
    print("="*70)
    
    try:
        response = requests.get(f"{MCP_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_health():
    """Test health check."""
    print("\n" + "="*70)
    print("TEST 2: Health Check")
    print("="*70)
    
    try:
        response = requests.get(f"{MCP_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_resource_companies():
    """Test companies resource."""
    print("\n" + "="*70)
    print("TEST 3: Resource - AI50 Companies")
    print("="*70)
    
    try:
        response = requests.get(f"{MCP_URL}/resource/ai50/companies")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Total Companies: {data.get('total')}")
        print(f"Sample: {data.get('companies', [])[:5]}")
        return response.status_code == 200 and data.get('success')
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_prompt_rag():
    """Test RAG prompt."""
    print("\n" + "="*70)
    print("TEST 4: Prompt - PE Dashboard (RAG)")
    print("="*70)
    
    try:
        response = requests.get(f"{MCP_URL}/prompt/pe-dashboard?prompt_type=rag")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Prompt Type: {data.get('prompt_type')}")
        content = data.get('content', '')
        print(f"Content Length: {len(content)} chars")
        print(f"First 200 chars: {content[:200]}...")
        return response.status_code == 200 and data.get('success')
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_prompt_structured():
    """Test structured prompt."""
    print("\n" + "="*70)
    print("TEST 5: Prompt - PE Dashboard (Structured)")
    print("="*70)
    
    try:
        response = requests.get(f"{MCP_URL}/prompt/pe-dashboard?prompt_type=structured")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Prompt Type: {data.get('prompt_type')}")
        content = data.get('content', '')
        print(f"Content Length: {len(content)} chars")
        print(f"First 200 chars: {content[:200]}...")
        return response.status_code == 200 and data.get('success')
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_tool_structured():
    """Test structured dashboard tool."""
    print("\n" + "="*70)
    print("TEST 6: Tool - Generate Structured Dashboard")
    print("="*70)
    
    try:
        payload = {"company_id": "anthropic"}
        response = requests.post(
            f"{MCP_URL}/tool/generate_structured_dashboard",
            json=payload
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            print(f"Company: {data.get('company_name')}")
            print(f"Tokens Used: {data.get('tokens_used')}")
            markdown = data.get('markdown', '')
            print(f"Dashboard Length: {len(markdown)} chars")
            print(f"First 300 chars: {markdown[:300]}...")
        else:
            print(f"Error: {data.get('error')}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_tool_rag():
    """Test RAG dashboard tool."""
    print("\n" + "="*70)
    print("TEST 7: Tool - Generate RAG Dashboard")
    print("="*70)
    
    try:
        payload = {"company_name": "Anthropic", "max_chunks": 10}
        response = requests.post(
            f"{MCP_URL}/tool/generate_rag_dashboard",
            json=payload
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            print(f"Company: {data.get('company_name')}")
            print(f"Chunks Used: {data.get('chunks_used')}")
            dashboard = data.get('dashboard', '')
            print(f"Dashboard Length: {len(dashboard)} chars")
            print(f"First 300 chars: {dashboard[:300]}...")
        else:
            print(f"Error: {data.get('error')}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("MCP SERVER TEST SUITE - LAB 14")
    print("="*70)
    print(f"\nTesting MCP Server at: {MCP_URL}")
    print("Make sure the server is running: python src/server/mcp_server.py")
    
    results = []
    
    # Run tests
    results.append(("Root", test_root()))
    results.append(("Health", test_health()))
    results.append(("Resource: Companies", test_resource_companies()))
    results.append(("Prompt: RAG", test_prompt_rag()))
    results.append(("Prompt: Structured", test_prompt_structured()))
    results.append(("Tool: Structured Dashboard", test_tool_structured()))
    results.append(("Tool: RAG Dashboard", test_tool_rag()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! MCP Server is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.")


if __name__ == "__main__":
    main()

