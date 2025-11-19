"""
Test Individual Tools - Interactive Testing
Run each tool separately to see how it works
FIXED: Properly uses Pydantic models
"""

import os
import sys
import asyncio
from pathlib import Path
import pytest
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.agents.tools import (
    get_latest_structured_payload,
    rag_search_company,
    report_layoff_signal,
    PayloadRequest,
    RAGSearchRequest,
    LayoffSignal
)
import json


@pytest.mark.asyncio
@patch('builtins.input', side_effect=['anthropic'])
async def test_tool_1_payload(mock_input):
    """Test Tool 1: Get Company Payload"""
    print("=" * 70)
    print("🔧 TOOL 1: get_latest_structured_payload()")
    print("=" * 70)
    print("\nWhat it does: Retrieves structured company data from JSON files")
    print("Use cases: Get funding, valuation, team info, products\n")
    
    company = input("Enter company name (e.g., anthropic, openai, cohere): ").strip()
    
    print(f"\n📡 Calling: get_latest_structured_payload(PayloadRequest(company_id='{company}'))\n")
    
    try:
        # Create Pydantic request object
        request = PayloadRequest(company_id=company)
        result = await get_latest_structured_payload(request)
        
        # Convert to dict for display
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        
        if not result.success or result_dict.get("error"):
            print(f"❌ Error: {result_dict.get('error', 'Unknown error')}")
        else:
            print("✅ SUCCESS! Retrieved data:\n")
            
            # Pretty print payload
            if result.payload:
                print(json.dumps(result.payload, indent=2))
                
                # Show key fields
                print("\n" + "=" * 70)
                print("📊 KEY METRICS:")
                print("=" * 70)
                if result.payload.get('valuation'):
                    print(f"💰 Valuation: ${result.payload['valuation']:,}")
                if result.payload.get('total_funding'):
                    print(f"💵 Total Funding: ${result.payload['total_funding']:,}")
                if result.payload.get('company_name'):
                    print(f"🏢 Company: {result.payload['company_name']}")
                if result.payload.get('headquarters'):
                    hq = result.payload['headquarters']
                    if isinstance(hq, dict):
                        print(f"📍 HQ: {hq.get('city', 'N/A')}, {hq.get('country', 'N/A')}")
                    else:
                        print(f"📍 HQ: {hq}")
                if result.payload.get('ceo'):
                    print(f"👤 CEO: {result.payload['ceo']}")
            else:
                print(json.dumps(result_dict, indent=2))
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


@pytest.mark.asyncio
@patch('builtins.input', side_effect=['anthropic', 'What does this company do?'])
async def test_tool_2_rag(mock_input):
    """Test Tool 2: RAG Search"""
    print("=" * 70)
    print("🔧 TOOL 2: rag_search_company()")
    print("=" * 70)
    print("\nWhat it does: Semantic search through company documents")
    print("Use cases: Find specific info, answer questions about company\n")
    
    company = input("Enter company name: ").strip()
    query = input("Enter your question: ").strip()
    
    print(f"\n📡 Calling: rag_search_company(RAGSearchRequest(company_id='{company}', query='{query}'))\n")
    
    try:
        # Create Pydantic request object
        request = RAGSearchRequest(company_id=company, query=query)
        result = await rag_search_company(request)
        
        # Convert to dict for display
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        
        if not result.success or result_dict.get("error"):
            print(f"❌ Error: {result_dict.get('error', 'Unknown error')}")
        else:
            print("✅ SUCCESS! Found information:\n")
            
            # Show results
            if result.results:
                print("=" * 70)
                print(f"📚 FOUND {len(result.results)} RELEVANT SNIPPETS:")
                print("=" * 70)
                for i, res in enumerate(result.results, 1):
                    print(f"\n[{i}] Score: {res.get('score', 0):.3f}")
                    text = res.get('text', '')
                    # Show first 300 chars
                    print(f"Text: {text[:300]}...")
                    if len(text) > 300:
                        print(f"      (truncated, {len(text)} total chars)")
            else:
                print("No results found.")
                print("\nFull response:")
                print(json.dumps(result_dict, indent=2))
                    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


@pytest.mark.asyncio
@patch('builtins.input', side_effect=['test_company', 'layoff', 'Test layoff', 'medium'])
async def test_tool_3_risk(mock_input):
    """Test Tool 3: Report Risk Signal"""
    print("=" * 70)
    print("🔧 TOOL 3: report_layoff_signal()")
    print("=" * 70)
    print("\nWhat it does: Log risk signals to JSON files")
    print("Use cases: Track layoffs, breaches, funding issues\n")
    
    company = input("Enter company name: ").strip()
    risk_type = input("Risk type (layoff/breach/funding/other): ").strip()
    description = input("Description: ").strip()
    severity = input("Severity (critical/high/medium/low): ").strip().lower()
    
    print(f"\n📡 Calling: report_layoff_signal(LayoffSignal(...))\n")
    
    try:
        # Create Pydantic signal object
        signal = LayoffSignal(
            company_id=company,
            signal_type=risk_type,
            description=description,
            severity=severity
        )
        
        result = await report_layoff_signal(signal)
        
        # Convert to dict for display
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        
        if not result.success:
            print(f"❌ Error: {result_dict.get('message', 'Unknown error')}")
        else:
            print("✅ SUCCESS! Risk logged:\n")
            print(json.dumps(result_dict, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def main_menu():
    """Interactive menu for testing tools."""
    print("\n" + "=" * 70)
    print("🧪 INDIVIDUAL TOOL TESTER")
    print("=" * 70)
    print("\nTest each tool separately to understand how it works!\n")
    
    while True:
        print("\n📋 MENU:")
        print("  1. Test Tool 1: Get Company Payload (get_latest_structured_payload)")
        print("  2. Test Tool 2: RAG Search (rag_search_company)")
        print("  3. Test Tool 3: Report Risk Signal (report_layoff_signal)")
        print("  4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            await test_tool_1_payload()
        elif choice == "2":
            await test_tool_2_rag()
        elif choice == "3":
            await test_tool_3_risk()
        elif choice == "4":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main_menu())