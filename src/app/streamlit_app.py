# """
# Streamlit Dashboard Viewer for Project ORBIT
# Lab 10 - Dashboard Deployment (Cloud Run Compatible)
# """
# import streamlit as st
# import requests
# from pathlib import Path
# import sys
# import os
# # At the top, add:
# from config import API_URL


# # Add parent to path
# sys.path.append(str(Path(__file__).resolve().parents[1]))

# from app.utils import (
#     DashboardLoader, 
#     format_score_display, 
#     compare_dashboards
# )

# # API Configuration - use environment variable or default
# API_URL = os.getenv(
#     'API_URL',
#     'http://localhost:8000'  # Default for local, replace with Cloud Run URL after deployment
# )

# # Page config
# st.set_page_config(
#     page_title="ORBIT PE Dashboard",
#     page_icon="🚀",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS
# st.markdown("""
# <style>
#     .main-header {
#         font-size: 2.5rem;
#         font-weight: bold;
#         color: #1f77b4;
#         text-align: center;
#         margin-bottom: 1rem;
#     }
#     .sub-header {
#         font-size: 1.2rem;
#         color: #666;
#         text-align: center;
#         margin-bottom: 2rem;
#     }
#     .metric-card {
#         background-color: #f0f2f6;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin: 0.5rem 0;
#     }
#     .api-status {
#         padding: 0.5rem;
#         border-radius: 0.25rem;
#         margin: 0.5rem 0;
#     }
# </style>
# """, unsafe_allow_html=True)


# def test_api_connection():
#     """Test if API is reachable"""
#     try:
#         response = requests.get(f"{API_URL}/health", timeout=5)
#         return response.status_code == 200, response.json()
#     except Exception as e:
#         return False, {"error": str(e)}


# def main():
#     """Main Streamlit application."""
    
#     # Initialize loader
#     loader = DashboardLoader()
    
#     # Header
#     st.markdown('<div class="main-header">🚀 ORBIT PE Dashboard</div>', unsafe_allow_html=True)
#     st.markdown('<div class="sub-header">Automated Intelligence for Forbes AI 50</div>', unsafe_allow_html=True)
    
#     # Sidebar
#     with st.sidebar:
#         st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=ORBIT", width=200)
        
#         st.markdown("---")
        
#         # API Status Check
#         api_online, api_data = test_api_connection()
        
#         if api_online:
#             st.success("✅ API Connected")
#             st.caption(f"Endpoint: {API_URL}")
#             if 'vector_store' in api_data:
#                 with st.expander("API Info"):
#                     st.json(api_data)
#         else:
#             st.error("❌ API Disconnected")
#             st.caption("Using file-based mode")
#             if 'error' in api_data:
#                 with st.expander("Error Details"):
#                     st.error(api_data['error'])
        
#         st.markdown("---")
#         # Then update API status check (around line 110):
#         with st.expander("🔌 API Status"):
#             try:
#                 response = requests.get(f"{API_URL}/health", timeout=5)
#                 if response.status_code == 200:
#                     st.success("✅ API Online")
#                     data = response.json()
#                     st.caption(f"URL: {API_URL}")
#                     st.caption(f"Vector Store: {'Loaded' if data.get('vector_store_initialized') else 'Not Loaded'}")
#                 else:
#                     st.error("❌ API Error")
#             except:
#                 st.warning("⚠️ API Offline")
#                 st.caption("Using file-based mode")
#         # Mode selection
#         mode = st.radio(
#             "📊 View Mode",
#             ["Dashboard Viewer", "Comparison Mode", "Statistics"],
#             help="Choose how to view the dashboards"
#         )
        
#         st.markdown("---")
        
#         # Get companies
#         companies = loader.get_all_companies()
        
#         if not companies:
#             st.error("⚠️ No dashboard data found!")
#             st.info("Run Labs 5-8 first to generate dashboards.")
#             return
        
#         # Company selector
#         selected_company = st.selectbox(
#             "🏢 Select Company",
#             companies,
#             help="Choose a company to view dashboard"
#         )
        
#         # Check availability
#         availability = loader.check_availability(selected_company)
        
#         st.markdown("**Available Pipelines:**")
#         if availability['rag']:
#             st.success("✅ Unstructured (RAG)")
#         else:
#             st.warning("⚠️ Unstructured (RAG) - not available")
        
#         if availability['structured']:
#             st.success("✅ Structured")
#         else:
#             st.warning("⚠️ Structured - not available")
    
#     # Main content area
#     if mode == "Dashboard Viewer":
#         show_dashboard_viewer(loader, selected_company, availability)
    
#     elif mode == "Comparison Mode":
#         show_comparison_mode(loader, selected_company, availability)
    
#     elif mode == "Statistics":
#         show_statistics(loader)


# def show_dashboard_viewer(loader, company_name, availability):
#     """Single dashboard viewer with pipeline selection."""
    
#     st.markdown(f"## 📄 Dashboard: {company_name}")
    
#     # Pipeline selector
#     available_pipelines = []
#     pipeline_labels = {}
    
#     if availability['rag']:
#         available_pipelines.append("Unstructured (RAG)")
#         pipeline_labels["Unstructured (RAG)"] = "rag"
    
#     if availability['structured']:
#         available_pipelines.append("Structured")
#         pipeline_labels["Structured"] = "structured"
    
#     if not available_pipelines:
#         st.error("No dashboards available for this company.")
#         return
    
