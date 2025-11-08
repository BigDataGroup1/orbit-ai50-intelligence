# """
# FastAPI app for RAG search + Structured dashboards - Cloud Run Deployment
# Builds vector index from GCS on first startup
# """
# import os
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from pathlib import Path
# from typing import Optional, List
# import sys
# import threading

# # Add parent directory to path
# sys.path.append(str(Path(__file__).resolve().parents[1]))

# from vectordb.embedder import VectorStore
# from dashboard.rag_generator import RAGDashboardGenerator
# from structured.structured_dashboard import generate_dashboard as generate_structured_dashboard

# # Initialize FastAPI
# app = FastAPI(
#     title="ORBIT AI50 Intelligence API",
#     description="RAG-powered API for Forbes AI 50 company intelligence",
#     version="2.0.0"
# )

# # CORS - allow all origins for Streamlit
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Global variables
# vector_store = None
# dashboard_generator = None
# build_in_progress = False


# @app.on_event("startup")
# async def startup_event():
#     """Initialize vector store - build from GCS if needed"""
#     global vector_store, dashboard_generator, build_in_progress
    
#     print("\n" + "="*70)
#     print("STARTING ORBIT API ON CLOUD RUN")
#     print("="*70)
    
#     try:
#         # Check if vector store already exists
#         qdrant_dir = Path("/app/data/qdrant_storage")
#         collection_dir = qdrant_dir / "collection" / "pe_companies"
        
#         needs_build = not collection_dir.exists() or not list(qdrant_dir.glob("*.sqlite"))
        
#         if needs_build:
#             print("\nVector store not found - building from GCS...")
#             print("This will take 10-15 minutes on first startup...")
#             print("API will start serving, but vector search disabled until build completes")
#             print("="*70)
            
#             # Run build in background thread
#             def build_index():
#                 global vector_store, dashboard_generator, build_in_progress
                
#                 try:
#                     build_in_progress = True
#                     print("Background build started...")
                    
#                     from vectordb.build_index import build_vector_index
                    
#                     build_vector_index(
#                         use_docker=False,
#                         clear_existing=True,
#                         use_gcs=True,
#                         bucket_name="orbit-raw-data-group1-2025"
#                     )
                    
#                     print("Vector index built! Loading into memory...")
                    
#                     # Load vector store
#                     vector_store = VectorStore(use_docker=False)
#                     dashboard_generator = RAGDashboardGenerator(vector_store)
                    
#                     build_in_progress = False
                    
#                     stats = vector_store.get_stats()
#                     companies = vector_store.get_companies()
                    
#                     print(f"SUCCESS: Loaded {len(companies)} companies, {stats['total_chunks']} chunks")
                    
#                 except Exception as e:
#                     build_in_progress = False
#                     print(f"FAILED: Build error - {e}")
#                     import traceback
#                     traceback.print_exc()
            
#             # Start background build
#             build_thread = threading.Thread(target=build_index, daemon=True)
#             build_thread.start()
            
#         else:
#             print("\nLoading existing vector store...")
            
#             vector_store = VectorStore(use_docker=False)
            
#             stats = vector_store.get_stats()
#             companies = vector_store.get_companies()
            
#             print(f"Loaded Qdrant with {stats['total_chunks']} chunks")
#             print(f"{len(companies)} companies indexed")
            
#             # Initialize RAG dashboard generator
#             print("\nLoading RAG dashboard generator...")
#             dashboard_generator = RAGDashboardGenerator(vector_store)
#             print("RAG generator ready")
            
#             print("\n" + "="*70)
#             print("API READY AND HEALTHY!")
#             print("="*70 + "\n")
        
#     except Exception as e:
#         print(f"Startup error: {e}")
#         import traceback
#         traceback.print_exc()


# # Pydantic models
# class SearchRequest(BaseModel):
#     query: str
#     k: int = 5
#     company_name: Optional[str] = None
#     page_type: Optional[str] = None


# class SearchResult(BaseModel):
#     text: str
#     company_name: str
#     page_type: str
#     score: float
#     tokens: int
#     session: str
#     source_file: str
#     is_daily_refresh: bool


# class SearchResponse(BaseModel):
#     results: List[SearchResult]
#     query: str
#     num_results: int
#     filters: dict


# class DashboardRequest(BaseModel):
#     company_name: str
#     max_chunks: int = 20


