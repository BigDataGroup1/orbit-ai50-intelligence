"""
Orbit Agentic Dashboard - Local Execution Script
Invokes MCP + Agentic workflow for all AI 50 companies

This script can run locally (standalone) or be used as an Airflow DAG task.

Usage:
    # Run locally for all companies
    python orbit_agentic_dashboard_local.py
    
    # Run for specific companies only
    python orbit_agentic_dashboard_local.py --limit 5
    
    # Run with auto-approve HITL
    python orbit_agentic_dashboard_local.py --auto-approve
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from google.cloud import storage
import argparse
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-g1-2025'

# Local paths
DATA_DIR = project_root / "data"
SEED_FILE = DATA_DIR / "forbes_ai50_seed.json"


def get_ai50_companies(limit: Optional[int] = None) -> List[Dict]:
    """
    Get list of all AI 50 companies.
    
    Args:
        limit: Optional limit on number of companies to process
        
    Returns:
        List of company dictionaries with company_id and company_name
    """
    logger.info("="*70)
    logger.info("Getting AI 50 Companies List")
    logger.info("="*70)
    
    # Try local seed file first
    if not SEED_FILE.exists():
        logger.info("Seed file not found locally. Downloading from GCS...")
        try:
            client = storage.Client(project=GCP_PROJECT_ID)
            bucket = client.bucket(GCS_PROCESSED_BUCKET)
            blob = bucket.blob('data/forbes_ai50_seed.json')
            
            SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(SEED_FILE))
            logger.info("✅ Downloaded seed file from GCS")
        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            raise
    
    # Load companies
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        companies_data = json.load(f)
    
    # Extract and normalize company IDs
    companies = []
    for company in companies_data:
        company_name = company.get('company_name', '')
        if company_name:
            # Normalize to company_id format
            company_id = company_name.lower().replace(' ', '_').replace('.', '').replace('-', '_')
            companies.append({
                'company_id': company_id,
                'company_name': company_name
            })
    
    # Apply limit if specified
    if limit:
        companies = companies[:limit]
        logger.info(f"Limited to first {limit} companies")
    
    logger.info(f"✅ Found {len(companies)} companies to process")
    
    return companies


async def run_workflow_for_company(company_id: str, company_name: str, auto_approve: bool = True) -> Dict:
    """
    Run agentic workflow for a single company.
    
    Args:
        company_id: Company identifier
        company_name: Company display name
        auto_approve: Auto-approve HITL without waiting
        
    Returns:
        Workflow result dictionary
    """
    try:
        from src.workflows.due_diligence_graph import run_workflow
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {company_name} ({company_id})")
        logger.info(f"{'='*70}")
        
        result = await run_workflow(company_id, auto_approve=auto_approve)
        
        # Extract key info
        workflow_result = {
            'company_id': company_id,
            'company_name': company_name,
            'success': not result.get('error'),
            'branch_taken': result.get('branch_taken', 'unknown'),
            'dashboard_score': result.get('dashboard_score', 0),
            'risks_detected': len(result.get('risk_keywords', [])),
            'requires_hitl': result.get('requires_hitl', False),
            'error': result.get('error'),
            'dashboard_file': result.get('metadata', {}).get('dashboard_file'),
            'trace_file': result.get('metadata', {}).get('trace_file'),
        }
        
        if workflow_result['success']:
            logger.info(f"  ✅ Success: {company_name}")
            logger.info(f"     Branch: {workflow_result['branch_taken']}, Score: {workflow_result['dashboard_score']:.1f}/100")
        else:
            logger.warning(f"  ⚠️  Failed: {company_name} - {workflow_result.get('error', 'Unknown error')}")
        
        return workflow_result
    
    except Exception as e:
        logger.error(f"  ❌ Error processing {company_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'company_id': company_id,
            'company_name': company_name,
            'success': False,
            'error': str(e)
        }


async def process_all_companies(companies: List[Dict], auto_approve: bool = True) -> List[Dict]:
    """
    Process all companies sequentially.
    
    Args:
        companies: List of company dictionaries
        auto_approve: Auto-approve HITL without waiting
        
    Returns:
        List of workflow results
    """
    logger.info("="*70)
    logger.info(f"Running Agentic Workflow for {len(companies)} Companies")
    logger.info("="*70)
    
    results = []
    
    for i, company_info in enumerate(companies, 1):
        company_id = company_info['company_id']
        company_name = company_info['company_name']
        
        result = await run_workflow_for_company(company_id, company_name, auto_approve)
        results.append(result)
        
        # Small delay between companies to avoid rate limits
        if i < len(companies):
            await asyncio.sleep(2)
    
    return results


def upload_dashboards_to_gcs(results: List[Dict]) -> int:
    """
    Upload generated dashboards and traces to GCS.
    
    Args:
        results: List of workflow results
        
    Returns:
        Number of files uploaded
    """
    logger.info("="*70)
    logger.info("Uploading Dashboards to GCS")
    logger.info("="*70)
    
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        upload_count = 0
        
        # Upload workflow dashboards
        dashboard_dir = DATA_DIR / "dashboards" / "workflow"
        if dashboard_dir.exists():
            logger.info("Uploading workflow dashboards...")
            for file_path in dashboard_dir.glob('*.md'):
                blob_name = f"data/dashboards/workflow/{file_path.name}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
                logger.info(f"  ✅ Uploaded: {file_path.name}")
        
        # Upload execution traces
        trace_dir = project_root / "docs"
        if trace_dir.exists():
            logger.info("Uploading execution traces...")
            for file_path in trace_dir.glob('execution_trace_*.md'):
                blob_name = f"data/execution_traces/{file_path.name}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
        
        logger.info(f"✅ Total files uploaded: {upload_count}")
        
        return upload_count
    
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


def save_local_report(results: List[Dict], upload_count: int) -> Path:
    """
    Save report locally.
    
    Args:
        results: List of workflow results
        upload_count: Number of files uploaded to GCS
        
    Returns:
        Path to saved report file
    """
    # Calculate statistics
    successful = sum(1 for r in results if r.get('success'))
    failed = len(results) - successful
    
    total_score = sum(r.get('dashboard_score', 0) for r in results if r.get('success'))
    avg_score = total_score / successful if successful > 0 else 0
    
    hitl_count = sum(1 for r in results if r.get('requires_hitl'))
    normal_count = successful - hitl_count
    
    total_risks = sum(r.get('risks_detected', 0) for r in results)
    
    report = {
        'script': 'orbit_agentic_dashboard_local',
        'execution_date': datetime.now().isoformat(),
        'status': 'SUCCESS',
        'summary': {
            'total_companies': len(results),
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / len(results) * 100) if results else 0
        },
        'workflow_stats': {
            'avg_dashboard_score': round(avg_score, 2),
            'hitl_required': hitl_count,
            'normal_flow': normal_count,
            'total_risks_detected': total_risks
        },
        'dashboards_uploaded': upload_count,
        'completed_at': datetime.now().isoformat(),
        'results': results
    }
    
    # Save locally
    reports_dir = DATA_DIR / "airflow_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = reports_dir / f"agentic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info("="*70)
    logger.info("📊 AGENTIC DASHBOARD REPORT")
    logger.info("="*70)
    logger.info(f"✅ Report saved: {report_file}")
    logger.info(f"📊 Total companies: {len(results)}")
    logger.info(f"✅ Successful: {successful}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📈 Avg dashboard score: {avg_score:.1f}/100")
    logger.info(f"🚨 HITL required: {hitl_count}")
    logger.info(f"📁 Dashboards uploaded: {upload_count}")
    logger.info("="*70)
    
    # Also save to GCS
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        blob_name = f"airflow_reports/agentic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(report_file))
        logger.info(f"✅ Report also uploaded to GCS: gs://{GCS_PROCESSED_BUCKET}/{blob_name}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to upload report to GCS: {e}")
    
    return report_file


async def main(limit: Optional[int] = None, auto_approve: bool = True):
    """
    Main execution function.
    
    Args:
        limit: Optional limit on number of companies to process
        auto_approve: Auto-approve HITL without waiting
    """
    # Use ASCII-safe output for Windows
    print("\n" + "="*70)
    print("ORBIT AGENTIC DASHBOARD - LOCAL EXECUTION")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Limit: {limit if limit else 'All companies'}")
    print(f"Auto-approve HITL: {auto_approve}")
    print("="*70 + "\n")
    
    # Step 1: Get companies
    companies = get_ai50_companies(limit=limit)
    
    if not companies:
        logger.error("No companies found!")
        return
    
    # Step 2: Process all companies
    results = await process_all_companies(companies, auto_approve=auto_approve)
    
    # Step 3: Upload dashboards to GCS
    upload_count = upload_dashboards_to_gcs(results)
    
    # Step 4: Generate and save report
    report_file = save_local_report(results, upload_count)
    
    print("\n" + "="*70)
    print("✅ EXECUTION COMPLETE")
    print("="*70)
    print(f"📄 Report saved: {report_file}")
    print("="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run agentic dashboard workflow for all AI 50 companies (local execution)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of companies to process (for testing)"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=True,
        help="Auto-approve HITL without waiting (default: True)"
    )
    parser.add_argument(
        "--no-auto-approve",
        dest="auto_approve",
        action="store_false",
        help="Require manual HITL approval"
    )
    
    args = parser.parse_args()
    
    # Run main function
    asyncio.run(main(limit=args.limit, auto_approve=args.auto_approve))