#     col1, col2, col3 = st.columns([2, 2, 1])
    
#     with col1:
#         selected_pipeline = st.selectbox(
#             "Select Pipeline",
#             available_pipelines,
#             help="Choose which pipeline's dashboard to view"
#         )
    
#     with col2:
#         show_metadata = st.checkbox("Show Metadata", value=True)
    
#     with col3:
#         show_scores = st.checkbox("Show Scores", value=True)
    
#     pipeline_key = pipeline_labels[selected_pipeline]
    
#     # Load dashboard
#     dashboard = loader.load_dashboard(company_name, pipeline_key)
#     evaluation = loader.load_evaluation(company_name, pipeline_key)
    
#     if not dashboard:
#         st.error(f"Dashboard not found for {company_name} ({selected_pipeline})")
#         return
    
#     # Display metadata and scores in columns
#     if show_metadata or show_scores:
#         col_meta, col_score = st.columns(2)
        
#         with col_meta:
#             if show_metadata and evaluation:
#                 st.markdown("### 📊 Metadata")
                
#                 metadata = evaluation.get('metadata', {})
                
#                 with st.expander("Generation Details", expanded=True):
#                     st.write(f"**Pipeline:** {selected_pipeline}")
#                     st.write(f"**Generated:** {evaluation.get('generated_at', 'Unknown')[:10]}")
                    
#                     if pipeline_key == 'rag':
#                         st.write(f"**Chunks Used:** {metadata.get('chunks_used', 0)}")
#                         st.write(f"**Daily Chunks:** {metadata.get('daily_chunks', 0)}")
#                         st.write(f"**Initial Chunks:** {metadata.get('initial_chunks', 0)}")
#                         st.write(f"**Avg Relevance:** {metadata.get('avg_score', 0):.3f}")
#                     else:
#                         st.write(f"**Source:** Structured payload")
                    
#                     st.write(f"**Tokens:** {metadata.get('prompt_tokens', 0) + metadata.get('completion_tokens', 0)}")
        
#         with col_score:
#             if show_scores and evaluation:
#                 st.markdown("### 🎯 Evaluation Scores")
                
#                 scores = evaluation.get('rubric_scores', {}) or evaluation.get('manual_scores', {})
                
#                 if scores:
#                     with st.expander("Rubric Scores", expanded=True):
#                         st.write(format_score_display(scores.get('factual_correctness'), 3))
#                         st.caption("Factual Correctness (0-3)")
                        
#                         st.write(format_score_display(scores.get('schema_adherence'), 2))
#                         st.caption("Schema Adherence (0-2)")
                        
#                         st.write(format_score_display(scores.get('provenance_use'), 2))
#                         st.caption("Provenance Use (0-2)")
                        
#                         st.write(format_score_display(scores.get('hallucination_control'), 2))
#                         st.caption("Hallucination Control (0-2)")
                        
#                         st.write(format_score_display(scores.get('readability'), 1))
#                         st.caption("Readability (0-1)")
                        
#                         st.markdown("---")
                        
#                         total = evaluation.get('total_score', sum(v for v in scores.values() if v is not None))
#                         st.markdown(f"### **Total: {total}/10**")
    
#     st.markdown("---")
    
#     # Display dashboard
#     st.markdown("### 📝 Dashboard Content")
    
#     # Add download button
#     st.download_button(
#         label="📥 Download Markdown",
#         data=dashboard,
#         file_name=f"{company_name}_{selected_pipeline}_dashboard.md",
#         mime="text/markdown"
#     )
    
#     # Render markdown
#     st.markdown(dashboard)


# def show_comparison_mode(loader, company_name, availability):
#     """Side-by-side comparison of Unstructured (RAG) vs Structured."""
    
#     st.markdown(f"## ⚖️ Comparison: {company_name}")
    
#     if not (availability['rag'] and availability['structured']):
#         st.warning("⚠️ Both pipelines needed for comparison.")
#         available_list = []
#         if availability['rag']:
#             available_list.append("Unstructured (RAG)")
#         if availability['structured']:
#             available_list.append("Structured")
#         st.info("Available: " + ", ".join(available_list))
#         return
    
#     # Load both dashboards
#     rag_dashboard = loader.load_dashboard(company_name, 'rag')
#     struct_dashboard = loader.load_dashboard(company_name, 'structured')
    
#     rag_eval = loader.load_evaluation(company_name, 'rag')
#     struct_eval = loader.load_evaluation(company_name, 'structured')
    
#     # Comparison metrics
#     st.markdown("### 📊 Quick Comparison")
    
#     col1, col2, col3, col4 = st.columns(4)
    
#     with col1:
#         rag_total = rag_eval.get('total_score', 0) if rag_eval else 0
#         st.metric("Unstructured Score", f"{rag_total}/10")
    
#     with col2:
#         struct_total = struct_eval.get('total_score', 0) if struct_eval else 0
#         st.metric("Structured Score", f"{struct_total}/10")
    
#     with col3:
#         diff = abs(rag_total - struct_total)
#         st.metric("Difference", f"{diff} pts")
    
#     with col4:
#         if rag_total > struct_total:
#             winner = "🏆 Unstructured"
#         elif struct_total > rag_total:
#             winner = "🏆 Structured"
#         else:
#             winner = "🤝 Tie"
#         st.metric("Winner", winner)
    
