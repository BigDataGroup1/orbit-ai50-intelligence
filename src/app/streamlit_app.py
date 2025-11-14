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

# Add parent to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils import (
    DashboardLoader, 
    format_score_display, 
    compare_dashboards
)

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
            ["Dashboard Viewer", "Comparison Mode", "Statistics"],
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


if __name__ == "__main__":
    main()