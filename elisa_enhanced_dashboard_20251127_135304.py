#!/usr/bin/env python3
"""
🧬 ELISA Dashboard - Full Featured & Stable Version
=================================================
Complete ELISA biomarker analysis with all visualizations
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import shapiro, levene, kruskal, mannwhitneyu, wilcoxon, chi2_contingency
from scipy import stats
import numpy as np
import os
from io import BytesIO

st.set_page_config(
    page_title="🧬 ELISA Test Dashboard", 
    page_icon="🧬",
    layout="wide"
)

def get_color_palette(scheme, groups=None, custom_colors=None):
    """Get color palette based on selected scheme"""
    if scheme == "Custom" and custom_colors:
        return custom_colors
    
    # Define color schemes with fallbacks for missing ones
    try:
        color_schemes = {
            "Default (Plotly)": px.colors.qualitative.Plotly,
            "Viridis": px.colors.sequential.Viridis,
            "Plasma": px.colors.sequential.Plasma,
            "Set1": px.colors.qualitative.Set1,
            "Set2": px.colors.qualitative.Set2,
            "Set3": px.colors.qualitative.Set3,
            "Pastel1": px.colors.qualitative.Pastel1,
            "Pastel2": px.colors.qualitative.Pastel2,
            "Dark2": px.colors.qualitative.Dark2,
            "Paired": ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896']
        }
    except AttributeError:
        # Fallback colors if some palettes are not available
        color_schemes = {
            "Default (Plotly)": ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'],
            "Viridis": ['#440154', '#482777', '#3f4a8a', '#31678e', '#26838f', '#1f9d8a', '#6cce5a', '#b6de2b'],
            "Plasma": ['#0d0887', '#5d01a6', '#9c179e', '#d0456c', '#f0704a', '#fca636', '#fcffa4'],
            "Set1": ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf'],
            "Set2": ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3'],
            "Set3": ['#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3', '#fdb462', '#b3de69', '#fccde5'],
            "Pastel1": ['#fbb4ae', '#b3cde3', '#ccebc5', '#decbe4', '#fed9a6', '#ffffcc', '#e5d8bd', '#fddaec'],
            "Pastel2": ['#b3e2cd', '#fdcdac', '#cbd5e8', '#f4cae4', '#e6f5c9', '#fff2ae', '#f1e2cc', '#cccccc'],
            "Dark2": ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d', '#666666'],
            "Paired": ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896']
        }
    
    if groups is not None and scheme in color_schemes:
        colors = color_schemes[scheme]
        return {group: colors[i % len(colors)] for i, group in enumerate(groups)}
    
    return color_schemes.get(scheme, color_schemes["Default (Plotly)"])

def apply_theme_styling(fig, theme, opacity=0.7):
    """Apply background theme styling to plotly figure"""
    if theme == "Dark":
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(30,30,30,0.8)',
            font_color='white'
        )
    elif theme == "Light":
        fig.update_layout(
            plot_bgcolor='rgba(255,255,255,0.9)',
            paper_bgcolor='rgba(248,248,248,0.8)',
            font_color='black'
        )
    elif theme == "Colorful":
        fig.update_layout(
            plot_bgcolor='rgba(240,248,255,0.6)',
            paper_bgcolor='rgba(250,235,215,0.7)',
            font_color='darkblue'
        )
    
    # Update traces opacity
    fig.update_traces(opacity=opacity)
    
    return fig

def generate_sample_elisa_data():
    """Generate sample ELISA data for demonstration"""
    np.random.seed(42)  # For reproducible results
    
    # Parameters
    n_subjects = 20
    biomarkers = ['TNF-alpha', 'IL-8', 'VEGF']
    timepoints = ['Baseline', 'Week 2', 'Week 8']
    groups = ['Treatment A', 'Treatment B', 'Control']
    
    data = []
    
    for subject_id in range(1, n_subjects + 1):
        group = np.random.choice(groups)
        age = np.random.randint(25, 75)
        sex = np.random.choice(['M', 'F'])
        bmi = np.random.normal(25, 4)
        
        for timepoint in timepoints:
            for biomarker in biomarkers:
                # Generate realistic concentration values based on biomarker
                if biomarker == 'TNF-alpha':
                    base_conc = np.random.lognormal(1.5, 0.8)  # 2-20 pg/mL range
                    units = 'pg/mL'
                elif biomarker == 'IL-8':
                    base_conc = np.random.lognormal(2.0, 0.6)  # 5-50 pg/mL range  
                    units = 'pg/mL'
                else:  # VEGF
                    base_conc = np.random.lognormal(4.0, 0.5)  # 20-200 pg/mL range
                    units = 'pg/mL'
                
                # Add group effects
                if group == 'Treatment A' and timepoint != 'Baseline':
                    base_conc *= 0.7  # 30% reduction
                elif group == 'Treatment B' and timepoint != 'Baseline':
                    base_conc *= 0.8  # 20% reduction
                
                # Add time effects
                if timepoint == 'Week 2':
                    base_conc *= np.random.normal(0.95, 0.1)
                elif timepoint == 'Week 8':
                    base_conc *= np.random.normal(0.85, 0.15)
                
                # Generate raw signal (OD values)
                raw_signal = base_conc * np.random.normal(0.1, 0.02) + np.random.normal(0.05, 0.01)
                
                # QC flags
                qc_flag = 'OK'
                if raw_signal < 0.02 or raw_signal > 3.0:
                    qc_flag = 'Warning'
                if raw_signal < 0.01 or raw_signal > 4.0:
                    qc_flag = 'Failed'
                
                data.append({
                    'MeasurementID': f'SAMP_{subject_id:03d}_{timepoint}_{biomarker}',
                    'AssayRunID': f'RUN_{np.random.randint(100, 999)}',
                    'SampleID': f'SAMP_{subject_id:03d}_{timepoint}',
                    'SubjectID': f'SUBJ_{subject_id:03d}',
                    'Marker': biomarker,
                    'AnalyteID': f'ANL_{hash(biomarker) % 1000}',
                    'Replicate': 1,
                    'RawSignal': round(raw_signal, 4),
                    'Concentration': round(base_conc, 3),
                    'Units': units,
                    'MeasurementTime': f'2025-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d} 09:00:00+00:00',
                    'Matrix': 'Serum',
                    'NominalTime': timepoint,
                    'ActualTime': f'{timepoint} + {np.random.randint(0, 48)}h',
                    'CollectionDateTime': f'2025-{np.random.randint(1,13):02d}-{np.random.randint(1,29):02d} 08:00:00+00:00',
                    'StudyID': 'DEMO_001',
                    'Group': group,
                    'DoseLevel': f'{np.random.choice([50, 100, 150])} mg' if group.startswith('Treatment') else 'Placebo',
                    'age': age,
                    'sex': sex,
                    'bmi': round(bmi, 1),
                    'well': f'{np.random.choice(["A", "B", "C", "D", "E", "F"])}{np.random.randint(1, 13)}',
                    'flag': qc_flag
                })
    
    return pd.DataFrame(data)

def validate_elisa_data(df):
    """Validate ELISA data structure and suggest fixes"""
    issues = []
    suggestions = []
    
    # Check for essential columns
    essential_cols = ['SubjectID', 'Marker', 'Concentration']
    missing_essential = [col for col in essential_cols if col not in df.columns]
    
    if missing_essential:
        issues.append(f"Missing essential columns: {', '.join(missing_essential)}")
        suggestions.append("Add missing columns or rename existing ones")
    
    # Check for recommended columns
    recommended_cols = ['Group', 'NominalTime', 'RawSignal']
    missing_recommended = [col for col in recommended_cols if col not in df.columns]
    
    if missing_recommended:
        issues.append(f"Missing recommended columns: {', '.join(missing_recommended)}")
        suggestions.append("Add these columns for full dashboard functionality")
    
    # Check data types
    if 'Concentration' in df.columns:
        if not pd.api.types.is_numeric_dtype(df['Concentration']):
            issues.append("Concentration column is not numeric")
            suggestions.append("Convert Concentration to numeric values")
    
    return issues, suggestions

def display_data_info(df):
    """Display comprehensive data information"""
    st.markdown("### 📋 Dataset Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Rows**: {len(df)}")
        st.info(f"**Columns**: {len(df.columns)}")
    
    with col2:
        if 'SubjectID' in df.columns:
            st.info(f"**Subjects**: {df['SubjectID'].nunique()}")
        if 'Marker' in df.columns:
            st.info(f"**Biomarkers**: {', '.join(df['Marker'].unique()[:3])}")
    
    with col3:
        if 'Group' in df.columns:
            st.info(f"**Groups**: {', '.join(df['Group'].unique())}")
        if 'NominalTime' in df.columns:
            st.info(f"**Timepoints**: {', '.join(df['NominalTime'].unique())}")
    
    # Data validation
    issues, suggestions = validate_elisa_data(df)
    
    if issues:
        st.warning("⚠️ **Data Issues Found:**")
        for issue in issues:
            st.markdown(f"- {issue}")
        
        with st.expander("💡 Suggestions to Fix Issues"):
            for suggestion in suggestions:
                st.markdown(f"- {suggestion}")
    else:
        st.success("✅ Data structure looks good!")

def main():
    st.title("🧬 ELISA Biomarker Analysis Dashboard")
    st.markdown("### 📊 Complete Analysis with Advanced Visualizations")
    
    # Initialize session state for data management
    if 'current_df' not in st.session_state:
        # Load default data
        data_file = "elisa_processed_data.csv"
        if os.path.exists(data_file):
            st.session_state.current_df = pd.read_csv(data_file)
            st.session_state.data_source = "elisa_processed_data.csv"
        else:
            # Generate sample data if no default file exists
            st.warning("⚠️ Default data file not found. Loading sample data.")
            st.session_state.current_df = generate_sample_elisa_data()
            st.session_state.data_source = "Sample Demo Data"
    
    df = st.session_state.current_df
    
    # Display current data info
    st.success(f"✅ Current Dataset: {st.session_state.data_source}")
    display_data_info(df)
    
    # Sidebar filters
    st.sidebar.header("🎛️ Analysis Controls")
    
    # Group filter
    if 'Group' in df.columns:
        selected_groups = st.sidebar.multiselect(
            "👥 Select Treatment Groups",
            options=df['Group'].unique(),
            default=df['Group'].unique()
        )
        df_filtered = df[df['Group'].isin(selected_groups)]
    else:
        df_filtered = df
    
    # Biomarker filter
    if 'Marker' in df.columns:
        selected_markers = st.sidebar.multiselect(
            "🧬 Select Biomarkers",
            options=df['Marker'].unique(), 
            default=df['Marker'].unique()
        )
        df_filtered = df_filtered[df_filtered['Marker'].isin(selected_markers)]
    
    st.sidebar.info(f"📊 Filtered data: {len(df_filtered)} measurements")
    
    # Data management section
    st.sidebar.markdown("---")
    st.sidebar.header("📂 Data Management")
    
    # Option to load different datasets
    data_option = st.sidebar.selectbox(
        "🔄 Choose Data Source",
        options=[
            "Current Dataset (elisa_processed_data.csv)",
            "Upload New CSV File",
            "Load Different Existing File",
            "Sample Demo Data"
        ],
        index=0
    )
    
    # Handle different data loading options
    if data_option == "Upload New CSV File":
            uploaded_file = st.sidebar.file_uploader(
                "📤 Upload ELISA CSV File",
                type=['csv'],
                help="Upload a CSV file with ELISA data. Should contain columns like SubjectID, Marker, Concentration, Group, etc."
            )
            
            if uploaded_file is not None:
                try:
                    new_df = pd.read_csv(uploaded_file)
                    st.sidebar.success(f"✅ Uploaded: {len(new_df)} rows")
                    
                    # Option to replace or append data
                    data_action = st.sidebar.radio(
                        "📊 Data Action",
                        ["Replace current data", "Append to current data"]
                    )
                    
                    if st.sidebar.button("🔄 Apply New Data"):
                        if data_action == "Replace current data":
                            st.session_state.current_df = new_df
                            st.session_state.data_source = uploaded_file.name
                            st.sidebar.success("✅ Data replaced!")
                        else:
                            # Append data
                            st.session_state.current_df = pd.concat([st.session_state.current_df, new_df], ignore_index=True)
                            st.session_state.data_source = f"{st.session_state.data_source} + {uploaded_file.name}"
                            st.sidebar.success(f"✅ Data appended! Total: {len(st.session_state.current_df)} rows")
                        st.rerun()
                        
                except Exception as e:
                    st.sidebar.error(f"❌ Error loading file: {e}")
    
    elif data_option == "Load Different Existing File":
            # List available CSV files in the directory
            csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
            
            if csv_files:
                selected_file = st.sidebar.selectbox(
                    "📁 Select File",
                    options=csv_files
                )
                
                if st.sidebar.button("📂 Load Selected File"):
                    try:
                        st.session_state.current_df = pd.read_csv(selected_file)
                        st.session_state.data_source = selected_file
                        st.sidebar.success(f"✅ Loaded {selected_file}: {len(st.session_state.current_df)} rows")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"❌ Error loading {selected_file}: {e}")
            else:
                st.sidebar.info("📝 No CSV files found in current directory")
    
    elif data_option == "Sample Demo Data":
            if st.sidebar.button("🎲 Generate Sample Data"):
                # Generate sample ELISA data
                sample_df = generate_sample_elisa_data()
                
                # Option to replace or append
                sample_action = st.sidebar.radio(
                    "📊 Sample Data Action",
                    ["Replace with sample", "Append sample data"]
                )
                
                if sample_action == "Replace with sample":
                    st.session_state.current_df = sample_df
                    st.session_state.data_source = "Sample Demo Data"
                    st.sidebar.success("✅ Sample data loaded!")
                else:
                    st.session_state.current_df = pd.concat([st.session_state.current_df, sample_df], ignore_index=True)
                    st.session_state.data_source = f"{st.session_state.data_source} + Sample Data"
                    st.sidebar.success(f"✅ Sample data added! Total: {len(st.session_state.current_df)} rows")
                st.rerun()
    
    # Data export options
    st.sidebar.markdown("**📤 Export Options:**")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💾 Save CSV"):
                csv_data = df_filtered.to_csv(index=False)
                st.sidebar.download_button(
                    label="⬇️ Download",
                    data=csv_data,
                    file_name=f"elisa_filtered_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("📊 Save Excel"):
                try:
                    # Try to export as Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_filtered.to_excel(writer, sheet_name='ELISA_Data', index=False)
                    excel_data = output.getvalue()
                    
                    st.sidebar.download_button(
                        label="⬇️ Download Excel",
                        data=excel_data,
                        file_name=f"elisa_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    # Fallback to CSV if Excel libraries not available
                    csv_data = df_filtered.to_csv(index=False)
                    st.sidebar.download_button(
                        label="⬇️ Download CSV",
                        data=csv_data,
                        file_name=f"elisa_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
                    st.sidebar.info("📝 Excel export not available, downloaded as CSV")
    
    # Color customization section
    st.sidebar.markdown("---")
    st.sidebar.header("🎨 Color Customization")
    
    # Color scheme selection
    color_scheme = st.sidebar.selectbox(
            "🌈 Choose Color Scheme",
            options=[
                "Default (Plotly)",
                "Set1",
                "Set2", 
                "Dark2",
                "Paired",
                "Pastel1",
                "Pastel2",
                "Viridis", 
                "Plasma",
                "Custom"
            ],
            index=0
        )
        
    # Custom colors if selected
    custom_colors = {}
    if color_scheme == "Custom":
        st.sidebar.markdown("**🎯 Custom Group Colors:**")
        if 'Group' in df_filtered.columns:
            for group in df_filtered['Group'].unique():
                custom_colors[group] = st.sidebar.color_picker(
                    f"Color for {group}",
                    value="#1f77b4" if "Active" in group or "Treatment" in group else "#ff7f0e"
                )
    
    # Background customization
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🎨 Background Customization**")
    
    background_theme = st.sidebar.selectbox(
        "🎭 Background Theme",
        options=["Default", "Dark", "Light", "Colorful", "Custom"],
        index=0
    )
    
    # Custom background colors if selected
    custom_bg_color = "#ffffff"  # default white
    custom_sidebar_color = "#f0f2f6"  # default sidebar color
    custom_text_color = "#262730"  # default text color
    
    if background_theme == "Custom":
        st.sidebar.markdown("**🎨 Custom Background Colors:**")
        
        custom_bg_color = st.sidebar.color_picker(
            "Main Background Color",
            value="#ffffff",
            help="Choose the main dashboard background color"
        )
        
        custom_sidebar_color = st.sidebar.color_picker(
            "Sidebar Background Color",
            value="#f0f2f6",
            help="Choose the sidebar background color"
        )
        
        custom_text_color = st.sidebar.color_picker(
            "Text Color",
            value="#262730",
            help="Choose the main text color"
        )
        
        # Additional custom options
        custom_header_color = st.sidebar.color_picker(
            "Header Background Color",
            value="#ffffff",
            help="Choose the header background color"
        )
        
        custom_metric_color = st.sidebar.color_picker(
            "Metric Card Background",
            value="#f8f9fa",
            help="Choose the metric cards background color"
        )
    
    # Background gradient option
    use_gradient = st.sidebar.checkbox(
        "🌈 Use Gradient Background",
        value=False,
        help="Apply gradient effect to background"
    )
    
    if use_gradient and background_theme == "Custom":
        gradient_color2 = st.sidebar.color_picker(
            "Gradient End Color",
            value="#e3f2fd",
            help="Choose the second color for gradient"
        )
    
    # Quick background presets
    st.sidebar.markdown("**🎨 Quick Background Presets:**")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🌊 Ocean", help="Blue ocean theme"):
            st.session_state.bg_preset = "ocean"
            st.rerun()
        
        if st.button("🌿 Forest", help="Green forest theme"):
            st.session_state.bg_preset = "forest"
            st.rerun()
    
    with col2:
        if st.button("🌅 Sunset", help="Orange sunset theme"):
            st.session_state.bg_preset = "sunset"
            st.rerun()
        
        if st.button("🌙 Night", help="Dark night theme"):
            st.session_state.bg_preset = "night"
            st.rerun()
    
    # Apply preset colors if selected
    if 'bg_preset' in st.session_state:
        if st.session_state.bg_preset == "ocean":
            custom_bg_color = "#0066cc"
            custom_sidebar_color = "#004499"
            custom_text_color = "#ffffff"
        elif st.session_state.bg_preset == "forest":
            custom_bg_color = "#228b22"
            custom_sidebar_color = "#006400" 
            custom_text_color = "#ffffff"
        elif st.session_state.bg_preset == "sunset":
            custom_bg_color = "#ff7f50"
            custom_sidebar_color = "#ff6347"
            custom_text_color = "#ffffff"
        elif st.session_state.bg_preset == "night":
            custom_bg_color = "#191970"
            custom_sidebar_color = "#0f0f23"
            custom_text_color = "#ffffff"
    
    # Background opacity control
    if background_theme == "Custom":
        bg_opacity = st.sidebar.slider(
            "🔘 Background Opacity",
            min_value=0.1,
            max_value=1.0,
            value=1.0,
            step=0.1,
            help="Adjust background transparency"
        )
    
    # Apply custom CSS styling
    def apply_custom_background_styling():
        if background_theme == "Custom":
            gradient_bg = ""
            if use_gradient:
                gradient_bg = f"background: linear-gradient(135deg, {custom_bg_color} 0%, {gradient_color2 if 'gradient_color2' in locals() else '#e3f2fd'} 100%) !important;"
            else:
                gradient_bg = f"background-color: {custom_bg_color} !important;"
            
            custom_css = f"""
            <style>
            /* Main app background */
            .stApp {{
                {gradient_bg}
                color: {custom_text_color} !important;
            }}
            
            /* Sidebar styling */
            .css-1d391kg {{
                background-color: {custom_sidebar_color} !important;
            }}
            
            /* Header styling */
            .css-18e3th9 {{
                background-color: {custom_header_color if 'custom_header_color' in locals() else custom_bg_color} !important;
            }}
            
            /* Metric cards */
            .css-1r6slb0 {{
                background-color: {custom_metric_color if 'custom_metric_color' in locals() else '#f8f9fa'} !important;
                border-radius: 10px !important;
                padding: 15px !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            }}
            
            /* Text color for headers */
            .css-10trblm {{
                color: {custom_text_color} !important;
            }}
            
            /* Tab styling */
            .stTabs [data-baseweb="tab-list"] button {{
                background-color: rgba(255,255,255,0.1) !important;
                color: {custom_text_color} !important;
            }}
            
            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
                background-color: rgba(255,255,255,0.3) !important;
            }}
            
            /* DataFrame styling */
            .css-81oif8 {{
                background-color: rgba(255,255,255,0.9) !important;
                border-radius: 5px !important;
            }}
            
            /* Info/success/warning boxes */
            .stAlert {{
                background-color: rgba(255,255,255,0.1) !important;
                border-radius: 5px !important;
            }}
            </style>
            """
            st.markdown(custom_css, unsafe_allow_html=True)
        
        elif background_theme == "Dark":
            dark_css = """
            <style>
            .stApp {
                background-color: #1e1e1e !important;
                color: #ffffff !important;
            }
            .css-1d391kg {
                background-color: #2d2d2d !important;
            }
            .css-1r6slb0 {
                background-color: #3d3d3d !important;
                border-radius: 10px !important;
            }
            </style>
            """
            st.markdown(dark_css, unsafe_allow_html=True)
            
        elif background_theme == "Light":
            light_css = """
            <style>
            .stApp {
                background-color: #fafafa !important;
                color: #1a1a1a !important;
            }
            .css-1d391kg {
                background-color: #ffffff !important;
                border: 1px solid #e0e0e0 !important;
            }
            .css-1r6slb0 {
                background-color: #ffffff !important;
                border: 1px solid #e0e0e0 !important;
                border-radius: 10px !important;
            }
            </style>
            """
            st.markdown(light_css, unsafe_allow_html=True)
            
        elif background_theme == "Colorful":
            colorful_css = """
            <style>
            .stApp {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                color: #ffffff !important;
            }
            .css-1d391kg {
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
            }
            .css-1r6slb0 {
                background: rgba(255,255,255,0.2) !important;
                border-radius: 10px !important;
                backdrop-filter: blur(10px) !important;
            }
            </style>
            """
            st.markdown(colorful_css, unsafe_allow_html=True)
    
    # Apply the custom styling
    apply_custom_background_styling()
    
    # Plot style options
    plot_opacity = st.sidebar.slider(
        "🔍 Plot Opacity",
        min_value=0.3,
        max_value=1.0,
        value=0.7,
        step=0.1
    )
    
    # Point/marker size
    marker_size = st.sidebar.slider(
        "⚫ Marker Size",
        min_value=3,
        max_value=12,
        value=6,
        step=1
    )
    
    # Animation controls
    st.sidebar.markdown("---")
    st.sidebar.header("🎥 Animation Options")
    
    enable_animations = st.sidebar.checkbox(
        "🎥 Enable Animations",
        value=False,
        help="Enable dynamic animations for visualizations"
    )
    
    if enable_animations:
        animation_frame = st.sidebar.selectbox(
            "Animation Frame",
            options=[
                "NominalTime",
                "Group", 
                "Marker",
                "SubjectID"
            ] if all(col in df_filtered.columns for col in ["NominalTime", "Group", "Marker", "SubjectID"]) else ["Group", "Marker"],
            help="Choose the dimension for animation frames"
        )
        
        animation_speed = st.sidebar.slider(
            "⏱️ Animation Speed (ms)",
            min_value=500,
            max_value=3000,
            value=1000,
            step=100,
            help="Animation transition duration"
        )
        
        auto_play = st.sidebar.checkbox(
            "▶️ Auto-play Animation",
            value=True,
            help="Start animation automatically"
        )
        
        show_animation_controls = st.sidebar.checkbox(
            "🎮 Show Play Controls",
            value=True,
            help="Display play/pause controls on plots"
        )
        
        # Animation style options
        animation_transition = st.sidebar.selectbox(
            "🔄 Transition Style",
            ["linear", "quad", "cubic", "sin", "exp", "circle", "elastic", "back", "bounce"],
            index=0,
            help="Animation transition easing function"
        )
    else:
        animation_frame = None
        animation_speed = 1000
        auto_play = False
        show_animation_controls = False
        animation_transition = "linear"
    
    # Color preview
    if 'Group' in df_filtered.columns:
            st.sidebar.markdown("**🎨 Color Preview:**")
            groups = df_filtered['Group'].unique()
            try:
                preview_colors = get_color_palette(color_scheme, groups, custom_colors)
            except Exception as e:
                st.sidebar.warning(f"Color preview error: Using defaults")
                preview_colors = get_color_palette("Default (Plotly)", groups, None)
            
            if isinstance(preview_colors, dict):
                for group, color in preview_colors.items():
                    st.sidebar.markdown(
                        f'<div style="display: flex; align-items: center; margin: 2px 0;">'
                        f'<div style="width: 20px; height: 20px; background-color: {color}; '
                        f'border-radius: 3px; margin-right: 8px; border: 1px solid #ccc;"></div>'
                        f'<span>{group}</span></div>',
                        unsafe_allow_html=True
                    )
            elif isinstance(preview_colors, list):
                for i, group in enumerate(groups):
                    color = preview_colors[i % len(preview_colors)]
                    st.sidebar.markdown(
                        f'<div style="display: flex; align-items: center; margin: 2px 0;">'
                        f'<div style="width: 20px; height: 20px; background-color: {color}; '
                        f'border-radius: 3px; margin-right: 8px; border: 1px solid #ccc;"></div>'
                        f'<span>{group}</span></div>',
                        unsafe_allow_html=True
                    )

    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Overview",
        "📊 Concentrations",
        "📈 Longitudinal", 
        "🔬 Statistics",
        "🔬 Quality Control",
        "🌍 3D Analysis"
    ])

    with tab1:
            st.header("🏠 Dataset Overview")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Measurements", len(df_filtered))
            with col2:
                if 'SubjectID' in df_filtered.columns:
                    st.metric("👥 Subjects", df_filtered['SubjectID'].nunique())
            with col3:
                if 'Marker' in df_filtered.columns:
                    st.metric("🧬 Biomarkers", df_filtered['Marker'].nunique())
            with col4:
                if 'NominalTime' in df_filtered.columns:
                    st.metric("⏰ Timepoints", df_filtered['NominalTime'].nunique())
            
            # Data preview
            st.subheader("📋 Data Preview")
            st.dataframe(df_filtered.head(10), width='stretch')
            
            # Basic statistics
            if 'Concentration' in df_filtered.columns and 'Marker' in df_filtered.columns:
                st.subheader("📊 Concentration Statistics by Biomarker")
                stats_df = df_filtered.groupby('Marker')['Concentration'].describe().round(3)
                st.dataframe(stats_df, width='stretch')
        
    with tab2:
            st.header("📊 Biomarker Concentration Analysis")
            
            if 'Concentration' in df_filtered.columns and 'Marker' in df_filtered.columns:
                # Get color settings with error handling
                groups = df_filtered['Group'].unique() if 'Group' in df_filtered.columns else None
                try:
                    color_map = get_color_palette(color_scheme, groups, custom_colors) if groups is not None else None
                except Exception as e:
                    st.warning(f"⚠️ Color scheme issue: {e}. Using default colors.")
                    color_map = get_color_palette("Default (Plotly)", groups, None) if groups is not None else None
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Animated or static box plot
                    if enable_animations and animation_frame in df_filtered.columns and animation_frame != 'Marker':
                        fig_box = px.box(
                            df_filtered,
                            x='Marker',
                            y='Concentration', 
                            color='Group' if 'Group' in df_filtered.columns else None,
                            animation_frame=animation_frame,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            title=f"🎥 Animated Concentration Distribution (by {animation_frame})",
                            points="all"
                        )
                        
                        # Add animation controls
                        fig_box.update_layout(
                            updatemenus=[
                                {
                                    "buttons": [
                                        {
                                            "args": [None, {"frame": {"duration": animation_speed, "redraw": True},
                                                           "fromcurrent": True, "transition": {"duration": animation_speed//2, "easing": animation_transition}}],
                                            "label": "▶️",
                                            "method": "animate"
                                        },
                                        {
                                            "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                                            "mode": "immediate", "transition": {"duration": 0}}],
                                            "label": "⏸️",
                                            "method": "animate"
                                        }
                                    ],
                                    "direction": "left",
                                    "pad": {"r": 10, "t": 87},
                                    "showactive": False,
                                    "type": "buttons",
                                    "x": 0.1,
                                    "xanchor": "right",
                                    "y": 0,
                                    "yanchor": "top"
                                }
                            ] if show_animation_controls else []
                        )
                    else:
                        fig_box = px.box(
                            df_filtered,
                            x='Marker',
                            y='Concentration', 
                            color='Group' if 'Group' in df_filtered.columns else None,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            title="📦 Concentration Distribution by Biomarker",
                            points="all"
                        )
                    fig_box.update_traces(marker=dict(size=marker_size))
                    fig_box.update_layout(height=500)
                    fig_box = apply_theme_styling(fig_box, background_theme, plot_opacity)
                    st.plotly_chart(fig_box, width='stretch')
                
                with col2:
                    # Animated or static violin plot
                    if enable_animations and animation_frame in df_filtered.columns and animation_frame != 'Marker':
                        fig_violin = px.violin(
                            df_filtered,
                            x='Marker',
                            y='Concentration',
                            color='Group' if 'Group' in df_filtered.columns else None,
                            animation_frame=animation_frame,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            box=True,
                            title=f"🎥 Animated Density Distribution (by {animation_frame})"
                        )
                        
                        # Add animation controls
                        fig_violin.update_layout(
                            updatemenus=[
                                {
                                    "buttons": [
                                        {
                                            "args": [None, {"frame": {"duration": animation_speed, "redraw": True},
                                                           "fromcurrent": True, "transition": {"duration": animation_speed//2, "easing": animation_transition}}],
                                            "label": "▶️",
                                            "method": "animate"
                                        },
                                        {
                                            "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                                            "mode": "immediate", "transition": {"duration": 0}}],
                                            "label": "⏸️",
                                            "method": "animate"
                                        }
                                    ],
                                    "direction": "left",
                                    "pad": {"r": 10, "t": 87},
                                    "showactive": False,
                                    "type": "buttons",
                                    "x": 0.1,
                                    "xanchor": "right",
                                    "y": 0,
                                    "yanchor": "top"
                                }
                            ] if show_animation_controls else []
                        )
                    else:
                        fig_violin = px.violin(
                            df_filtered,
                            x='Marker',
                            y='Concentration',
                            color='Group' if 'Group' in df_filtered.columns else None,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            box=True,
                            title="🎻 Concentration Density Distribution"
                        )
                    fig_violin.update_layout(height=500)
                    fig_violin = apply_theme_styling(fig_violin, background_theme, plot_opacity)
                    st.plotly_chart(fig_violin, width='stretch')
                
                # Histogram by group
                if 'Group' in df_filtered.columns:
                    fig_hist = px.histogram(
                        df_filtered,
                        x='Concentration',
                        color='Group',
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        facet_col='Marker',
                        title="📊 Concentration Histograms by Group",
                        nbins=20,
                        opacity=plot_opacity
                    )
                    fig_hist = apply_theme_styling(fig_hist, background_theme, plot_opacity)
                    st.plotly_chart(fig_hist, width='stretch')
            else:
                st.warning("⚠️ Concentration data not available for visualization")
        
    with tab3:
            st.header("📈 Longitudinal Analysis")
            
            if all(col in df_filtered.columns for col in ['NominalTime', 'Concentration', 'SubjectID']):
                # Get color settings with error handling
                groups = df_filtered['Group'].unique() if 'Group' in df_filtered.columns else None
                try:
                    color_map = get_color_palette(color_scheme, groups, custom_colors) if groups is not None else None
                except Exception as e:
                    st.warning(f"⚠️ Color scheme issue: {e}. Using default colors.")
                    color_map = get_color_palette("Default (Plotly)", groups, None) if groups is not None else None
                
                # Animated or static individual trajectories
                if enable_animations and 'SubjectID' in df_filtered.columns and animation_frame == 'SubjectID':
                    fig_lines = px.line(
                        df_filtered,
                        x='NominalTime',
                        y='Concentration',
                        color='Group' if 'Group' in df_filtered.columns else 'SubjectID',
                        animation_frame='SubjectID',
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        line_group='SubjectID',
                        facet_col='Marker' if 'Marker' in df_filtered.columns else None,
                        title="🎥 Animated Individual Subject Trajectories",
                        markers=True
                    )
                    
                    # Add animation controls
                    fig_lines.update_layout(
                        updatemenus=[
                            {
                                "buttons": [
                                    {
                                        "args": [None, {"frame": {"duration": animation_speed, "redraw": True},
                                                       "fromcurrent": True, "transition": {"duration": animation_speed//2, "easing": animation_transition}}],
                                        "label": "▶️",
                                        "method": "animate"
                                    },
                                    {
                                        "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                                        "mode": "immediate", "transition": {"duration": 0}}],
                                        "label": "⏸️",
                                        "method": "animate"
                                    }
                                ],
                                "direction": "left",
                                "pad": {"r": 10, "t": 87},
                                "showactive": False,
                                "type": "buttons",
                                "x": 0.1,
                                "xanchor": "right",
                                "y": 0,
                                "yanchor": "top"
                            }
                        ] if show_animation_controls else []
                    )
                elif enable_animations and animation_frame in df_filtered.columns and animation_frame == 'NominalTime':
                    # Time-based animation showing data building up
                    fig_lines = px.scatter(
                        df_filtered,
                        x='NominalTime',
                        y='Concentration',
                        color='Group' if 'Group' in df_filtered.columns else 'SubjectID',
                        animation_frame='NominalTime',
                        animation_group='SubjectID',
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        facet_col='Marker' if 'Marker' in df_filtered.columns else None,
                        title="🎥 Animated Time Evolution",
                        size_max=marker_size*2
                    )
                    
                    # Add animation controls
                    fig_lines.update_layout(
                        updatemenus=[
                            {
                                "buttons": [
                                    {
                                        "args": [None, {"frame": {"duration": animation_speed, "redraw": True},
                                                       "fromcurrent": True, "transition": {"duration": animation_speed//2, "easing": animation_transition}}],
                                        "label": "▶️",
                                        "method": "animate"
                                    },
                                    {
                                        "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                                        "mode": "immediate", "transition": {"duration": 0}}],
                                        "label": "⏸️",
                                        "method": "animate"
                                    }
                                ],
                                "direction": "left",
                                "pad": {"r": 10, "t": 87},
                                "showactive": False,
                                "type": "buttons",
                                "x": 0.1,
                                "xanchor": "right",
                                "y": 0,
                                "yanchor": "top"
                            }
                        ] if show_animation_controls else []
                    )
                else:
                    fig_lines = px.line(
                        df_filtered,
                        x='NominalTime',
                        y='Concentration',
                        color='Group' if 'Group' in df_filtered.columns else 'SubjectID',
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        line_group='SubjectID',
                        facet_col='Marker' if 'Marker' in df_filtered.columns else None,
                        title="📈 Individual Subject Concentration Trajectories",
                        markers=True
                    )
                fig_lines.update_traces(
                    line=dict(width=2), 
                    marker=dict(size=marker_size),
                    opacity=plot_opacity
                )
                fig_lines = apply_theme_styling(fig_lines, background_theme, plot_opacity)
                st.plotly_chart(fig_lines, width='stretch')
                
                # Mean trajectories
                if 'Group' in df_filtered.columns and 'Marker' in df_filtered.columns:
                    mean_data = df_filtered.groupby(['Group', 'Marker', 'NominalTime'])['Concentration'].agg(['mean', 'std', 'count']).reset_index()
                    mean_data['se'] = mean_data['std'] / np.sqrt(mean_data['count'])
                    
                    fig_mean = px.line(
                        mean_data,
                        x='NominalTime',
                        y='mean',
                        color='Group',
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        facet_col='Marker',
                        title="📊 Mean Concentration Trajectories with Standard Error",
                        error_y='se',
                        markers=True
                    )
                    fig_mean.update_traces(
                        line=dict(width=3),
                        marker=dict(size=marker_size + 2)
                    )
                    fig_mean.update_layout(yaxis_title="Mean Concentration")
                    fig_mean = apply_theme_styling(fig_mean, background_theme, plot_opacity)
                    st.plotly_chart(fig_mean, width='stretch')
            else:
                st.warning("⚠️ Longitudinal data columns not available")
        
    with tab4:
            st.header("🔬 Advanced Statistical Analysis")
            
            # Statistical analysis method selection
            st.sidebar.markdown("---")
            st.sidebar.header("📊 Statistical Options")
            
            stat_method = st.sidebar.selectbox(
                "Select Analysis Method",
                [
                    "Group Comparisons",
                    "ANOVA Analysis", 
                    "Non-parametric Tests",
                    "Normality & Assumptions",
                    "Effect Size Analysis",
                    "Correlation Analysis",
                    "All Methods"
                ]
            )
            
            alpha_level = st.sidebar.slider(
                "Significance Level (α)",
                min_value=0.001,
                max_value=0.1,
                value=0.05,
                step=0.001
            )
            
            if all(col in df_filtered.columns for col in ['Concentration', 'Group', 'Marker']):
                
                if stat_method in ["Group Comparisons", "All Methods"]:
                    st.subheader("📊 Group Comparisons (T-tests)")
                    
                    results = []
                    for marker in df_filtered['Marker'].unique():
                        marker_data = df_filtered[df_filtered['Marker'] == marker]
                        groups = marker_data['Group'].unique()
                        
                        if len(groups) >= 2:
                            group1_data = marker_data[marker_data['Group'] == groups[0]]['Concentration'].dropna()
                            group2_data = marker_data[marker_data['Group'] == groups[1]]['Concentration'].dropna()
                            
                            if len(group1_data) > 1 and len(group2_data) > 1:
                                # Independent t-test
                                stat, p_value = stats.ttest_ind(group1_data, group2_data)
                                
                                # Cohen's d (effect size)
                                pooled_std = np.sqrt(((len(group1_data) - 1) * group1_data.var() + 
                                                    (len(group2_data) - 1) * group2_data.var()) / 
                                                   (len(group1_data) + len(group2_data) - 2))
                                cohens_d = (group1_data.mean() - group2_data.mean()) / pooled_std
                                effect_size = "Small" if abs(cohens_d) < 0.5 else "Medium" if abs(cohens_d) < 0.8 else "Large"
                                
                                results.append({
                                    'Biomarker': marker,
                                    'Comparison': f"{groups[0]} vs {groups[1]}",
                                    'Group 1 Mean': round(group1_data.mean(), 3),
                                    'Group 2 Mean': round(group2_data.mean(), 3),
                                    'Group 1 SD': round(group1_data.std(), 3),
                                    'Group 2 SD': round(group2_data.std(), 3),
                                    'T-statistic': round(stat, 4),
                                    'P-value': round(p_value, 6),
                                    "Cohen's d": round(cohens_d, 3),
                                    'Effect Size': effect_size,
                                    f'Significant (p<{alpha_level})': '✅ Yes' if p_value < alpha_level else '❌ No'
                                })
                    
                    if results:
                        results_df = pd.DataFrame(results)
                        st.dataframe(results_df, width='stretch')
                    else:
                        st.info("📝 No statistical comparisons available")
                
                if stat_method in ["ANOVA Analysis", "All Methods"]:
                    st.subheader("🔬 ANOVA Analysis")
                    
                    anova_results = []
                    for marker in df_filtered['Marker'].unique():
                        marker_data = df_filtered[df_filtered['Marker'] == marker]
                        groups = marker_data['Group'].unique()
                        
                        if len(groups) > 2:
                            group_data = [marker_data[marker_data['Group'] == group]['Concentration'].dropna() 
                                        for group in groups]
                            
                            # Remove empty groups
                            group_data = [data for data in group_data if len(data) > 0]
                            
                            if len(group_data) > 2 and all(len(data) > 1 for data in group_data):
                                f_stat, p_value = stats.f_oneway(*group_data)
                                
                                # Eta-squared (effect size)
                                ss_between = sum(len(data) * (data.mean() - marker_data['Concentration'].mean())**2 
                                               for data in group_data)
                                ss_total = ((marker_data['Concentration'] - marker_data['Concentration'].mean())**2).sum()
                                eta_squared = ss_between / ss_total if ss_total > 0 else 0
                                
                                anova_results.append({
                                    'Biomarker': marker,
                                    'Groups': len(groups),
                                    'F-statistic': round(f_stat, 4),
                                    'P-value': round(p_value, 6),
                                    'Eta-squared': round(eta_squared, 3),
                                    f'Significant (p<{alpha_level})': '✅ Yes' if p_value < alpha_level else '❌ No'
                                })
                    
                    if anova_results:
                        anova_df = pd.DataFrame(anova_results)
                        st.dataframe(anova_df, width='stretch')
                    else:
                        st.info("📝 ANOVA requires 3+ groups")
                
                if stat_method in ["Non-parametric Tests", "All Methods"]:
                    st.subheader("📈 Non-parametric Tests")
                    
                    nonparam_results = []
                    for marker in df_filtered['Marker'].unique():
                        marker_data = df_filtered[df_filtered['Marker'] == marker]
                        groups = marker_data['Group'].unique()
                        
                        if len(groups) >= 2:
                            if len(groups) == 2:
                                # Mann-Whitney U test
                                group1_data = marker_data[marker_data['Group'] == groups[0]]['Concentration'].dropna()
                                group2_data = marker_data[marker_data['Group'] == groups[1]]['Concentration'].dropna()
                                
                                if len(group1_data) > 0 and len(group2_data) > 0:
                                    stat, p_value = mannwhitneyu(group1_data, group2_data, alternative='two-sided')
                                    
                                    nonparam_results.append({
                                        'Biomarker': marker,
                                        'Test': 'Mann-Whitney U',
                                        'Comparison': f"{groups[0]} vs {groups[1]}",
                                        'U-statistic': round(stat, 4),
                                        'P-value': round(p_value, 6),
                                        f'Significant (p<{alpha_level})': '✅ Yes' if p_value < alpha_level else '❌ No'
                                    })
                            
                            else:
                                # Kruskal-Wallis test
                                group_data = [marker_data[marker_data['Group'] == group]['Concentration'].dropna() 
                                            for group in groups]
                                group_data = [data for data in group_data if len(data) > 0]
                                
                                if len(group_data) > 2:
                                    stat, p_value = kruskal(*group_data)
                                    
                                    nonparam_results.append({
                                        'Biomarker': marker,
                                        'Test': 'Kruskal-Wallis',
                                        'Comparison': f"{len(groups)} groups",
                                        'H-statistic': round(stat, 4),
                                        'P-value': round(p_value, 6),
                                        f'Significant (p<{alpha_level})': '✅ Yes' if p_value < alpha_level else '❌ No'
                                    })
                    
                    if nonparam_results:
                        nonparam_df = pd.DataFrame(nonparam_results)
                        st.dataframe(nonparam_df, width='stretch')
                    else:
                        st.info("📝 No non-parametric tests available")
                
                if stat_method in ["Normality & Assumptions", "All Methods"]:
                    st.subheader("📋 Normality & Statistical Assumptions")
                    
                    normality_results = []
                    for marker in df_filtered['Marker'].unique():
                        marker_data = df_filtered[df_filtered['Marker'] == marker]
                        
                        for group in marker_data['Group'].unique():
                            group_data = marker_data[marker_data['Group'] == group]['Concentration'].dropna()
                            
                            if len(group_data) >= 3:
                                # Shapiro-Wilk normality test
                                shapiro_stat, shapiro_p = shapiro(group_data)
                                
                                normality_results.append({
                                    'Biomarker': marker,
                                    'Group': group,
                                    'N': len(group_data),
                                    'Shapiro-Wilk Statistic': round(shapiro_stat, 4),
                                    'Shapiro-Wilk P-value': round(shapiro_p, 6),
                                    'Normal Distribution': '✅ Yes' if shapiro_p > alpha_level else '❌ No',
                                    'Mean': round(group_data.mean(), 3),
                                    'Median': round(group_data.median(), 3),
                                    'Skewness': round(stats.skew(group_data), 3)
                                })
                    
                    if normality_results:
                        norm_df = pd.DataFrame(normality_results)
                        st.dataframe(norm_df, width='stretch')
                        
                        # Levene's test for equal variances
                        st.subheader("⚖️ Equal Variance Test (Levene's Test)")
                        levene_results = []
                        
                        for marker in df_filtered['Marker'].unique():
                            marker_data = df_filtered[df_filtered['Marker'] == marker]
                            groups = marker_data['Group'].unique()
                            
                            if len(groups) >= 2:
                                group_data = [marker_data[marker_data['Group'] == group]['Concentration'].dropna() 
                                            for group in groups]
                                group_data = [data for data in group_data if len(data) > 1]
                                
                                if len(group_data) >= 2:
                                    levene_stat, levene_p = levene(*group_data)
                                    
                                    levene_results.append({
                                        'Biomarker': marker,
                                        'Groups Tested': len(group_data),
                                        'Levene Statistic': round(levene_stat, 4),
                                        'P-value': round(levene_p, 6),
                                        'Equal Variances': '✅ Yes' if levene_p > alpha_level else '❌ No'
                                    })
                        
                        if levene_results:
                            levene_df = pd.DataFrame(levene_results)
                            st.dataframe(levene_df, width='stretch')
                    else:
                        st.info("📝 Need at least 3 samples per group for normality testing")
                
                if stat_method in ["Effect Size Analysis", "All Methods"]:
                    st.subheader("📏 Effect Size Analysis")
                    
                    effect_results = []
                    for marker in df_filtered['Marker'].unique():
                        marker_data = df_filtered[df_filtered['Marker'] == marker]
                        groups = marker_data['Group'].unique()
                        
                        if len(groups) >= 2:
                            group1_data = marker_data[marker_data['Group'] == groups[0]]['Concentration'].dropna()
                            group2_data = marker_data[marker_data['Group'] == groups[1]]['Concentration'].dropna()
                            
                            if len(group1_data) > 1 and len(group2_data) > 1:
                                # Cohen's d
                                pooled_std = np.sqrt(((len(group1_data) - 1) * group1_data.var() + 
                                                    (len(group2_data) - 1) * group2_data.var()) / 
                                                   (len(group1_data) + len(group2_data) - 2))
                                cohens_d = (group1_data.mean() - group2_data.mean()) / pooled_std
                                
                                # Glass's delta
                                glass_delta = (group1_data.mean() - group2_data.mean()) / group2_data.std()
                                
                                # Hedge's g (bias-corrected Cohen's d)
                                correction_factor = 1 - (3 / (4 * (len(group1_data) + len(group2_data)) - 9))
                                hedges_g = cohens_d * correction_factor
                                
                                effect_interpretation = (
                                    "Small" if abs(cohens_d) < 0.5 else 
                                    "Medium" if abs(cohens_d) < 0.8 else "Large"
                                )
                                
                                effect_results.append({
                                    'Biomarker': marker,
                                    'Comparison': f"{groups[0]} vs {groups[1]}",
                                    "Cohen's d": round(cohens_d, 3),
                                    "Hedge's g": round(hedges_g, 3),
                                    "Glass's Δ": round(glass_delta, 3),
                                    'Effect Size': effect_interpretation,
                                    'Practical Significance': '✅ Meaningful' if abs(cohens_d) >= 0.5 else '❓ Small'
                                })
                    
                    if effect_results:
                        effect_df = pd.DataFrame(effect_results)
                        st.dataframe(effect_df, width='stretch')
                        
                        st.info(
                            "📖 **Effect Size Interpretation:**\n\n"
                            "• **Small**: d = 0.2-0.5 (subtle difference)\n"
                            "• **Medium**: d = 0.5-0.8 (moderate difference)\n"
                            "• **Large**: d ≥ 0.8 (substantial difference)"
                        )
                    else:
                        st.info("📝 No effect size calculations available")
                
                if stat_method in ["Correlation Analysis", "All Methods"]:
                    st.subheader("🔗 Advanced Correlation Analysis")
                    
                    # Correlation method selection
                    corr_method = st.selectbox(
                        "Correlation Method",
                        ["Pearson", "Spearman", "Kendall"]
                    )
                    
                    numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
                    if len(numeric_cols) > 1:
                        # Calculate correlation matrix
                        if corr_method == "Pearson":
                            corr_matrix = df_filtered[numeric_cols].corr(method='pearson')
                        elif corr_method == "Spearman":
                            corr_matrix = df_filtered[numeric_cols].corr(method='spearman')
                        else:  # Kendall
                            corr_matrix = df_filtered[numeric_cols].corr(method='kendall')
                        
                        # Color scale based on scheme selection
                        color_scale = 'RdBu_r'  # default
                        if color_scheme == 'Viridis':
                            color_scale = 'Viridis'
                        elif color_scheme == 'Plasma':
                            color_scale = 'Plasma'
                        elif color_scheme in ['Set1', 'Set2', 'Pastel1']:
                            color_scale = 'RdYlBu_r'
                        
                        fig_corr = px.imshow(
                            corr_matrix,
                            text_auto=True,
                            aspect="auto",
                            title=f"🔥 {corr_method} Correlation Matrix",
                            color_continuous_scale=color_scale,
                            zmin=-1, zmax=1
                        )
                        fig_corr.update_layout(height=500)
                        fig_corr = apply_theme_styling(fig_corr, background_theme, 1.0)
                        st.plotly_chart(fig_corr, width='stretch')
                        
                        # Significant correlations table
                        st.subheader("📊 Significant Correlations")
                        sig_corrs = []
                        
                        for i in range(len(numeric_cols)):
                            for j in range(i+1, len(numeric_cols)):
                                col1, col2 = numeric_cols[i], numeric_cols[j]
                                corr_val = corr_matrix.iloc[i, j]
                                
                                # Calculate p-value
                                if corr_method == "Pearson":
                                    corr_stat, p_val = stats.pearsonr(df_filtered[col1].dropna(), df_filtered[col2].dropna())
                                elif corr_method == "Spearman":
                                    corr_stat, p_val = stats.spearmanr(df_filtered[col1].dropna(), df_filtered[col2].dropna())
                                else:  # Kendall
                                    corr_stat, p_val = stats.kendalltau(df_filtered[col1].dropna(), df_filtered[col2].dropna())
                                
                                if abs(corr_val) > 0.1:  # Only show correlations > 0.1
                                    strength = (
                                        "Very Strong" if abs(corr_val) >= 0.8 else
                                        "Strong" if abs(corr_val) >= 0.6 else
                                        "Moderate" if abs(corr_val) >= 0.4 else
                                        "Weak" if abs(corr_val) >= 0.2 else "Very Weak"
                                    )
                                    
                                    sig_corrs.append({
                                        'Variable 1': col1,
                                        'Variable 2': col2,
                                        'Correlation': round(corr_val, 3),
                                        'P-value': round(p_val, 6),
                                        'Strength': strength,
                                        'Direction': 'Positive' if corr_val > 0 else 'Negative',
                                        f'Significant (p<{alpha_level})': '✅ Yes' if p_val < alpha_level else '❌ No'
                                    })
                        
                        if sig_corrs:
                            sig_corr_df = pd.DataFrame(sig_corrs)
                            sig_corr_df = sig_corr_df.sort_values('Correlation', key=abs, ascending=False)
                            st.dataframe(sig_corr_df, width='stretch')
                        else:
                            st.info("📝 No significant correlations found")
                    else:
                        st.warning("⚠️ Need at least 2 numeric columns for correlation analysis")
            else:
                st.warning("⚠️ Statistical analysis requires Concentration, Group, and Marker columns")
        
    with tab5:
            st.header("🔬 Quality Control Analysis")
            
            # QC flags
            if 'flag' in df_filtered.columns:
                col1, col2 = st.columns(2)
                
                with col1:
                    flag_counts = df_filtered['flag'].value_counts()
                    
                    # Custom colors for QC flags
                    qc_colors = {
                        'OK': '#2E8B57' if color_scheme == 'Custom' else None,
                        'Warning': '#FFD700' if color_scheme == 'Custom' else None,
                        'Failed': '#DC143C' if color_scheme == 'Custom' else None
                    }
                    
                    fig_flags = px.pie(
                        values=flag_counts.values,
                        names=flag_counts.index,
                        title="🚩 Quality Control Flags",
                        color_discrete_map=qc_colors if color_scheme == 'Custom' else None,
                        color_discrete_sequence=get_color_palette(color_scheme) if color_scheme != 'Custom' else None
                    )
                    fig_flags = apply_theme_styling(fig_flags, background_theme, plot_opacity)
                    st.plotly_chart(fig_flags, width='stretch')
                
                with col2:
                    if 'Group' in df_filtered.columns:
                        flag_group = pd.crosstab(df_filtered['Group'], df_filtered['flag'])
                        
                        fig_flag_group = px.bar(
                            flag_group,
                            title="🚩 QC Flags by Group",
                            barmode='stack',
                            color_discrete_sequence=get_color_palette(color_scheme) if isinstance(get_color_palette(color_scheme), list) else None
                        )
                        fig_flag_group = apply_theme_styling(fig_flag_group, background_theme, plot_opacity)
                        st.plotly_chart(fig_flag_group, width='stretch')
            
            # Raw signal analysis
            if 'RawSignal' in df_filtered.columns:
                st.subheader("📡 Raw Signal Quality")
                
                col1, col2 = st.columns(2)
                
                # Get color settings for raw signal plots with error handling
                groups = df_filtered['Group'].unique() if 'Group' in df_filtered.columns else None
                try:
                    color_map = get_color_palette(color_scheme, groups, custom_colors) if groups is not None else None
                except Exception as e:
                    st.warning(f"⚠️ Color scheme issue: {e}. Using default colors.")
                    color_map = get_color_palette("Default (Plotly)", groups, None) if groups is not None else None
                
                with col1:
                    fig_raw = px.histogram(
                        df_filtered,
                        x='RawSignal',
                        color='Group' if 'Group' in df_filtered.columns else None,
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        title="📊 Raw Signal Distribution",
                        nbins=30,
                        opacity=plot_opacity
                    )
                    fig_raw = apply_theme_styling(fig_raw, background_theme, plot_opacity)
                    st.plotly_chart(fig_raw, width='stretch')
                
                with col2:
                    if 'Marker' in df_filtered.columns:
                        fig_raw_marker = px.box(
                            df_filtered,
                            x='Marker',
                            y='RawSignal',
                            color='Group' if 'Group' in df_filtered.columns else None,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            title="📦 Raw Signal by Biomarker"
                        )
                        fig_raw_marker.update_traces(marker=dict(size=marker_size))
                        fig_raw_marker = apply_theme_styling(fig_raw_marker, background_theme, plot_opacity)
                        st.plotly_chart(fig_raw_marker, width='stretch')

    with tab6:
        st.header("🌍 3D Interactive Analysis")
        
        # 3D analysis options in sidebar
        st.sidebar.markdown("---")
        st.sidebar.header("🌍 3D Visualization Options")
        
        view_3d_type = st.sidebar.selectbox(
            "Select 3D Analysis Type",
            [
                "3D Scatter Plot",
                "3D Surface Plot", 
                "3D Biomarker Space",
                "3D Time Series",
                "3D Correlation Volume",
                "3D Statistical Distribution"
            ]
        )
        
        # 3D plot styling options
        plot_3d_style = st.sidebar.selectbox(
            "3D Plot Style",
            ["Default", "Dark", "Presentation", "Scientific"]
        )
        
        point_size_3d = st.sidebar.slider(
            "🔴 3D Point Size",
            min_value=2,
            max_value=20,
            value=8,
            step=1
        )
        
        show_3d_grid = st.sidebar.checkbox(
            "🔲 Show 3D Grid",
            value=True
        )
        
        camera_angle = st.sidebar.selectbox(
            "📷 Camera Angle",
            ["Default", "Top View", "Side View", "Isometric", "Custom"]
        )
        
        if all(col in df_filtered.columns for col in ['Concentration', 'Group', 'Marker']):
            
            if view_3d_type == "3D Scatter Plot":
                st.subheader("🌌 3D Biomarker Scatter Analysis")
                
                # Select axes for 3D scatter
                numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
                
                if len(numeric_cols) >= 3:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        x_axis_3d = st.selectbox(
                            "X-Axis (3D)",
                            options=numeric_cols,
                            index=0
                        )
                    
                    with col2:
                        y_axis_3d = st.selectbox(
                            "Y-Axis (3D)",
                            options=numeric_cols,
                            index=1 if len(numeric_cols) > 1 else 0
                        )
                    
                    with col3:
                        z_axis_3d = st.selectbox(
                            "Z-Axis (3D)",
                            options=numeric_cols,
                            index=2 if len(numeric_cols) > 2 else 0
                        )
                    
                    # Create animated or static 3D scatter plot
                    if enable_animations and animation_frame in df_filtered.columns and animation_frame != z_axis_3d:
                        fig_3d_scatter = px.scatter_3d(
                            df_filtered,
                            x=x_axis_3d,
                            y=y_axis_3d,
                            z=z_axis_3d,
                            color='Group' if 'Group' in df_filtered.columns else None,
                            size='Concentration' if 'Concentration' in df_filtered.columns else None,
                            animation_frame=animation_frame,
                            animation_group='SubjectID' if 'SubjectID' in df_filtered.columns else None,
                            hover_data=['Marker', 'SubjectID'] if all(col in df_filtered.columns for col in ['Marker', 'SubjectID']) else None,
                            title=f"🎥 Animated 3D Analysis: {x_axis_3d} vs {y_axis_3d} vs {z_axis_3d} (by {animation_frame})",
                            color_discrete_sequence=get_color_palette(color_scheme) if isinstance(get_color_palette(color_scheme), list) else None
                        )
                        
                        # Configure 3D animation
                        fig_3d_scatter.update_layout(
                            updatemenus=[
                                {
                                    "buttons": [
                                        {
                                            "args": [None, {"frame": {"duration": animation_speed, "redraw": True},
                                                           "fromcurrent": True, "transition": {"duration": animation_speed//2, "easing": animation_transition}}],
                                            "label": "▶️",
                                            "method": "animate"
                                        },
                                        {
                                            "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                                            "mode": "immediate", "transition": {"duration": 0}}],
                                            "label": "⏸️",
                                            "method": "animate"
                                        }
                                    ],
                                    "direction": "left",
                                    "pad": {"r": 10, "t": 87},
                                    "showactive": False,
                                    "type": "buttons",
                                    "x": 0.1,
                                    "xanchor": "right",
                                    "y": 0,
                                    "yanchor": "top"
                                }
                            ] if show_animation_controls else []
                        )
                    else:
                        fig_3d_scatter = px.scatter_3d(
                            df_filtered,
                            x=x_axis_3d,
                            y=y_axis_3d,
                            z=z_axis_3d,
                            color='Group' if 'Group' in df_filtered.columns else None,
                            size='Concentration' if 'Concentration' in df_filtered.columns else None,
                            hover_data=['Marker', 'SubjectID'] if all(col in df_filtered.columns for col in ['Marker', 'SubjectID']) else None,
                            title=f"🌌 3D Analysis: {x_axis_3d} vs {y_axis_3d} vs {z_axis_3d}",
                            color_discrete_sequence=get_color_palette(color_scheme) if isinstance(get_color_palette(color_scheme), list) else None
                        )
                    
                    # Update 3D layout
                    fig_3d_scatter.update_traces(
                        marker=dict(
                            size=point_size_3d,
                            opacity=plot_opacity
                        )
                    )
                    
                    # Set camera angle
                    if camera_angle == "Top View":
                        camera_dict = dict(eye=dict(x=0, y=0, z=2.5))
                    elif camera_angle == "Side View":
                        camera_dict = dict(eye=dict(x=2.5, y=0, z=0))
                    elif camera_angle == "Isometric":
                        camera_dict = dict(eye=dict(x=1.2, y=1.2, z=1.2))
                    else:
                        camera_dict = dict(eye=dict(x=1.5, y=1.5, z=1.5))
                    
                    fig_3d_scatter.update_layout(
                        scene=dict(
                            camera=camera_dict,
                            xaxis_title=x_axis_3d,
                            yaxis_title=y_axis_3d,
                            zaxis_title=z_axis_3d,
                            xaxis=dict(showgrid=show_3d_grid),
                            yaxis=dict(showgrid=show_3d_grid),
                            zaxis=dict(showgrid=show_3d_grid)
                        ),
                        height=600
                    )
                    
                    st.plotly_chart(fig_3d_scatter, width='stretch')
                else:
                    st.warning("⚠️ Need at least 3 numeric columns for 3D scatter plot")
            
            elif view_3d_type == "3D Biomarker Space":
                st.subheader("🧬 3D Biomarker Interaction Space")
                
                # Create biomarker comparison matrix in 3D
                markers = df_filtered['Marker'].unique()
                if len(markers) >= 2:
                    
                    # Prepare data for 3D biomarker space
                    biomarker_3d_data = []
                    
                    for i, marker1 in enumerate(markers):
                        for j, marker2 in enumerate(markers):
                            if i != j:
                                data1 = df_filtered[df_filtered['Marker'] == marker1]['Concentration']
                                data2 = df_filtered[df_filtered['Marker'] == marker2]['Concentration']
                                
                                if len(data1) > 0 and len(data2) > 0:
                                    # Calculate correlation or interaction metric
                                    if len(data1) == len(data2):
                                        corr_val = np.corrcoef(data1, data2)[0, 1]
                                    else:
                                        corr_val = 0
                                    
                                    biomarker_3d_data.append({
                                        'Marker1': marker1,
                                        'Marker2': marker2,
                                        'Mean1': data1.mean(),
                                        'Mean2': data2.mean(),
                                        'Correlation': corr_val,
                                        'Interaction': abs(corr_val) * (data1.mean() + data2.mean()) / 2
                                    })
                    
                    if biomarker_3d_data:
                        biomarker_3d_df = pd.DataFrame(biomarker_3d_data)
                        
                        fig_bio_3d = px.scatter_3d(
                            biomarker_3d_df,
                            x='Mean1',
                            y='Mean2', 
                            z='Correlation',
                            color='Interaction',
                            size='Interaction',
                            hover_data=['Marker1', 'Marker2'],
                            title="🧬 3D Biomarker Interaction Space",
                            color_continuous_scale='Viridis'
                        )
                        
                        fig_bio_3d.update_traces(marker=dict(size=point_size_3d, opacity=plot_opacity))
                        fig_bio_3d.update_layout(
                            scene=dict(
                                xaxis_title="Biomarker 1 Mean Concentration",
                                yaxis_title="Biomarker 2 Mean Concentration", 
                                zaxis_title="Correlation Coefficient",
                                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
                            ),
                            height=600
                        )
                        
                        st.plotly_chart(fig_bio_3d, width='stretch')
                else:
                    st.warning("⚠️ Need at least 2 biomarkers for 3D biomarker space analysis")
            
            elif view_3d_type == "3D Time Series":
                st.subheader("⏰ 3D Temporal Analysis")
                
                if 'NominalTime' in df_filtered.columns:
                    # Create 3D time series plot
                    fig_time_3d = px.scatter_3d(
                        df_filtered,
                        x='NominalTime',
                        y='Concentration',
                        z='SubjectID' if 'SubjectID' in df_filtered.columns else 'Marker',
                        color='Group',
                        hover_data=['Marker'],
                        title="⏰ 3D Temporal Biomarker Evolution",
                        color_discrete_sequence=get_color_palette(color_scheme) if isinstance(get_color_palette(color_scheme), list) else None
                    )
                    
                    fig_time_3d.update_traces(marker=dict(size=point_size_3d, opacity=plot_opacity))
                    fig_time_3d.update_layout(
                        scene=dict(
                            xaxis_title="Time Point",
                            yaxis_title="Concentration",
                            zaxis_title="Subject/Marker ID",
                            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
                        ),
                        height=600
                    )
                    
                    st.plotly_chart(fig_time_3d, width='stretch')
                else:
                    st.warning("⚠️ Need temporal data (NominalTime column) for 3D time series")
            
            elif view_3d_type == "3D Surface Plot":
                st.subheader("🌊 3D Surface Analysis")
                
                # Create surface plot of concentration data
                if 'SubjectID' in df_filtered.columns and 'NominalTime' in df_filtered.columns:
                    
                    # Pivot data for surface plot
                    pivot_data = df_filtered.pivot_table(
                        values='Concentration',
                        index='SubjectID',
                        columns='NominalTime',
                        aggfunc='mean'
                    ).fillna(0)
                    
                    if not pivot_data.empty:
                        fig_surface = go.Figure(data=[go.Surface(
                            z=pivot_data.values,
                            x=pivot_data.columns,
                            y=pivot_data.index,
                            colorscale='Viridis',
                            opacity=plot_opacity
                        )])
                        
                        fig_surface.update_layout(
                            title="🌊 3D Concentration Surface by Subject and Time",
                            scene=dict(
                                xaxis_title="Time Point",
                                yaxis_title="Subject ID",
                                zaxis_title="Concentration",
                                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
                            ),
                            height=600
                        )
                        
                        st.plotly_chart(fig_surface, width='stretch')
                    else:
                        st.warning("⚠️ Unable to create surface plot with current data structure")
                else:
                    st.warning("⚠️ Need SubjectID and NominalTime columns for surface plot")
            
            elif view_3d_type == "3D Statistical Distribution":
                st.subheader("📈 3D Statistical Distribution Analysis")
                
                # Create 3D histogram/distribution plot
                fig_dist_3d = px.scatter_3d(
                    df_filtered,
                    x='Concentration',
                    y='RawSignal' if 'RawSignal' in df_filtered.columns else 'Concentration',
                    z='CV' if 'CV' in df_filtered.columns else 'Concentration',
                    color='Group',
                    size='Concentration',
                    hover_data=['Marker', 'SubjectID'] if all(col in df_filtered.columns for col in ['Marker', 'SubjectID']) else None,
                    title="📈 3D Statistical Distribution Space",
                    color_discrete_sequence=get_color_palette(color_scheme) if isinstance(get_color_palette(color_scheme), list) else None
                )
                
                fig_dist_3d.update_traces(marker=dict(size=point_size_3d, opacity=plot_opacity))
                fig_dist_3d.update_layout(
                    scene=dict(
                        xaxis_title="Concentration",
                        yaxis_title="Raw Signal" if 'RawSignal' in df_filtered.columns else "Concentration (Y)",
                        zaxis_title="CV" if 'CV' in df_filtered.columns else "Concentration (Z)",
                        camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
                    ),
                    height=600
                )
                
                st.plotly_chart(fig_dist_3d, width='stretch')
            
            # 3D Analysis Summary
            st.subheader("📄 3D Analysis Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(
                    f"🌍 **3D View**: {view_3d_type}\n\n"
                    f"📷 **Camera Angle**: {camera_angle}\n\n"
                    f"🔴 **Point Size**: {point_size_3d}\n\n"
                    f"🔲 **Grid**: {'Enabled' if show_3d_grid else 'Disabled'}"
                )
            
            with col2:
                st.info(
                    f"📊 **Data Points**: {len(df_filtered)}\n\n"
                    f"🧬 **Biomarkers**: {df_filtered['Marker'].nunique() if 'Marker' in df_filtered.columns else 'N/A'}\n\n"
                    f"👥 **Groups**: {df_filtered['Group'].nunique() if 'Group' in df_filtered.columns else 'N/A'}\n\n"
                    f"⏰ **Timepoints**: {df_filtered['NominalTime'].nunique() if 'NominalTime' in df_filtered.columns else 'N/A'}"
                )
        else:
            st.warning("⚠️ 3D analysis requires Concentration, Group, and Marker columns")

    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🌐 **Dashboard URL**: http://localhost:8512")
    with col2:
        st.info(f"🎨 **Color Scheme**: {color_scheme}")
    with col3:
        animation_status = "🎥 Enabled" if enable_animations else "⏹️ Disabled"
        st.info(f"🎬 **Animations**: {animation_status}")

if __name__ == "__main__":
    main()