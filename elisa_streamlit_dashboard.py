#!/usr/bin/env python3
"""
🧬 ELISA Biomarker Analysis Dashboard
=====================================
Comprehensive Streamlit dashboard for visualizing ELISA biomarker analysis results
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
    .sub-header {
        font-size: 1.5rem;
        color: #4682B4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .biomarker-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stats-box {
        background-color: #f8f9fa;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.25rem 0.25rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2E8B57;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_elisa_data():
    """Load ELISA analysis data from CSV files"""
    try:
        # File paths
        base_path = r"c:\Users\sarda\Git\test_flask_server2"
        
        # Main processed data
        processed_file = os.path.join(base_path, "elisa_processed_data.csv")
        if os.path.exists(processed_file):
            processed_data = pd.read_csv(processed_file)
        else:
            st.error(f"❌ Main data file not found: {processed_file}")
            return None, None, None, None, None
        
        # Try to load other analysis files
        excel_dir = os.path.join(base_path, "ELISA_Excel_Sheets")
        
        pivot_data = None
        changes_data = None
        demographics_data = None
        correlations_data = None
        
        if os.path.exists(excel_dir):
            pivot_file = os.path.join(excel_dir, "02_PivotTable.csv")
            changes_file = os.path.join(excel_dir, "05_LongitudinalChanges.csv")
            demo_file = os.path.join(excel_dir, "06_Demographics.csv")
            corr_file = os.path.join(excel_dir, "08_Correlations.csv")
            
            if os.path.exists(pivot_file):
                pivot_data = pd.read_csv(pivot_file, index_col=0)
            if os.path.exists(changes_file):
                changes_data = pd.read_csv(changes_file)
            if os.path.exists(demo_file):
                demographics_data = pd.read_csv(demo_file, index_col=0)
            if os.path.exists(corr_file):
                correlations_data = pd.read_csv(corr_file, index_col=0)
        
        return processed_data, pivot_data, changes_data, demographics_data, correlations_data
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None, None, None, None, None

def create_biomarker_overview(data):
    """Create biomarker overview visualizations"""
    if data is None:
        st.error("❌ No data available for biomarker overview")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 Total Subjects</h3>
            <h2>{data['SubjectID'].nunique()}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🧬 Biomarkers</h3>
            <h2>{data['Marker'].nunique()}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Data Points</h3>
            <h2>{len(data)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏥 Groups</h3>
            <h2>{data['Group'].nunique()}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Biomarker cards
    col1, col2 = st.columns(2)
    
    biomarkers = data['Marker'].unique()
    for i, marker in enumerate(biomarkers):
        marker_data = data[data['Marker'] == marker]
        avg_conc = marker_data['Concentration'].mean()
        units = marker_data['Units'].iloc[0] if 'Units' in marker_data.columns else 'units'
        
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(f"""
            <div class="biomarker-card">
                <h3>🧬 {marker}</h3>
                <h4>Avg: {avg_conc:.3f} {units}</h4>
                <p>Range: {marker_data['Concentration'].min():.3f} - {marker_data['Concentration'].max():.3f}</p>
            </div>
            """, unsafe_allow_html=True)

def create_concentration_plots(data):
    """Create concentration visualization plots"""
    if data is None:
        st.error("❌ No data available for concentration plots")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Box plot by group and timepoint
        fig_box = px.box(
            data, 
            x='NominalTime', 
            y='Concentration', 
            color='Group',
            facet_col='Marker',
            title="📊 Biomarker Concentrations by Group and Timepoint",
            labels={'Concentration': 'Concentration (pg/mL)', 'NominalTime': 'Timepoint'},
            color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        )
        fig_box.update_layout(height=500)
        st.plotly_chart(fig_box, width='stretch')
    
    with col2:
        # Violin plot
        fig_violin = px.violin(
            data,
            x='Group',
            y='Concentration',
            color='NominalTime',
            facet_col='Marker',
            title="🎻 Distribution of Concentrations by Group",
            box=True,
            color_discrete_sequence=['#FF9F43', '#10AC84']
        )
        fig_violin.update_layout(height=500)
        st.plotly_chart(fig_violin, width='stretch')
    
    # Individual trajectories
    st.subheader("📈 Individual Subject Trajectories")
    
    fig_trajectories = px.line(
        data,
        x='NominalTime',
        y='Concentration',
        color='Group',
        line_group='SubjectID',
        facet_col='Marker',
        title="Individual Subject Biomarker Trajectories Over Time",
        labels={'Concentration': 'Concentration (pg/mL)', 'NominalTime': 'Timepoint'}
    )
    fig_trajectories.update_traces(opacity=0.6)
    fig_trajectories.update_layout(height=600)
    st.plotly_chart(fig_trajectories, width='stretch')

def create_longitudinal_analysis(changes_data):
    """Create longitudinal change analysis"""
    if changes_data is None:
        st.error("❌ No longitudinal data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Percent change distribution
        fig_change = px.histogram(
            changes_data,
            x='Percent_Change',
            color='Group',
            facet_col='Marker',
            title="📊 Distribution of Percent Changes from Baseline",
            labels={'Percent_Change': 'Percent Change (%)', 'count': 'Number of Subjects'},
            opacity=0.7,
            nbins=15
        )
        fig_change.add_vline(x=-20, line_dash="dash", line_color="red", 
                            annotation_text="20% Reduction Threshold")
        fig_change.update_layout(height=500)
        st.plotly_chart(fig_change, width='stretch')
    
    with col2:
        # Scatter plot: baseline vs week 4
        # Create a copy with positive size values for plotting
        plot_data = changes_data.copy()
        plot_data['Size_for_Plot'] = abs(plot_data['Absolute_Change']) + 1  # Add 1 to ensure minimum size
        
        fig_scatter = px.scatter(
            plot_data,
            x='Concentration_Baseline',
            y='Concentration_Week4',
            color='Group',
            size='Size_for_Plot',
            facet_col='Marker',
            title="🎯 Baseline vs Week 4 Concentrations",
            labels={'Concentration_Baseline': 'Baseline Concentration',
                   'Concentration_Week4': 'Week 4 Concentration'},
            hover_data=['SubjectID', 'Percent_Change', 'Absolute_Change']
        )
        # Add diagonal line (no change)
        for i, marker in enumerate(changes_data['Marker'].unique()):
            marker_data = changes_data[changes_data['Marker'] == marker]
            min_val = min(marker_data['Concentration_Baseline'].min(), 
                         marker_data['Concentration_Week4'].min())
            max_val = max(marker_data['Concentration_Baseline'].max(), 
                         marker_data['Concentration_Week4'].max())
            fig_scatter.add_shape(
                type="line",
                x0=min_val, y0=min_val,
                x1=max_val, y1=max_val,
                line=dict(color="black", width=1, dash="dash"),
                row=1, col=i+1
            )
        fig_scatter.update_layout(height=500)
        st.plotly_chart(fig_scatter, width='stretch')

def create_responder_analysis(changes_data):
    """Create responder analysis visualizations"""
    if changes_data is None:
        st.error("❌ No responder data available")
        return
    
    # Calculate response rates
    response_summary = changes_data.groupby(['Group', 'Marker']).agg({
        'Responder_20pct': ['sum', 'count'],
        'Percent_Change': ['mean', 'std']
    }).round(2)
    response_summary.columns = ['_'.join(col).strip() for col in response_summary.columns.values]
    response_summary['Response_Rate'] = (response_summary['Responder_20pct_sum'] / 
                                       response_summary['Responder_20pct_count'] * 100).round(1)
    response_summary = response_summary.reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Response rate bar chart
        fig_response = px.bar(
            response_summary,
            x='Group',
            y='Response_Rate',
            color='Marker',
            title="🎯 Response Rate by Group and Biomarker (≥20% Reduction)",
            labels={'Response_Rate': 'Response Rate (%)', 'Group': 'Treatment Group'},
            text='Response_Rate',
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        fig_response.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_response.update_layout(height=500)
        st.plotly_chart(fig_response, width='stretch')
    
    with col2:
        # Waterfall chart for each group
        st.subheader("💧 Change Distribution by Group")
        
        for group in changes_data['Group'].unique():
            group_data = changes_data[changes_data['Group'] == group]
            
            fig_waterfall = go.Figure()
            
            for marker in group_data['Marker'].unique():
                marker_data = group_data[group_data['Marker'] == marker]
                
                fig_waterfall.add_trace(go.Box(
                    y=marker_data['Percent_Change'],
                    name=f"{group} - {marker}",
                    boxpoints='all',
                    jitter=0.3,
                    pointpos=-1.8
                ))
            
            fig_waterfall.add_hline(y=-20, line_dash="dash", line_color="red",
                                  annotation_text="Response Threshold")
            fig_waterfall.update_layout(
                title=f"Percent Changes - {group}",
                yaxis_title="Percent Change (%)",
                height=300
            )
            st.plotly_chart(fig_waterfall, width='stretch')

def create_demographic_analysis(data, demographics_data):
    """Create demographic analysis"""
    if data is None:
        st.error("❌ No data available for demographic analysis")
        return
    
    # Subject demographics
    subjects = data.drop_duplicates('SubjectID')[['SubjectID', 'Group', 'age', 'sex', 'bmi']]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Age distribution
        fig_age = px.histogram(
            subjects,
            x='age',
            color='Group',
            title="👥 Age Distribution by Group",
            labels={'age': 'Age (years)', 'count': 'Number of Subjects'},
            opacity=0.7,
            nbins=10
        )
        st.plotly_chart(fig_age, width='stretch')
    
    with col2:
        # Sex distribution
        sex_counts = subjects.groupby(['Group', 'sex']).size().reset_index(name='count')
        fig_sex = px.bar(
            sex_counts,
            x='Group',
            y='count',
            color='sex',
            title="⚧ Sex Distribution by Group",
            labels={'count': 'Number of Subjects'},
            color_discrete_map={'M': '#4A90E2', 'F': '#F5A623'}
        )
        st.plotly_chart(fig_sex, width='stretch')
    
    with col3:
        # BMI distribution
        fig_bmi = px.box(
            subjects,
            x='Group',
            y='bmi',
            title="📊 BMI Distribution by Group",
            labels={'bmi': 'BMI (kg/m²)'},
            color='Group'
        )
        st.plotly_chart(fig_bmi, width='stretch')
    
    # Demographics summary table
    st.subheader("📋 Demographic Summary")
    
    demo_summary = subjects.groupby('Group').agg({
        'age': ['count', 'mean', 'std'],
        'bmi': ['mean', 'std']
    }).round(2)
    demo_summary.columns = ['_'.join(col).strip() for col in demo_summary.columns.values]
    demo_summary['Female_pct'] = subjects.groupby('Group')['sex'].apply(
        lambda x: (x == 'F').mean() * 100
    ).round(1)
    
    st.dataframe(demo_summary, width='stretch')

def create_correlation_analysis(correlations_data, data):
    """Create correlation analysis"""
    if correlations_data is None and data is None:
        st.error("❌ No correlation data available")
        return
    
    # If correlation data not available, compute it
    if correlations_data is None and data is not None:
        numeric_cols = ['Concentration', 'RawSignal', 'age', 'bmi']
        available_cols = [col for col in numeric_cols if col in data.columns]
        correlations_data = data[available_cols].corr()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Correlation heatmap
        fig_corr = px.imshow(
            correlations_data,
            title="🔥 Correlation Matrix Heatmap",
            color_continuous_scale='RdBu',
            aspect='auto',
            text_auto=True
        )
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, width='stretch')
    
    with col2:
        # Correlation network (if significant correlations exist)
        st.subheader("🕸️ Correlation Network")
        
        # Find significant correlations (>0.3 or <-0.3)
        mask = np.abs(correlations_data) > 0.3
        mask = mask & (correlations_data != 1.0)  # Exclude self-correlations
        
        if mask.any().any():
            significant_corr = []
            for i in range(len(correlations_data.columns)):
                for j in range(i+1, len(correlations_data.columns)):
                    if mask.iloc[i, j]:
                        significant_corr.append({
                            'Variable1': correlations_data.columns[i],
                            'Variable2': correlations_data.columns[j],
                            'Correlation': correlations_data.iloc[i, j]
                        })
            
            if significant_corr:
                corr_df = pd.DataFrame(significant_corr)
                
                for _, row in corr_df.iterrows():
                    color = "🔴" if row['Correlation'] < 0 else "🔵"
                    st.write(f"{color} **{row['Variable1']}** ↔ **{row['Variable2']}**: {row['Correlation']:.3f}")
            else:
                st.write("No significant correlations found (|r| > 0.3)")
        else:
            st.write("No significant correlations found")

def create_raw_signal_analysis(data):
    """Create raw signal vs concentration analysis"""
    if data is None:
        st.error("❌ No data available for raw signal analysis")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Raw signal vs concentration scatter plot
        fig_signal = px.scatter(
            data,
            x='RawSignal',
            y='Concentration',
            color='Marker',
            size='Concentration',
            facet_col='NominalTime',
            title="📊 Raw Signal vs Concentration Relationship",
            labels={'RawSignal': 'Raw Signal (OD)', 'Concentration': 'Concentration'},
            hover_data=['SubjectID', 'Group']
        )
        fig_signal.update_layout(height=500)
        st.plotly_chart(fig_signal, width='stretch')
    
    with col2:
        # Signal-to-concentration ratio by group
        data['Signal_Conc_Ratio'] = data['RawSignal'] / data['Concentration']
        
        fig_ratio = px.box(
            data,
            x='Group',
            y='Signal_Conc_Ratio',
            color='Marker',
            title="📈 Signal-to-Concentration Ratio by Group",
            labels={'Signal_Conc_Ratio': 'Signal/Concentration Ratio'}
        )
        fig_ratio.update_layout(height=500)
        st.plotly_chart(fig_ratio, width='stretch')
    
    # Raw signal distribution by timepoint
    st.subheader("🔬 Raw Signal Distribution Analysis")
    
    fig_signal_dist = px.histogram(
        data,
        x='RawSignal',
        color='NominalTime',
        facet_col='Marker',
        title="Raw Signal Distribution by Biomarker and Timepoint",
        labels={'RawSignal': 'Raw Signal (OD)', 'count': 'Frequency'},
        opacity=0.7
    )
    fig_signal_dist.update_layout(height=400)
    st.plotly_chart(fig_signal_dist, width='stretch')

def create_dose_response_analysis(data):
    """Create dose-response analysis"""
    if data is None:
        st.error("❌ No data available for dose-response analysis")
        return
    
    st.subheader("💊 Dose-Response Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Concentration by dose level
        fig_dose = px.box(
            data,
            x='DoseLevel',
            y='Concentration',
            color='NominalTime',
            facet_col='Marker',
            title="📊 Biomarker Concentration by Dose Level",
            labels={'DoseLevel': 'Dose Level', 'Concentration': 'Concentration'}
        )
        fig_dose.update_layout(height=500)
        st.plotly_chart(fig_dose, width='stretch')
    
    with col2:
        # Dose response summary table
        dose_summary = data.groupby(['DoseLevel', 'Marker', 'NominalTime']).agg({
            'Concentration': ['count', 'mean', 'std'],
            'SubjectID': 'nunique'
        }).round(3)
        dose_summary.columns = ['_'.join(col).strip() for col in dose_summary.columns.values]
        dose_summary = dose_summary.reset_index()
        
        st.subheader("📋 Dose-Response Summary")
        st.dataframe(dose_summary, width='stretch')

def create_quality_control_analysis(data):
    """Create quality control analysis"""
    if data is None:
        st.error("❌ No data available for QC analysis")
        return
    
    st.subheader("🔬 Quality Control Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # QC flags summary
        flag_counts = data['flag'].value_counts()
        st.metric("Total Measurements", len(data))
        st.metric("QC Flags", len(flag_counts))
        for flag, count in flag_counts.items():
            st.write(f"**{flag}**: {count} measurements")
    
    with col2:
        # Well distribution
        st.subheader("🧪 Well Usage")
        well_counts = data['well'].value_counts().head(10)
        st.bar_chart(well_counts)
    
    with col3:
        # Assay run info
        st.metric("Assay Runs", data['AssayRunID'].nunique())
        st.metric("Sample IDs", data['SampleID'].nunique())
        st.metric("Matrix Types", data['Matrix'].nunique())
        
        # Collection timing
        collection_dates = pd.to_datetime(data['CollectionDateTime']).dt.date.value_counts()
        st.subheader("📅 Collection Dates")
        for date, count in collection_dates.items():
            st.write(f"**{date}**: {count} samples")

def create_advanced_analytics(data):
    """Create advanced analytics section"""
    if data is None:
        st.error("❌ No data available for advanced analytics")
        return
    
    st.subheader("🤖 Advanced Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Biomarker ratio analysis
        st.subheader("🧬 Biomarker Ratios")
        
        # Calculate IL-6/CRP ratio for each subject and timepoint
        pivot_for_ratio = data.pivot_table(
            values='Concentration',
            index=['SubjectID', 'Group', 'NominalTime'],
            columns='Marker',
            aggfunc='mean'
        ).reset_index()
        
        if 'IL-6' in pivot_for_ratio.columns and 'CRP' in pivot_for_ratio.columns:
            pivot_for_ratio['IL6_CRP_Ratio'] = pivot_for_ratio['IL-6'] / pivot_for_ratio['CRP']
            
            fig_ratio = px.box(
                pivot_for_ratio,
                x='Group',
                y='IL6_CRP_Ratio',
                color='NominalTime',
                title="IL-6/CRP Ratio by Group and Timepoint",
                labels={'IL6_CRP_Ratio': 'IL-6/CRP Ratio'}
            )
            st.plotly_chart(fig_ratio, width='stretch')
            
            # Show ratio statistics
            ratio_stats = pivot_for_ratio.groupby(['Group', 'NominalTime'])['IL6_CRP_Ratio'].agg(['mean', 'std', 'median']).round(3)
            st.dataframe(ratio_stats, width='stretch')
        else:
            st.info("💡 Biomarker ratio analysis requires both IL-6 and CRP data")
    
    with col2:
        # Temporal analysis
        st.subheader("⏰ Temporal Analysis")
        
        # Time between collection and measurement
        data_temp = data.copy()
        data_temp['CollectionDateTime'] = pd.to_datetime(data_temp['CollectionDateTime'])
        data_temp['MeasurementTime'] = pd.to_datetime(data_temp['MeasurementTime'])
        
        if not data_temp['CollectionDateTime'].equals(data_temp['MeasurementTime']):
            data_temp['Processing_Time_Hours'] = (
                data_temp['MeasurementTime'] - data_temp['CollectionDateTime']
            ).dt.total_seconds() / 3600
            
            fig_processing = px.histogram(
                data_temp,
                x='Processing_Time_Hours',
                title="Sample Processing Time Distribution",
                labels={'Processing_Time_Hours': 'Hours from Collection to Measurement'}
            )
            st.plotly_chart(fig_processing, width='stretch')
        else:
            st.info("💡 Collection and measurement times are identical")
        
        # Actual time analysis
        actual_time_dist = data['ActualTime'].value_counts()
        st.subheader("📋 Actual Time Distribution")
        for time, count in actual_time_dist.items():
            st.write(f"**{time}**: {count} measurements")

def create_statistical_tests(data):
    """Create statistical analysis section"""
    if data is None:
        st.error("❌ No data available for statistical tests")
        return
    
    st.subheader("📊 Statistical Analysis")
    
    # Perform t-tests between groups for each biomarker and timepoint
    results = []
    
    for marker in data['Marker'].unique():
        for timepoint in data['NominalTime'].unique():
            subset = data[(data['Marker'] == marker) & (data['NominalTime'] == timepoint)]
            groups = subset['Group'].unique()
            
            if len(groups) >= 2:
                group1_data = subset[subset['Group'] == groups[0]]['Concentration']
                group2_data = subset[subset['Group'] == groups[1]]['Concentration']
                
                if len(group1_data) > 0 and len(group2_data) > 0:
                    t_stat, p_value = stats.ttest_ind(group1_data, group2_data)
                    
                    # Cohen's d effect size
                    pooled_std = np.sqrt(((len(group1_data) - 1) * group1_data.std()**2 + 
                                        (len(group2_data) - 1) * group2_data.std()**2) / 
                                       (len(group1_data) + len(group2_data) - 2))
                    cohens_d = (group1_data.mean() - group2_data.mean()) / pooled_std if pooled_std > 0 else 0
                    
                    results.append({
                        'Biomarker': marker,
                        'Timepoint': timepoint,
                        'Group1': f"{groups[0]} (n={len(group1_data)})",
                        'Group2': f"{groups[1]} (n={len(group2_data)})",
                        'Mean1': group1_data.mean(),
                        'Mean2': group2_data.mean(),
                        'T-statistic': t_stat,
                        'P-value': p_value,
                        'Cohens_d': cohens_d,
                        'Significance': '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'ns'
                    })
    
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.round(4)
        
        st.dataframe(results_df, width='stretch')
        
        # Significance summary
        sig_counts = results_df['Significance'].value_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Highly Significant (***)", sig_counts.get('***', 0))
        with col2:
            st.metric("Very Significant (**)", sig_counts.get('**', 0))
        with col3:
            st.metric("Significant (*)", sig_counts.get('*', 0))
        with col4:
            st.metric("Not Significant (ns)", sig_counts.get('ns', 0))
    else:
        st.write("No statistical comparisons could be performed")

# Main Application
def main():
    # Header
    st.markdown('<h1 class="main-header">🧬 ELISA Biomarker Analysis Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 2rem;">Comprehensive visualization and analysis of ELISA biomarker data</p>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner("📊 Loading ELISA analysis data..."):
        processed_data, pivot_data, changes_data, demographics_data, correlations_data = load_elisa_data()
    
    if processed_data is None:
        st.error("❌ Could not load ELISA data. Please ensure the analysis files are available.")
        st.info("💡 Run the ELISA data processing script first to generate the required files.")
        return
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Dashboard Controls")
        
        # Data filters
        st.subheader("📊 Data Filters")
        
        selected_groups = st.multiselect(
            "Select Groups:",
            options=processed_data['Group'].unique(),
            default=list(processed_data['Group'].unique())
        )
        
        selected_markers = st.multiselect(
            "Select Biomarkers:",
            options=processed_data['Marker'].unique(),
            default=list(processed_data['Marker'].unique())
        )
        
        selected_timepoints = st.multiselect(
            "Select Timepoints:",
            options=processed_data['NominalTime'].unique(),
            default=list(processed_data['NominalTime'].unique())
        )
        
        # Additional filters
        st.subheader("🎛️ Advanced Filters")
        
        selected_dose_levels = st.multiselect(
            "Select Dose Levels:",
            options=processed_data['DoseLevel'].unique(),
            default=list(processed_data['DoseLevel'].unique())
        )
        
        # Concentration range filter
        conc_min, conc_max = st.slider(
            "Concentration Range:",
            min_value=float(processed_data['Concentration'].min()),
            max_value=float(processed_data['Concentration'].max()),
            value=(float(processed_data['Concentration'].min()), float(processed_data['Concentration'].max())),
            step=0.1
        )
        
        # Quality filter
        include_qc_flags = st.multiselect(
            "QC Flags to Include:",
            options=processed_data['flag'].unique(),
            default=list(processed_data['flag'].unique())
        )
        
        # Filter data
        filtered_data = processed_data[
            (processed_data['Group'].isin(selected_groups)) &
            (processed_data['Marker'].isin(selected_markers)) &
            (processed_data['NominalTime'].isin(selected_timepoints)) &
            (processed_data['DoseLevel'].isin(selected_dose_levels)) &
            (processed_data['Concentration'] >= conc_min) &
            (processed_data['Concentration'] <= conc_max) &
            (processed_data['flag'].isin(include_qc_flags))
        ]
        
        st.markdown("---")
        st.subheader("📈 Filtered Data Summary")
        st.metric("Subjects", filtered_data['SubjectID'].nunique())
        st.metric("Data Points", len(filtered_data))
        
        # Study information
        st.markdown("---")
        st.subheader("ℹ️ Study Info")
        st.write("**Analysis Date:**", datetime.now().strftime("%B %d, %Y"))
        st.write("**Data Source:** ELISA CSV Processing")
        st.write("**Analysis Type:** Longitudinal Biomarker Study")
        
        # Dashboard URL information
        st.markdown("---")
        st.subheader("🌐 Dashboard Access")
        st.success("**Dashboard URL:**")
        st.code("http://localhost:8501")
        st.info("💡 Copy this URL to share or bookmark the dashboard")
        
        # Quick status
        st.metric("Dashboard Status", "🟢 ONLINE")
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🏠 Overview", 
        "📊 Concentrations", 
        "📈 Longitudinal", 
        "🎯 Responders", 
        "👥 Demographics", 
        "🔬 Statistics",
        "📡 Raw Signals",
        "💊 Dose-Response",
        "🔬 Quality Control"
    ])
    
    with tab1:
        st.header("🏠 Study Overview")
        create_biomarker_overview(filtered_data)
        
        # Enhanced data summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Data Dimensions")
            st.write(f"**Total Variables**: {len(filtered_data.columns)}")
            st.write(f"**Raw Signal Range**: {filtered_data['RawSignal'].min():.3f} - {filtered_data['RawSignal'].max():.3f}")
            st.write(f"**Dose Levels**: {', '.join(filtered_data['DoseLevel'].unique())}")
            st.write(f"**Quality Flags**: {', '.join(filtered_data['flag'].unique())}")
            st.write(f"**Matrix Type**: {', '.join(filtered_data['Matrix'].unique())}")
            st.write(f"**Wells Used**: {filtered_data['well'].nunique()} unique wells")
        
        with col2:
            st.subheader("⏰ Temporal Coverage")
            st.write(f"**Assay Runs**: {filtered_data['AssayRunID'].nunique()}")
            st.write(f"**Sample IDs**: {filtered_data['SampleID'].nunique()}")
            collection_dates = pd.to_datetime(filtered_data['CollectionDateTime']).dt.date.nunique()
            st.write(f"**Collection Days**: {collection_dates}")
            st.write(f"**Actual Times**: {', '.join(filtered_data['ActualTime'].unique())}")
            st.write(f"**Replicates**: {filtered_data['Replicate'].nunique()}")
        
        # Data preview with all key columns
        st.subheader("📋 Complete Data Preview")
        display_cols = ['SubjectID', 'Group', 'Marker', 'NominalTime', 'Concentration', 'RawSignal', 'DoseLevel', 'age', 'sex', 'bmi', 'well', 'flag']
        st.dataframe(filtered_data[display_cols].head(10), width='stretch')
        
        # Data completeness check
        st.subheader("🔍 Data Completeness")
        completeness = {}
        for col in filtered_data.columns:
            non_null = filtered_data[col].notna().sum()
            completeness[col] = f"{non_null}/{len(filtered_data)} ({non_null/len(filtered_data)*100:.1f}%)"
        
        completeness_df = pd.DataFrame(list(completeness.items()), columns=['Variable', 'Completeness'])
        st.dataframe(completeness_df, width='stretch')
    
    with tab2:
        st.header("📊 Biomarker Concentrations")
        create_concentration_plots(filtered_data)
    
    with tab3:
        st.header("📈 Longitudinal Analysis")
        if changes_data is not None:
            # Filter changes data
            filtered_changes = changes_data[
                (changes_data['Group'].isin(selected_groups)) &
                (changes_data['Marker'].isin(selected_markers))
            ]
            create_longitudinal_analysis(filtered_changes)
        else:
            st.info("💡 Longitudinal change data not available. Run the complete analysis pipeline.")
    
    with tab4:
        st.header("🎯 Responder Analysis")
        if changes_data is not None:
            filtered_changes = changes_data[
                (changes_data['Group'].isin(selected_groups)) &
                (changes_data['Marker'].isin(selected_markers))
            ]
            create_responder_analysis(filtered_changes)
        else:
            st.info("💡 Responder analysis data not available. Run the complete analysis pipeline.")
    
    with tab5:
        st.header("👥 Demographics Analysis")
        create_demographic_analysis(filtered_data, demographics_data)
    
    with tab6:
        st.header("🔬 Statistical Analysis")
        create_statistical_tests(filtered_data)
        
        st.markdown("---")
        st.subheader("🔥 Correlation Analysis")
        create_correlation_analysis(correlations_data, filtered_data)
        
        st.markdown("---")
        st.subheader("🤖 Advanced Analytics")
        create_advanced_analytics(filtered_data)
    
    with tab7:
        st.header("📡 Raw Signal Analysis")
        create_raw_signal_analysis(filtered_data)
    
    with tab8:
        st.header("💊 Dose-Response Analysis")
        create_dose_response_analysis(filtered_data)
    
    with tab9:
        st.header("🔬 Quality Control Analysis")
        create_quality_control_analysis(filtered_data)
    
    # Footer
    st.markdown("---")
    
    # Add URL information
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🌐 **Dashboard URL**: http://localhost:8501")
    with col2:
        st.info("📊 **Data Files**: All ELISA analysis loaded")
    with col3:
        st.info("🔄 **Status**: Dashboard fully operational")
    
    st.markdown(
        f"""
        <div style='text-align: center; color: #666;'>
            <p>🧬 ELISA Biomarker Analysis Dashboard • Built with Streamlit & Plotly</p>
            <p>📊 Powered by pandas, scipy, and advanced statistical analysis • © 2025</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
