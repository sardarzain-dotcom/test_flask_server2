#!/usr/bin/env python3
"""
🧬 ELISA Dashboard Launcher
===========================
Simple launcher for the ELISA Biomarker Analysis Dashboard
"""

import streamlit as st
import os
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="🧬 ELISA Dashboard Launcher",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .info-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .file-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .status-good {
        color: #28a745;
        font-weight: bold;
    }
    .status-missing {
        color: #dc3545;
        font-weight: bold;
    }
    .command-box {
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 0.25rem 0.25rem 0;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-header">🧬 ELISA Analysis Dashboard Hub</h1>', unsafe_allow_html=True)

# Check for data files
def check_data_files():
    base_path = r"c:\Users\sarda\Git\test_flask_server2"
    
    files_to_check = {
        'Main Data': 'elisa_processed_data.csv',
        'Dashboard Script': 'elisa_streamlit_dashboard.py',
        'Excel Sheets': 'ELISA_Excel_Sheets'
    }
    
    status = {}
    for name, file_path in files_to_check.items():
        full_path = os.path.join(base_path, file_path)
        status[name] = os.path.exists(full_path)
    
    return status

# Information box
st.markdown("""
<div class="info-box">
    <h2>🎯 Welcome to the ELISA Biomarker Analysis Dashboard</h2>
    <p>This comprehensive dashboard provides interactive visualization and statistical analysis of your ELISA biomarker data.</p>
    <p><strong>Features:</strong> Concentration plots, longitudinal analysis, responder analysis, demographics, and statistical testing</p>
</div>
""", unsafe_allow_html=True)

# Check data status
st.header("📊 Data Status Check")
status = check_data_files()

col1, col2, col3 = st.columns(3)

with col1:
    status_text = "✅ Available" if status['Main Data'] else "❌ Missing"
    status_class = "status-good" if status['Main Data'] else "status-missing"
    st.markdown(f'<p class="{status_class}">Main Data: {status_text}</p>', unsafe_allow_html=True)

with col2:
    status_text = "✅ Available" if status['Dashboard Script'] else "❌ Missing"
    status_class = "status-good" if status['Dashboard Script'] else "status-missing"
    st.markdown(f'<p class="{status_class}">Dashboard: {status_text}</p>', unsafe_allow_html=True)

with col3:
    status_text = "✅ Available" if status['Excel Sheets'] else "❌ Missing"
    status_class = "status-good" if status['Excel Sheets'] else "status-missing"
    st.markdown(f'<p class="{status_class}">Excel Files: {status_text}</p>', unsafe_allow_html=True)

if all(status.values()):
    st.success("🎉 All required files are available! You can launch the dashboard.")
    
    # Launch instructions
    st.header("🚀 Launch Dashboard")
    
    st.markdown("""
    <div class="command-box">
        <strong>To launch the ELISA Dashboard, run this command in your terminal:</strong><br><br>
        <code>streamlit run elisa_streamlit_dashboard.py</code><br><br>
        <strong>The dashboard will open at:</strong><br>
        <code>http://localhost:8501</code><br><br>
        <strong>If that doesn't work, try:</strong><br>
        <code>streamlit run elisa_streamlit_dashboard.py --server.port 8502</code><br>
        <strong>Then visit:</strong> <code>http://localhost:8502</code>
    </div>
    """, unsafe_allow_html=True)
    
    # Add a direct clickable link
    st.markdown("### 🔗 Quick Access")
    st.markdown("[🚀 Click here when dashboard is running: http://localhost:8501](http://localhost:8501)")
    st.markdown("[🚀 Alternative port: http://localhost:8502](http://localhost:8502)")
    
    # Alternative command
    st.info("💡 **Alternative:** You can also run `streamlit run streamlit_demo.py` to see this launcher page")
    
else:
    st.error("❌ Some required files are missing. Please ensure you have run the ELISA data analysis first.")
    
    st.subheader("📝 Required Steps:")
    if not status['Main Data']:
        st.write("1. ❌ Run the ELISA data processing script to generate `elisa_processed_data.csv`")
    else:
        st.write("1. ✅ ELISA data processing completed")
    
    if not status['Dashboard Script']:
        st.write("2. ❌ Dashboard script missing - should be auto-created")
    else:
        st.write("2. ✅ Dashboard script available")
    
    if not status['Excel Sheets']:
        st.write("3. ❌ Run the Excel conversion to generate analysis sheets")
    else:
        st.write("3. ✅ Excel sheets available")

# Dashboard features
st.header("🎨 Dashboard Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="file-box">
        <h3>📊 Visualization Features</h3>
        <ul style="text-align: left;">
            <li>Interactive concentration plots</li>
            <li>Box plots and violin plots</li>
            <li>Individual subject trajectories</li>
            <li>Correlation heatmaps</li>
            <li>Response distribution charts</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="file-box">
        <h3>🔬 Analysis Features</h3>
        <ul style="text-align: left;">
            <li>Statistical t-tests between groups</li>
            <li>Effect size calculations (Cohen's d)</li>
            <li>Responder analysis (≥20% reduction)</li>
            <li>Demographic summaries</li>
            <li>Longitudinal change tracking</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# File locations
st.header("📂 File Locations")
st.write("**Project Directory:** `c:\\Users\\sarda\\Git\\test_flask_server2`")
st.write("**Main Data:** `elisa_processed_data.csv`")
st.write("**Dashboard Script:** `elisa_streamlit_dashboard.py`")
st.write("**Excel Files:** `ELISA_Excel_Sheets/` folder")
st.write("**Downloads:** `Downloads/ELISA_Excel_Sheets/` folder")

# Sidebar info
with st.sidebar:
    st.header("ℹ️ Dashboard Info")
    st.write("**Created:** November 27, 2025")
    st.write("**Technology:** Streamlit + Plotly")
    st.write("**Data Source:** ELISA CSV Analysis")
    
    st.markdown("---")
    st.header("📋 Quick Commands")
    
    st.code("# Install Streamlit if needed\npip install streamlit plotly", language="bash")
    st.code("# Launch main dashboard\nstreamlit run elisa_streamlit_dashboard.py", language="bash")
    st.code("# Launch this launcher\nstreamlit run streamlit_demo.py", language="bash")
    st.code("# Stop dashboard\nCtrl+C in terminal", language="bash")
    
    st.markdown("---")
    st.subheader("🔗 Useful Links")
    st.write("• [Streamlit Documentation](https://docs.streamlit.io)")
    st.write("• [Plotly Documentation](https://plotly.com/python/)")

# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666;'>
        <p>🧬 ELISA Dashboard Launcher • Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
        <p>📊 Ready to visualize your biomarker analysis results!</p>
    </div>
    """,
    unsafe_allow_html=True
)