# class DashboardResponse(BaseModel):
#     company_name: str
#     dashboard: str
#     success: bool
#     metadata: Optional[dict] = None
#     error: Optional[str] = None


# @app.get("/")
# async def root():
#     """Health check - shows build status"""
#     if vector_store:
#         stats = vector_store.get_stats()
#         companies = vector_store.get_companies()
        
#         return {
#             "status": "healthy",
#             "message": "ORBIT AI50 Intelligence API",
#             "version": "2.0.0",
#             "environment": "Cloud Run",
#             "vector_store": {
#                 "status": "loaded",
#                 "total_chunks": stats['total_chunks'],
#                 "total_companies": len(companies),
#                 "vector_dimension": stats['vector_dimension']
#             },
#             "endpoints": {
#                 "health": "/health",
#                 "docs": "/docs",
#                 "search": "/rag/search",
#                 "companies": "/companies",
#                 "rag_dashboard": "/dashboard/rag",
#                 "structured_dashboard": "/dashboard/structured",
#                 "admin_status": "/admin/status",
#                 "admin_reload": "/admin/reload-vector-store"
#             }
#         }
#     else:
#         # Check if build is in progress
#         status_msg = "Building vector index from GCS..." if build_in_progress else "Vector store not loaded"
        
#         return {
#             "status": "initializing",
#             "message": status_msg,
#             "vector_store": {
#                 "status": "building" if build_in_progress else "not_loaded"
#             },
#             "note": "First startup takes 10-15 minutes to build index from GCS"
#         }


# @app.get("/health")
# async def health_check():
#     """Detailed health check"""
#     return {
#         "status": "ok",
#         "vector_store_initialized": vector_store is not None,
#         "dashboard_generator_initialized": dashboard_generator is not None,
#         "build_in_progress": build_in_progress,
#         "service": "orbit-api",
#         "version": "2.0.0"
#     }


# @app.post("/admin/reload-vector-store")
# async def reload_vector_store():
#     """Reload vector store after background build completes"""
#     global vector_store, dashboard_generator
    
#     try:
#         print("Reloading vector store...")
        
#         vector_store = VectorStore(use_docker=False)
#         dashboard_generator = RAGDashboardGenerator(vector_store)
        
#         stats = vector_store.get_stats()
#         companies = vector_store.get_companies()
        
#         return {
#             "status": "success",
#             "message": "Vector store reloaded",
#             "stats": {
#                 "total_companies": len(companies),
#                 "total_chunks": stats['total_chunks'],
#                 "vector_dimension": stats['vector_dimension']
#             }
#         }
    
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Reload failed: {str(e)}"
#         )


# @app.get("/admin/status")
# async def admin_status():
#     """Check current system status"""
#     qdrant_dir = Path("/app/data/qdrant_storage")
    
#     return {
#         "vector_store_loaded": vector_store is not None,
#         "dashboard_generator_loaded": dashboard_generator is not None,
#         "build_in_progress": build_in_progress,
#         "qdrant_dir_exists": qdrant_dir.exists(),
#         "qdrant_files": list(qdrant_dir.glob("*")) if qdrant_dir.exists() else [],
#         "stats": vector_store.get_stats() if vector_store else None,
#         "companies_count": len(vector_store.get_companies()) if vector_store else 0
#     }


# @app.post("/rag/search", response_model=SearchResponse)
# async def search(request: SearchRequest):
#     """Search vector store"""
#     if vector_store is None:
#         raise HTTPException(
#             status_code=503, 
#             detail="Vector store not initialized. Building in progress - check /admin/status"
#         )
    
#     try:
#         results = vector_store.search(
#             query=request.query,
#             k=request.k,
#             company_name=request.company_name,
#             page_type=request.page_type
#         )
        
#         formatted_results = [
#             SearchResult(
#                 text=r['text'],
#                 company_name=r['metadata']['company_name'],
#                 page_type=r['metadata']['page_type'],
#                 score=r['score'],
#                 tokens=r['tokens'],
#                 session=r['metadata']['session'],
#                 source_file=r['metadata']['source_file'],
#                 is_daily_refresh=r['metadata'].get('is_daily_refresh', False)
#             )
#             for r in results
#         ]
        
