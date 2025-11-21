# Orbit Airflow DAGs

This directory contains the Airflow DAGs for the Orbit AI50 Intelligence project.

## DAGs Overview

### 1. `orbit_initial_load_dag.py`
**Purpose:** Initial data load and payload assembly

**Schedule:** `@once` (manual trigger only)

**Tasks:**
1. Run structured extraction from raw scraped data
2. Assemble payloads from structured data
3. Build initial vector database index
4. Upload results to GCS
5. Generate final report

**Usage:**
- Run once after initial data scraping
- Processes all companies in raw data directory
- Creates structured data, payloads, and vector DB

### 2. `orbit_daily_update_dag.py`
**Purpose:** Incremental updates of snapshots and vector DB

**Schedule:** Daily at 3 AM UTC (`0 3 * * *`)

**Tasks:**
1. Download today's daily scraped data from GCS
2. Update structured data with new snapshots
3. Reassemble payloads with updated data
4. Update vector DB with new chunks
5. Upload updates to GCS
6. Generate daily report

**Usage:**
- Runs automatically daily
- Processes only new/changed data
- Incremental updates (doesn't clear existing data)

### 3. `orbit_agentic_dashboard_dag.py`
**Purpose:** Invokes MCP + Agentic workflow daily for all AI 50 companies

**Schedule:** Daily at 4 AM UTC (`0 4 * * *`)

**Tasks:**
1. Get list of all AI 50 companies
2. Run due diligence workflow for each company
3. Generate dashboards via MCP
4. Upload dashboards to GCS
5. Generate final report

**Usage:**
- Runs automatically daily after daily update
- Processes all AI 50 companies
- Generates agentic dashboards using MCP tools

## Deployment

### Local Testing
```bash
# Copy DAGs to Airflow dags directory
cp airflow/dags/*.py /path/to/airflow/dags/

# Ensure all dependencies are installed in Airflow environment
pip install -r requirements.txt
```

### Cloud Composer (GCP)
```bash
# Upload DAGs to Cloud Composer
gsutil cp airflow/dags/*.py gs://YOUR-COMPOSER-BUCKET/dags/

# Wait 2-3 minutes for DAGs to appear in Airflow UI
```

## Configuration

All DAGs use these environment variables:
- `GCP_PROJECT_ID`: GCP project ID (default: `orbit-ai50-intelligence`)
- `GCS_RAW_BUCKET`: Raw data bucket (default: `orbit-raw-data-g1-2025`)
- `GCS_PROCESSED_BUCKET`: Processed data bucket (default: `orbit-processed-data-g1-2025`)

## Dependencies

DAGs require:
- Python 3.10+
- All packages from `requirements.txt`
- Access to GCS buckets
- OpenAI API key (for structured extraction and workflows)

## File Paths

DAGs expect these paths in Airflow environment:
- DAGs: `/home/airflow/gcs/dags/`
- Data: `/home/airflow/data/`
- Source code: `/home/airflow/gcs/dags/src/`

## Checkpoints

✅ **Initial Load DAG:** Creates structured data, payloads, and vector DB
✅ **Daily Update DAG:** Updates snapshots and vector DB incrementally
✅ **Agentic Dashboard DAG:** Generates dashboards for all AI 50 companies

