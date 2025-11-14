"""
Comprehensive Tool Test - Run on ALL Companies
Generates test_results.json in data/ folder
"""

import asyncio
import json
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agents.tools import (
    get_latest_structured_payload,
    rag_search_company,
    list_available_companies,
    PayloadRequest,
    RAGSearchRequest
)


async def test_all_companies():
    """Run all tools on all companies and generate comprehensive results."""
    
    print("\n" + "="*70)
    print("COMPREHENSIVE TOOL TEST - ALL COMPANIES")
    print("="*70 + "\n")
    
    # Get all companies
    companies = list_available_companies()
    print(f"📊 Found {len(companies)} companies to test\n")
    
    results = {
        "test_run_timestamp": datetime.now().isoformat(),
        "total_companies": len(companies),
        "tests_per_company": 2,  # Tool 1 and Tool 2
        "companies": []
    }
    
    # Test each company
    for i, company_id in enumerate(companies, 1):
        print(f"[{i}/{len(companies)}] Testing {company_id}...")
        
        company_result = {
            "company_id": company_id,
            "test_1_payload": {},
            "test_2_rag_search": {}
        }
        
        # Test 1: Get Payload
        try:
            payload_req = PayloadRequest(company_id=company_id)
            payload_resp = await get_latest_structured_payload(payload_req)
            
            company_result["test_1_payload"] = {
                "success": payload_resp.success,
                "has_data": payload_resp.payload is not None,
                "payload_size_bytes": len(json.dumps(payload_resp.payload)) if payload_resp.payload else 0,
                "error": payload_resp.error
            }
            
            if payload_resp.success:
                print(f"  ✅ Tool 1: Payload retrieved ({company_result['test_1_payload']['payload_size_bytes']} bytes)")
            else:
                print(f"  ❌ Tool 1: {payload_resp.error}")
                
        except Exception as e:
            company_result["test_1_payload"] = {
                "success": False,
                "error": str(e)
            }
            print(f"  ❌ Tool 1: Exception - {e}")
        
        # Test 2: RAG Search
        try:
            rag_req = RAGSearchRequest(
                company_id=company_id,
                query="What does this company do?"
            )
            rag_resp = await rag_search_company(rag_req)
            
            company_result["test_2_rag_search"] = {
                "success": rag_resp.success,
                "results_count": len(rag_resp.results),
                "has_results": len(rag_resp.results) > 0,
                "error": rag_resp.error
            }
            
            if rag_resp.success and rag_resp.results:
                print(f"  ✅ Tool 2: RAG search returned {len(rag_resp.results)} results")
            else:
                print(f"  ⚠️  Tool 2: {rag_resp.error or 'No results'}")
                
        except Exception as e:
            company_result["test_2_rag_search"] = {
                "success": False,
                "error": str(e)
            }
            print(f"  ❌ Tool 2: Exception - {e}")
        
        results["companies"].append(company_result)
        print()
    
    # Generate summary statistics
    results["summary"] = {
        "tool_1_success_count": sum(1 for c in results["companies"] if c["test_1_payload"]["success"]),
        "tool_2_success_count": sum(1 for c in results["companies"] if c["test_2_rag_search"]["success"]),
        "tool_1_success_rate": sum(1 for c in results["companies"] if c["test_1_payload"]["success"]) / len(companies) * 100,
        "tool_2_success_rate": sum(1 for c in results["companies"] if c["test_2_rag_search"]["success"]) / len(companies) * 100,
        "companies_with_both_working": sum(1 for c in results["companies"] 
                                           if c["test_1_payload"]["success"] and c["test_2_rag_search"]["success"])
    }
    
    # Save results
    actual_root = project_root.parent if project_root.name == "src" else project_root
    output_file = actual_root / "data" / "test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, indent=2, fp=f)
    
    # Print summary
    print("="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    print(f"Total companies tested: {results['total_companies']}")
    print(f"\nTool 1 (Get Payload):")
    print(f"  Success: {results['summary']['tool_1_success_count']}/{len(companies)} ({results['summary']['tool_1_success_rate']:.1f}%)")
    print(f"\nTool 2 (RAG Search):")
    print(f"  Success: {results['summary']['tool_2_success_count']}/{len(companies)} ({results['summary']['tool_2_success_rate']:.1f}%)")
    print(f"\nCompanies with both tools working: {results['summary']['companies_with_both_working']}/{len(companies)}")
    print(f"\n✅ Results saved to: {output_file}")
    print("="*70 + "\n")
    
    return results


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_all_companies())