#         return SearchResponse(
#             results=formatted_results,
#             query=request.query,
#             num_results=len(formatted_results),
#             filters={
#                 "company_name": request.company_name,
#                 "page_type": request.page_type
#             }
#         )
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# @app.post("/dashboard/rag", response_model=DashboardResponse)
# async def generate_rag_dashboard(request: DashboardRequest):
#     """Generate RAG dashboard"""
#     if dashboard_generator is None:
#         raise HTTPException(
#             status_code=503,
#             detail="Dashboard generator not initialized. Check /admin/status"
#         )
    
#     try:
#         result = dashboard_generator.generate_dashboard(
#             company_name=request.company_name,
#             max_chunks=request.max_chunks
#         )
#         return DashboardResponse(**result)
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# @app.post("/dashboard/structured", response_model=DashboardResponse)
# async def generate_structured_dashboard_endpoint(request: DashboardRequest):
#     """Generate Structured dashboard"""
#     try:
#         result = generate_structured_dashboard(request.company_name)
        
#         if result['success']:
#             return DashboardResponse(
#                 company_name=result['company_name'],
#                 dashboard=result['markdown'],
#                 success=True,
#                 metadata={
#                     'tokens_used': result.get('tokens_used', 0),
#                     'pipeline': 'structured'
#                 }
#             )
#         else:
#             return DashboardResponse(
#                 company_name=request.company_name,
#                 dashboard="",
#                 success=False,
#                 error=result.get('error', 'Unknown error')
#             )
    
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail=f"Payload not found for {request.company_name}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# @app.get("/companies")
# async def get_companies():
#     """Get companies list"""
#     if vector_store is None:
#         raise HTTPException(status_code=503, detail="Vector store not initialized")
    
#     return {
#         "companies": vector_store.get_companies(),
#         "total": len(vector_store.get_companies())
#     }


# @app.get("/stats")
# async def get_stats():
#     """Get statistics"""
#     if vector_store is None:
#         raise HTTPException(status_code=503, detail="Vector store not initialized")
    
#     stats = vector_store.get_stats()
    
#     return {
#         "total_chunks": stats['total_chunks'],
#         "total_companies": len(vector_store.get_companies()),
#         "vector_dimension": stats['vector_dimension']
#     }


# if __name__ == "__main__":
#     import uvicorn
    
#     port = int(os.getenv("PORT", 8000))
    
#     print(f"""
# ╔═══════════════════════════════════════════════════════════╗
# ║     ORBIT API - RAG + STRUCTURED PIPELINES                ║
# ╚═══════════════════════════════════════════════════════════╝

# Starting FastAPI server on port {port}...
# API docs: http://localhost:{port}/docs
#     """)
    
#     uvicorn.run(app, host="0.0.0.0", port=port)

