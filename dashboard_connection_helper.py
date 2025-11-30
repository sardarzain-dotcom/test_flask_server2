#!/usr/bin/env python3
"""
🚀 ELISA Dashboard Launcher & Connection Helper
==============================================
This script helps launch and maintain stable access to the ELISA Dashboard
"""

import streamlit as st
import subprocess
import time
import os
import requests
from pathlib import Path

# Dashboard configuration
DASHBOARD_FILE = "elisa_streamlit_dashboard.py"
TEST_DASHBOARD_FILE = "elisa_test_dashboard.py"
PORTS_TO_TRY = [8507, 8508, 8509, 8510, 8511]

st.set_page_config(
    page_title="🚀 ELISA Dashboard Launcher",
    page_icon="🚀", 
    layout="wide"
)

def check_port_available(port):
    """Check if a port is available"""
    try:
        response = requests.get(f"http://localhost:{port}", timeout=2)
        return True
    except:
        return False

def main():
    st.title("🚀 ELISA Dashboard Connection Helper")
    
    st.markdown("""
    ## 🔗 Dashboard Access Links
    
    **Try these URLs in your browser:**
    """)
    
    # Show all possible dashboard URLs
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 **Primary Access URLs**")
        for port in PORTS_TO_TRY:
            if check_port_available(port):
                st.success(f"✅ **WORKING**: http://localhost:{port}")
            else:
                st.info(f"🔗 Try: http://localhost:{port}")
    
    with col2:
        st.markdown("### 🌐 **Network Access URLs**")
        for port in PORTS_TO_TRY:
            st.info(f"🔗 Network: http://192.168.2.29:{port}")
    
    # File status
    st.markdown("---")
    st.markdown("## 📁 File Status Check")
    
    files_to_check = [
        "elisa_processed_data.csv",
        "elisa_streamlit_dashboard.py", 
        "elisa_test_dashboard.py",
        "Launch_Dashboard.bat",
        "ELISA_Dashboard_Links.html"
    ]
    
    col1, col2, col3 = st.columns(3)
    
    for i, file in enumerate(files_to_check):
        col = [col1, col2, col3][i % 3]
        with col:
            if os.path.exists(file):
                st.success(f"✅ {file}")
            else:
                st.error(f"❌ {file}")
    
    # Quick launch section
    st.markdown("---")
    st.markdown("## 🚀 Quick Launch Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 **Method 1: Direct URL**
        1. Copy: `http://localhost:8507`
        2. Paste in browser
        3. Access dashboard
        """)
        
    with col2:
        st.markdown("""
        ### 📁 **Method 2: Batch File**
        1. Find: `Start_ELISA_Dashboard_STABLE.bat`
        2. Double-click to run
        3. Wait for URL to appear
        """)
        
    with col3:
        st.markdown("""
        ### ⌨️ **Method 3: Command Line**
        ```bash
        streamlit run elisa_test_dashboard.py --server.port 8507
        ```
        """)
    
    # Connection troubleshooting
    st.markdown("---")
    st.markdown("""
    ## 🔧 **Troubleshooting Connection Issues**
    
    ### If dashboard won't load:
    1. **Check if process is running**: Look for terminal window with Streamlit output
    2. **Try different ports**: Use 8507, 8508, 8509, 8510, or 8511
    3. **Clear browser cache**: Press Ctrl+F5 to refresh
    4. **Restart dashboard**: Close terminal, run launch command again
    
    ### Common solutions:
    - ✅ Use **http://localhost:8507** (test dashboard - always works)
    - ✅ Try **http://localhost:8508** if 8507 is busy
    - ✅ Use the batch file launcher for automated startup
    - ✅ Check Windows Firewall if network access fails
    """)
    
    # Current status
    st.markdown("---")
    
    # Test current working URLs
    working_urls = []
    for port in PORTS_TO_TRY:
        if check_port_available(port):
            working_urls.append(f"http://localhost:{port}")
    
    if working_urls:
        st.success(f"🎉 **Dashboard Available**: {', '.join(working_urls)}")
        st.markdown("**Click any of the URLs above to access your ELISA Dashboard!**")
    else:
        st.warning("⚠️ No dashboard detected. Please start the dashboard using one of the launch methods above.")
        st.info("💡 **Quick Start**: Run `streamlit run elisa_test_dashboard.py --server.port 8507` in terminal")

if __name__ == "__main__":
    main()