#     # Detailed score comparison
#     with st.expander("📈 Detailed Score Breakdown", expanded=True):
#         if rag_eval and struct_eval:
#             rag_scores = rag_eval.get('rubric_scores', {}) or rag_eval.get('manual_scores', {})
#             struct_scores = struct_eval.get('rubric_scores', {}) or struct_eval.get('manual_scores', {})
            
#             score_cols = st.columns(5)
            
#             criteria = [
#                 ('factual_correctness', 'Factual', 3),
#                 ('schema_adherence', 'Schema', 2),
#                 ('provenance_use', 'Provenance', 2),
#                 ('hallucination_control', 'Hallucination', 2),
#                 ('readability', 'Readability', 1)
#             ]
            
#             for i, (key, label, max_score) in enumerate(criteria):
#                 with score_cols[i]:
#                     st.markdown(f"**{label}**")
#                     rag_score = rag_scores.get(key, 0)
#                     struct_score = struct_scores.get(key, 0)
                    
#                     st.write(f"Unstructured: {rag_score}/{max_score}")
#                     st.write(f"Structured: {struct_score}/{max_score}")
                    
#                     if rag_score > struct_score:
#                         st.success("→ Unstructured")
#                     elif struct_score > rag_score:
#                         st.info("→ Structured")
#                     else:
#                         st.write("= Tie")
    
#     # Content comparison
#     comparison = compare_dashboards(rag_dashboard, struct_dashboard)
    
#     with st.expander("🔍 Content Comparison"):
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.markdown("**Unstructured Dashboard**")
#             st.write(f"Sections: {comparison['rag_sections']}")
#             st.write(f"Length: {comparison['rag_length']} chars")
#             st.write(f"'Not disclosed': {comparison['rag_not_disclosed']} times")
        
#         with col2:
#             st.markdown("**Structured Dashboard**")
#             st.write(f"Sections: {comparison['structured_sections']}")
#             st.write(f"Length: {comparison['structured_length']} chars")
#             st.write(f"'Not disclosed': {comparison['structured_not_disclosed']} times")
    
#     st.markdown("---")
    
#     # Side-by-side display
#     st.markdown("### 📄 Side-by-Side View")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.markdown("#### Unstructured (RAG) Pipeline")
#         st.markdown(rag_dashboard)
    
#     with col2:
#         st.markdown("#### Structured Pipeline")
#         st.markdown(struct_dashboard)


# def show_statistics(loader):
#     """Show overall statistics and insights."""
    
#     st.markdown("## 📊 Project Statistics")
    
#     stats = loader.get_statistics()
    
#     # Overall metrics
#     col1, col2, col3, col4 = st.columns(4)
    
#     with col1:
#         st.metric("Total Companies", stats['total_companies'])
    
#     with col2:
#         st.metric("Unstructured Dashboards", stats['rag_dashboards'])
    
#     with col3:
#         st.metric("Structured Dashboards", stats['structured_dashboards'])
    
#     with col4:
#         completion = (stats['rag_dashboards'] + stats['structured_dashboards']) / (stats['total_companies'] * 2) * 100
#         st.metric("Completion", f"{completion:.1f}%")
    
#     st.markdown("---")
    
#     # Evaluation status
#     st.markdown("### 🎯 Evaluation Status (Lab 9)")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.markdown("**Unstructured Pipeline**")
#         st.progress(stats['rag_evaluated'] / max(1, stats['rag_dashboards']))
#         st.write(f"{stats['rag_evaluated']}/{stats['rag_dashboards']} evaluated")
    
#     with col2:
#         st.markdown("**Structured Pipeline**")
#         st.progress(stats['structured_evaluated'] / max(1, stats['structured_dashboards']))
#         st.write(f"{stats['structured_evaluated']}/{stats['structured_dashboards']} evaluated")
    
#     st.markdown("---")
    
#     # Company list
#     st.markdown("### 🏢 All Companies")
    
#     companies = loader.get_all_companies()
    
#     for i, company in enumerate(companies, 1):
#         availability = loader.check_availability(company)
        
#         col1, col2, col3 = st.columns([3, 1, 1])
        
#         with col1:
#             st.write(f"{i}. {company}")
        
#         with col2:
#             if availability['rag']:
#                 st.success("✅ Unstructured")
#             else:
#                 st.error("❌ Unstructured")
        
#         with col3:
#             if availability['structured']:
#                 st.success("✅ Structured")
#             else:
#                 st.error("❌ Structured")


# if __name__ == "__main__":
#     main()

"""
Streamlit Dashboard Viewer for Project ORBIT
Lab 10 - Dashboard Deployment (Cloud Run Compatible)
"""
import streamlit as st
import requests
from pathlib import Path
import sys
import os
from datetime import datetime
import json
import pandas as pd

# Add parent to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils import (
    DashboardLoader, 
    format_score_display, 
    compare_dashboards
)

# Import enhanced agent for chat
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from src.agents.interactive_agent_enhanced import EnhancedInteractivePEAgent, AVAILABLE_COMPANIES
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    EnhancedInteractivePEAgent = None
    AVAILABLE_COMPANIES = []

# # API Configuration - use environment variable or default
# API_URL = os.getenv(
#     'API_URL',
#     'http://localhost:8000'  # Default for local, override with env var for Cloud Run
# )