"""
FastAPI app for RAG search + Structured dashboards - App Engine Standard Deployment
Builds vector index from GCS on first startup
Author: Tapas
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
import sys
import threading
from google.cloud import storage

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from vectordb.embedder import VectorStore
from dashboard.rag_generator import RAGDashboardGenerator
from structured.structured_dashboard import generate_dashboard as generate_structured_dashboard

# GCP Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "orbit-ai50-intelligence")
GCS_RAW_BUCKET = os.getenv("GCS_RAW_BUCKET", "orbit-raw-data-group1-2025")
GCS_PROCESSED_BUCKET = os.getenv("GCS_PROCESSED_BUCKET", "orbit-processed-data-group1-2025")

# Initialize FastAPI
app = FastAPI(
    title="ORBIT AI50 Intelligence API",
    description="RAG-powered API for Forbes AI 50 company intelligence",
    version="2.0.0"
)

# CORS - allow all origins for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
vector_store = None
dashboard_generator = None
build_in_progress = False
storage_client = None


def get_gcs_client():
    """Get or create GCS client"""
    global storage_client
    if storage_client is None:
        storage_client = storage.Client(project=GCP_PROJECT_ID)
    return storage_client


def check_gcs_access():
    """Verify GCS access on startup"""
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_RAW_BUCKET)
        
        if not bucket.exists():
            print(f"⚠️  WARNING: Bucket {GCS_RAW_BUCKET} not accessible")
            return False
        
        # Test read access
        blobs = list(bucket.list_blobs(max_results=1))
        file_count = len(list(bucket.list_blobs(max_results=100)))
        print(f"✅ GCS Access OK - found {file_count} files in bucket")
        return True
    except Exception as e:
        print(f"❌ GCS Access Error: {e}")
        return False


# @app.on_event("startup")
# async def startup_event():
#     """Initialize vector store - build from GCS if needed"""
#     global vector_store, dashboard_generator, build_in_progress
    
#     print("\n" + "="*70)
#     print("STARTING ORBIT API ON APP ENGINE STANDARD")
#     print("="*70)
#     print(f"GCP Project: {GCP_PROJECT_ID}")
#     print(f"Raw Bucket: {GCS_RAW_BUCKET}")
#     print(f"Processed Bucket: {GCS_PROCESSED_BUCKET}")
#     print(f"Instance: {os.getenv('GAE_INSTANCE', 'local')}")
#     print(f"Service: {os.getenv('GAE_SERVICE', 'default')}")
#     print("="*70)
    
#     # Check GCS access
#     if not check_gcs_access():
#         print("⚠️  Continuing without GCS - vector search will fail")
    
#     try:
#         # ✅ CRITICAL: App Engine Standard uses /tmp for temporary storage
#         qdrant_dir = Path("/tmp/qdrant_storage")
#         collection_dir = qdrant_dir / "collection" / "pe_companies"
        
#         needs_build = not collection_dir.exists() or not list(qdrant_dir.glob("*.sqlite"))
        
#         if needs_build:
#             print("\n⚠️  Vector store not found - building from GCS...")
#             print("This will take 10-15 minutes on first startup...")
#             print("API will start serving, but vector search disabled until build completes")
#             print("="*70)
            
#             # Run build in background thread
#             def build_index():
#                 global vector_store, dashboard_generator, build_in_progress
                
#                 try:
#                     build_in_progress = True
#                     print("🔨 Background build started...")
                    
#                     from vectordb.build_index import build_vector_index
                    
#                     build_vector_index(
#                         use_docker=False,
#                         clear_existing=True,
#                         use_gcs=True,
#                         bucket_name=GCS_RAW_BUCKET
#                     )
                    
#                     print("✅ Vector index built successfully!")
                    
#                     # ✅ FIX: Wait for locks to release before loading
#                     import time
#                     print("⏳ Waiting 5 seconds for locks to release...")
#                     time.sleep(5)
                    
#                     # ✅ Try loading with retry logic
#                     max_retries = 3
#                     for attempt in range(max_retries):
#                         try:
#                             print(f"📦 Loading vector store (attempt {attempt + 1}/{max_retries})...")
#                             vector_store = VectorStore(use_docker=False)
#                             dashboard_generator = RAGDashboardGenerator(vector_store)
                            
#                             build_in_progress = False
                            
#                             stats = vector_store.get_stats()
#                             companies = vector_store.get_companies()
                            
#                             print(f"✅ SUCCESS: Loaded {len(companies)} companies, {stats['total_chunks']} chunks")
#                             return  # Success!
                            
#                         except RuntimeError as e:
#                             if "already accessed" in str(e) and attempt < max_retries - 1:
#                                 print(f"⚠️ Lock conflict, waiting 5 seconds...")
#                                 time.sleep(5)
#                             else:
#                                 raise
                    
#                 except Exception as e:
#                     build_in_progress = False
#                     print(f"❌ FAILED: Build error - {e}")
#                     import traceback
#                     traceback.print_exc()
                    
#             # Start background build
#             build_thread = threading.Thread(target=build_index, daemon=True)
#             build_thread.start()
            
#         else:
#             print("\n📦 Loading existing vector store...")
            
#             vector_store = VectorStore(use_docker=False)
            
#             stats = vector_store.get_stats()
#             companies = vector_store.get_companies()
            
#             print(f"✅ Loaded Qdrant with {stats['total_chunks']} chunks")
#             print(f"✅ {len(companies)} companies indexed")
            
#             # Initialize RAG dashboard generator
#             print("\n🤖 Loading RAG dashboard generator...")
#             dashboard_generator = RAGDashboardGenerator(vector_store)
#             print("✅ RAG generator ready")
            
#             print("\n" + "="*70)
#             print("🚀 API READY AND HEALTHY!")
#             print("="*70 + "\n")
        
#     except Exception as e:
#         print(f"❌ Startup error: {e}")
#         import traceback
#         traceback.print_exc()

@app.on_event("startup")
async def startup_event():
    """Initialize vector store - DOWNLOAD from GCS"""
    global vector_store, dashboard_generator
    
    print("\n" + "="*70)
    print("🚀 STARTING ORBIT API")
    print("="*70)
    
    try:
        qdrant_dir = Path("/tmp/qdrant_storage")
        
        # Download raw files from GCS
        if not qdrant_dir.exists() or not list(qdrant_dir.glob("**/*.sqlite")):
            print("\n📥 Downloading vector DB from GCS...")
            
            try:
                client = get_gcs_client()
                bucket = client.bucket(GCS_PROCESSED_BUCKET)
                
                # Download all files from qdrant_index/ prefix
                blobs = list(bucket.list_blobs(prefix="qdrant_index/"))
                
                if not blobs:
                    print("❌ No vector DB found in GCS!")
                    return
                
                print(f"   Found {len(blobs)} files to download...")
                
                for blob in blobs:
                    if blob.name.endswith('/'):
                        continue  # Skip directory markers
                    
                    # Remove 'qdrant_index/' prefix to get relative path
                    relative_path = blob.name.replace('qdrant_index/', '')
                    local_file = qdrant_dir / relative_path
                    
                    # Create parent directories
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Download
                    blob.download_to_filename(str(local_file))
                    print(f"   ✓ {relative_path}")
                
                print(f"   ✅ Downloaded {len(blobs)} files")
                
            except Exception as e:
                print(f"   ❌ Download failed: {e}")
                return
        
        # Load vector store
        print("\n📦 Loading vector store...")
        try:
            vector_store = VectorStore(use_docker=False, data_dir=Path("/tmp/qdrant_storage"))
            
            stats = vector_store.get_stats()
            companies = vector_store.get_companies()
            
            print(f"✅ Loaded {stats['total_chunks']} chunks")
            print(f"✅ {len(companies)} companies")
            
            # Initialize dashboard generator
            dashboard_generator = RAGDashboardGenerator(vector_store)
            
            print("\n✅ API READY!")
        except Exception as vs_error:
            print(f"❌ Failed to load vector store: {vs_error}")
            print(f"   Vector store will not be available.")
            vector_store = None
            dashboard_generator = None
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        import traceback
        traceback.print_exc()
# ============================================================================
# Pydantic Models
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    company_name: Optional[str] = None
    page_type: Optional[str] = None


class SearchResult(BaseModel):
    text: str
    company_name: str
    page_type: str
    score: float
    tokens: int
    session: str
    source_file: str
    is_daily_refresh: bool


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    num_results: int
    filters: dict


class DashboardRequest(BaseModel):
    company_name: str
    max_chunks: int = 20


class DashboardResponse(BaseModel):
    company_name: str
    dashboard: str
    success: bool
    metadata: Optional[dict] = None
    error: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - shows API status and available endpoints"""
    if vector_store:
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        return {
            "status": "healthy",
            "message": "ORBIT AI50 Intelligence API",
            "version": "2.0.0",
            "environment": "App Engine Standard",
            "gcp": {
                "project_id": GCP_PROJECT_ID,
                "raw_bucket": GCS_RAW_BUCKET,
                "processed_bucket": GCS_PROCESSED_BUCKET
            },
            "vector_store": {
                "status": "loaded",
                "total_chunks": stats['total_chunks'],
                "total_companies": len(companies),
                "vector_dimension": stats['vector_dimension']
            },
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "search": "/rag/search",
                "companies": "/companies",
                "stats": "/stats",
                "rag_dashboard": "/dashboard/rag",
                "structured_dashboard": "/dashboard/structured",
                "gcs_buckets": "/gcs/buckets",
                "gcs_files": "/gcs/files/{bucket_type}",
                "admin_status": "/admin/status",
                "admin_reload": "/admin/reload-vector-store"
            }
        }
    else:
        # Check if build is in progress
        status_msg = "Building vector index from GCS..." if build_in_progress else "Vector store not loaded"
        
        return {
            "status": "initializing",
            "message": status_msg,
            "environment": "App Engine Standard",
            "gcp": {
                "project_id": GCP_PROJECT_ID,
                "raw_bucket": GCS_RAW_BUCKET,
                "processed_bucket": GCS_PROCESSED_BUCKET
            },
            "vector_store": {
                "status": "building" if build_in_progress else "not_loaded"
            },
            "note": "First startup takes 10-15 minutes to build index from GCS"
        }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    try:
        client = get_gcs_client()
        raw_bucket = client.bucket(GCS_RAW_BUCKET)
        gcs_status = "connected" if raw_bucket.exists() else "bucket_not_found"
    except Exception as e:
        gcs_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "vector_store_initialized": vector_store is not None,
        "dashboard_generator_initialized": dashboard_generator is not None,
        "build_in_progress": build_in_progress,
        "gcs_status": gcs_status,
        "service": "orbit-api",
        "version": "2.0.0",
        "environment": "App Engine Standard",
        "gcp_project": GCP_PROJECT_ID,
        "instance": os.getenv('GAE_INSTANCE', 'local')
    }


