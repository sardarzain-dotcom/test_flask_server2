#!/usr/bin/env python3
"""
🧬 ELISA Biomarker Analysis Dashboard - COMPLETE VERSION
======================================================
Full-featured Streamlit dashboard with all visualizations and data analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from datetime import datetime
import os
import json
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Set page config
st.set_page_config(
    page_title="🧬 ELISA Biomarker Analysis Dashboard",
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
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-metric {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_elisa_data():
    """Load ELISA analysis data with comprehensive error handling"""
    try:
        # Main processed data
        processed_file = "elisa_processed_data.csv"
        if not os.path.exists(processed_file):
            st.error(f"❌ Main data file not found: {processed_file}")
            return None, None, None, None, None
        
        processed_data = pd.read_csv(processed_file)
        st.success(f"✅ Loaded main dataset: {len(processed_data)} records")
        
        # Load additional analysis files
        excel_files = {
            'pivot': "ELISA_Excel_Sheets/02_PivotTable.csv",
            'changes': "ELISA_Excel_Sheets/05_LongitudinalChanges.csv", 
            'demographics': "ELISA_Excel_Sheets/06_Demographics.csv",
            'correlations': "ELISA_Excel_Sheets/08_Correlations.csv"
        }
        
        additional_data = {}
        for key, filepath in excel_files.items():
            if os.path.exists(filepath):
                try:
                    if key == 'pivot' or key == 'demographics' or key == 'correlations':
                        additional_data[key] = pd.read_csv(filepath, index_col=0)
                    else:
                        additional_data[key] = pd.read_csv(filepath)
                    st.success(f"✅ Loaded {key} data: {len(additional_data[key])} records")
                except Exception as e:
                    st.warning(f"⚠️ Could not load {key} data: {e}")
                    additional_data[key] = None
            else:
                st.info(f"📝 Optional file not found: {filepath}")
                additional_data[key] = None
        
        return (processed_data, 
                additional_data.get('pivot'), 
                additional_data.get('changes'),
                additional_data.get('demographics'),
                additional_data.get('correlations'))
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None, None, None, None, None

def create_concentration_plots(data):
    """Create comprehensive concentration visualizations"""
    st.subheader("📊 Biomarker Concentration Analysis")
    
    if 'Concentration' not in data.columns:
        st.warning("⚠️ Concentration data not available")
        return
    
    # Concentration by biomarker and group
    col1, col2 = st.columns(2)
    
    with col1:
        # Box plot
        fig_box = px.box(
            data, 
            x='Marker', 
            y='Concentration',
            color='Group',
            title="📦 Concentration Distribution by Biomarker",
            points="all",
            hover_data=['SubjectID', 'NominalTime']
        )
        fig_box.update_layout(height=500)
        st.plotly_chart(fig_box, width='stretch')
    
    with col2:
        # Violin plot
        fig_violin = px.violin(
            data,
            x='Marker',
            y='Concentration', 
            color='Group',
            box=True,
            title="🎻 Concentration Density Distribution",
            hover_data=['SubjectID', 'NominalTime']
        )
        fig_violin.update_layout(height=500)
        st.plotly_chart(fig_violin, width='stretch')

def create_longitudinal_plots(data, changes_data=None):
    """Create longitudinal analysis visualizations"""
    st.subheader("📈 Longitudinal Analysis")
    
    # Subject trajectory plots
    if 'NominalTime' in data.columns and 'Concentration' in data.columns:
        # Line plot showing individual trajectories
        fig_lines = px.line(
            data,
            x='NominalTime',
            y='Concentration',
            color='Group',
            line_group='SubjectID',
            facet_col='Marker',
            title="📈 Individual Subject Trajectories",
            markers=True,
            hover_data=['SubjectID', 'Group']
        )
        fig_lines.update_traces(line=dict(width=1), marker=dict(size=4))
        st.plotly_chart(fig_lines, width='stretch')
        
        # Mean trajectory with error bars
        mean_data = data.groupby(['Group', 'Marker', 'NominalTime'])['Concentration'].agg(['mean', 'std', 'count']).reset_index()
        mean_data['se'] = mean_data['std'] / np.sqrt(mean_data['count'])
        
        fig_mean = px.line(
            mean_data,
            x='NominalTime',
            y='mean',
            color='Group',
            facet_col='Marker',
            title="📊 Mean Concentration Trajectories",
            error_y='se',
            markers=True
        )
        fig_mean.update_layout(yaxis_title="Mean Concentration")
        st.plotly_chart(fig_mean, width='stretch')
    
    # Changes analysis if available
    if changes_data is not None and not changes_data.empty:
        st.subheader("🔄 Concentration Changes Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Percent change distribution
            fig_changes = px.histogram(
                changes_data,
                x='Percent_Change',
                color='Group',
                facet_col='Marker',
                title="📊 Distribution of Percent Changes",
                nbins=20,
                opacity=0.7
            )
            st.plotly_chart(fig_changes, width='stretch')
        
        with col2:
            # Scatter: baseline vs change
            if 'Concentration_Baseline' in changes_data.columns:
                plot_data = changes_data.copy()
                plot_data['Size_for_Plot'] = abs(plot_data.get('Absolute_Change', 1)) + 1
                
                fig_scatter = px.scatter(
                    plot_data,
                    x='Concentration_Baseline',
                    y='Percent_Change',
                    color='Group',
                    size='Size_for_Plot',
                    facet_col='Marker',
                    title="🎯 Baseline vs Percent Change",
                    hover_data=['SubjectID']
                )
                st.plotly_chart(fig_scatter, width='stretch')

def create_statistical_analysis(data):
    """Create statistical analysis section"""
    st.subheader("🔬 Statistical Analysis")
    
    if 'Concentration' not in data.columns:
        st.warning("⚠️ Concentration data not available for statistical analysis")
        return
    
    # Statistical tests
    markers = data['Marker'].unique()
    groups = data['Group'].unique()
    
    if len(groups) >= 2:
        st.write("### 📊 Group Comparisons (T-tests)")
        
        results = []
        for marker in markers:
            marker_data = data[data['Marker'] == marker]
            group_data = {}
            
            for group in groups:
                group_values = marker_data[marker_data['Group'] == group]['Concentration'].dropna()
                group_data[group] = group_values
            
            # Perform t-tests between groups
            if len(group_data) == 2:
                group_names = list(group_data.keys())
                stat, p_value = stats.ttest_ind(group_data[group_names[0]], group_data[group_names[1]])
                
                results.append({
                    'Biomarker': marker,
                    'Comparison': f"{group_names[0]} vs {group_names[1]}",
                    'T-statistic': round(stat, 4),
                    'P-value': round(p_value, 4),
                    'Significant': '✅ Yes' if p_value < 0.05 else '❌ No'
                })
        
        if results:
            results_df = pd.DataFrame(results)
            st.dataframe(results_df, width='stretch')
    
    # Correlation analysis
    if len(data) > 10:
        st.write("### 🔗 Correlation Analysis")
        
        # Create correlation matrix for numeric columns
        numeric_data = data.select_dtypes(include=[np.number])
        if len(numeric_data.columns) > 1:
            corr_matrix = numeric_data.corr()
            
            # Create heatmap
            fig_corr = px.imshow(
                corr_matrix,
                text_auto=True,
                aspect="auto",
                title="🔥 Correlation Heatmap",
                color_continuous_scale='RdBu_r'
            )
            fig_corr.update_layout(height=500)
            st.plotly_chart(fig_corr, width='stretch')

def create_quality_control_section(data):
    """Create quality control analysis"""
    st.subheader("🔬 Quality Control Analysis")
    
    # QC flags analysis
    if 'flag' in data.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            # QC flag distribution
            flag_counts = data['flag'].value_counts()
            fig_flags = px.pie(
                values=flag_counts.values,
                names=flag_counts.index,
                title="🚩 Quality Control Flags Distribution"
            )
            st.plotly_chart(fig_flags, width='stretch')
        
        with col2:
            # QC by group
            if 'Group' in data.columns:
                flag_group = pd.crosstab(data['Group'], data['flag'])
                fig_flag_group = px.bar(
                    flag_group,
                    title="🚩 QC Flags by Group",
                    barmode='stack'
                )
                st.plotly_chart(fig_flag_group, width='stretch')
    
    # Raw signal analysis
    if 'RawSignal' in data.columns:
        st.write("### 📡 Raw Signal Quality")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Raw signal distribution
            fig_raw = px.histogram(
                data,
                x='RawSignal',
                color='Group',
                title="📊 Raw Signal Distribution",
                nbins=30,
                opacity=0.7
            )
            st.plotly_chart(fig_raw, width='stretch')
        
        with col2:
            # Raw signal by marker
            if 'Marker' in data.columns:
                fig_raw_marker = px.box(
                    data,
                    x='Marker',
                    y='RawSignal',
                    color='Group',
                    title="📦 Raw Signal by Biomarker"
                )
                st.plotly_chart(fig_raw_marker, width='stretch')

def main():
    """Main dashboard function"""
    st.markdown('<h1 class="main-header">🧬 ELISA Biomarker Analysis Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("### 📊 Comprehensive Analysis of ELISA Biomarker Data")
    
    # Load data
    with st.spinner("🔄 Loading ELISA data..."):
        processed_data, pivot_data, changes_data, demographics_data, correlations_data = load_elisa_data()
    
    if processed_data is None:
        st.error("❌ Could not load data. Please check if files exist.")
        return
    
    # Sidebar filters
    st.sidebar.header("🎛️ Dashboard Controls")
    
    # Basic data info
    st.sidebar.markdown("### 📈 Data Overview")
    st.sidebar.info(f"**Total Records**: {len(processed_data)}")
    
    if 'SubjectID' in processed_data.columns:
        st.sidebar.info(f"**Subjects**: {processed_data['SubjectID'].nunique()}")
    
    if 'Marker' in processed_data.columns:
        st.sidebar.info(f"**Biomarkers**: {', '.join(processed_data['Marker'].unique())}")
    
    # Filters
    filtered_data = processed_data.copy()
    
    if 'Group' in processed_data.columns:
        groups = st.sidebar.multiselect(
            "👥 Select Groups",
            options=processed_data['Group'].unique(),
            default=processed_data['Group'].unique()
        )
        filtered_data = filtered_data[filtered_data['Group'].isin(groups)]
    
    if 'Marker' in processed_data.columns:
        markers = st.sidebar.multiselect(
            "🧬 Select Biomarkers", 
            options=processed_data['Marker'].unique(),
            default=processed_data['Marker'].unique()
        )
        filtered_data = filtered_data[filtered_data['Marker'].isin(markers)]
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview",
        "📊 Concentrations", 
        "📈 Longitudinal",
        "🔬 Statistics",
        "🔬 Quality Control"
    ])
    
    with tab1:
        st.header("🏠 Dataset Overview")
        
        # Data summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Measurements", len(filtered_data))
        
        with col2:
            if 'SubjectID' in filtered_data.columns:
                st.metric("👥 Subjects", filtered_data['SubjectID'].nunique())
        
        with col3:
            if 'Marker' in filtered_data.columns:
                st.metric("🧬 Biomarkers", filtered_data['Marker'].nunique())
        
        with col4:
            if 'NominalTime' in filtered_data.columns:
                st.metric("⏰ Timepoints", filtered_data['NominalTime'].nunique())
        
        # Data preview
        st.subheader("📋 Data Preview")
        st.dataframe(filtered_data.head(10), width='stretch')
        
        # Basic statistics
        if 'Concentration' in filtered_data.columns:
            st.subheader("📊 Basic Statistics")
            stats_df = filtered_data.groupby('Marker')['Concentration'].describe()
            st.dataframe(stats_df, width='stretch')
    
    with tab2:
        create_concentration_plots(filtered_data)
    
    with tab3:
        create_longitudinal_plots(filtered_data, changes_data)
    
    with tab4:
        create_statistical_analysis(filtered_data)
    
    with tab5:
        create_quality_control_section(filtered_data)
    
    # Footer with URL
    st.markdown("---")
    st.info("🌐 **Dashboard URL**: http://localhost:8509 | 📊 All ELISA analysis visualizations loaded")

if __name__ == "__main__":
    main()