# API Configuration - use environment variable or default
API_URL = os.getenv(
    'API_URL',
    'https://orbit-api-667820328373.us-central1.run.app'  # FastAPI deployed URL
)
# Page config
st.set_page_config(
    page_title="ORBIT PE Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .api-status {
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def test_api_connection():
    """Test if API is reachable"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}


def main():
    """Main Streamlit application."""
    
    # Initialize loader
    loader = DashboardLoader()
    
    # Header
    st.markdown('<div class="main-header">🚀 ORBIT PE Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Automated Intelligence for Forbes AI 50</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=ORBIT", width=200)
        
        st.markdown("---")
        
        # Mode selection
        mode = st.radio(
            "📊 View Mode",
            ["Dashboard Viewer", "Comparison Mode", "Statistics", "🤖 AI Chat Assistant", "📊 Agentic Reports", "🔍 Backend Requests"],
            help="Choose how to view the dashboards"
        )
        
        st.markdown("---")
        
        # Get companies
        companies = loader.get_all_companies()
        
        if not companies:
            st.error("⚠️ No dashboard data found!")
            st.info("Run Labs 5-8 first to generate dashboards.")
            return
        
        # Company selector
        selected_company = st.selectbox(
            "🏢 Select Company",
            companies,
            help="Choose a company to view dashboard"
        )
        
        # Check availability
        availability = loader.check_availability(selected_company)
        
        st.markdown("**Available Pipelines:**")
        if availability['rag']:
            st.success("✅ Unstructured (RAG)")
        else:
            st.warning("⚠️ Unstructured (RAG) - not available")
        
        if availability['structured']:
            st.success("✅ Structured")
        else:
            st.warning("⚠️ Structured - not available")
        
        st.markdown("---")
        
        # API Status Check (single version)
        with st.expander("🔌 API Status"):
            api_online, api_data = test_api_connection()
            
            if api_online:
                st.success("✅ API Online")
                st.caption(f"URL: {API_URL}")
                
                vector_loaded = api_data.get('vector_store_initialized', False)
                if vector_loaded:
                    st.caption("✅ Vector Store: Loaded")
                else:
                    st.caption("⚠️ Vector Store: Not Loaded")
                
                # Show API details without nested expander
                st.markdown("**API Details:**")
                st.json(api_data)
            else:
                st.warning("⚠️ API Offline")
                st.caption("Using file-based mode")
                if 'error' in api_data:
                    st.caption(f"Error: {api_data['error'][:100]}")
    
    # Main content area
    if mode == "Dashboard Viewer":
        show_dashboard_viewer(loader, selected_company, availability)
    
    elif mode == "Comparison Mode":
        show_comparison_mode(loader, selected_company, availability)
    
    elif mode == "Statistics":
        show_statistics(loader)
    
    elif mode == "🤖 AI Chat Assistant":
        show_chat_assistant()
    
    elif mode == "📊 Agentic Reports":
        show_agentic_reports(loader)
    
    elif mode == "🔍 Backend Requests":
        show_backend_requests()


def show_dashboard_viewer(loader, company_name, availability):
    """Single dashboard viewer with pipeline selection."""
    
    st.markdown(f"## 📄 Dashboard: {company_name}")
    
    # Pipeline selector
    available_pipelines = []
    pipeline_labels = {}
    
    if availability['rag']:
        available_pipelines.append("Unstructured (RAG)")
        pipeline_labels["Unstructured (RAG)"] = "rag"
    
    if availability['structured']:
        available_pipelines.append("Structured")
        pipeline_labels["Structured"] = "structured"
    
    if not available_pipelines:
        st.error("No dashboards available for this company.")
        return
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_pipeline = st.selectbox(
            "Select Pipeline",
            available_pipelines,
            help="Choose which pipeline's dashboard to view"
        )
    
    with col2:
        show_metadata = st.checkbox("Show Metadata", value=True)
    
    with col3:
        show_scores = st.checkbox("Show Scores", value=True)
    
    pipeline_key = pipeline_labels[selected_pipeline]
    
    # Load dashboard
    dashboard = loader.load_dashboard(company_name, pipeline_key)
    evaluation = loader.load_evaluation(company_name, pipeline_key)
    
    if not dashboard:
        st.error(f"Dashboard not found for {company_name} ({selected_pipeline})")
        return
    
    # Display metadata and scores in columns
    if show_metadata or show_scores:
        col_meta, col_score = st.columns(2)
        
        with col_meta:
            if show_metadata and evaluation:
                st.markdown("### 📊 Metadata")
                
                metadata = evaluation.get('metadata', {})
                
                with st.expander("Generation Details", expanded=True):
                    st.write(f"**Pipeline:** {selected_pipeline}")
                    st.write(f"**Generated:** {evaluation.get('generated_at', 'Unknown')[:10]}")
                    
                    if pipeline_key == 'rag':
                        st.write(f"**Chunks Used:** {metadata.get('chunks_used', 0)}")
                        st.write(f"**Daily Chunks:** {metadata.get('daily_chunks', 0)}")
                        st.write(f"**Initial Chunks:** {metadata.get('initial_chunks', 0)}")
                        st.write(f"**Avg Relevance:** {metadata.get('avg_score', 0):.3f}")
                    else:
                        st.write(f"**Source:** Structured payload")
                    
                    st.write(f"**Tokens:** {metadata.get('prompt_tokens', 0) + metadata.get('completion_tokens', 0)}")
        
        with col_score:
            if show_scores and evaluation:
                st.markdown("### 🎯 Evaluation Scores")
                
                scores = evaluation.get('rubric_scores', {}) or evaluation.get('manual_scores', {})
                
                if scores:
                    with st.expander("Rubric Scores", expanded=True):
                        st.write(format_score_display(scores.get('factual_correctness'), 3))
                        st.caption("Factual Correctness (0-3)")
                        
                        st.write(format_score_display(scores.get('schema_adherence'), 2))
                        st.caption("Schema Adherence (0-2)")
                        
                        st.write(format_score_display(scores.get('provenance_use'), 2))
                        st.caption("Provenance Use (0-2)")
                        
                        st.write(format_score_display(scores.get('hallucination_control'), 2))
                        st.caption("Hallucination Control (0-2)")
                        
                        st.write(format_score_display(scores.get('readability'), 1))
                        st.caption("Readability (0-1)")
                        
                        st.markdown("---")
                        
                        total = evaluation.get('total_score', sum(v for v in scores.values() if v is not None))
                        st.markdown(f"### **Total: {total}/10**")
    
    st.markdown("---")
    
    # Display dashboard
    st.markdown("### 📝 Dashboard Content")
    
    # Add download button
    st.download_button(
        label="📥 Download Markdown",
        data=dashboard,
        file_name=f"{company_name}_{selected_pipeline}_dashboard.md",
        mime="text/markdown"
    )
    
    # Render markdown
    st.markdown(dashboard)


def show_comparison_mode(loader, company_name, availability):
    """Side-by-side comparison of Unstructured (RAG) vs Structured."""
    
    st.markdown(f"## ⚖️ Comparison: {company_name}")
    
    if not (availability['rag'] and availability['structured']):
        st.warning("⚠️ Both pipelines needed for comparison.")
        available_list = []
        if availability['rag']:
            available_list.append("Unstructured (RAG)")
        if availability['structured']:
            available_list.append("Structured")
        st.info("Available: " + ", ".join(available_list))
        return
    
    # Load both dashboards
    rag_dashboard = loader.load_dashboard(company_name, 'rag')
    struct_dashboard = loader.load_dashboard(company_name, 'structured')
    
    rag_eval = loader.load_evaluation(company_name, 'rag')
    struct_eval = loader.load_evaluation(company_name, 'structured')
    
    # Comparison metrics
    st.markdown("### 📊 Quick Comparison")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        rag_total = rag_eval.get('total_score', 0) if rag_eval else 0
        st.metric("Unstructured Score", f"{rag_total}/10")
    
    with col2:
        struct_total = struct_eval.get('total_score', 0) if struct_eval else 0
        st.metric("Structured Score", f"{struct_total}/10")
    
    with col3:
        diff = abs(rag_total - struct_total)
        st.metric("Difference", f"{diff} pts")
    
    with col4:
        if rag_total > struct_total:
            winner = "🏆 Unstructured"
        elif struct_total > rag_total:
            winner = "🏆 Structured"
        else:
            winner = "🤝 Tie"
        st.metric("Winner", winner)
    
    # Detailed score comparison
    with st.expander("📈 Detailed Score Breakdown", expanded=True):
        if rag_eval and struct_eval:
            rag_scores = rag_eval.get('rubric_scores', {}) or rag_eval.get('manual_scores', {})
            struct_scores = struct_eval.get('rubric_scores', {}) or struct_eval.get('manual_scores', {})
            
            score_cols = st.columns(5)
            
            criteria = [
                ('factual_correctness', 'Factual', 3),
                ('schema_adherence', 'Schema', 2),
                ('provenance_use', 'Provenance', 2),
                ('hallucination_control', 'Hallucination', 2),
                ('readability', 'Readability', 1)
            ]
            
            for i, (key, label, max_score) in enumerate(criteria):
                with score_cols[i]:
                    st.markdown(f"**{label}**")
                    rag_score = rag_scores.get(key, 0)
                    struct_score = struct_scores.get(key, 0)
                    
                    st.write(f"Unstructured: {rag_score}/{max_score}")
                    st.write(f"Structured: {struct_score}/{max_score}")
                    
                    if rag_score > struct_score:
                        st.success("→ Unstructured")
                    elif struct_score > rag_score:
                        st.info("→ Structured")
                    else:
                        st.write("= Tie")
    
    # Content comparison
    comparison = compare_dashboards(rag_dashboard, struct_dashboard)
    
    with st.expander("🔍 Content Comparison"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Unstructured Dashboard**")
            st.write(f"Sections: {comparison['rag_sections']}")
            st.write(f"Length: {comparison['rag_length']} chars")
            st.write(f"'Not disclosed': {comparison['rag_not_disclosed']} times")
        
        with col2:
            st.markdown("**Structured Dashboard**")
            st.write(f"Sections: {comparison['structured_sections']}")
            st.write(f"Length: {comparison['structured_length']} chars")
            st.write(f"'Not disclosed': {comparison['structured_not_disclosed']} times")
    
    st.markdown("---")
    
    # Side-by-side display
    st.markdown("### 📄 Side-by-Side View")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Unstructured (RAG) Pipeline")
        st.markdown(rag_dashboard)
    
    with col2:
        st.markdown("#### Structured Pipeline")
        st.markdown(struct_dashboard)


def show_statistics(loader):
    """Show overall statistics and insights."""
    
    st.markdown("## 📊 Project Statistics")
    
    stats = loader.get_statistics()
    
    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Companies", stats['total_companies'])
    
    with col2:
        st.metric("Unstructured Dashboards", stats['rag_dashboards'])
    
    with col3:
        st.metric("Structured Dashboards", stats['structured_dashboards'])
    
    with col4:
        completion = (stats['rag_dashboards'] + stats['structured_dashboards']) / (stats['total_companies'] * 2) * 100
        st.metric("Completion", f"{completion:.1f}%")
    
    st.markdown("---")
    
    # Evaluation status
    st.markdown("### 🎯 Evaluation Status (Lab 9)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Unstructured Pipeline**")
        st.progress(stats['rag_evaluated'] / max(1, stats['rag_dashboards']))
        st.write(f"{stats['rag_evaluated']}/{stats['rag_dashboards']} evaluated")
    
    with col2:
        st.markdown("**Structured Pipeline**")
        st.progress(stats['structured_evaluated'] / max(1, stats['structured_dashboards']))
        st.write(f"{stats['structured_evaluated']}/{stats['structured_dashboards']} evaluated")
    
    st.markdown("---")
    
    # Company list with API status
    st.markdown("### 🏢 All Companies")
    
    # Show API connection status
    api_online, api_data = test_api_connection()
    if api_online:
        st.info(f"🔗 Connected to: {API_URL}")
    else:
        st.warning("📁 File-based mode (API offline)")
    
    companies = loader.get_all_companies()
    
    for i, company in enumerate(companies, 1):
        availability = loader.check_availability(company)
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"{i}. {company}")
        
        with col2:
            if availability['rag']:
                st.success("✅ Unstructured")
            else:
                st.error("❌ Unstructured")
        
        with col3:
            if availability['structured']:
                st.success("✅ Structured")
            else:
                st.error("❌ Structured")


def show_chat_assistant():
    """Show AI Chat Assistant interface with tool usage tracking."""
    
    if not AGENT_AVAILABLE:
        st.error("⚠️ AI Chat Assistant is not available. Please check dependencies.")
        return
    
    st.markdown("## 🤖 AI Chat Assistant - PE Due Diligence")
    st.markdown("Ask questions about Forbes AI 50 companies. The agent will use tools to find answers.")
    
    # Initialize session state - check if agent exists first
    try:
        if "agent" not in st.session_state:
            if EnhancedInteractivePEAgent is None:
                st.error("Agent class not available. Please check imports.")
                return
            st.session_state.agent = EnhancedInteractivePEAgent()
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "tool_calls" not in st.session_state:
            st.session_state.tool_calls = []
    except Exception as e:
        st.error(f"Failed to initialize chat assistant: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        return
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show tool calls for assistant messages
            if message["role"] == "assistant" and message.get("tool_calls"):
                with st.expander(f"🔧 Tools Used ({len(message['tool_calls'])} tool(s))"):
                    for i, tool_call in enumerate(message["tool_calls"], 1):
                        st.markdown(f"**Tool {i}: {tool_call['tool_name']}**")
                        st.json({
                            "Arguments": tool_call.get("arguments", {}),
                            "Success": tool_call.get("success", False),
                            "Timestamp": tool_call.get("timestamp", "N/A")
                        })
                        
                        # Show result preview
                        result = tool_call.get("result", {})
                        if isinstance(result, dict):
                            if "error" in result:
                                st.error(f"❌ Error: {result['error']}")
                            else:
                                # Show key fields
                                preview_keys = ["company_id", "company_name", "valuation", "total_funding", 
                                              "recommendation", "score", "risk_score", "success"]
                                preview = {k: v for k, v in result.items() if k in preview_keys and v is not None}
                                if preview:
                                    st.json(preview)
                                else:
                                    st.info("✅ Tool executed successfully")
                        else:
                            st.info(f"✅ Result: {str(result)[:200]}...")
    
    # Chat input
    user_query = st.chat_input("Ask about a company (e.g., 'What is Anthropic's valuation?')")
    
    if user_query:
        # Check if agent is initialized
        if "agent" not in st.session_state:
            st.error("⚠️ Agent not initialized. Please refresh the page.")
            return
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)
        
        # Process with agent
        with st.chat_message("assistant"):
            with st.spinner("🤔 Agent thinking..."):
                try:
                    import asyncio
                    import concurrent.futures
                    
                    # Check agent exists before running
                    if "agent" not in st.session_state or st.session_state.agent is None:
                        st.error("⚠️ Agent not initialized. Please refresh the page.")
                        return
                    
                    # Store agent reference before threading
                    agent = st.session_state.agent
                    
                    # Run async function in a thread to avoid event loop conflicts
                    def run_async():
                        return asyncio.run(agent.process_query(user_query))
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async)
                        response, tool_calls = future.result(timeout=300)  # 5 min timeout
                    
                    # Display response
                    st.markdown(response)
                    
                    # Store message with tool calls
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "tool_calls": tool_calls
                    })
                    
                    # Show tool usage
                    if tool_calls:
                        st.markdown("---")
                        st.markdown(f"### 🔧 Tools Used ({len(tool_calls)})")
                        
                        for i, tool_call in enumerate(tool_calls, 1):
                            with st.expander(f"Tool {i}: **{tool_call['tool_name']}**"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown("**Arguments:**")
                                    st.json(tool_call.get("arguments", {}))
                                
                                with col2:
                                    status = "✅ Success" if tool_call.get("success") else "❌ Failed"
                                    st.markdown(f"**Status:** {status}")
                                    if tool_call.get("timestamp"):
                                        st.caption(f"Time: {tool_call['timestamp']}")
                                
                                # Show result
                                result = tool_call.get("result", {})
                                if isinstance(result, dict):
                                    if "error" in result:
                                        st.error(f"Error: {result['error']}")
                                    else:
                                        st.markdown("**Result:**")
                                        # Show formatted result
                                        if "company_name" in result:
                                            st.info(f"Company: {result.get('company_name')}")
                                        if "valuation" in result:
                                            st.info(f"Valuation: ${result.get('valuation'):,.0f}" if result.get('valuation') else "N/A")
                                        if "recommendation" in result:
                                            st.success(f"Recommendation: {result.get('recommendation')}")
                                        if "score" in result:
                                            st.metric("Score", result.get('score'))
                                        
                                        # Show full result in expander
                                        with st.expander("View Full Result"):
                                            st.json(result)
                                else:
                                    st.info(f"Result: {str(result)[:500]}...")
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    import traceback
                    st.code(traceback.format_exc())
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 💡 Example Queries")
        example_queries = [
            "What is Anthropic's valuation?",
            "Compare Anthropic, OpenAI, and Cohere",
            "What are the financial metrics for Anthropic?",
            "Generate an investment recommendation for Anthropic",
            "Calculate risk score for Anthropic",
            "Generate a dashboard for Anthropic"
        ]
        
        for query in example_queries:
            if st.button(query, key=f"example_{query}", use_container_width=True):
                st.session_state.example_query = query
                st.rerun()
        
        if "example_query" in st.session_state:
            # This will be processed in the next rerun
            pass
        
        st.markdown("---")
        st.markdown("### 📋 Available Companies")
        st.caption(f"{len(AVAILABLE_COMPANIES)} companies available")
        
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent.clear_history()
            st.rerun()


def show_agentic_reports(loader):
    """Show agentic workflow reports generated by DAG."""
    st.markdown("## 📊 Agentic Workflow Reports")
    st.markdown("View reports generated by the agentic dashboard DAG")
    
    # Check for reports
    reports_dir = Path("data/airflow_reports")
    if not reports_dir.exists():
        st.warning("⚠️ No reports directory found. Run the DAG first to generate reports.")
        st.info("""
        **To generate reports:**
        1. Run the standalone script: `python orbit_agentic_dashboard_local.py --limit 3`
        2. Or run the Airflow DAG: `orbit_agentic_dashboard_dag_local`
        
        Reports will be saved in `data/airflow_reports/`
        """)
        return
    
    # List all report files
    report_files = sorted(reports_dir.glob("agentic_dashboard_*.json"), reverse=True)
    
    if not report_files:
        st.info("No reports found. Run the DAG to generate reports.")
        return
    
    # Select report
    report_names = [f.name for f in report_files]
    selected_report = st.selectbox("Select Report", report_names)
    
    if selected_report:
        report_path = reports_dir / selected_report
        with open(report_path, 'r', encoding='utf-8') as f:
            import json
            report = json.load(f)
        
        # Display summary
        st.markdown("### 📈 Report Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Companies", report.get('summary', {}).get('total_companies', 0))
        with col2:
            st.metric("Successful", report.get('summary', {}).get('successful', 0))
        with col3:
            st.metric("Failed", report.get('summary', {}).get('failed', 0))
        with col4:
            success_rate = report.get('summary', {}).get('success_rate', 0)
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Workflow stats
        st.markdown("### 📊 Workflow Statistics")
        workflow_stats = report.get('workflow_stats', {})
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Avg Dashboard Score", f"{workflow_stats.get('avg_dashboard_score', 0):.1f}/100")
        with col2:
            st.metric("Total Risks", workflow_stats.get('total_risks_detected', 0))
        
        # Results table
        st.markdown("### 📋 Company Results")
        results = report.get('results', [])
        
        if results:
            import pandas as pd
            df_data = []
            for r in results:
                df_data.append({
                    "Company": r.get('company_name', 'N/A'),
                    "Status": "✅" if r.get('success') else "❌",
                    "Branch": r.get('branch_taken', 'N/A'),
                    "Score": r.get('dashboard_score', 0),
                    "Risks": r.get('risks_detected', 0)
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Detailed view
            st.markdown("### 🔍 Detailed Results")
            selected_company = st.selectbox("Select Company for Details", [r.get('company_name') for r in results])
            
            if selected_company:
                company_result = next((r for r in results if r.get('company_name') == selected_company), None)
                if company_result:
                    st.json(company_result)
        
        # Full report
        with st.expander("View Full Report JSON"):
            st.json(report)


def show_backend_requests():
    """Show backend request logs and monitoring."""
    st.markdown("## 🔍 Backend Request Monitor")
    st.markdown("View all requests made to the FastAPI backend")
    
    # Get API URL - use same API_URL as rest of app, or default to localhost:8080 (FastAPI port)
    # Check if API_URL is set to Cloud Run URL, otherwise use local
    if 'orbit-api' in API_URL or 'run.app' in API_URL:
        api_url = API_URL  # Use Cloud Run URL
    else:
        api_url = 'http://localhost:8080'  # Local FastAPI runs on 8080
    
    if api_url.endswith('/'):
        api_url = api_url[:-1]
    
    # Show API URL being used
    st.info(f"🔗 Connecting to: `{api_url}`")
    
    # Fetch request logs
    try:
        response = requests.get(f"{api_url}/admin/requests?limit=200", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Show statistics
            st.markdown("### 📊 Request Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Requests", data.get('total_requests', 0))
            with col2:
                st.metric("Showing", data.get('showing', 0))
            with col3:
                logs = data.get('logs', [])
                if logs:
                    avg_duration = sum(log.get('duration_ms', 0) for log in logs) / len(logs)
                    st.metric("Avg Duration", f"{avg_duration:.1f}ms")
                else:
                    st.metric("Avg Duration", "N/A")
            
            # Status code breakdown
            stats = data.get('statistics', {})
            if stats.get('status_codes'):
                st.markdown("### 📈 Status Code Breakdown")
                status_items = list(stats['status_codes'].items())
                status_cols = st.columns(len(status_items))
                for i, (status, count) in enumerate(status_items):
                    with status_cols[i]:
                        color = "🟢" if 200 <= status < 300 else "🔴" if status >= 400 else "🟡"
                        st.metric(f"{color} {status}", count)
            
            # Top paths
            if stats.get('top_paths'):
                st.markdown("### 🔝 Top Requested Paths")
                top_paths_df = pd.DataFrame([
                    {"Path": path, "Count": count}
                    for path, count in list(stats['top_paths'].items())[:10]
                ])
                st.dataframe(top_paths_df, use_container_width=True, hide_index=True)
            
            # Request logs table
            st.markdown("### 📋 Recent Requests")
            
            logs = data.get('logs', [])
            if logs:
                # Create DataFrame
                logs_df = pd.DataFrame(logs)
                
                # Format timestamp
                if 'timestamp' in logs_df.columns:
                    logs_df['time'] = pd.to_datetime(logs_df['timestamp']).dt.strftime('%H:%M:%S')
                
                # Select columns to show
                display_cols = ['time', 'method', 'path', 'status_code', 'duration_ms', 'client_ip']
                available_cols = [col for col in display_cols if col in logs_df.columns]
                
                # Show table
                st.dataframe(
                    logs_df[available_cols].tail(50),  # Show last 50
                    use_container_width=True,
                    hide_index=True
                )
                
                # Filter options
                with st.expander("🔍 Filter Requests"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        filter_method = st.multiselect(
                            "Filter by Method",
                            options=list(logs_df['method'].unique()) if 'method' in logs_df.columns else [],
                            default=[]
                        )
                    
                    with col2:
                        filter_status = st.multiselect(
                            "Filter by Status",
                            options=sorted(logs_df['status_code'].unique()) if 'status_code' in logs_df.columns else [],
                            default=[]
                        )
                    
                    # Apply filters
                    filtered_df = logs_df.copy()
                    if filter_method and 'method' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['method'].isin(filter_method)]
                    if filter_status and 'status_code' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['status_code'].isin(filter_status)]
                    
                    if len(filtered_df) < len(logs_df):
                        st.dataframe(
                            filtered_df[available_cols],
                            use_container_width=True,
                            hide_index=True
                        )
                
                # Detailed view
                st.markdown("### 🔍 Request Details")
                if len(logs) > 0:
                    selected_idx = st.selectbox(
                        "Select Request to View Details",
                        range(len(logs)),
                        format_func=lambda x: f"{logs[x].get('timestamp', '')[:19]} - {logs[x].get('method', '')} {logs[x].get('path', '')} ({logs[x].get('status_code', '')})"
                    )
                    
                    if selected_idx is not None:
                        selected_log = logs[selected_idx]
                        st.json(selected_log)
            else:
                st.info("No requests logged yet. Make some requests to see them here!")
        elif response.status_code == 404:
            st.warning(f"⚠️ Endpoint not found: `/admin/requests`")
            st.info(f"""
            **The `/admin/requests` endpoint is not available on this backend.**
            
            This might mean:
            - The FastAPI server is an older version
            - The endpoint hasn't been deployed yet
            
            **To enable request logging:**
            1. Make sure you're running the latest version of `src/api/main.py`
            2. The endpoint should be available at: `{api_url}/admin/requests`
            3. Check the API docs at: `{api_url}/docs`
            """)
        else:
            st.error(f"❌ Failed to fetch request logs: HTTP {response.status_code}")
            # Try to show response text if not JSON
            try:
                error_data = response.json()
                st.json(error_data)
            except (ValueError, requests.exceptions.JSONDecodeError):
                st.code(response.text[:500] if response.text else "No response body")
    
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to backend at {api_url}")
        
        # Show correct port based on URL
        if 'localhost' in api_url or '127.0.0.1' in api_url:
            port = api_url.split(':')[-1] if ':' in api_url else '8080'
            st.info(f"""
            **Make sure FastAPI is running:**
            1. Open Terminal
            2. cd orbit-ai50-intelligence
            3. Run: `python src/api/main.py` OR use: `.\\START_CHAT.bat`
            4. Wait for "Uvicorn running on http://0.0.0.0:{port}"
            5. Refresh this page
            """)
        else:
            st.info(f"Trying to connect to: {api_url}")
            st.info("If this is a Cloud Run URL, make sure it's deployed and accessible.")
    except requests.exceptions.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON response from backend")
        st.info("The backend returned a response that couldn't be parsed as JSON.")
        with st.expander("Error Details"):
            st.code(str(e))
    except Exception as e:
        st.error(f"❌ Error fetching request logs: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
    
    # Auto-refresh option
    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh every 5 seconds", value=False)
    if auto_refresh:
        import time
        time.sleep(5)
        st.rerun()


if __name__ == "__main__":
    main()