@app.get("/gcs/buckets")
async def get_buckets_info():
    """Get information about GCS buckets"""
    try:
        client = get_gcs_client()
        
        buckets_info = {}
        for bucket_name in [GCS_RAW_BUCKET, GCS_PROCESSED_BUCKET]:
            try:
                bucket = client.bucket(bucket_name)
                if bucket.exists():
                    blobs = list(bucket.list_blobs(max_results=1000))
                    total_size = sum(blob.size for blob in blobs if blob.size)
                    buckets_info[bucket_name] = {
                        "exists": True,
                        "file_count": len(blobs),
                        "total_size_mb": round(total_size / (1024 * 1024), 2),
                        "location": bucket.location if hasattr(bucket, 'location') else "unknown"
                    }
                else:
                    buckets_info[bucket_name] = {"exists": False}
            except Exception as e:
                buckets_info[bucket_name] = {"error": str(e)}
        
        return {
            "project_id": GCP_PROJECT_ID,
            "buckets": buckets_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing buckets: {str(e)}")


@app.get("/gcs/files/{bucket_type}")
async def get_bucket_files(bucket_type: str, prefix: str = "", max_results: int = 100):
    """
    List files in a bucket
    
    Args:
        bucket_type: 'raw' or 'processed'
        prefix: optional prefix to filter files (e.g., 'data/raw/')
        max_results: maximum number of files to return
    """
    bucket_name = GCS_RAW_BUCKET if bucket_type == "raw" else GCS_PROCESSED_BUCKET
    
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=max_results)
        
        files = []
        for blob in blobs:
            files.append({
                "name": blob.name,
                "size": blob.size,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "content_type": blob.content_type
            })
        
        return {
            "bucket": bucket_name,
            "bucket_type": bucket_type,
            "prefix": prefix,
            "file_count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.post("/admin/reload-vector-store")
async def reload_vector_store():
    """Reload vector store after background build completes"""
    global vector_store, dashboard_generator
    
    try:
        print("♻️  Reloading vector store...")
        
        vector_store = VectorStore(use_docker=False, data_dir=Path("/tmp/qdrant_storage"))
        dashboard_generator = RAGDashboardGenerator(vector_store)
        
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        return {
            "status": "success",
            "message": "Vector store reloaded",
            "stats": {
                "total_companies": len(companies),
                "total_chunks": stats['total_chunks'],
                "vector_dimension": stats['vector_dimension']
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reload failed: {str(e)}"
        )


@app.get("/admin/status")
async def admin_status():
    """Check current system status - for debugging"""
    # App Engine uses /tmp for temporary storage
    qdrant_dir = Path("/tmp/qdrant_storage")
    
    gcs_info = {}
    try:
        client = get_gcs_client()
        for bucket_name in [GCS_RAW_BUCKET, GCS_PROCESSED_BUCKET]:
            bucket = client.bucket(bucket_name)
            gcs_info[bucket_name] = {
                "exists": bucket.exists(),
                "accessible": True
            }
    except Exception as e:
        gcs_info["error"] = str(e)
    
    return {
        "vector_store_loaded": vector_store is not None,
        "dashboard_generator_loaded": dashboard_generator is not None,
        "build_in_progress": build_in_progress,
        "qdrant_dir_exists": qdrant_dir.exists(),
        "qdrant_files": [str(f) for f in qdrant_dir.glob("*")] if qdrant_dir.exists() else [],
        "stats": vector_store.get_stats() if vector_store else None,
        "companies_count": len(vector_store.get_companies()) if vector_store else 0,
        "gcp": {
            "project_id": GCP_PROJECT_ID,
            "buckets": gcs_info,
            "instance": os.getenv('GAE_INSTANCE', 'local'),
            "service": os.getenv('GAE_SERVICE', 'default')
        },
        "environment": "App Engine Standard"
    }


# ============================================================================
# RAG Pipeline Endpoints
# ============================================================================

@app.post("/rag/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search vector store using RAG"""
    if vector_store is None:
        raise HTTPException(
            status_code=503, 
            detail="Vector store not initialized. Building in progress - check /admin/status"
        )
    
    try:
        results = vector_store.search(
            query=request.query,
            k=request.k,
            company_name=request.company_name,
            page_type=request.page_type
        )
        
        formatted_results = [
            SearchResult(
                text=r['text'],
                company_name=r['metadata']['company_name'],
                page_type=r['metadata']['page_type'],
                score=r['score'],
                tokens=r['tokens'],
                session=r['metadata']['session'],
                source_file=r['metadata']['source_file'],
                is_daily_refresh=r['metadata'].get('is_daily_refresh', False)
            )
            for r in results
        ]
        
        return SearchResponse(
            results=formatted_results,
            query=request.query,
            num_results=len(formatted_results),
            filters={
                "company_name": request.company_name,
                "page_type": request.page_type
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/dashboard/rag", response_model=DashboardResponse)
async def generate_rag_dashboard(request: DashboardRequest):
    """Generate RAG dashboard for a company"""
    if dashboard_generator is None:
        raise HTTPException(
            status_code=503,
            detail="Dashboard generator not initialized. Check /admin/status"
        )
    
    try:
        result = dashboard_generator.generate_dashboard(
            company_name=request.company_name,
            max_chunks=request.max_chunks
        )
        return DashboardResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ============================================================================
# Structured Pipeline Endpoints
# ============================================================================

@app.post("/dashboard/structured", response_model=DashboardResponse)
async def generate_structured_dashboard_endpoint(request: DashboardRequest):
    """Generate Structured dashboard for a company"""
    try:
        result = generate_structured_dashboard(request.company_name)
        
        if result['success']:
            return DashboardResponse(
                company_name=result['company_name'],
                dashboard=result['markdown'],
                success=True,
                metadata={
                    'tokens_used': result.get('tokens_used', 0),
                    'pipeline': 'structured'
                }
            )
        else:
            return DashboardResponse(
                company_name=request.company_name,
                dashboard="",
                success=False,
                error=result.get('error', 'Unknown error')
            )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail=f"Payload not found for {request.company_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Generation failed: {str(e)}"
        )


# ============================================================================
# Data Endpoints
# ============================================================================

@app.get("/companies")
async def get_companies():
    """Get list of all companies in vector store"""
    if vector_store is None:
        raise HTTPException(
            status_code=503, 
            detail="Vector store not initialized"
        )
    
    return {
        "companies": vector_store.get_companies(),
        "total": len(vector_store.get_companies())
    }


@app.get("/stats")
async def get_stats():
    """Get vector store statistics"""
    if vector_store is None:
        raise HTTPException(
            status_code=503, 
            detail="Vector store not initialized"
        )
    
    stats = vector_store.get_stats()
    
    return {
        "total_chunks": stats['total_chunks'],
        "total_companies": len(vector_store.get_companies()),
        "vector_dimension": stats['vector_dimension'],
        "gcp_project": GCP_PROJECT_ID,
        "environment": "App Engine Standard"
    }


# ============================================================================
# Main Entry Point (for local testing)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8080))
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     ORBIT API - RAG + STRUCTURED PIPELINES                ║
║     Environment: App Engine Standard                      ║
║     GCP Project: {GCP_PROJECT_ID:<39} ║
╚═══════════════════════════════════════════════════════════╝

Starting FastAPI server on port {port}...
API docs: http://localhost:{port}/docs

Endpoints:
  GET  /                    - API status
  GET  /health              - Health check
  GET  /docs                - Swagger UI
  POST /rag/search          - Vector search
  POST /dashboard/rag       - Generate RAG dashboard
  POST /dashboard/structured - Generate structured dashboard
  GET  /companies           - List companies
  GET  /gcs/buckets         - GCS bucket info
  GET  /admin/status        - System status
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=port)