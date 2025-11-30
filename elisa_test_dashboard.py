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
import json
import xml.etree.ElementTree as ET
import sqlite3
from pathlib import Path
import openpyxl
from datetime import datetime, timedelta
import time
import hashlib
try:
    import xlrd
except ImportError:
    xlrd = None

st.set_page_config(
    page_title="🧬 ELISA Test Dashboard", 
    page_icon="🧬",
    layout="wide"
)

def check_file_changes(file_path):
    """Check if a file has been modified since last check"""
    if not os.path.exists(file_path):
        return False, None
    
    try:
        current_mtime = os.path.getmtime(file_path)
        if hasattr(st.session_state, 'file_mtime') and hasattr(st.session_state, 'last_file_path'):
            if st.session_state.last_file_path == file_path and current_mtime > st.session_state.file_mtime:
                st.session_state.file_mtime = current_mtime
                return True, datetime.fromtimestamp(current_mtime)
        
        st.session_state.file_mtime = current_mtime
        st.session_state.last_file_path = file_path
        return False, datetime.fromtimestamp(current_mtime)
    except Exception:
        return False, None

def auto_update_data_from_file(file_path):
    """Automatically update data if source file has changed with intelligent reconciliation"""
    if not file_path or not os.path.exists(file_path):
        return False
    
    try:
        # Only update if the file path matches current data source
        if hasattr(st.session_state, 'data_source') and file_path in st.session_state.data_source:
            new_df = pd.read_csv(file_path)
            
            # Check if data actually changed
            new_hash = hashlib.md5(str(new_df.values.tobytes()).encode()).hexdigest()
            old_hash = getattr(st.session_state, 'data_hash', None)
            
            if new_hash != old_hash:
                old_df = getattr(st.session_state, 'current_df', None)
                
                # Intelligently reconcile data structure changes
                reconciled_df, reconciliation_log, warnings = adaptive_data_reconciliation(
                    old_df, new_df, force_compatibility=True
                )
                
                # Update session state
                st.session_state.current_df = reconciled_df
                st.session_state.data_hash = new_hash
                st.session_state.data_update_count += 1
                st.session_state.last_update_time = datetime.now()
                
                # Store reconciliation information
                if 'reconciliation_history' not in st.session_state:
                    st.session_state.reconciliation_history = []
                
                reconciliation_entry = {
                    'timestamp': datetime.now(),
                    'changes_log': reconciliation_log,
                    'warnings': warnings,
                    'old_shape': old_df.shape if old_df is not None else (0, 0),
                    'new_shape': reconciled_df.shape
                }
                st.session_state.reconciliation_history.append(reconciliation_entry)
                
                # Re-analyze and adapt with new column mappings
                previous_mappings = getattr(st.session_state, 'column_mappings', {})
                new_mappings, mapping_suggestions = intelligent_column_mapping(reconciled_df, previous_mappings)
                
                st.session_state.column_mappings = new_mappings
                analysis_results = extract_and_analyze_data(reconciled_df, file_path)
                analysis_results['column_mappings'] = new_mappings
                analysis_results['mapping_suggestions'] = mapping_suggestions
                
                st.session_state.adaptive_config = adapt_dashboard_to_data(reconciled_df, analysis_results)
                st.session_state.data_analysis = analysis_results
                
                # Add smart suggestions for structure changes
                if reconciliation_log or warnings:
                    for log_entry in reconciliation_log[:3]:  # Show top 3
                        suggestion = {
                            'type': 'data_change',
                            'message': f"Data structure: {log_entry}",
                            'timestamp': datetime.now()
                        }
                        st.session_state.smart_suggestions.append(suggestion)
                
                return True
        return False
    except Exception as e:
        # Store error information
        error_suggestion = {
            'type': 'warning',
            'message': f"Auto-update failed: {str(e)}",
            'timestamp': datetime.now()
        }
        if 'smart_suggestions' not in st.session_state:
            st.session_state.smart_suggestions = []
        st.session_state.smart_suggestions.append(error_suggestion)
        return False

def smart_data_refresh():
    """Smart data refresh based on current data source"""
    if not hasattr(st.session_state, 'data_source'):
        return
    
    # Check for CSV file updates
    if st.session_state.data_source.endswith('.csv'):
        base_path = st.session_state.data_source.split(' ')[0]  # Remove any additional info
        if auto_update_data_from_file(base_path):
            st.success("🔄 Data automatically updated from file changes!")
            time.sleep(1)  # Brief pause for user to see update
            st.rerun()

def detect_column_changes(old_df, new_df):
    """Detect missing, new, and changed columns between datasets"""
    old_cols = set(old_df.columns) if old_df is not None else set()
    new_cols = set(new_df.columns)
    
    changes = {
        'missing_columns': list(old_cols - new_cols),
        'new_columns': list(new_cols - old_cols),
        'common_columns': list(old_cols & new_cols),
        'column_changes': [],
        'data_type_changes': []
    }
    
    # Check for data type changes in common columns
    if old_df is not None:
        for col in changes['common_columns']:
            if old_df[col].dtype != new_df[col].dtype:
                changes['data_type_changes'].append({
                    'column': col,
                    'old_type': str(old_df[col].dtype),
                    'new_type': str(new_df[col].dtype)
                })
    
    return changes

def intelligent_column_mapping(df, previous_mappings=None):
    """Intelligently map columns to ELISA standard format"""
    column_map = {}
    suggestions = []
    
    # Standard ELISA column patterns
    patterns = {
        'subject_id': ['subject', 'patient', 'id', 'sample_id', 'subjectid', 'patient_id', 'participant'],
        'group': ['group', 'treatment', 'condition', 'arm', 'cohort', 'treatment_group', 'study_group'],
        'biomarker': ['marker', 'biomarker', 'protein', 'analyte', 'target', 'assay', 'test'],
        'concentration': ['concentration', 'level', 'value', 'result', 'amount', 'conc', 'ng_ml', 'pg_ml'],
        'timepoint': ['timepoint', 'visit', 'time', 'day', 'week', 'month', 'baseline', 'followup'],
        'qc_flag': ['qc', 'flag', 'quality', 'pass', 'fail', 'status', 'valid'],
        'batch': ['batch', 'plate', 'run', 'assay_id', 'experiment'],
        'dilution': ['dilution', 'dil', 'factor', 'ratio']
    }

def smart_detect_columns(df, column_type='biomarker'):
    """Centralized intelligent column detection with fallbacks"""
    patterns = {
        'biomarker': ['marker', 'biomarker', 'protein', 'analyte', 'target', 'assay', 'test'],
        'group': ['group', 'treatment', 'condition', 'arm', 'cohort', 'treatment_group', 'study_group'],
        'concentration': ['concentration', 'level', 'value', 'result', 'amount', 'conc', 'ng_ml', 'pg_ml'],
        'subject': ['subject', 'patient', 'id', 'sample_id', 'subjectid', 'patient_id', 'participant'],
        'timepoint': ['timepoint', 'visit', 'time', 'day', 'week', 'month', 'baseline', 'followup']
    }
    
    if column_type not in patterns:
        return []
    
    detected = []
    keywords = patterns[column_type]
    
    # First try: exact pattern matches
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in keywords):
            detected.append(col)
    
    # Fallback: legacy hardcoded names
    if not detected and column_type == 'biomarker':
        fallback_names = ['Marker', 'Biomarker', 'Analyte']
        detected = [col for col in df.columns if col in fallback_names]
    elif not detected and column_type == 'group':
        fallback_names = ['Group', 'Treatment', 'Arm', 'Cohort']
        detected = [col for col in df.columns if col in fallback_names]
    elif not detected and column_type == 'concentration':
        fallback_names = ['Concentration', 'Value', 'Level', 'Result']
        detected = [col for col in df.columns if col in fallback_names]
    
    return detected
    
    # Use previous mappings as starting point if available
    if previous_mappings:
        column_map.update(previous_mappings)
    
    # Find best matches for each column
    for col in df.columns:
        col_lower = col.lower().replace('_', ' ').replace('-', ' ')
        best_match = None
        best_score = 0
        
        for standard_name, keywords in patterns.items():
            for keyword in keywords:
                if keyword in col_lower:
                    score = len(keyword) / len(col_lower)  # Longer matches get higher scores
                    if score > best_score:
                        best_match = standard_name
                        best_score = score
        
        if best_match and best_score > 0.3:  # Threshold for confidence
            column_map[best_match] = col
            suggestions.append(f"Mapped '{col}' to {best_match} (confidence: {best_score:.2f})")
    
    return column_map, suggestions

def handle_missing_columns(df, optional_columns, column_mappings):
    """Handle missing optional columns by creating defaults when beneficial for analysis"""
    handled_columns = []
    suggestions = []
    
    for optional_col in optional_columns:
        if optional_col not in column_mappings:
            # Try to create reasonable defaults only if they would enhance analysis
            if optional_col == 'subject_id' and len(df) > 1:
                # Create sequential subject IDs only if multiple rows exist
                df[f'auto_{optional_col}'] = [f'Subject_{i+1}' for i in range(len(df))]
                handled_columns.append(f'auto_{optional_col}')
                suggestions.append(f"Created automatic subject IDs as 'auto_{optional_col}' to enable longitudinal analysis")
            
            elif optional_col == 'group' and len(df) > 5:
                # Create single group only if dataset is large enough for group analysis
                df[f'auto_{optional_col}'] = 'Group_1'
                handled_columns.append(f'auto_{optional_col}')
                suggestions.append(f"Created default group as 'auto_{optional_col}' to enable group comparisons")
            
            elif optional_col == 'timepoint' and 'subject_id' in column_mappings:
                # Create baseline timepoint only if subjects are tracked
                df[f'auto_{optional_col}'] = 'Baseline'
                handled_columns.append(f'auto_{optional_col}')
                suggestions.append(f"Created default timepoint as 'auto_{optional_col}' for longitudinal structure")
            
            elif optional_col == 'qc_flag' and any(col for col in df.columns if 'quality' in col.lower() or 'qc' in col.lower()):
                # Default to 'Pass' for QC only if QC-related data exists
                df[f'auto_{optional_col}'] = 'Pass'
                handled_columns.append(f'auto_{optional_col}')
                suggestions.append(f"Created default QC flags as 'auto_{optional_col}' based on existing QC data")
            
            else:
                suggestions.append(f"Note: '{optional_col}' column not found - some analysis features may be limited")
    
    return df, handled_columns, suggestions

def adaptive_data_reconciliation(old_df, new_df, force_compatibility=True):
    """Reconcile data structure differences between old and new datasets"""
    if old_df is None:
        return new_df, [], ["Initial data load - no reconciliation needed"]
    
    changes = detect_column_changes(old_df, new_df)
    reconciliation_log = []
    warnings = []
    
    # Handle missing columns
    if changes['missing_columns']:
        reconciliation_log.append(f"Missing columns detected: {changes['missing_columns']}")
        if force_compatibility:
            # Add missing columns with NaN values
            for col in changes['missing_columns']:
                new_df[col] = np.nan
                reconciliation_log.append(f"Added missing column '{col}' with NaN values")
    
    # Handle new columns
    if changes['new_columns']:
        reconciliation_log.append(f"New columns detected: {changes['new_columns']}")
        # New columns are automatically included
    
    # Handle data type changes
    if changes['data_type_changes']:
        for change in changes['data_type_changes']:
            col = change['column']
            try:
                # Try to convert to the old type for compatibility
                if force_compatibility:
                    old_type = change['old_type']
                    if 'int' in old_type:
                        new_df[col] = pd.to_numeric(new_df[col], errors='coerce').fillna(0).astype('int64')
                    elif 'float' in old_type:
                        new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
                    elif 'object' in old_type:
                        new_df[col] = new_df[col].astype(str)
                    reconciliation_log.append(f"Converted '{col}' from {change['new_type']} to {old_type}")
                else:
                    warnings.append(f"Data type changed for '{col}': {change['old_type']} → {change['new_type']}")
            except Exception as e:
                warnings.append(f"Could not convert column '{col}': {str(e)}")
    
    # Ensure column order consistency if needed
    if force_compatibility and len(changes['common_columns']) > 0:
        # Reorder columns to match old dataset where possible
        old_col_order = [col for col in old_df.columns if col in new_df.columns]
        new_only_cols = [col for col in new_df.columns if col not in old_df.columns]
        final_order = old_col_order + new_only_cols
        new_df = new_df[final_order]
        reconciliation_log.append("Reordered columns to maintain consistency")
    
    return new_df, reconciliation_log, warnings

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

def read_file_by_type(uploaded_file, file_type=None):
    """Read uploaded file based on its type and return DataFrame"""
    if file_type is None:
        file_type = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_type == 'csv':
            # Try different encodings and separators for CSV
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    return df, f"CSV file loaded with {encoding} encoding"
                except UnicodeDecodeError:
                    continue
            # Try different separators
            for sep in [',', ';', '\t', '|']:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep=sep, encoding='utf-8')
                    return df, f"CSV file loaded with '{sep}' separator"
                except:
                    continue
                    
        elif file_type in ['xlsx', 'xls']:
            # Excel files
            uploaded_file.seek(0)
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            if len(sheet_names) == 1:
                df = pd.read_excel(uploaded_file, sheet_name=0)
                return df, f"Excel file loaded (sheet: {sheet_names[0]})"
            else:
                # Multiple sheets - return first sheet for now
                df = pd.read_excel(uploaded_file, sheet_name=0)
                return df, f"Excel file loaded (sheet: {sheet_names[0]}, {len(sheet_names)} sheets available)"
                
        elif file_type == 'json':
            # JSON files
            uploaded_file.seek(0)
            json_data = json.load(uploaded_file)
            
            if isinstance(json_data, list):
                df = pd.DataFrame(json_data)
            elif isinstance(json_data, dict):
                # Try to normalize nested JSON
                df = pd.json_normalize(json_data)
            else:
                df = pd.DataFrame([json_data])
            return df, "JSON file loaded and normalized"
            
        elif file_type == 'txt':
            # Text files - try to parse as delimited
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8')
            lines = content.strip().split('\n')
            
            # Detect delimiter
            first_line = lines[0]
            delimiters = ['\t', ',', ';', '|', ' ']
            best_delimiter = '\t'
            max_columns = 0
            
            for delim in delimiters:
                cols = len(first_line.split(delim))
                if cols > max_columns:
                    max_columns = cols
                    best_delimiter = delim
            
            # Parse with detected delimiter
            data = []
            headers = lines[0].split(best_delimiter)
            
            for line in lines[1:]:
                if line.strip():
                    data.append(line.split(best_delimiter))
            
            df = pd.DataFrame(data, columns=headers)
            return df, f"Text file loaded with '{best_delimiter}' delimiter"
            
        elif file_type == 'xml':
            # XML files
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8')
            root = ET.fromstring(content)
            
            # Convert XML to list of dictionaries
            data = []
            for child in root:
                item = {}
                for subchild in child:
                    item[subchild.tag] = subchild.text
                data.append(item)
            
            if not data:
                # Try different XML structure
                data = [root.attrib] if root.attrib else [{'content': root.text}]
            
            df = pd.DataFrame(data)
            return df, "XML file loaded and parsed"
            
        elif file_type == 'db' or file_type == 'sqlite':
            # Database files (SQLite)
            uploaded_file.seek(0)
            # Save temp file to read with sqlite3
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.read())
            
            conn = sqlite3.connect(temp_path)
            tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
            
            if len(tables) > 0:
                table_name = tables.iloc[0]['name']
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                conn.close()
                os.remove(temp_path)
                return df, f"Database file loaded (table: {table_name})"
            else:
                conn.close()
                os.remove(temp_path)
                return pd.DataFrame(), "Database file loaded but no tables found"
        
        else:
            return pd.DataFrame(), f"Unsupported file type: {file_type}"
            
    except Exception as e:
        return pd.DataFrame(), f"Error reading file: {str(e)}"
    
    return pd.DataFrame(), "Unknown error occurred"

def adapt_dashboard_to_data(df, analysis_results):
    """Adapt dashboard configuration based on column mapping analysis"""
    adaptive_config = {
        'suggested_tabs': [],
        'recommended_analyses': [],
        'filter_suggestions': [],
        'visualization_options': [],
        'statistical_tests': [],
        'export_formats': ['CSV', 'Excel'],
        'data_insights': {},
        'priority_analyses': [],
        'analysis_workflow': []
    }
    
    # Handle None analysis_results gracefully
    if analysis_results is None:
        analysis_results = {}
    
    # Get analysis capabilities from column mapping
    mapped_cols = analysis_results.get('mapped_columns', {})
    capabilities = analysis_results.get('analysis_capabilities', {})
    statistical_readiness = analysis_results.get('statistical_readiness', {})
    
    # Essential tabs - always include Overview
    adaptive_config['suggested_tabs'].append('Overview')
    
    # Configure tabs based on analysis capabilities
    if capabilities.get('concentration_analysis', False):
        adaptive_config['suggested_tabs'].append('Concentrations')
        adaptive_config['visualization_options'].extend(['Box Plot', 'Violin Plot', 'Histogram', 'Density Plot'])
        adaptive_config['priority_analyses'].append('Concentration Distribution Analysis')
    
    if capabilities.get('group_comparison', False):
        adaptive_config['suggested_tabs'].append('Statistics')
        if statistical_readiness.get('group_comparison', {}).get('ready', False):
            adaptive_config['statistical_tests'].extend(['t-test', 'ANOVA', 'Mann-Whitney U', 'Kruskal-Wallis'])
            adaptive_config['recommended_analyses'].append('Group Comparison Analysis')
            adaptive_config['priority_analyses'].append('Statistical Group Comparison')
        else:
            adaptive_config['recommended_analyses'].append('Group Analysis (with data preparation needed)')
    
    if capabilities.get('longitudinal_analysis', False):
        adaptive_config['suggested_tabs'].append('Longitudinal')
        adaptive_config['visualization_options'].extend(['Time Series', 'Line Plot', 'Area Chart', 'Trajectory Plot'])
        if statistical_readiness.get('longitudinal', {}).get('ready', False):
            adaptive_config['recommended_analyses'].append('Longitudinal Trend Analysis')
            adaptive_config['priority_analyses'].append('Time Course Analysis')
        else:
            adaptive_config['recommended_analyses'].append('Longitudinal Analysis (prepare subject tracking)')
    
    if capabilities.get('quality_control', False):
        adaptive_config['suggested_tabs'].append('Quality Control')
        adaptive_config['visualization_options'].extend(['QC Plot', 'Outlier Detection', 'Batch Effects'])
        adaptive_config['recommended_analyses'].append('Data Quality Assessment')
    
    if capabilities.get('correlation_analysis', False):
        if statistical_readiness.get('correlation', {}).get('ready', False):
            adaptive_config['visualization_options'].extend(['Correlation Matrix', 'Scatter Matrix', 'Heatmap'])
            adaptive_config['recommended_analyses'].append('Correlation Analysis')
    
    if capabilities.get('multivariate_analysis', False):
        adaptive_config['suggested_tabs'].append('3D Analysis')
        adaptive_config['visualization_options'].extend(['3D Scatter', '3D Surface', 'PCA Plot'])
        adaptive_config['recommended_analyses'].append('Multivariate Analysis')
    
    if capabilities.get('dose_response', False):
        adaptive_config['visualization_options'].extend(['Dose-Response Curve', 'EC50 Analysis'])
        adaptive_config['recommended_analyses'].append('Dose-Response Analysis')
        adaptive_config['priority_analyses'].append('Pharmacological Analysis')
    
    # Advanced features based on data complexity
    if len(df.columns) > 5:
        adaptive_config['suggested_tabs'].append('Quality Control')
        adaptive_config['recommended_analyses'].append('Data Quality Assessment')
    
    if len(df.columns) >= 3 and len(df) > 20:
        adaptive_config['suggested_tabs'].append('3D Analysis')
        adaptive_config['visualization_options'].extend(['3D Scatter', '3D Surface', 'Correlation Matrix'])
    
    # Always include Data Insights for new data
    adaptive_config['suggested_tabs'].append('Data Insights')
    
    # Generate analysis workflow based on column mappings and readiness
    workflow = generate_analysis_workflow(mapped_cols, capabilities, statistical_readiness)
    adaptive_config['analysis_workflow'] = workflow
    
    # Smart filter suggestions based on mapped columns
    filter_suggestions = generate_smart_filters(df, mapped_cols)
    adaptive_config['filter_suggestions'] = filter_suggestions
    
    # Export format suggestions
    if 'timepoint' in mapped_cols:
        adaptive_config['export_formats'].extend(['JSON', 'Time Series CSV'])
    if len(df.columns) > 10:
        adaptive_config['export_formats'].extend(['Excel Multi-sheet', 'Database'])
    
    # Data insights
    adaptive_config['data_insights'] = {
        'primary_analysis_type': 'ELISA Biomarker Analysis' if any(key in mapped_cols for key in ['marker', 'concentration']) else 'General Data Analysis',
        'complexity_level': 'High' if len(df.columns) > 8 else 'Medium' if len(df.columns) > 4 else 'Basic',
        'recommended_workflow': get_recommended_workflow(mapped_cols, df),
        'data_readiness': assess_data_readiness(df, analysis_results)
    }
    
    return adaptive_config

def generate_analysis_workflow(mapped_cols, capabilities, statistical_readiness):
    """Generate optimal analysis workflow based on column mappings"""
    workflow = []
    
    # Always start with overview
    workflow.append({
        'step': 1,
        'title': 'Data Overview',
        'description': 'Review data structure and column mappings',
        'tab': 'Overview',
        'priority': 'high'
    })
    
    # Add steps based on what's actually mapped and ready
    step_num = 2
    
    if capabilities.get('concentration_analysis', False):
        conc_col = mapped_cols.get('concentration', 'concentration')
        workflow.append({
            'step': step_num,
            'title': 'Concentration Analysis',
            'description': f'Analyze {conc_col} distribution and descriptive statistics',
            'tab': 'Concentrations',
            'priority': 'high'
        })
        step_num += 1
    
    if capabilities.get('quality_control', False):
        workflow.append({
            'step': step_num,
            'title': 'Quality Control',
            'description': 'Assess data quality and identify outliers',
            'tab': 'Quality Control',
            'priority': 'high'
        })
        step_num += 1
    
    if statistical_readiness.get('group_comparison', {}).get('ready', False):
        group_col = mapped_cols.get('group', 'group')
        workflow.append({
            'step': step_num,
            'title': 'Group Comparisons',
            'description': f'Statistical comparison between {group_col} categories',
            'tab': 'Statistics',
            'priority': 'high'
        })
        step_num += 1
    elif capabilities.get('group_comparison', False):
        workflow.append({
            'step': step_num,
            'title': 'Group Analysis Preparation',
            'description': 'Prepare data for group comparison analysis',
            'tab': 'Statistics',
            'priority': 'medium'
        })
        step_num += 1
    
    if statistical_readiness.get('longitudinal', {}).get('ready', False):
        time_col = mapped_cols.get('timepoint', 'timepoint')
        workflow.append({
            'step': step_num,
            'title': 'Longitudinal Analysis',
            'description': f'Analyze changes over {time_col}',
            'tab': 'Longitudinal',
            'priority': 'high'
        })
        step_num += 1
    
    if capabilities.get('correlation_analysis', False) and statistical_readiness.get('correlation', {}).get('ready', False):
        workflow.append({
            'step': step_num,
            'title': 'Correlation Analysis',
            'description': 'Explore relationships between variables',
            'tab': '3D Analysis',
            'priority': 'medium'
        })
        step_num += 1
    
    if capabilities.get('multivariate_analysis', False):
        workflow.append({
            'step': step_num,
            'title': 'Advanced Analysis',
            'description': 'Multivariate and 3D analysis',
            'tab': '3D Analysis',
            'priority': 'low'
        })
        step_num += 1
    
    # Always end with insights
    workflow.append({
        'step': step_num,
        'title': 'Results Summary',
        'description': 'Review all analysis results and insights',
        'tab': 'Data Insights',
        'priority': 'medium'
    })
    
    return workflow

def detect_plate_layout(df):
    """Detect plate layout and well mapping from uploaded data"""
    plate_info = {
        'layout_detected': False,
        'plate_format': None,
        'well_mapping': {},
        'plate_dimensions': None,
        'replicates': [],
        'controls': [],
        'samples': []
    }
    
    # Look for well position columns
    well_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['well', 'position', 'row', 'col', 'plate'])]
    
    if well_columns:
        plate_info['layout_detected'] = True
        
        # Try to detect plate format from well patterns
        for col in well_columns:
            if col in df.columns:
                well_values = df[col].dropna().astype(str)
                
                # Check for standard well formats (A01, A1, etc.)
                if any(well_values.str.match(r'^[A-H][0-9]{1,2}$|^[A-P][0-9]{1,2}$')):
                    unique_wells = well_values.unique()
                    
                    # Determine plate format
                    max_row = max([well[0] for well in unique_wells if len(well) > 0])
                    max_col = max([int(well[1:]) for well in unique_wells if len(well) > 1 and well[1:].isdigit()])
                    
                    if max_row <= 'H' and max_col <= 12:
                        plate_info['plate_format'] = '96-well'
                        plate_info['plate_dimensions'] = (8, 12)
                    elif max_row <= 'P' and max_col <= 24:
                        plate_info['plate_format'] = '384-well'
                        plate_info['plate_dimensions'] = (16, 24)
                    
                    # Map wells to data
                    for idx, row in df.iterrows():
                        well_pos = str(row[col])
                        if well_pos in unique_wells:
                            plate_info['well_mapping'][well_pos] = {
                                'row_index': idx,
                                'sample_info': row.to_dict()
                            }
                    
                    break
    
    # Detect replicates, controls, and samples
    if 'well_mapping' in plate_info and plate_info['well_mapping']:
        # Look for control patterns
        control_indicators = ['blank', 'ctrl', 'control', 'std', 'standard', 'cal', 'calibrator']
        
        for well, info in plate_info['well_mapping'].items():
            sample_data = info['sample_info']
            
            # Check if this is a control
            is_control = False
            for key, value in sample_data.items():
                if isinstance(value, str) and any(indicator in value.lower() for indicator in control_indicators):
                    is_control = True
                    plate_info['controls'].append({
                        'well': well,
                        'type': 'control',
                        'info': sample_data
                    })
                    break
            
            if not is_control:
                plate_info['samples'].append({
                    'well': well,
                    'type': 'sample',
                    'info': sample_data
                })
        
        # Detect replicates (same sample in multiple wells)
        sample_groups = {}
        for sample in plate_info['samples']:
            # Group by potential replicate identifiers
            for key, value in sample['info'].items():
                if isinstance(value, str) and any(keyword in key.lower() for keyword in ['subject', 'sample', 'id']):
                    if value not in sample_groups:
                        sample_groups[value] = []
                    sample_groups[value].append(sample)
        
        # Identify replicates (groups with multiple wells)
        for sample_id, wells in sample_groups.items():
            if len(wells) > 1:
                plate_info['replicates'].append({
                    'sample_id': sample_id,
                    'wells': [w['well'] for w in wells],
                    'replicate_count': len(wells)
                })
    
    return plate_info

def adapt_to_plate_layout(df, plate_info):
    """Adapt analysis based on detected plate layout"""
    adaptations = {
        'replicate_handling': None,
        'control_analysis': None,
        'spatial_analysis': None,
        'plate_effects': None,
        'recommendations': []
    }
    
    if plate_info['layout_detected']:
        adaptations['recommendations'].append(f"✅ {plate_info['plate_format']} plate layout detected")
        
        # Replicate handling
        if plate_info['replicates']:
            adaptations['replicate_handling'] = {
                'strategy': 'average',
                'replicates_found': len(plate_info['replicates']),
                'total_replicate_wells': sum(r['replicate_count'] for r in plate_info['replicates'])
            }
            adaptations['recommendations'].append(f"🔄 {len(plate_info['replicates'])} replicated samples detected - averaging enabled")
        
        # Control analysis
        if plate_info['controls']:
            adaptations['control_analysis'] = {
                'controls_found': len(plate_info['controls']),
                'control_types': list(set([c.get('type', 'unknown') for c in plate_info['controls']]))
            }
            adaptations['recommendations'].append(f"🎯 {len(plate_info['controls'])} control wells detected")
        
        # Spatial analysis capabilities
        if plate_info['plate_dimensions']:
            rows, cols = plate_info['plate_dimensions']
            adaptations['spatial_analysis'] = {
                'enabled': True,
                'dimensions': plate_info['plate_dimensions'],
                'total_wells': rows * cols
            }
            adaptations['recommendations'].append(f"🗺️ Spatial analysis enabled for {rows}x{cols} layout")
        
        # Plate effects detection
        if len(plate_info['well_mapping']) > 20:  # Sufficient wells for plate effects
            adaptations['plate_effects'] = {
                'detection_enabled': True,
                'edge_effect_analysis': True,
                'batch_effect_analysis': True
            }
            adaptations['recommendations'].append("📊 Plate effects analysis enabled")
    
    return adaptations

def generate_smart_filters(df, mapped_cols):
    """Generate intelligent filter suggestions based on column mappings"""
    filters = []
    
    # Priority filters based on mapped columns
    priority_filters = ['group', 'timepoint', 'biomarker', 'batch']
    
    for filter_type in priority_filters:
        if filter_type in mapped_cols:
            col_name = mapped_cols[filter_type]
            if col_name in df.columns:
                unique_vals = df[col_name].nunique()
                if 2 <= unique_vals <= 50:  # Reasonable for filtering
                    filters.append({
                        'column': col_name,
                        'type': 'multiselect',
                        'values': list(df[col_name].unique()),
                        'reason': f'Filter by {filter_type} ({unique_vals} categories)',
                        'priority': 'high' if filter_type in ['group', 'timepoint'] else 'medium',
                        'mapped_as': filter_type
                    })
    
    # Additional categorical filters from unmapped columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    mapped_col_names = set(mapped_cols.values())
    
    for col in categorical_cols:
        if col not in mapped_col_names:  # Not already mapped
            unique_vals = df[col].nunique()
            if 2 <= unique_vals <= 20:  # Good for filtering
                filters.append({
                    'column': col,
                    'type': 'multiselect',
                    'values': list(df[col].unique()),
                    'reason': f'Filter by {col} ({unique_vals} categories)',
                    'priority': 'low',
                    'mapped_as': 'unmapped'
                })
    
    # Numeric range filters for key columns
    if 'concentration' in mapped_cols:
        conc_col = mapped_cols['concentration']
        if conc_col in df.columns and pd.api.types.is_numeric_dtype(df[conc_col]):
            conc_data = df[conc_col].dropna()
            if len(conc_data) > 0:
                filters.append({
                    'column': conc_col,
                    'type': 'range',
                    'min_value': float(conc_data.min()),
                    'max_value': float(conc_data.max()),
                    'reason': f'Filter by concentration range',
                    'priority': 'medium',
                    'mapped_as': 'concentration'
                })
    
    return filters

def get_recommended_workflow(mapped_cols, df):
    """Generate recommended analysis workflow based on data structure"""
    workflow = []
    
    workflow.append("1. 📊 Start with Overview tab for data exploration")
    
    if 'concentration' in mapped_cols:
        workflow.append("2. 🧪 Check Concentrations tab for biomarker levels")
    
    if 'timepoint' in mapped_cols:
        workflow.append("3. 📈 Analyze Longitudinal changes over time")
    
    if 'group' in mapped_cols:
        workflow.append("4. 📊 Perform Statistical comparisons between groups")
    
    workflow.append("5. 🔍 Review Quality Control for data validation")
    
    if len(df.columns) >= 3:
        workflow.append("6. 🌍 Explore 3D Analysis for complex relationships")
    
    workflow.append("7. 💡 Check Data Insights for detailed analysis summary")
    
    return workflow

def analyze_capabilities_from_mapping(df, column_mappings):
    """Determine analysis capabilities based on successful column mappings"""
    capabilities = {
        'basic_statistics': False,
        'group_comparison': False,
        'longitudinal_analysis': False,
        'concentration_analysis': False,
        'quality_control': False,
        'correlation_analysis': False,
        'multivariate_analysis': False,
        'dose_response': False
    }
    
    # Basic statistics - needs any numeric column
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        capabilities['basic_statistics'] = True
    
    # Concentration analysis - optional, uses any numeric column if concentration not mapped
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if 'concentration' in column_mappings:
        conc_col = column_mappings['concentration']
        if conc_col in df.columns and pd.api.types.is_numeric_dtype(df[conc_col]):
            capabilities['concentration_analysis'] = True
    elif len(numeric_cols) > 0:
        # Enable concentration analysis with any numeric column
        capabilities['concentration_analysis'] = True
    
    # Group comparison - flexible, can use any categorical + numeric combination
    categorical_cols = df.select_dtypes(include=['object']).columns
    if 'group' in column_mappings and len(numeric_cols) > 0:
        group_col = column_mappings['group']
        if group_col in df.columns and df[group_col].nunique() >= 2:
            capabilities['group_comparison'] = True
    elif len(categorical_cols) > 0 and len(numeric_cols) > 0:
        # Enable if any categorical column with multiple values exists
        for cat_col in categorical_cols:
            if df[cat_col].nunique() >= 2:
                capabilities['group_comparison'] = True
                break
    
    # Longitudinal analysis - flexible, can use any time-like column with numeric data
    if 'timepoint' in column_mappings and len(numeric_cols) > 0:
        time_col = column_mappings['timepoint']
        if time_col in df.columns and df[time_col].nunique() >= 2:
            capabilities['longitudinal_analysis'] = True
    elif len(numeric_cols) > 0:
        # Look for any time-like columns
        time_like_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['time', 'date', 'visit', 'day', 'week', 'month'])]
        for time_col in time_like_cols:
            if df[time_col].nunique() >= 2:
                capabilities['longitudinal_analysis'] = True
                break
    
    # Quality control - needs QC flag or can create from other columns
    if 'qc_flag' in column_mappings or 'batch' in column_mappings:
        capabilities['quality_control'] = True
    elif len(numeric_cols) > 1:  # Can do QC analysis with multiple numeric columns
        capabilities['quality_control'] = True
    
    # Correlation analysis - needs multiple numeric columns
    if len(numeric_cols) >= 2:
        capabilities['correlation_analysis'] = True
    
    # Multivariate analysis - needs subject, multiple biomarkers or multiple numeric columns
    if 'subject_id' in column_mappings and len(numeric_cols) >= 3:
        capabilities['multivariate_analysis'] = True
    elif 'biomarker' in column_mappings:
        biomarker_col = column_mappings['biomarker']
        if biomarker_col in df.columns and df[biomarker_col].nunique() >= 3:
            capabilities['multivariate_analysis'] = True
    
    # Dose response - needs concentration and group (assuming groups represent doses)
    if capabilities['group_comparison'] and 'concentration' in column_mappings:
        group_col = column_mappings['group']
        # Check if group names suggest dose levels
        group_names = df[group_col].unique().astype(str)
        dose_indicators = ['dose', 'mg', 'µg', 'ng', 'low', 'med', 'high', '0.', '1.', '2.', '5.', '10.']
        if any(indicator in ' '.join(group_names).lower() for indicator in dose_indicators):
            capabilities['dose_response'] = True
    
    return capabilities

def assess_statistical_readiness(df, column_mappings):
    """Assess statistical readiness for each analysis type based on column mappings"""
    readiness = {
        'descriptive_stats': {'ready': False, 'requirements': [], 'issues': []},
        'group_comparison': {'ready': False, 'requirements': [], 'issues': []},
        'longitudinal': {'ready': False, 'requirements': [], 'issues': []},
        'correlation': {'ready': False, 'requirements': [], 'issues': []},
        'quality_control': {'ready': False, 'requirements': [], 'issues': []}
    }
    
    # Descriptive statistics readiness
    if 'concentration' in column_mappings:
        conc_col = column_mappings['concentration']
        if conc_col in df.columns:
            conc_data = df[conc_col]
            if pd.api.types.is_numeric_dtype(conc_data):
                missing_pct = (conc_data.isnull().sum() / len(conc_data)) * 100
                if missing_pct < 50:
                    readiness['descriptive_stats']['ready'] = True
                else:
                    readiness['descriptive_stats']['issues'].append(f"High missing data: {missing_pct:.1f}%")
            else:
                readiness['descriptive_stats']['issues'].append("Concentration column is not numeric")
        readiness['descriptive_stats']['requirements'] = ['Numeric concentration column']
    else:
        readiness['descriptive_stats']['issues'].append("No concentration column mapped")
        readiness['descriptive_stats']['requirements'] = ['Concentration column mapping needed']
    
    # Group comparison readiness
    if 'group' in column_mappings and 'concentration' in column_mappings:
        group_col = column_mappings['group']
        conc_col = column_mappings['concentration']
        
        requirements_met = True
        requirements = ['Group column', 'Numeric concentration column', 'At least 2 groups', 'Minimum 3 samples per group']
        
        if group_col in df.columns and conc_col in df.columns:
            group_counts = df[group_col].value_counts()
            if len(group_counts) < 2:
                readiness['group_comparison']['issues'].append("Less than 2 groups")
                requirements_met = False
            elif group_counts.min() < 3:
                readiness['group_comparison']['issues'].append(f"Some groups have <3 samples (min: {group_counts.min()})")
                requirements_met = False
            
            if not pd.api.types.is_numeric_dtype(df[conc_col]):
                readiness['group_comparison']['issues'].append("Concentration column is not numeric")
                requirements_met = False
        else:
            readiness['group_comparison']['issues'].append("Required columns not found")
            requirements_met = False
        
        readiness['group_comparison']['ready'] = requirements_met
        readiness['group_comparison']['requirements'] = requirements
    else:
        readiness['group_comparison']['issues'].append("Group or concentration mapping missing")
        readiness['group_comparison']['requirements'] = ['Group and concentration column mappings needed']
    
    # Longitudinal analysis readiness
    if 'timepoint' in column_mappings and 'concentration' in column_mappings:
        time_col = column_mappings['timepoint']
        conc_col = column_mappings['concentration']
        
        requirements_met = True
        requirements = ['Timepoint column', 'Numeric concentration', 'At least 2 timepoints', 'Subject ID (recommended)']
        
        if time_col in df.columns and conc_col in df.columns:
            time_counts = df[time_col].nunique()
            if time_counts < 2:
                readiness['longitudinal']['issues'].append("Less than 2 timepoints")
                requirements_met = False
            
            if 'subject_id' not in column_mappings:
                readiness['longitudinal']['issues'].append("No subject ID - limited longitudinal analysis")
            
            if not pd.api.types.is_numeric_dtype(df[conc_col]):
                readiness['longitudinal']['issues'].append("Concentration column is not numeric")
                requirements_met = False
        else:
            readiness['longitudinal']['issues'].append("Required columns not found")
            requirements_met = False
        
        readiness['longitudinal']['ready'] = requirements_met
        readiness['longitudinal']['requirements'] = requirements
    else:
        readiness['longitudinal']['issues'].append("Timepoint or concentration mapping missing")
        readiness['longitudinal']['requirements'] = ['Timepoint and concentration column mappings needed']
    
    # Correlation analysis readiness
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) >= 2:
        readiness['correlation']['ready'] = True
        readiness['correlation']['requirements'] = ['At least 2 numeric columns']
    else:
        readiness['correlation']['issues'].append(f"Only {len(numeric_cols)} numeric columns found")
        readiness['correlation']['requirements'] = ['At least 2 numeric columns needed']
    
    # Quality control readiness
    if 'qc_flag' in column_mappings or len(numeric_cols) > 0:
        readiness['quality_control']['ready'] = True
        readiness['quality_control']['requirements'] = ['QC flag column OR numeric data for outlier detection']
    else:
        readiness['quality_control']['issues'].append("No QC indicators or numeric data")
        readiness['quality_control']['requirements'] = ['QC flag column or numeric columns needed']
    
    return readiness

def assess_data_readiness(df, analysis_results):
    """Assess overall data readiness using column mapping insights"""
    readiness_score = 100
    issues = []
    
    # Get mapped columns for more intelligent assessment
    mapped_columns = analysis_results.get('mapped_columns', {})
    
    # Check for missing values in mapped columns
    critical_missing = 0
    for standard_name, actual_col in mapped_columns.items():
        if actual_col in df.columns:
            missing_pct = (df[actual_col].isnull().sum() / len(df)) * 100
            if missing_pct > 20:
                critical_missing += 1
                issues.append(f"High missing data in {standard_name}: {missing_pct:.1f}%")
                readiness_score -= 15
            elif missing_pct > 5:
                issues.append(f"Some missing data in {standard_name}: {missing_pct:.1f}%")
                readiness_score -= 5
    
    # Check for duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        readiness_score -= min(20, dup_count * 2)  # Cap penalty at 20 points
        issues.append(f"{dup_count} duplicate rows found")
    
    # Assess column mapping success (no essential columns required)
    recommended_mappings = ['subject_id', 'group', 'timepoint', 'concentration', 'biomarker']  # All optional but recommended
    
    recommended_mapped = sum(1 for col in recommended_mappings if col in mapped_columns)
    
    if recommended_mapped == 0:
        readiness_score -= 20
        issues.append("No standard ELISA columns detected - generic analysis will be used")
    elif recommended_mapped < 3:
        readiness_score -= 10
        issues.append(f"Only {recommended_mapped}/{len(recommended_mappings)} standard columns mapped")
    
    # Check data size adequacy
    if len(df) < 5:
        readiness_score -= 40
        issues.append("Very small dataset size (<5 rows)")
    elif len(df) < 10:
        readiness_score -= 20
        issues.append("Small dataset size (<10 rows)")
    
    # Check for statistical analysis viability
    statistical_readiness = analysis_results.get('statistical_readiness', {})
    ready_analyses = sum(1 for analysis in statistical_readiness.values() if analysis.get('ready', False))
    
    if ready_analyses == 0:
        readiness_score -= 25
        issues.append("No statistical analyses are ready to perform")
    elif ready_analyses < 3:
        readiness_score -= 10
        issues.append(f"Only {ready_analyses} statistical analyses are ready")
    
    # Final assessment
    status = "Excellent" if readiness_score >= 90 else "Good" if readiness_score >= 75 else "Fair" if readiness_score >= 60 else "Needs Improvement"
    
    return {
        'score': max(0, readiness_score),  # Don't go below 0
        'status': status,
        'issues': issues,
        'mapped_columns': len(mapped_columns),
        'ready_analyses': ready_analyses
    }

def read_column_ids_and_update_analysis(df, file_name):
    """Dynamically read column IDs from input data and configure analysis accordingly"""
    column_analysis = {
        'detected_columns': list(df.columns),
        'column_count': len(df.columns),
        'column_types': {},
        'column_patterns': {},
        'potential_mappings': {},
        'analysis_paths': [],
        'data_relationships': {},
        'recommended_visualizations': []
    }
    
    # Analyze each column for type, pattern, and potential use
    for col_id in df.columns:
        col_data = df[col_id]
        
        # Basic type analysis
        column_analysis['column_types'][col_id] = {
            'dtype': str(col_data.dtype),
            'is_numeric': pd.api.types.is_numeric_dtype(col_data),
            'is_categorical': isinstance(col_data.dtype, pd.CategoricalDtype) or col_data.dtype == 'object',
            'unique_values': col_data.nunique(),
            'null_count': col_data.isnull().sum(),
            'sample_values': col_data.dropna().head(3).tolist() if not col_data.empty else []
        }
        
        # Pattern recognition for ELISA-specific columns
        col_lower = col_id.lower()
        patterns = []
        
        if any(term in col_lower for term in ['subject', 'patient', 'id', 'participant']):
            patterns.append('subject_identifier')
        if any(term in col_lower for term in ['group', 'treatment', 'arm', 'cohort']):
            patterns.append('treatment_group')
        if any(term in col_lower for term in ['concentration', 'conc', 'level', 'amount', 'value', 'measurement', 'result', 'reading', 'response', 'intensity', 'expression', 'activity']):
            patterns.append('measurement_value')
        if any(term in col_lower for term in ['marker', 'biomarker', 'analyte', 'protein', 'gene', 'cytokine', 'antibody']):
            patterns.append('biomarker_name')
        if any(term in col_lower for term in ['time', 'day', 'hour', 'visit', 'week', 'month', 'year', 'date']):
            patterns.append('timepoint')
        if any(term in col_lower for term in ['well', 'position', 'row', 'col', 'plate']):
            patterns.append('plate_position')
        if any(term in col_lower for term in ['signal', 'od', 'absorbance', 'raw', 'optical', 'density', 'fluorescence', 'luminescence']):
            patterns.append('raw_signal')
        
        column_analysis['column_patterns'][col_id] = patterns
        
        # Determine potential analysis uses
        if column_analysis['column_types'][col_id]['is_numeric']:
            # More flexible primary endpoint detection
            is_primary_endpoint = False
            
            # Direct pattern matches for measurement values
            if 'measurement_value' in patterns or 'raw_signal' in patterns:
                is_primary_endpoint = True
            
            # Additional heuristics for numeric measurement columns
            elif column_analysis['column_types'][col_id]['unique_values'] > 5:  # Likely continuous measurement
                # Check if it's not clearly a metadata column
                non_measurement_terms = ['id', 'count', 'number', 'index', 'rank', 'order']
                if not any(term in col_lower for term in non_measurement_terms):
                    # Check if it has reasonable measurement characteristics
                    sample_values = column_analysis['column_types'][col_id]['sample_values']
                    if sample_values and all(isinstance(v, (int, float)) for v in sample_values):
                        is_primary_endpoint = True
            
            # Assign mapping based on classification
            if is_primary_endpoint:
                column_analysis['potential_mappings'][col_id] = 'primary_endpoint'
            elif 'raw_signal' in patterns:
                column_analysis['potential_mappings'][col_id] = 'quality_control'
            else:
                column_analysis['potential_mappings'][col_id] = 'continuous_variable'
        else:
            if 'subject_identifier' in patterns:
                column_analysis['potential_mappings'][col_id] = 'grouping_variable'
            elif 'treatment_group' in patterns:
                column_analysis['potential_mappings'][col_id] = 'stratification_factor'
            elif 'biomarker_name' in patterns:
                column_analysis['potential_mappings'][col_id] = 'analysis_dimension'
            else:
                column_analysis['potential_mappings'][col_id] = 'categorical_variable'
    
    # Determine possible analysis paths based on detected columns
    analysis_paths = determine_analysis_paths(column_analysis)
    column_analysis['analysis_paths'] = analysis_paths
    
    return column_analysis

def determine_analysis_paths(column_analysis):
    """Determine what types of analysis are possible based on column structure"""
    paths = []
    mappings = column_analysis['potential_mappings']
    
    # Check for basic statistical analysis
    numeric_endpoints = [col for col, mapping in mappings.items() if mapping == 'primary_endpoint']
    grouping_vars = [col for col, mapping in mappings.items() if mapping in ['stratification_factor', 'grouping_variable']]
    
    if numeric_endpoints:
        paths.append({
            'type': 'descriptive_statistics',
            'description': f'Statistical analysis of {len(numeric_endpoints)} numeric endpoint(s)',
            'columns': numeric_endpoints,
            'confidence': 'high'
        })
        
        if grouping_vars:
            paths.append({
                'type': 'comparative_analysis', 
                'description': f'Group comparison using {len(grouping_vars)} grouping variable(s)',
                'columns': numeric_endpoints + grouping_vars,
                'confidence': 'high'
            })
    
    # Check for biomarker analysis
    biomarker_cols = [col for col, patterns in column_analysis['column_patterns'].items() 
                     if 'biomarker_name' in patterns]
    if biomarker_cols and numeric_endpoints:
        paths.append({
            'type': 'biomarker_analysis',
            'description': f'Multi-biomarker analysis across {len(biomarker_cols)} marker(s)',
            'columns': biomarker_cols + numeric_endpoints,
            'confidence': 'high'
        })
    
    # Check for longitudinal analysis
    time_cols = [col for col, patterns in column_analysis['column_patterns'].items() 
                if 'timepoint' in patterns]
    if time_cols and numeric_endpoints:
        paths.append({
            'type': 'longitudinal_analysis',
            'description': f'Time-series analysis using {len(time_cols)} time variable(s)', 
            'columns': time_cols + numeric_endpoints,
            'confidence': 'medium'
        })
    
    # Check for plate-based QC analysis
    plate_cols = [col for col, patterns in column_analysis['column_patterns'].items() 
                 if 'plate_position' in patterns]
    raw_signal_cols = [col for col, patterns in column_analysis['column_patterns'].items() 
                      if 'raw_signal' in patterns]
    
    if plate_cols and (raw_signal_cols or numeric_endpoints):
        paths.append({
            'type': 'plate_qc_analysis',
            'description': f'Plate-based quality control using {len(plate_cols)} position variable(s)',
            'columns': plate_cols + (raw_signal_cols or numeric_endpoints),
            'confidence': 'medium'
        })
    
    return paths

def extract_and_analyze_data(df, file_name):
    """Extract meaningful data from newly imported files and prepare for analysis using dynamic column reading"""
    try:
        # Validate inputs
        if df is None or df.empty:
            return None
        
        # First, read and analyze all column IDs dynamically
        column_analysis = read_column_ids_and_update_analysis(df, file_name or "Unknown")
    
        analysis_results = {
        'original_shape': df.shape,
        'columns': list(df.columns),
        'column_analysis': column_analysis,
        'data_types': df.dtypes.to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'recommendations': [],
        'mapped_columns': {},
        'processed_df': df.copy(),
        'analysis_capabilities': {},
        'statistical_readiness': {}
        }
        
        # Get intelligent column mappings as the primary analysis driver
        column_mappings, mapping_suggestions = intelligent_column_mapping(df)
        analysis_results['mapped_columns'] = column_mappings
        analysis_results['mapping_suggestions'] = mapping_suggestions
        
        # Configure analysis capabilities based on mapped columns
        capabilities = analyze_capabilities_from_mapping(df, column_mappings)
        analysis_results['analysis_capabilities'] = capabilities
        
        # Assess statistical readiness for each analysis type
        statistical_readiness = assess_statistical_readiness(df, column_mappings)
        analysis_results['statistical_readiness'] = statistical_readiness
        
        # Data quality analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        analysis_results['numeric_columns'] = list(numeric_cols)
        analysis_results['categorical_columns'] = list(categorical_cols)
        
        # Generate dynamic recommendations based on column analysis
        column_analysis = analysis_results['column_analysis']
        
        # Add recommendations for each detected analysis path
        for path in column_analysis['analysis_paths']:
            confidence_icon = "🔥" if path['confidence'] == 'high' else "⚡" if path['confidence'] == 'medium' else "💡"
            analysis_results['recommendations'].append(f"{confidence_icon} {path['description']}")
        
        # Specific column-based recommendations
        primary_endpoints = [col for col, mapping in column_analysis['potential_mappings'].items() 
                            if mapping == 'primary_endpoint']
        if primary_endpoints:
            for col in primary_endpoints:
                desc_stats = df[col].describe()
                analysis_results['recommendations'].append(
                    f"🧬 Primary endpoint '{col}' detected - Mean: {desc_stats['mean']:.2f}, Range: {desc_stats['min']:.2f}-{desc_stats['max']:.2f}"
                )
        
        stratification_factors = [col for col, mapping in column_analysis['potential_mappings'].items() 
                                 if mapping == 'stratification_factor']
        if stratification_factors:
            for col in stratification_factors:
                unique_vals = df[col].unique()
                analysis_results['recommendations'].append(
                    f"👥 Stratification factor '{col}' detected - {len(unique_vals)} groups: {', '.join(map(str, unique_vals[:3]))}{'...' if len(unique_vals) > 3 else ''}"
                )
        
        analysis_dimensions = [col for col, mapping in column_analysis['potential_mappings'].items() 
                              if mapping == 'analysis_dimension']
        if analysis_dimensions:
            for col in analysis_dimensions:
                unique_markers = df[col].unique()
                analysis_results['recommendations'].append(
                    f"🔬 Analysis dimension '{col}' detected - {len(unique_markers)} unique values for multi-dimensional analysis"
                )
        
        # Generate visualization recommendations based on column analysis
        viz_recommendations = generate_visualization_recommendations(column_analysis, df)
        analysis_results['visualization_recommendations'] = viz_recommendations
        
        for viz in viz_recommendations:
            analysis_results['recommendations'].append(f"📊 {viz['description']} using columns: {', '.join(viz['columns'])}")
        
        # Missing data analysis and handling
        missing_data = df.isnull().sum()
        total_missing = missing_data.sum()
        missing_percentage = (total_missing / (len(df) * len(df.columns))) * 100
        
        # Create cleaned dataset for analysis (remove rows with missing values in key columns)
        key_columns = [col for col, mapping in column_analysis['potential_mappings'].items() 
                       if mapping in ['primary_endpoint', 'stratification_factor', 'analysis_dimension']]
        
        if key_columns:
            df_clean = df.dropna(subset=key_columns)
            removed_rows = len(df) - len(df_clean)
            
            if removed_rows > 0:
                analysis_results['data_cleaning'] = {
                    'original_rows': len(df),
                    'cleaned_rows': len(df_clean),
                    'removed_rows': removed_rows,
                    'removal_percentage': (removed_rows / len(df)) * 100,
                    'key_columns_used': key_columns,
                    'cleaning_note': f"Removed {removed_rows} rows ({(removed_rows/len(df)*100):.1f}%) with missing values in key analysis columns: {', '.join(key_columns)}"
                }
                analysis_results['processed_df'] = df_clean
                analysis_results['recommendations'].append(
                    f"⚠️ Data cleaning: {removed_rows} rows removed due to missing values in key columns"
                )
            else:
                analysis_results['data_cleaning'] = {
                    'original_rows': len(df),
                    'cleaned_rows': len(df),
                    'removed_rows': 0,
                    'cleaning_note': "No missing data found in key analysis columns"
                }
        
        # Missing data summary
        analysis_results['missing_data_summary'] = {
            'total_missing_values': int(total_missing),
            'missing_percentage': round(missing_percentage, 2),
            'columns_with_missing': [col for col, count in missing_data.items() if count > 0],
            'missing_by_column': {col: {'count': int(count), 'percentage': round((count/len(df))*100, 2)} 
                                 for col, count in missing_data.items() if count > 0}
        }
        
        # Data preprocessing suggestions  
        missing_data = df.isnull().sum()
        
        return analysis_results

    except Exception as e:
        # Return a basic structure if analysis fails
        return {
            'original_shape': df.shape if df is not None else (0, 0),
            'columns': list(df.columns) if df is not None else [],
            'column_analysis': {'column_patterns': {}, 'analysis_paths': [], 'potential_mappings': {}},
            'data_types': df.dtypes.to_dict() if df is not None else {},
            'missing_values': df.isnull().sum().to_dict() if df is not None else {},
            'recommendations': [f"⚠️ Analysis error: {str(e)}"],
            'mapped_columns': {},
            'processed_df': df.copy() if df is not None and not df.empty else pd.DataFrame(),
            'analysis_capabilities': {},
            'statistical_readiness': {},
            'error': str(e)
        }

def generate_visualization_recommendations(column_analysis, df):
    """Generate dynamic visualization recommendations based on detected column structure"""
    recommendations = []
    mappings = column_analysis['potential_mappings']
    
    # Primary endpoint visualizations
    primary_endpoints = [col for col, mapping in mappings.items() if mapping == 'primary_endpoint']
    stratification_factors = [col for col, mapping in mappings.items() if mapping == 'stratification_factor']
    
    if primary_endpoints:
        # Basic distribution plots
        for endpoint in primary_endpoints:
            recommendations.append({
                'type': 'histogram',
                'description': f'Distribution plot for {endpoint}',
                'columns': [endpoint],
                'priority': 'high'
            })
        
        # Comparative plots if grouping variables exist
        if stratification_factors:
            for endpoint in primary_endpoints:
                for factor in stratification_factors:
                    recommendations.append({
                        'type': 'boxplot',
                        'description': f'Group comparison: {endpoint} by {factor}',
                        'columns': [endpoint, factor],
                        'priority': 'high'
                    })
    
    # Time-series visualizations
    time_cols = [col for col, patterns in column_analysis['column_patterns'].items() if 'timepoint' in patterns]
    if time_cols and primary_endpoints:
        for time_col in time_cols:
            for endpoint in primary_endpoints:
                recommendations.append({
                    'type': 'line_plot',
                    'description': f'Time trend: {endpoint} over {time_col}',
                    'columns': [time_col, endpoint],
                    'priority': 'medium'
                })
    
    # Plate layout visualizations
    plate_cols = [col for col, patterns in column_analysis['column_patterns'].items() if 'plate_position' in patterns]
    if plate_cols and primary_endpoints:
        for plate_col in plate_cols:
            for endpoint in primary_endpoints:
                recommendations.append({
                    'type': 'heatmap',
                    'description': f'Plate heatmap: {endpoint} by {plate_col}',
                    'columns': [plate_col, endpoint],
                    'priority': 'medium'
                })
    
    # Correlation matrix for multiple numeric endpoints
    if len(primary_endpoints) > 1:
        recommendations.append({
            'type': 'correlation_matrix',
            'description': f'Correlation analysis across {len(primary_endpoints)} endpoints',
            'columns': primary_endpoints,
            'priority': 'medium'
        })
    
    return recommendations

def update_analysis_interface_from_columns(column_analysis):
    """Update the analysis interface based on dynamically detected columns"""
    interface_config = {
        'available_analyses': [],
        'column_selectors': {},
        'visualization_options': [],
        'statistical_tests': []
    }
    
    mappings = column_analysis['potential_mappings']
    
    # Configure analysis options based on detected column types
    primary_endpoints = [col for col, mapping in mappings.items() if mapping == 'primary_endpoint']
    stratification_factors = [col for col, mapping in mappings.items() if mapping == 'stratification_factor']
    grouping_variables = [col for col, mapping in mappings.items() if mapping == 'grouping_variable']
    analysis_dimensions = [col for col, mapping in mappings.items() if mapping == 'analysis_dimension']
    
    # Enable basic statistics for any numeric endpoints
    if primary_endpoints:
        interface_config['available_analyses'].append({
            'name': 'Descriptive Statistics',
            'type': 'descriptive',
            'columns': primary_endpoints,
            'description': f'Statistical summary for {len(primary_endpoints)} numeric variable(s)'
        })
        
        interface_config['column_selectors']['primary_endpoint'] = {
            'label': 'Select Primary Measurement',
            'options': primary_endpoints,
            'default': primary_endpoints[0] if primary_endpoints else None,
            'help': 'Choose the main numeric variable for analysis'
        }
    
    # Enable group comparisons if stratification factors exist
    if primary_endpoints and (stratification_factors or grouping_variables):
        grouping_cols = stratification_factors + grouping_variables
        interface_config['available_analyses'].append({
            'name': 'Group Comparison',
            'type': 'comparative',
            'columns': primary_endpoints + grouping_cols,
            'description': f'Compare {len(primary_endpoints)} measurement(s) across groups'
        })
        
        interface_config['column_selectors']['grouping_variable'] = {
            'label': 'Select Grouping Variable',
            'options': grouping_cols,
            'default': grouping_cols[0] if grouping_cols else None,
            'help': 'Choose variable to group data for comparison'
        }
    
    # Enable multi-dimensional analysis if analysis dimensions exist
    if analysis_dimensions and primary_endpoints:
        interface_config['available_analyses'].append({
            'name': 'Multi-Dimensional Analysis',
            'type': 'multidimensional',
            'columns': analysis_dimensions + primary_endpoints,
            'description': f'Analyze {len(primary_endpoints)} measurement(s) across {len(analysis_dimensions)} dimension(s)'
        })
        
        interface_config['column_selectors']['analysis_dimension'] = {
            'label': 'Select Analysis Dimension',
            'options': analysis_dimensions,
            'default': analysis_dimensions[0] if analysis_dimensions else None,
            'help': 'Choose dimension for multi-level analysis (e.g., biomarker, timepoint)'
        }
    
    return interface_config
    if missing_data.sum() > 0:
        analysis_results['recommendations'].append(f"⚠️ {missing_data.sum()} missing values detected - consider data cleaning")
    
    # Check for duplicate entries
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        analysis_results['recommendations'].append(f"🔄 {duplicate_count} duplicate rows found - review for data quality")
    
    # Suggest analysis types based on data structure
    if len(analysis_results['mapped_columns']) >= 3:
        analysis_results['recommendations'].append("📊 Data structure suitable for comprehensive ELISA analysis")
    
    if 'group' in analysis_results['mapped_columns'] and 'concentration' in analysis_results['mapped_columns']:
        analysis_results['recommendations'].append("🔬 Ready for group comparison analysis (t-tests, ANOVA)")
    
    if 'timepoint' in analysis_results['mapped_columns'] and len(analysis_results.get('unique_timepoints', [])) > 1:
        analysis_results['recommendations'].append("📈 Longitudinal analysis available (time-series, repeated measures)")
    
    # Auto-standardize column names for better processing
    processed_df = df.copy()
    for standard_name, original_col in analysis_results['mapped_columns'].items():
        if original_col in processed_df.columns:
            processed_df = processed_df.rename(columns={original_col: standard_name.title()})
    
    analysis_results['processed_df'] = processed_df
    
    return analysis_results

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

def find_column_by_patterns(df, patterns, legacy_names=None):
    """Find columns using both pattern matching and legacy names"""
    found_cols = []
    
    # First try pattern matching if available
    if hasattr(find_column_by_patterns, '_column_analysis'):
        column_analysis = find_column_by_patterns._column_analysis
        potential_mappings = column_analysis.get('potential_mappings', {})
        found_cols = [col for col, mapping in potential_mappings.items() if mapping in patterns]
    
    # If no pattern matches found, try legacy names
    if not found_cols and legacy_names:
        found_cols = [col for col in df.columns if col in legacy_names]
    
    return found_cols

def set_column_analysis_cache(column_analysis):
    """Cache column analysis for helper functions"""
    find_column_by_patterns._column_analysis = column_analysis

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
    """Validate ELISA data structure and suggest fixes using dynamic column detection"""
    issues = []
    suggestions = []
    
    # Use dynamic column analysis instead of hardcoded names
    try:
        column_analysis = read_column_ids_and_update_analysis(df, "Validation")
        
        # Check for analysis capabilities based on detected patterns
        potential_mappings = column_analysis.get('potential_mappings', {})
        
        # Look for primary endpoints (numeric measurement columns)
        primary_endpoints = [col for col, mapping in potential_mappings.items() if mapping == 'primary_endpoint']
        all_numeric = [col for col, info in column_analysis['column_types'].items() if info['is_numeric']]
        
        if not primary_endpoints:
            if all_numeric:
                # We have numeric columns but none classified as primary endpoints
                issues.append(f"Found {len(all_numeric)} numeric columns but none classified as measurement columns")
                suggestions.append(f"Numeric columns available: {', '.join(all_numeric[:5])}{'...' if len(all_numeric) > 5 else ''}")
                suggestions.append("These columns will be available for analysis even without specific naming patterns")
                # Promote all numeric columns to primary endpoints as fallback
                for col in all_numeric:
                    if col not in potential_mappings or potential_mappings[col] == 'continuous_variable':
                        column_analysis['potential_mappings'][col] = 'primary_endpoint'
                primary_endpoints = all_numeric
            else:
                issues.append("No numeric measurement columns detected")
                suggestions.append("Include columns with concentration, signal, or measurement values")
        
        if primary_endpoints:
            suggestions.append(f"Found {len(primary_endpoints)} measurement column(s) for analysis: {', '.join(primary_endpoints[:3])}{'...' if len(primary_endpoints) > 3 else ''}")
        
        # Look for grouping variables
        grouping_vars = [col for col, mapping in potential_mappings.items() 
                        if mapping in ['stratification_factor', 'grouping_variable']]
        if not grouping_vars:
            issues.append("No grouping/treatment columns detected")
            suggestions.append("Include columns for group assignments, treatments, or categories")
        else:
            suggestions.append(f"Found {len(grouping_vars)} grouping variable(s) for comparisons")
        
        # Look for subject identifiers
        subject_ids = [col for col, mapping in potential_mappings.items() if 'subject' in mapping or 'identifier' in mapping]
        if not subject_ids:
            suggestions.append("Consider adding subject/patient ID columns for longitudinal analysis")
        else:
            suggestions.append(f"Found {len(subject_ids)} subject identifier(s) for tracking")
            
        # Analysis path feedback
        analysis_paths = column_analysis.get('analysis_paths', [])
        if analysis_paths:
            high_confidence = [p for p in analysis_paths if p.get('confidence') == 'high']
            suggestions.append(f"Dashboard can perform {len(high_confidence)} high-confidence analysis types")
        
    except Exception as e:
        # Fallback to basic column check
        suggestions.append("Using basic data structure validation")
        if len(df.columns) == 0:
            issues.append("No columns found in dataset")
        elif len(df) == 0:
            issues.append("No data rows found in dataset")
        else:
            suggestions.append(f"Dataset has {len(df)} rows and {len(df.columns)} columns - ready for analysis")
    
    # Check data types
    if 'Concentration' in df.columns:
        # Find concentration column dynamically
        conc_cols = [col for col in df.columns if any(term in col.lower() for term in ['concentration', 'value', 'level', 'amount'])]
        conc_col = conc_cols[0] if conc_cols else None
        if conc_col and not pd.api.types.is_numeric_dtype(df[conc_col]):
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
        # Find subject ID column dynamically
        subject_cols = [col for col in df.columns if any(term in col.lower() for term in ['subject', 'patient', 'id', 'participant'])]
        if subject_cols:
            st.info(f"**Subjects**: {df[subject_cols[0]].nunique()}")
        # Find marker columns dynamically
        marker_cols = [col for col in df.columns if col in ['Marker', 'Biomarker', 'Analyte']]
        if marker_cols:
            st.info(f"**Biomarkers**: {', '.join(df[marker_cols[0]].unique()[:3])}")
    
    with col3:
        # Find group column dynamically
        group_cols_local = [col for col in df.columns if any(term in col.lower() for term in ['group', 'treatment', 'condition', 'arm', 'cohort'])]
        if group_cols_local:
            st.info(f"**Groups**: {', '.join(df[group_cols_local[0]].unique())}")
        # Find timepoint column dynamically
        time_cols = [col for col in df.columns if any(term in col.lower() for term in ['time', 'timepoint', 'visit', 'day', 'week'])]
        if time_cols:
            st.info(f"**Timepoints**: {', '.join(df[time_cols[0]].unique())}")
    
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
    
    # Initialize session state for data management and adaptive features
    if 'current_df' not in st.session_state:
        st.session_state.current_df = None
        st.session_state.data_source = None
        st.session_state.last_data_hash = None
        st.session_state.plate_mapping = {}
        st.session_state.plate_layout_detected = False
    
    # Initialize adaptive update settings
    if 'auto_refresh_enabled' not in st.session_state:
        st.session_state.auto_refresh_enabled = False
    if 'data_update_count' not in st.session_state:
        st.session_state.data_update_count = 0
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = datetime.now()
    if 'data_versions' not in st.session_state:
        st.session_state.data_versions = []
    if 'smart_suggestions' not in st.session_state:
        st.session_state.smart_suggestions = []
    
    # Smart data refresh if auto-refresh is enabled
    if st.session_state.auto_refresh_enabled:
        smart_data_refresh()
    
    # Check if we have data loaded
    if st.session_state.current_df is None:
        # Show prominent main page upload interface
        st.markdown("---")
        st.markdown("## 📤 **Upload Your ELISA Data**")
        st.markdown("*Get started by uploading your biomarker data or generate sample data for testing*")
        st.markdown("")
        
        # Create main upload section with better layout
        upload_col1, upload_col2 = st.columns([3, 2])
        
        with upload_col1:
            st.markdown("### 🗂️ File Upload")
            
            # Main page file uploader
            main_uploaded_file = st.file_uploader(
                "Choose your ELISA data file",
                type=['csv', 'xlsx', 'xls', 'txt', 'json', 'xml', 'db', 'sqlite'],
                help="Upload your ELISA data in any supported format. The dashboard will automatically detect column structure and configure analysis options.",
                key="main_upload"
            )
            
            if main_uploaded_file is not None:
                file_type = main_uploaded_file.name.split('.')[-1].lower()
                st.success(f"📋 File detected: **{main_uploaded_file.name}** ({file_type.upper()})")
                
                # Processing section
                with st.expander("🔍 **File Processing & Preview**", expanded=True):
                    try:
                        new_df, load_message = read_file_by_type(main_uploaded_file, file_type)
                        
                        if not new_df.empty:
                            st.info(f"✅ {load_message}")
                            st.metric("📊 Data Dimensions", f"{len(new_df)} rows × {len(new_df.columns)} columns")
                            
                            # Show data preview
                            st.markdown("**📋 Data Preview:**")
                            st.dataframe(new_df.head(5), width='stretch')
                            
                            # Dynamic column analysis with error handling
                            analysis_results = extract_and_analyze_data(new_df, main_uploaded_file.name)
                            
                            # Ensure analysis_results is valid
                            if analysis_results is None:
                                st.error("❌ Failed to analyze data structure. Please check your file format.")
                                st.stop()
                            
                            column_analysis = analysis_results.get('column_analysis', {})
                            if not column_analysis:
                                st.warning("⚠️ Column analysis incomplete. Using basic processing.")
                                column_analysis = {'column_patterns': {}, 'analysis_paths': [], 'potential_mappings': {}}
                            
                            # Show analysis insights
                            insight_col1, insight_col2 = st.columns(2)
                            
                            with insight_col1:
                                st.markdown("**🔍 Detected Column Patterns:**")
                                patterns_found = False
                                for col_id, patterns in column_analysis.get('column_patterns', {}).items():
                                    if patterns:
                                        pattern_str = ", ".join(patterns)
                                        st.write(f"• `{col_id}`: {pattern_str}")
                                        patterns_found = True
                                if not patterns_found:
                                    st.write("• No specific patterns detected")
                            
                            with insight_col2:
                                st.markdown("**🚀 Available Analysis Paths:**")
                                analysis_paths = column_analysis.get('analysis_paths', [])
                                if analysis_paths:
                                    for path in analysis_paths:
                                        confidence_icon = "🔥" if path.get('confidence') == 'high' else "⚡" if path.get('confidence') == 'medium' else "💡"
                                        st.write(f"{confidence_icon} {path.get('description', 'Analysis available')}")
                                else:
                                    st.write("• Basic statistical analysis available")
                            
                            # Load data button
                            if st.button("🚀 **Load Data & Start Analysis**", type="primary"):
                                # Process and load the data with error handling
                                processed_data = analysis_results.get('processed_df')
                                if processed_data is None or processed_data.empty:
                                    processed_data = new_df.copy()  # Use original data as fallback
                                    st.warning("⚠️ Using original data due to processing issues.")
                                
                                adaptive_config = adapt_dashboard_to_data(processed_data, analysis_results)
                                
                                # Update session state
                                st.session_state.current_df = processed_data
                                st.session_state.data_source = f"{main_uploaded_file.name} ({file_type.upper()})"
                                st.session_state.data_analysis = analysis_results
                                st.session_state.adaptive_config = adaptive_config
                                st.session_state.last_data_hash = hash(str(processed_data.values.tobytes()))
                                st.session_state.data_update_count = 1
                                st.session_state.last_update_time = datetime.now()
                                
                                # Version tracking
                                version_info = {
                                    'timestamp': datetime.now(),
                                    'source': f"{main_uploaded_file.name} ({file_type.upper()})",
                                    'rows': processed_data.shape[0],
                                    'columns': processed_data.shape[1],
                                    'hash': hashlib.md5(str(processed_data.values.tobytes()).encode()).hexdigest()
                                }
                                st.session_state.data_versions = [version_info]
                                
                                st.success("✅ Data loaded successfully! Dashboard configured automatically.")
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error processing file: {str(e)}")
                        st.info("💡 Try a different file format or check your data structure.")
        
        with upload_col2:
            st.markdown("### 📊 **Supported Formats**")
            st.markdown("""
            **📁 File Types:**
            - 📊 **Excel**: .xlsx, .xls (multi-sheet)
            - 📄 **CSV**: .csv (auto-detect delimiter)  
            - 📝 **Text**: .txt (tab/comma/semicolon)
            - 🔧 **JSON**: .json (nested structures)
            - 🗄️ **Database**: .db, .sqlite
            - 🌐 **XML**: .xml (auto-parse)
            
            **🧬 ELISA Data Features:**
            - ✅ Automatic column detection
            - ✅ Biomarker pattern recognition
            - ✅ Plate layout identification
            - ✅ Quality control metrics
            - ✅ Statistical analysis setup
            """)
            
            st.markdown("---")
            st.markdown("### 🧪 **Quick Start Options**")
            
            if st.button("📊 **Generate Sample Data**", type="secondary"):
                sample_df = generate_sample_elisa_data()
                analysis_results = extract_and_analyze_data(sample_df, "Sample ELISA Data")
                adaptive_config = adapt_dashboard_to_data(sample_df, analysis_results)
                
                st.session_state.current_df = sample_df
                st.session_state.data_source = "Generated Sample Data"
                st.session_state.data_analysis = analysis_results
                st.session_state.adaptive_config = adaptive_config
                st.session_state.last_data_hash = hash(str(sample_df.values.tobytes()))
                st.session_state.data_update_count = 1
                st.session_state.last_update_time = datetime.now()
                
                # Version tracking
                version_info = {
                    'timestamp': datetime.now(),
                    'source': "Generated Sample Data",
                    'rows': sample_df.shape[0],
                    'columns': sample_df.shape[1],
                    'hash': hashlib.md5(str(sample_df.values.tobytes()).encode()).hexdigest()
                }
                st.session_state.data_versions = [version_info]
                
                st.success("✅ Sample data generated! Exploring analysis capabilities...")
                st.rerun()
            
            st.info("💡 **Tip:** The dashboard automatically detects your data structure and configures analysis options accordingly!")
        
        st.stop()  # Don't show the rest of the interface until data is loaded
    
    # Data Management Section (when data is already loaded)
    else:
        st.markdown("---")
        st.markdown("### 📊 **Current Dataset**")
        
        # Data info row
        data_info_col1, data_info_col2, data_info_col3, data_info_col4 = st.columns(4)
        
        with data_info_col1:
            st.metric("📋 **Data Source**", st.session_state.data_source or "Unknown")
        with data_info_col2:
            st.metric("📊 **Records**", len(st.session_state.current_df))
        with data_info_col3:
            st.metric("📈 **Columns**", len(st.session_state.current_df.columns))
        with data_info_col4:
            if hasattr(st.session_state, 'last_update_time'):
                st.metric("🕒 **Last Updated**", st.session_state.last_update_time.strftime("%H:%M:%S"))
        
        # Data management options
        with st.expander("📤 **Upload New Data**", expanded=False):
            st.markdown("*Replace current data with a new dataset*")
            
            new_upload = st.file_uploader(
                "Choose new ELISA data file",
                type=['csv', 'xlsx', 'xls', 'txt', 'json', 'xml', 'db', 'sqlite'],
                help="Upload new data to replace current dataset",
                key="replace_upload"
            )
            
            if new_upload is not None:
                new_file_type = new_upload.name.split('.')[-1].lower()
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.info(f"📋 New file: **{new_upload.name}** ({new_file_type.upper()})")
                
                with col2:
                    if st.button("🔄 **Replace Data**", type="primary"):
                        try:
                            new_df, load_message = read_file_by_type(new_upload, new_file_type)
                            analysis_results = extract_and_analyze_data(new_df, new_upload.name)
                            adaptive_config = adapt_dashboard_to_data(new_df, analysis_results)
                            
                            # Update session state
                            st.session_state.current_df = new_df
                            st.session_state.data_source = f"{new_upload.name} ({new_file_type.upper()})"
                            st.session_state.data_analysis = analysis_results
                            st.session_state.adaptive_config = adaptive_config
                            st.session_state.last_data_hash = hash(str(new_df.values.tobytes()))
                            st.session_state.data_update_count += 1
                            st.session_state.last_update_time = datetime.now()
                            
                            st.success("✅ Data replaced successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error loading new data: {str(e)}")
        
        st.markdown("---")
    
    # Check for data changes and adapt if needed
    current_data_hash = hash(str(st.session_state.current_df.values.tobytes()))
    if hasattr(st.session_state, 'last_data_hash') and current_data_hash != st.session_state.last_data_hash:
        st.session_state.data_update_count += 1
        st.session_state.last_update_time = datetime.now()
        st.session_state.last_data_hash = current_data_hash
        
        # Re-analyze data and update adaptive configuration
        if st.session_state.current_df is not None and not st.session_state.current_df.empty:
            try:
                analysis_results = extract_and_analyze_data(st.session_state.current_df, st.session_state.data_source or "Unknown")
                st.session_state.adaptive_config = adapt_dashboard_to_data(st.session_state.current_df, analysis_results)
                st.session_state.data_analysis = analysis_results
            except Exception as e:
                st.error(f"Error analyzing data: {str(e)}")
                # Use basic configuration as fallback
                st.session_state.adaptive_config = adapt_dashboard_to_data(st.session_state.current_df, {})
    
    df = st.session_state.current_df
    
    # Adaptive dashboard header with update status
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.success(f"✅ Current Dataset: {st.session_state.data_source}")
    
    with col2:
        if st.session_state.data_update_count > 0:
            st.metric(
                "📊 Updates", 
                st.session_state.data_update_count,
                delta=f"Last: {st.session_state.last_update_time.strftime('%H:%M')}"
            )
        else:
            st.metric("📊 Updates", "0", delta="Initial load")
    
    with col3:
        # Auto-refresh toggle
        auto_refresh = st.checkbox(
            "🔄 Auto-adapt", 
            value=st.session_state.auto_refresh_enabled,
            help="Automatically detect and adapt to data changes"
        )
        st.session_state.auto_refresh_enabled = auto_refresh
    
    with col4:
        # Manual refresh button
        if st.button("🔄 Refresh", help="Manually refresh and re-analyze data"):
            # Force re-analysis of current data
            if df is not None and not df.empty:
                analysis_results = extract_and_analyze_data(df, st.session_state.data_source)
                st.session_state.adaptive_config = adapt_dashboard_to_data(df, analysis_results)
                st.session_state.data_analysis = analysis_results
                st.rerun()
    
    display_data_info(df)
    
    # Show recent data structure changes if any
    if hasattr(st.session_state, 'reconciliation_history') and st.session_state.reconciliation_history:
        latest_reconciliation = st.session_state.reconciliation_history[-1]
        if latest_reconciliation['changes_log'] or latest_reconciliation['warnings']:
            with st.expander("🔧 Recent Data Structure Changes", expanded=True):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if latest_reconciliation['changes_log']:
                        st.subheader("✅ Applied Changes")
                        for change in latest_reconciliation['changes_log']:
                            st.success(f"• {change}")
                
                with col2:
                    if latest_reconciliation['warnings']:
                        st.subheader("⚠️ Warnings")
                        for warning in latest_reconciliation['warnings']:
                            st.warning(f"• {warning}")
                
                shape_change = f"{latest_reconciliation['old_shape']} → {latest_reconciliation['new_shape']}"
                st.info(f"📊 Data shape changed: {shape_change}")
    
    # Display adaptive configuration if available
    if hasattr(st.session_state, 'adaptive_config') and st.session_state.adaptive_config:
        config = st.session_state.adaptive_config
        
        # Create expandable adaptive dashboard info
        with st.expander("🤖 Adaptive Dashboard Configuration", expanded=False):
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                st.subheader("🎯 Analysis Type")
                st.info(config['data_insights']['primary_analysis_type'])
                st.metric("Complexity Level", config['data_insights']['complexity_level'])
                
            with col2:
                st.subheader("💡 Data Readiness")
                readiness = config['data_insights']['data_readiness']
                st.metric("Readiness Score", f"{readiness['score']}/100")
                st.info(f"Status: {readiness['status']}")
                
            with col3:
                st.subheader("📈 Available Analyses")
                if config['recommended_analyses']:
                    for analysis in config['recommended_analyses']:
                        st.write(f"• {analysis}")
                else:
                    st.write("• Basic statistical analysis")
            
            # Show recommended workflow based on column mapping
            if config.get('analysis_workflow'):
                st.subheader("🗺️ Recommended Analysis Workflow")
                for workflow_step in config['analysis_workflow']:
                    priority_emoji = "🔥" if workflow_step['priority'] == 'high' else "⚡" if workflow_step['priority'] == 'medium' else "💡"
                    st.write(f"{priority_emoji} **Step {workflow_step['step']}**: {workflow_step['title']}")
                    st.write(f"   📍 {workflow_step['description']} → Go to *{workflow_step['tab']}* tab")
            
            # Show column mapping insights
            if hasattr(st.session_state, 'column_mappings') and st.session_state.column_mappings:
                st.subheader("🎯 Active Column Mappings")
                mapping_col1, mapping_col2 = st.columns(2)
                mappings = list(st.session_state.column_mappings.items())
                mid_point = len(mappings) // 2
                
                with mapping_col1:
                    for standard, actual in mappings[:mid_point]:
                        st.write(f"• **{standard.replace('_', ' ').title()}**: `{actual}`")
                
                with mapping_col2:
                    for standard, actual in mappings[mid_point:]:
                        st.write(f"• **{standard.replace('_', ' ').title()}**: `{actual}`")
            
            # Show statistical readiness for each analysis type
            if hasattr(st.session_state, 'data_analysis') and st.session_state.data_analysis and 'statistical_readiness' in st.session_state.data_analysis:
                stat_readiness = st.session_state.data_analysis['statistical_readiness']
                st.subheader("📊 Analysis Readiness Status")
                
                ready_analyses = [name for name, status in stat_readiness.items() if status.get('ready', False)]
                not_ready = [name for name, status in stat_readiness.items() if not status.get('ready', False)]
                
                if ready_analyses:
                    st.success(f"✅ Ready: {', '.join(ready_analyses).replace('_', ' ').title()}")
                
                if not_ready:
                    st.info(f"🔧 Needs preparation: {', '.join(not_ready).replace('_', ' ').title()}")
            
            # Show data readiness issues if any
            if readiness['issues']:
                st.subheader("⚠️ Data Quality Notes")
                for issue in readiness['issues']:
                    st.warning(f"• {issue}")
    
    # Sidebar filters
    st.sidebar.header("🎛️ Analysis Controls")
    
    # Adaptive filtering based on data structure
    df_filtered = df.copy()
    
    # Use adaptive configuration with column mapping insights
    if hasattr(st.session_state, 'adaptive_config') and st.session_state.adaptive_config:
        config = st.session_state.adaptive_config
        filter_suggestions = config.get('filter_suggestions', [])
        
        # Group filters by priority
        high_priority = [f for f in filter_suggestions if f.get('priority') == 'high']
        medium_priority = [f for f in filter_suggestions if f.get('priority') == 'medium']
        low_priority = [f for f in filter_suggestions if f.get('priority') == 'low']
        
        # Apply high priority filters first (always visible)
        for filter_config in high_priority:
            col_name = filter_config['column']
            mapped_as = filter_config.get('mapped_as', col_name)
            
            if col_name in df_filtered.columns:
                if filter_config['type'] == 'multiselect':
                    display_name = f"🎯 {mapped_as.replace('_', ' ').title()}" if mapped_as != 'unmapped' else f"📊 {col_name}"
                    selected_values = st.sidebar.multiselect(
                        display_name,
                        options=filter_config['values'],
                        default=filter_config['values'],
                        help=filter_config['reason']
                    )
                    df_filtered = df_filtered[df_filtered[col_name].isin(selected_values)]
                
                elif filter_config['type'] == 'range':
                    display_name = f"📏 {mapped_as.replace('_', ' ').title()} Range"
                    min_val, max_val = st.sidebar.slider(
                        display_name,
                        min_value=filter_config['min_value'],
                        max_value=filter_config['max_value'],
                        value=(filter_config['min_value'], filter_config['max_value']),
                        help=filter_config['reason']
                    )
                    df_filtered = df_filtered[(df_filtered[col_name] >= min_val) & (df_filtered[col_name] <= max_val)]
        
        # Medium priority filters in expander
        if medium_priority:
            with st.sidebar.expander("📊 Additional Filters", expanded=False):
                for filter_config in medium_priority:
                    col_name = filter_config['column']
                    mapped_as = filter_config.get('mapped_as', col_name)
                    
                    if col_name in df_filtered.columns:
                        if filter_config['type'] == 'multiselect':
                            display_name = f"🔍 {mapped_as.replace('_', ' ').title()}" if mapped_as != 'unmapped' else f"📋 {col_name}"
                            selected_values = st.multiselect(
                                display_name,
                                options=filter_config['values'],
                                default=filter_config['values'],
                                help=filter_config['reason']
                            )
                            df_filtered = df_filtered[df_filtered[col_name].isin(selected_values)]
                        
                        elif filter_config['type'] == 'range':
                            display_name = f"📏 {mapped_as.replace('_', ' ').title()}"
                            min_val, max_val = st.slider(
                                display_name,
                                min_value=filter_config['min_value'],
                                max_value=filter_config['max_value'],
                                value=(filter_config['min_value'], filter_config['max_value']),
                                help=filter_config['reason']
                            )
                            df_filtered = df_filtered[(df_filtered[col_name] >= min_val) & (df_filtered[col_name] <= max_val)]
        
        # Low priority filters in collapsed expander
        if low_priority:
            with st.sidebar.expander("🔧 Advanced Filters", expanded=False):
                for filter_config in low_priority:
                    col_name = filter_config['column']
                    if col_name in df_filtered.columns and filter_config['type'] == 'multiselect':
                        selected_values = st.multiselect(
                            f"🔍 {col_name}",
                            options=filter_config['values'],
                            default=filter_config['values'],
                            help=filter_config['reason']
                        )
                        df_filtered = df_filtered[df_filtered[col_name].isin(selected_values)]
    
    # Fallback to standard ELISA filters
    else:
        # Group filter
        group_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['group', 'treatment', 'condition', 'arm'])]
        if group_cols:
            group_col = group_cols[0]
            selected_groups = st.sidebar.multiselect(
                f"👥 Select {group_col}",
                options=df[group_col].unique(),
                default=df[group_col].unique()
            )
            df_filtered = df_filtered[df_filtered[group_col].isin(selected_groups)]
        
        # Biomarker filter
        marker_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['marker', 'biomarker', 'protein', 'analyte'])]
        if marker_cols:
            marker_col = marker_cols[0]
            selected_markers = st.sidebar.multiselect(
                f"🧬 Select {marker_col}",
                options=df[marker_col].unique(), 
                default=df[marker_col].unique()
            )
            df_filtered = df_filtered[df_filtered[marker_col].isin(selected_markers)]
    
    st.sidebar.info(f"📊 Filtered data: {len(df_filtered)} measurements")
    
    # Data monitoring and management section
    st.sidebar.markdown("---")
    st.sidebar.header("📂 Data Management")
    
    # Real-time data monitoring
    with st.sidebar.expander("📡 Data Monitoring", expanded=False):
        st.write(f"📊 Current rows: **{len(df_filtered):,}**")
        st.write(f"📈 Total updates: **{st.session_state.data_update_count}**")
        if hasattr(st.session_state, 'last_update_time'):
            time_since = datetime.now() - st.session_state.last_update_time
            st.write(f"⏱️ Last update: **{time_since.seconds//60}m {time_since.seconds%60}s ago**")
        
        # Data quality indicators
        missing_data = df_filtered.isnull().sum().sum()
        if missing_data > 0:
            st.warning(f"⚠️ {missing_data} missing values detected")
        else:
            st.success("✅ No missing values")
        
        # Auto-refresh settings
        if st.session_state.auto_refresh_enabled:
            refresh_interval = st.slider(
                "🔄 Auto-refresh interval (seconds)", 
                min_value=5, max_value=300, value=30
            )
            if st.button("⏸️ Pause Auto-refresh"):
                st.session_state.auto_refresh_enabled = False
                st.rerun()
        
        # File monitoring for supported data sources
        if st.session_state.data_source.endswith('.csv'):
            base_file = st.session_state.data_source.split(' ')[0]
            if os.path.exists(base_file):
                file_changed, file_time = check_file_changes(base_file)
                if file_changed:
                    st.success("🔄 File updated detected!")
                    if st.button("📥 Load Updated Data"):
                        if auto_update_data_from_file(base_file):
                            st.success("✅ Data updated successfully!")
                            st.rerun()
                
                if file_time:
                    st.write(f"📅 File modified: {file_time.strftime('%H:%M:%S')}")
            else:
                st.warning("⚠️ Source file not found")
        
        # Data version history
        if len(st.session_state.data_versions) > 0:
            st.write("📚 Data Versions:")
            for i, version in enumerate(st.session_state.data_versions[-3:]):  # Show last 3
                st.write(f"• v{i+1}: {version['timestamp'].strftime('%H:%M')} ({version['rows']} rows)")
    
    # Data Structure Management
    with st.sidebar.expander("🔧 Data Structure Management", expanded=False):
        if hasattr(st.session_state, 'column_mappings') and st.session_state.column_mappings:
            st.write("📊 **Current Column Mappings:**")
            for standard, actual in st.session_state.column_mappings.items():
                st.write(f"• {standard}: `{actual}`")
        
        # Show reconciliation history
        if hasattr(st.session_state, 'reconciliation_history') and st.session_state.reconciliation_history:
            st.write("🔄 **Recent Structure Changes:**")
            latest = st.session_state.reconciliation_history[-1]
            if latest['changes_log']:
                for change in latest['changes_log'][-3:]:  # Show last 3
                    st.info(f"📝 {change}")
            if latest['warnings']:
                for warning in latest['warnings'][-2:]:  # Show last 2
                    st.warning(f"⚠️ {warning}")
        
        # Manual column mapping override
        st.write("🎯 **Manual Column Mapping:**")
        if st.button("🔄 Re-map Columns"):
            if hasattr(st.session_state, 'current_df') and st.session_state.current_df is not None:
                new_mappings, suggestions = intelligent_column_mapping(st.session_state.current_df)
                st.session_state.column_mappings = new_mappings
                for suggestion in suggestions:
                    st.success(f"✅ {suggestion}")
                st.rerun()
        
        # Data structure repair options
        if st.button("🛠️ Repair Data Structure"):
            if hasattr(st.session_state, 'current_df'):
                df = st.session_state.current_df
                optional_cols = ['subject_id', 'group', 'biomarker', 'concentration']
                mappings = getattr(st.session_state, 'column_mappings', {})
                
                repaired_df, handled_cols, repair_suggestions = handle_missing_columns(
                    df.copy(), optional_cols, mappings
                )
                
                if handled_cols:
                    st.session_state.current_df = repaired_df
                    st.session_state.data_update_count += 1
                    st.session_state.last_update_time = datetime.now()
                    
                    for suggestion in repair_suggestions:
                        st.success(f"🔧 {suggestion}")
                    st.rerun()
                else:
                    st.info("✅ No repairs needed - data structure is complete")
    
    # Plate Layout Information
    if hasattr(st.session_state, 'plate_layout_detected') and st.session_state.plate_layout_detected:
        with st.sidebar.expander("🧪 Plate Layout Information", expanded=False):
            plate_info = st.session_state.plate_mapping
            
            if plate_info.get('plate_format'):
                st.write(f"🎯 **Format**: {plate_info['plate_format']}")
                
            if plate_info.get('plate_dimensions'):
                rows, cols = plate_info['plate_dimensions']
                st.write(f"📏 **Dimensions**: {rows} rows × {cols} columns")
                
            if plate_info.get('replicates'):
                st.write(f"🔄 **Replicates**: {len(plate_info['replicates'])} samples")
                
            if plate_info.get('controls'):
                st.write(f"🎯 **Controls**: {len(plate_info['controls'])} wells")
                
            if plate_info.get('samples'):
                st.write(f"🧬 **Samples**: {len(plate_info['samples'])} wells")
                
            total_wells = len(plate_info.get('well_mapping', {}))
            if total_wells > 0:
                st.write(f"📊 **Total Wells**: {total_wells}")
                
                # Well utilization
                if plate_info.get('plate_dimensions'):
                    max_wells = plate_info['plate_dimensions'][0] * plate_info['plate_dimensions'][1]
                    utilization = (total_wells / max_wells) * 100
                    st.write(f"📈 **Utilization**: {utilization:.1f}%")
            
            # Plate effects analysis button
            if total_wells > 20:
                if st.button("🗺️ Analyze Plate Effects"):
                    st.info("🔬 Plate effects analysis would be implemented here")
                    # This would analyze edge effects, systematic patterns, etc.
    
    # Smart suggestions panel
    if len(st.session_state.smart_suggestions) > 0:
        with st.sidebar.expander("💡 Smart Suggestions", expanded=True):
            for suggestion in st.session_state.smart_suggestions[-5:]:  # Show last 5
                if suggestion['type'] == 'data_change':
                    st.info(f"🔍 {suggestion['message']}")
                elif suggestion['type'] == 'analysis':
                    st.success(f"📊 {suggestion['message']}")
                elif suggestion['type'] == 'warning':
                    st.warning(f"⚠️ {suggestion['message']}")
    
    # Option to load different datasets
    # Show current data source info
    if st.session_state.data_source:
        st.sidebar.success(f"📊 Current: {st.session_state.data_source}")
    
    data_option = st.sidebar.selectbox(
        "🔄 Data Management",
        options=[
            "Keep Current Data",
            "Upload New File (Multi-format)",
            "Replace with Sample Data",
            "Clear All Data"
        ],
        index=0
    )
    
    # Handle different data management options
    if data_option == "Clear All Data":
        if st.sidebar.button("🗑️ Clear All Data", type="secondary"):
            # Clear all session state data
            keys_to_clear = ['current_df', 'data_source', 'last_data_hash', 'column_mappings', 'plate_mapping', 'plate_layout_detected', 'data_versions', 'reconciliation_history', 'smart_suggestions']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("🧽 All data cleared! Please refresh the page.")
            st.rerun()
    
    elif data_option == "Replace with Sample Data":
        if st.sidebar.button("🎆 Generate New Sample Data"):
            st.session_state.current_df = generate_sample_elisa_data()
            st.session_state.data_source = "Generated Sample Data"
            st.session_state.last_data_hash = hash(str(st.session_state.current_df.values.tobytes()))
            st.session_state.data_update_count += 1
            st.session_state.last_update_time = datetime.now()
            st.sidebar.success("✅ New sample data generated!")
            st.rerun()
    
    elif data_option == "Upload New File (Multi-format)":
            st.sidebar.markdown("**📁 Supported File Types:**")
            st.sidebar.markdown("""
            - 📊 **Excel**: .xlsx, .xls
            - 📄 **CSV**: .csv (auto-detect delimiter)
            - 📝 **Text**: .txt (tab/comma/semicolon separated)
            - 🔧 **JSON**: .json (nested structures supported)
            - 🗄️ **Database**: .db, .sqlite
            - 🌐 **XML**: .xml (auto-parse structure)
            """)
            
            uploaded_file = st.sidebar.file_uploader(
                "📤 Upload ELISA Data File",
                type=['csv', 'xlsx', 'xls', 'txt', 'json', 'xml', 'db', 'sqlite'],
                help="Upload your ELISA data in any supported format. The system will auto-detect and parse the file structure."
            )
            
            if uploaded_file is not None:
                file_type = uploaded_file.name.split('.')[-1].lower()
                st.sidebar.info(f"📋 File type detected: {file_type.upper()}")
                
                # Show file preview option
                if st.sidebar.checkbox("👁️ Preview file before loading", value=True):
                    try:
                        new_df, load_message = read_file_by_type(uploaded_file, file_type)
                        
                        if not new_df.empty:
                            st.sidebar.success(f"✅ {load_message}")
                            st.sidebar.info(f"📊 Preview: {len(new_df)} rows × {len(new_df.columns)} columns")
                            
                            # Show data preview
                            with st.sidebar.expander("🔍 Data Preview", expanded=False):
                                st.dataframe(new_df.head(3), width='stretch')
                                
                            # Dynamic column reading and intelligent analysis
                            analysis_results = extract_and_analyze_data(new_df, uploaded_file.name)
                            column_analysis = analysis_results['column_analysis']
                            
                            # Show dynamic column analysis with detected patterns
                            with st.sidebar.expander("📋 Dynamic Column Analysis", expanded=True):
                                st.write("**📊 Data Overview:**")
                                st.write(f"• Rows: {analysis_results['original_shape'][0]}")
                                st.write(f"• Columns: {analysis_results['original_shape'][1]}")
                                
                                st.write("**🔍 Detected Column Patterns:**")
                                for col_id, patterns in column_analysis['column_patterns'].items():
                                    if patterns:
                                        pattern_str = ", ".join(patterns)
                                        st.write(f"• `{col_id}`: {pattern_str}")
                                
                                st.write("**🎯 Potential Analysis Mappings:**")
                                for col_id, mapping in column_analysis['potential_mappings'].items():
                                    mapping_display = mapping.replace('_', ' ').title()
                                    st.write(f"• `{col_id}`: {mapping_display}")
                                
                                st.write("**🔥 Available Analysis Paths:**")
                                for path in column_analysis['analysis_paths']:
                                    confidence_icon = "🔥" if path['confidence'] == 'high' else "⚡" if path['confidence'] == 'medium' else "💡"
                                    st.write(f"{confidence_icon} {path['description']}")
                                
                                st.write("**💡 Dynamic Recommendations:**")
                                for rec in analysis_results['recommendations']:
                                    st.write(f"• {rec}")
                            
                            # Option to replace or append data
                            data_action = st.sidebar.radio(
                                "📊 Data Action",
                                ["Replace current data", "Append to current data"]
                            )
                            
                            if st.sidebar.button("🔄 Apply New Data"):
                                # Use processed data from intelligent extraction
                                processed_data = analysis_results['processed_df']
                                
                                if data_action == "Replace current data":
                                    # Generate adaptive configuration
                                    adaptive_config = adapt_dashboard_to_data(processed_data, analysis_results)
                                    
                                    # Update session state with change tracking and versioning
                                    old_shape = st.session_state.current_df.shape if hasattr(st.session_state, 'current_df') else (0, 0)
                                    
                                    # Save version history
                                    version_info = {
                                        'timestamp': datetime.now(),
                                        'source': f"{uploaded_file.name} ({file_type.upper()})",
                                        'rows': processed_data.shape[0],
                                        'columns': processed_data.shape[1],
                                        'hash': hashlib.md5(str(processed_data.values.tobytes()).encode()).hexdigest()
                                    }
                                    st.session_state.data_versions.append(version_info)
                                    
                                    # Detect plate layout and mapping
                                    plate_info = detect_plate_layout(processed_data)
                                    plate_adaptations = adapt_to_plate_layout(processed_data, plate_info)
                                    
                                    # Store plate mapping information
                                    st.session_state.plate_mapping = plate_info
                                    st.session_state.plate_layout_detected = plate_info['layout_detected']
                                    
                                    # Intelligent column mapping and structure adaptation
                                    column_mappings, mapping_suggestions = intelligent_column_mapping(
                                        processed_data, getattr(st.session_state, 'column_mappings', {})
                                    )
                                    
                                    # Handle optional standard columns (create defaults only if analysis would benefit)
                                    optional_columns = ['subject_id', 'group', 'biomarker', 'concentration']
                                    enhanced_df, handled_columns, handle_suggestions = handle_missing_columns(
                                        processed_data.copy(), optional_columns, column_mappings
                                    )
                                    
                                    # Show plate mapping results if detected
                                    if plate_info['layout_detected']:
                                        st.sidebar.success(f"🧪 Plate layout detected: {plate_info['plate_format']}")
                                        for rec in plate_adaptations['recommendations']:
                                            st.sidebar.info(f"🔬 {rec}")
                                    
                                    # Update current state with enhanced data
                                    st.session_state.current_df = enhanced_df
                                    st.session_state.data_source = f"{uploaded_file.name} ({file_type.upper()})"
                                    st.session_state.data_analysis = analysis_results
                                    st.session_state.adaptive_config = adaptive_config
                                    st.session_state.column_mappings = column_mappings
                                    st.session_state.last_data_hash = hash(str(enhanced_df.values.tobytes()))
                                    st.session_state.data_hash = version_info['hash']
                                    st.session_state.data_update_count += 1
                                    st.session_state.last_update_time = datetime.now()
                                    
                                    # Show mapping and handling results
                                    if mapping_suggestions:
                                        for suggestion in mapping_suggestions:
                                            st.sidebar.info(f"🎯 {suggestion}")
                                    
                                    if handled_columns:
                                        for suggestion in handle_suggestions:
                                            st.sidebar.success(f"🔧 {suggestion}")
                                    
                                    # Add smart suggestions
                                    if old_shape != processed_data.shape:
                                        suggestion = {
                                            'type': 'data_change',
                                            'message': f"Data structure changed: {old_shape} → {processed_data.shape}",
                                            'timestamp': datetime.now()
                                        }
                                        st.session_state.smart_suggestions.append(suggestion)
                                    
                                    # Suggest analyses based on new data
                                    if adaptive_config['recommended_analyses']:
                                        for analysis in adaptive_config['recommended_analyses'][:2]:  # Top 2
                                            suggestion = {
                                                'type': 'analysis',
                                                'message': f"Try {analysis} with new data",
                                                'timestamp': datetime.now()
                                            }
                                            st.session_state.smart_suggestions.append(suggestion)
                                    
                                    # Show change summary
                                    new_shape = processed_data.shape
                                    st.sidebar.success("✅ Data extracted and dashboard adapted!")
                                    st.sidebar.info(f"📊 Changed: {old_shape} → {new_shape}")
                                    
                                    # Show adaptive configuration summary
                                    if analysis_results['mapped_columns']:
                                        st.sidebar.info(f"🎯 Mapped {len(analysis_results['mapped_columns'])} ELISA columns")
                                    if adaptive_config['recommended_analyses']:
                                        st.sidebar.info(f"📊 {len(adaptive_config['recommended_analyses'])} analysis types configured")
                                    if adaptive_config['data_insights']['data_readiness']['status']:
                                        readiness = adaptive_config['data_insights']['data_readiness']['status']
                                        st.sidebar.info(f"💡 Data readiness: {readiness}")
                                else:
                                    # Append data with intelligent column matching
                                    try:
                                        # Try to align columns for better compatibility
                                        current_cols = set(st.session_state.current_df.columns)
                                        new_cols = set(processed_data.columns)
                                        common_cols = current_cols.intersection(new_cols)
                                        
                                        if len(common_cols) > 0:
                                            # Use common columns for appending
                                            current_subset = st.session_state.current_df[list(common_cols)]
                                            new_subset = processed_data[list(common_cols)]
                                            combined_df = pd.concat([current_subset, new_subset], ignore_index=True)
                                            
                                            # Add any unique columns from new data
                                            unique_new_cols = new_cols - current_cols
                                            if unique_new_cols:
                                                for col in unique_new_cols:
                                                    combined_df[col] = pd.concat([
                                                        pd.Series([np.nan] * len(current_subset)),
                                                        processed_data[col]
                                                    ], ignore_index=True)
                                        else:
                                            # If no common columns, just concatenate all
                                            combined_df = pd.concat([st.session_state.current_df, processed_data], ignore_index=True, sort=False)
                                        
                                        st.session_state.current_df = combined_df
                                        st.session_state.data_source = f"{st.session_state.data_source} + {uploaded_file.name}"
                                        st.sidebar.success(f"✅ Data extracted and appended! Total: {len(combined_df)} rows")
                                        st.sidebar.info(f"🔗 Merged {len(common_cols)} common columns")
                                        
                                    except Exception as append_error:
                                        st.sidebar.error(f"❌ Error appending data: {append_error}")
                                        st.sidebar.info("💡 Try 'Replace current data' instead")
                                        return
                                st.rerun()
                        else:
                            st.sidebar.error(f"❌ {load_message}")
                            
                    except Exception as e:
                        st.sidebar.error(f"❌ Error reading {file_type.upper()} file: {e}")
                        st.sidebar.info("💡 Try a different file format or check file structure")
                
                else:
                    # Direct load without preview
                    if st.sidebar.button("🚀 Load File Directly"):
                        try:
                            new_df, load_message = read_file_by_type(uploaded_file, file_type)
                            if not new_df.empty:
                                # Perform intelligent data extraction
                                analysis_results = extract_and_analyze_data(new_df, uploaded_file.name)
                                processed_data = analysis_results['processed_df']
                                
                                # Generate adaptive configuration for direct loading
                                adaptive_config = adapt_dashboard_to_data(processed_data, analysis_results)
                                
                                st.session_state.current_df = processed_data
                                st.session_state.data_source = f"{uploaded_file.name} ({file_type.upper()})"
                                st.session_state.data_analysis = analysis_results  # Store analysis results
                                st.session_state.adaptive_config = adaptive_config  # Store adaptive settings
                                
                                st.sidebar.success(f"✅ {load_message}")
                                st.sidebar.success(f"📊 Loaded: {len(processed_data)} rows × {len(processed_data.columns)} columns")
                                st.sidebar.info(f"🤖 Dashboard automatically adapted to your data!")
                                
                                if analysis_results['mapped_columns']:
                                    st.sidebar.info(f"🎯 Auto-mapped {len(analysis_results['mapped_columns'])} ELISA columns")
                                if adaptive_config['recommended_analyses']:
                                    st.sidebar.info(f"📊 {len(adaptive_config['recommended_analyses'])} analysis types ready")
                                
                                st.rerun()
                            else:
                                st.sidebar.error(f"❌ {load_message}")
                        except Exception as e:
                            st.sidebar.error(f"❌ Error loading file: {e}")
    
    elif data_option == "Load Different Existing File":
            # List available data files in the directory
            supported_extensions = ['.csv', '.xlsx', '.xls', '.txt', '.json', '.xml', '.db', '.sqlite']
            data_files = []
            
            for ext in supported_extensions:
                data_files.extend([f for f in os.listdir('.') if f.lower().endswith(ext)])
            
            if data_files:
                selected_file = st.sidebar.selectbox(
                    "📁 Select Data File",
                    options=sorted(data_files)
                )
                
                # Show file type info
                file_ext = selected_file.split('.')[-1].lower()
                st.sidebar.info(f"📋 File type: {file_ext.upper()}")
                
                if st.sidebar.button("📂 Load Selected File"):
                    try:
                        if file_ext == 'csv':
                            loaded_df = pd.read_csv(selected_file)
                            load_message = f"CSV file loaded: {len(loaded_df)} rows"
                        else:
                            # Use the file reading function for other types
                            with open(selected_file, 'rb') as f:
                                loaded_df, load_message = read_file_by_type(f, file_ext)
                        
                        if not loaded_df.empty:
                            st.session_state.current_df = loaded_df
                            st.session_state.data_source = f"{selected_file} ({file_ext.upper()})"
                            st.sidebar.success(f"✅ {load_message}")
                            st.rerun()
                        else:
                            st.sidebar.error(f"❌ Could not load {selected_file}")
                    except Exception as e:
                        st.sidebar.error(f"❌ Error loading {selected_file}: {e}")
            else:
                st.sidebar.info("📝 No supported data files found in current directory")
                st.sidebar.markdown("**Supported formats:** CSV, Excel, TXT, JSON, XML, Database")
    
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
    st.sidebar.markdown("**📤 Multi-Format Export:**")
    
    # Adaptive export format selection
    export_options = ["CSV", "Excel (.xlsx)", "JSON", "XML", "Tab-separated (.txt)"]
    
    # Add intelligent format suggestions based on adaptive config
    if hasattr(st.session_state, 'adaptive_config') and st.session_state.adaptive_config:
        config = st.session_state.adaptive_config
        suggested_formats = config.get('export_formats', [])
        if suggested_formats:
            # Prioritize suggested formats
            export_options = suggested_formats + [fmt for fmt in export_options if fmt not in suggested_formats]
    
    export_format = st.sidebar.selectbox(
        "📁 Choose Export Format",
        options=export_options,
        help="Formats are ordered by relevance to your data type"
    )
    
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    
    if st.sidebar.button("💾 Export Data"):
        try:
            if export_format == "CSV":
                csv_data = df_filtered.to_csv(index=False)
                st.sidebar.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"elisa_data_{timestamp}.csv",
                    mime="text/csv"
                )
                
            elif export_format == "Excel (.xlsx)":
                output = BytesIO()
                try:
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_filtered.to_excel(writer, sheet_name='ELISA_Data', index=False)
                        
                        # Add metadata sheet
                        metadata = pd.DataFrame({
                            'Export_Info': ['Timestamp', 'Source', 'Rows', 'Columns', 'Groups', 'Markers'],
                            'Values': [
                                timestamp,
                                st.session_state.data_source,
                                len(df_filtered),
                                len(df_filtered.columns),
                                ', '.join(df_filtered[group_cols[0]].unique()) if group_cols and group_cols[0] in df_filtered.columns else 'N/A',
                                ', '.join(df_filtered[dimension_cols[0]].unique()) if dimension_cols and dimension_cols[0] in df_filtered.columns else 'N/A'
                            ]
                        })
                        metadata.to_excel(writer, sheet_name='Export_Info', index=False)
                    
                    excel_data = output.getvalue()
                    st.sidebar.download_button(
                        label="⬇️ Download Excel",
                        data=excel_data,
                        file_name=f"elisa_data_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.sidebar.error(f"Excel export error: {e}")
                    # Fallback to CSV
                    csv_data = df_filtered.to_csv(index=False)
                    st.sidebar.download_button(
                        label="⬇️ Download CSV (fallback)",
                        data=csv_data,
                        file_name=f"elisa_data_{timestamp}.csv",
                        mime="text/csv"
                    )
                    
            elif export_format == "JSON":
                json_data = df_filtered.to_json(orient='records', indent=2)
                st.sidebar.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name=f"elisa_data_{timestamp}.json",
                    mime="application/json"
                )
                
            elif export_format == "XML":
                # Convert DataFrame to XML
                xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n<ELISA_Data>\n'
                for idx, row in df_filtered.iterrows():
                    xml_data += '  <Record>\n'
                    for col in df_filtered.columns:
                        value = str(row[col]) if pd.notna(row[col]) else ''
                        xml_data += f'    <{col}>{value}</{col}>\n'
                    xml_data += '  </Record>\n'
                xml_data += '</ELISA_Data>'
                
                st.sidebar.download_button(
                    label="⬇️ Download XML",
                    data=xml_data,
                    file_name=f"elisa_data_{timestamp}.xml",
                    mime="application/xml"
                )
                
            elif export_format == "Tab-separated (.txt)":
                txt_data = df_filtered.to_csv(sep='\t', index=False)
                st.sidebar.download_button(
                    label="⬇️ Download TXT",
                    data=txt_data,
                    file_name=f"elisa_data_{timestamp}.txt",
                    mime="text/plain"
                )
                
        except Exception as e:
            st.sidebar.error(f"❌ Export error: {e}")
    
    # Quick export shortcuts
    st.sidebar.markdown("**⚡ Quick Export:**")
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📄 CSV",
            data=csv_data,
            file_name=f"elisa_{timestamp}.csv",
            mime="text/csv",
            help="Quick CSV download"
        )
    
    with col2:
        json_data = df_filtered.to_json(orient='records', indent=2)
        st.download_button(
            label="🔧 JSON",
            data=json_data,
            file_name=f"elisa_{timestamp}.json",
            mime="application/json",
            help="Quick JSON download"
        )
    
    with col3:
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, sheet_name='Data', index=False)
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Excel",
                data=excel_data,
                file_name=f"elisa_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Quick Excel download"
            )
        except:
            st.markdown("📊 Excel")  # Disabled if not available
    
    # Initialize column detection variables for sidebar use
    group_cols = smart_detect_columns(df_filtered, 'group') if 'df_filtered' in locals() and df_filtered is not None else []
    dimension_cols = smart_detect_columns(df_filtered, 'biomarker') if 'df_filtered' in locals() and df_filtered is not None else []
    primary_endpoints = smart_detect_columns(df_filtered, 'concentration') if 'df_filtered' in locals() and df_filtered is not None else []
    
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
            # Use dynamic group column detection
            group_col = group_cols[0] if group_cols else 'Group'
            if group_col in df_filtered.columns:
                for group in df_filtered[group_col].unique():
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
    group_col = group_cols[0] if group_cols else 'Group'
    if group_col in df_filtered.columns:
            st.sidebar.markdown("**🎨 Color Preview:**")
            groups = df_filtered[group_col].unique()
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

    # Dynamic column selection based on detected structure
    if hasattr(st.session_state, 'data_analysis') and st.session_state.data_analysis.get('column_analysis'):
        column_analysis = st.session_state.data_analysis['column_analysis']
        interface_config = update_analysis_interface_from_columns(column_analysis)
        
        with st.sidebar:
            st.markdown("---")
            st.subheader("🎯 Dynamic Column Selection")
            
            # Add column selectors based on detected structure
            for selector_key, selector_config in interface_config.get('column_selectors', {}).items():
                if selector_config['options']:
                    selected_col = st.selectbox(
                        selector_config['label'],
                        options=selector_config['options'],
                        index=0,
                        key=f"dynamic_{selector_key}",
                        help=selector_config['help']
                    )
                    # Store selection in session state for use in analysis
                    st.session_state[f'selected_{selector_key}'] = selected_col
            
            # Show analysis readiness indicator
            if interface_config.get('available_analyses'):
                st.success(f"✅ {len(interface_config['available_analyses'])} analysis type(s) available")
            else:
                st.warning("⚠️ Upload data to enable dynamic analysis")

    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🏠 Overview",
        "📊 Concentrations",
        "⏰ Timeline", 
        "🔬 Statistics",
        "🔬 Quality Control",
        "🌍 3D Analysis",
        "🔬 Data Insights",
        "📋 Pivot Tables"
    ])

    with tab1:
        st.header("🏠 Dataset Overview")
        
        # Get column analysis if available
        column_analysis = {}
        if hasattr(st.session_state, 'data_analysis') and st.session_state.data_analysis:
            column_analysis = st.session_state.data_analysis.get('column_analysis', {})
            set_column_analysis_cache(column_analysis)
        
        interface_config = update_analysis_interface_from_columns(column_analysis) if column_analysis else {}
        
        # View mode toggle
        view_mode = st.radio("📊 View Mode:", ["Quick Summary", "Extensive Analysis"], horizontal=True)
        
        if view_mode == "Quick Summary":
            # Quick metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Records", len(df_filtered))
            with col2:
                st.metric("📋 Columns", len(df_filtered.columns))
            with col3:
                st.metric("📈 Numeric", len(df_filtered.select_dtypes(include=['number']).columns))
            with col4:
                data_quality = 1 - df_filtered.isnull().sum().sum() / (len(df_filtered) * len(df_filtered.columns))
                st.metric("✅ Quality", f"{data_quality:.1%}")
            
            # Minimal data preview
            st.subheader("📋 Data Preview")
            st.dataframe(df_filtered.head(5), width='stretch')
            
        else:  # Extensive Analysis
            # Show dynamic column analysis results
            if column_analysis:
                st.subheader("🔍 Detected Data Structure")
                
                col_detect1, col_detect2 = st.columns(2)
                
                with col_detect1:
                    st.write("**📋 Column Classifications:**")
                    for col_id, mapping in column_analysis.get('potential_mappings', {}).items():
                        mapping_display = mapping.replace('_', ' ').title()
                        st.write(f"• **{col_id}**: {mapping_display}")
                
                with col_detect2:
                    st.write("**🚀 Available Analysis Paths:**")
                    for path in column_analysis.get('analysis_paths', []):
                        confidence_color = "🔥" if path['confidence'] == 'high' else "⚡" if path['confidence'] == 'medium' else "💡"
                        st.write(f"{confidence_color} {path['description']}")
            
            # Dynamic summary metrics based on detected columns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total Records", len(df_filtered))
            
            with col2:
                # Find subject identifier columns dynamically (including legacy names)
                subject_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() 
                               if mapping in ['grouping_variable', 'subject_identifier']]
                
                # Also check for common legacy column names
                if not subject_cols:
                    legacy_subject_cols = [col for col in df_filtered.columns 
                                          if col in ['SubjectID', 'Subject_ID', 'subject_id', 'PatientID', 'Patient_ID']]
                    if legacy_subject_cols:
                        subject_cols = legacy_subject_cols
                
                if subject_cols:
                    subject_col = subject_cols[0]
                    st.metric(f"👥 Unique {subject_col.replace('_', ' ').title()}", df_filtered[subject_col].nunique())
                else:
                    st.metric("👥 Data Points", len(df_filtered))
            
            with col3:
                # Find analysis dimension columns dynamically (including legacy names)
                dimension_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() 
                                 if mapping == 'analysis_dimension']
                
                # Also check for common legacy biomarker column names
                if not dimension_cols:
                    legacy_marker_cols = [col for col in df_filtered.columns 
                                         if col in ['Marker', 'Biomarker', 'marker', 'biomarker', 'Analyte', 'analyte']]
                    if legacy_marker_cols:
                        dimension_cols = legacy_marker_cols
                
                if dimension_cols:
                    dim_col = dimension_cols[0]
                    st.metric(f"🧬 {dim_col.replace('_', ' ').title()}", df_filtered[dim_col].nunique())
                else:
                    primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() 
                                        if mapping == 'primary_endpoint']
                    if primary_endpoints:
                        st.metric("📈 Numeric Variables", len(primary_endpoints))
                    else:
                        st.metric("📊 Columns", len(df_filtered.columns))
            
            with col4:
                # Find time-related columns dynamically
                time_cols = [col for col, patterns in column_analysis.get('column_patterns', {}).items() 
                            if 'timepoint' in patterns]
                if time_cols:
                    time_col = time_cols[0]
                    st.metric(f"⏰ {time_col.replace('_', ' ').title()}", df_filtered[time_col].nunique())
                else:
                    # Show stratification factors instead
                    strat_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() 
                                 if mapping == 'stratification_factor']
                    if strat_cols:
                        strat_col = strat_cols[0]
                        st.metric(f"🔄 {strat_col.replace('_', ' ').title()}", df_filtered[strat_col].nunique())
                    else:
                        st.metric("📋 Data Quality", f"{(1 - df_filtered.isnull().sum().sum() / (len(df_filtered) * len(df_filtered.columns))):.1%}")
            
            # Extended data preview
            st.subheader("📋 Data Preview")
            st.dataframe(df_filtered.head(10), width='stretch')
            
            # Basic statistics using dynamic column detection
            primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'primary_endpoint']
            dimension_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'analysis_dimension']
            
        # Use smart detection with fallbacks
        if not dimension_cols:
            dimension_cols = smart_detect_columns(df_filtered, 'biomarker')
        
        if primary_endpoints and dimension_cols:
            measurement_col = primary_endpoints[0]
            dimension_col = dimension_cols[0]
            st.subheader(f"📊 {measurement_col.replace('_', ' ').title()} Statistics by {dimension_col.replace('_', ' ').title()}")
            stats_df = df_filtered.groupby(dimension_col)[measurement_col].describe().round(3)
            st.dataframe(stats_df, width='stretch')
        elif primary_endpoints:
            measurement_col = primary_endpoints[0]
            st.subheader(f"📊 {measurement_col.replace('_', ' ').title()} Statistics")
            stats_df = df_filtered[measurement_col].describe().round(3)
            st.dataframe(stats_df.to_frame().T, width='stretch')
        
    with tab2:
        # Use dynamic column detection for biomarker analysis
        primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'primary_endpoint']
        dimension_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'analysis_dimension']
        group_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'stratification_factor']
        
        # Enhanced fallback with broader pattern matching
        if not dimension_cols:
            dimension_cols = [col for col in df_filtered.columns if col in ['Marker', 'Biomarker', 'Analyte']]
            # Also look for columns with biomarker-like names
            if not dimension_cols:
                dimension_cols = [col for col in df_filtered.columns if any(keyword in col.lower() for keyword in ['marker', 'biomarker', 'analyte', 'protein', 'cytokine'])]
        
        if not group_cols:
            group_cols = [col for col in df_filtered.columns if col in ['Group', 'Treatment', 'Arm', 'Cohort']]
            # Enhanced group detection with more patterns
            if not group_cols:
                group_cols = [col for col in df_filtered.columns if any(keyword in col.lower() for keyword in ['group', 'treatment', 'condition', 'arm', 'cohort', 'category', 'class', 'type'])]
            # Look for categorical columns with reasonable number of unique values (2-10)
            if not group_cols:
                categorical_cols = df_filtered.select_dtypes(include=['object', 'category']).columns
                group_cols = [col for col in categorical_cols if 2 <= df_filtered[col].nunique() <= 10]
        
        measurement_label = primary_endpoints[0].replace('_', ' ').title() if primary_endpoints else 'Measurement'
        st.header(f"📊 {measurement_label} Analysis")
        
        if primary_endpoints:
                measurement_col = primary_endpoints[0]
                dimension_col = dimension_cols[0] if dimension_cols else None
                group_col = group_cols[0] if group_cols else None
                
                # Get color settings with error handling
                groups = df_filtered[group_col].unique() if group_col else None
                try:
                    color_map = get_color_palette(color_scheme, groups, custom_colors) if groups is not None else None
                except Exception as e:
                    st.warning(f"⚠️ Color scheme issue: {e}. Using default colors.")
                    color_map = get_color_palette("Default (Plotly)", groups, None) if groups is not None else None
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Animated or static box plot
                    if enable_animations and animation_frame in df_filtered.columns and animation_frame != dimension_col:
                        fig_box = px.box(
                            df_filtered,
                            x=dimension_col if dimension_col else measurement_col,
                            y=measurement_col, 
                            color=group_col if group_col else None,
                            animation_frame=animation_frame,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            title=f"🎥 Animated {measurement_col.replace('_', ' ').title()} Distribution (by {animation_frame})",
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
                            x=dimension_col if dimension_col else measurement_col,
                            y=measurement_col, 
                            color=group_col if group_col else None,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            title=f"📦 {measurement_col.replace('_', ' ').title()} Distribution" + (f" by {dimension_col.replace('_', ' ').title()}" if dimension_col else ""),
                            points="all"
                        )
                    fig_box.update_traces(marker=dict(size=marker_size))
                    fig_box.update_layout(height=500)
                    fig_box = apply_theme_styling(fig_box, background_theme, plot_opacity)
                    st.plotly_chart(fig_box, width='stretch')
                
                with col2:
                    # Animated or static violin plot
                    if enable_animations and animation_frame in df_filtered.columns and animation_frame != dimension_col:
                        fig_violin = px.violin(
                            df_filtered,
                            x=dimension_col if dimension_col else measurement_col,
                            y=measurement_col,
                            color=group_col if group_col else None,
                            animation_frame=animation_frame,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            box=True,
                            title=f"🎥 Animated {measurement_col.replace('_', ' ').title()} Density Distribution (by {animation_frame})"
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
                            x=dimension_col if dimension_col else measurement_col,
                            y=measurement_col,
                            color=group_col if group_col else None,
                            color_discrete_map=color_map if isinstance(color_map, dict) else None,
                            color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                            box=True,
                            title=f"🎻 {measurement_col.replace('_', ' ').title()} Density Distribution"
                        )
                    fig_violin.update_layout(height=500)
                    fig_violin = apply_theme_styling(fig_violin, background_theme, plot_opacity)
                    st.plotly_chart(fig_violin, width='stretch')
                
                # Histogram by group
                if group_col:
                    fig_hist = px.histogram(
                        df_filtered,
                        x=measurement_col,
                        color=group_col,
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        facet_col=dimension_col if dimension_col else None,
                        title=f"📊 {measurement_col.replace('_', ' ').title()} Histograms by {group_col.replace('_', ' ').title()}",
                        nbins=20,
                        opacity=plot_opacity
                    )
                    fig_hist = apply_theme_styling(fig_hist, background_theme, plot_opacity)
                    st.plotly_chart(fig_hist, width='stretch')
        else:
            primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'primary_endpoint']
            if primary_endpoints:
                st.info(f"📊 Available measurement columns: {', '.join(primary_endpoints[:3])}{'...' if len(primary_endpoints) > 3 else ''}")
                st.info("💡 Try using the Data Overview tab for basic visualization of these columns")
            else:
                st.warning("⚠️ No numeric measurement columns detected for visualization")
        
    with tab3:
        st.header("📈 Longitudinal Analysis")
        
        # Find dynamic column mappings for longitudinal analysis
        time_cols = [col for col, patterns in column_analysis.get('column_patterns', {}).items() if 'timepoint' in patterns]
        primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'primary_endpoint']
        subject_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping in ['grouping_variable', 'subject_identifier']]
        
        # Check for legacy column names as fallback
        if not time_cols:
            time_cols = [col for col in df_filtered.columns if col in ['NominalTime', 'ActualTime', 'Time', 'Timepoint', 'Visit']]
        if not subject_cols:
            subject_cols = [col for col in df_filtered.columns if col in ['SubjectID', 'Subject_ID', 'PatientID', 'Patient_ID']]
        
        if time_cols and primary_endpoints and subject_cols:
            time_col = time_cols[0]
            measurement_col = primary_endpoints[0]
            subject_col = subject_cols[0]
            
            # Get grouping columns for color coding
            group_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'stratification_factor']
            if not group_cols:
                group_cols = [col for col in df_filtered.columns if col in ['Group', 'Treatment', 'Arm', 'Cohort']]
                # Enhanced group detection
                if not group_cols:
                    group_cols = [col for col in df_filtered.columns if any(keyword in col.lower() for keyword in ['group', 'treatment', 'condition', 'arm', 'cohort', 'category', 'class', 'type'])]
                # Look for categorical columns with reasonable number of unique values
                if not group_cols:
                    categorical_cols = df_filtered.select_dtypes(include=['object', 'category']).columns
                    group_cols = [col for col in categorical_cols if 2 <= df_filtered[col].nunique() <= 10]
                    
            # Get dimension columns for faceting
            dimension_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'analysis_dimension']
            if not dimension_cols:
                dimension_cols = [col for col in df_filtered.columns if col in ['Marker', 'Biomarker', 'Analyte']]
            
            groups = df_filtered[group_cols[0]].unique() if group_cols else None
            try:
                color_map = get_color_palette(color_scheme, groups, custom_colors) if groups is not None else None
            except Exception as e:
                st.warning(f"⚠️ Color scheme issue: {e}. Using default colors.")
                color_map = get_color_palette("Default (Plotly)", groups, None) if groups is not None else None
            
            # Animated or static individual trajectories
            dimension_col = dimension_cols[0] if dimension_cols else None
            group_col = group_cols[0] if group_cols else None
            
            if enable_animations and subject_col in df_filtered.columns and animation_frame == subject_col:
                fig_lines = px.line(
                    df_filtered,
                    x=time_col,
                    y=measurement_col,
                        color=group_col if group_col else subject_col,
                        animation_frame=subject_col,
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        line_group=subject_col,
                        facet_col=dimension_col if dimension_col else None,
                        title=f"🎥 Animated Individual {subject_col.replace('_', ' ').title()} Trajectories",
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
            elif enable_animations and animation_frame in df_filtered.columns and animation_frame == time_col:
                    # Time-based animation showing data building up
                    fig_lines = px.scatter(
                        df_filtered,
                        x=time_col,
                        y=measurement_col,
                        color=group_col if group_col else subject_col,
                        animation_frame=time_col,
                        animation_group=subject_col,
                        color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        facet_col=dimension_col if dimension_col else None,
                        title=f"🎥 Animated {time_col.replace('_', ' ').title()} Evolution",
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
                    x=time_col,
                    y=measurement_col,
                    color=group_col if group_col else subject_col,
                    color_discrete_map=color_map if isinstance(color_map, dict) else None,
                    color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                    line_group=subject_col,
                    facet_col=dimension_col if dimension_col else None,
                    title=f"📈 Individual {subject_col.replace('_', ' ').title()} {measurement_col.replace('_', ' ').title()} Trajectories",
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
            if group_col and dimension_col:
                # Build grouping columns list for aggregation
                group_cols_for_agg = [group_col, dimension_col, time_col]
                
                mean_data = df_filtered.groupby(group_cols_for_agg)[measurement_col].agg(['mean', 'std', 'count']).reset_index()
                mean_data['se'] = mean_data['std'] / np.sqrt(mean_data['count'])
                
                fig_mean = px.line(
                    mean_data,
                    x=time_col,
                    y='mean',
                    color=group_col,
                    color_discrete_map=color_map if isinstance(color_map, dict) else None,
                        color_discrete_sequence=color_map if isinstance(color_map, list) else None,
                        facet_col=dimension_col,
                        title=f"📊 Mean {measurement_col.replace('_', ' ').title()} Trajectories with Standard Error",
                        error_y='se',
                        markers=True
                    )
                fig_mean.update_traces(
                    line=dict(width=3),
                    marker=dict(size=marker_size + 2)
                )
                fig_mean.update_layout(yaxis_title=f"Mean {measurement_col.replace('_', ' ').title()}")
                fig_mean = apply_theme_styling(fig_mean, background_theme, plot_opacity)
                st.plotly_chart(fig_mean, width='stretch')
            else:
                missing_components = []
                if not time_cols:
                    missing_components.append("time/visit columns")
                if not primary_endpoints:
                    missing_components.append("measurement columns")
                if not subject_cols:
                    missing_components.append("subject ID columns")
                
                st.warning(f"⚠️ Longitudinal analysis requires: {', '.join(missing_components)}")
                if time_cols or primary_endpoints or subject_cols:
                    available = []
                    if time_cols:
                        available.append(f"Time columns: {', '.join(time_cols[:2])}")
                    if primary_endpoints:
                        available.append(f"Measurements: {', '.join(primary_endpoints[:2])}")
                    if subject_cols:
                        available.append(f"Subject IDs: {', '.join(subject_cols[:2])}")
                    st.info(f"✅ Found: {' | '.join(available)}")
        
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
        
        # Use dynamic column detection for statistical analysis
        primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'primary_endpoint']
        group_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'stratification_factor']
        dimension_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'analysis_dimension']
        
        # Fallback to legacy column names
        if not group_cols:
            group_cols = [col for col in df_filtered.columns if col in ['Group', 'Treatment', 'Arm', 'Cohort']]
        if not dimension_cols:
            dimension_cols = [col for col in df_filtered.columns if col in ['Marker', 'Biomarker', 'Analyte']]
            
        if primary_endpoints:
            # Debug information to help identify issues
            st.sidebar.write("🔍 **Debug Info:**")
            st.sidebar.write(f"Primary endpoints: {len(primary_endpoints)} found")
            st.sidebar.write(f"Group columns: {len(group_cols)} found") 
            st.sidebar.write(f"Dimension columns: {len(dimension_cols)} found")
            
            # Basic statistical analysis available with just measurement columns
            # More advanced analyses require grouping or dimension columns
            
            if stat_method == "Group Comparisons" and group_cols and dimension_cols and primary_endpoints:
                    st.subheader("📊 Group Comparisons (T-tests)")
                    
                    # Use dynamic columns
                    measurement_col = primary_endpoints[0]
                    group_col = group_cols[0]
                    dimension_col = dimension_cols[0]
                    
                    results = []
                    for marker in df_filtered[dimension_col].unique():
                        marker_data = df_filtered[df_filtered[dimension_col] == marker]
                        groups = marker_data[group_col].unique()
                        
                        if len(groups) >= 2:
                            # Extract data and track missing values
                            group1_raw = marker_data[marker_data[group_col] == groups[0]][measurement_col]
                            group2_raw = marker_data[marker_data[group_col] == groups[1]][measurement_col]
                            
                            group1_data = group1_raw.dropna()
                            group2_data = group2_raw.dropna()
                            
                            group1_missing = len(group1_raw) - len(group1_data)
                            group2_missing = len(group2_raw) - len(group2_data)
                            
                            if len(group1_data) > 1 and len(group2_data) > 1:
                                try:
                                    # Independent t-test (missing data already removed)
                                    stat, p_value = stats.ttest_ind(group1_data, group2_data)
                                    
                                    # Cohen's d (effect size)
                                    pooled_std = np.sqrt(((len(group1_data) - 1) * group1_data.var() + 
                                                        (len(group2_data) - 1) * group2_data.var()) / 
                                                       (len(group1_data) + len(group2_data) - 2))
                                    cohens_d = (group1_data.mean() - group2_data.mean()) / pooled_std
                                    effect_size = "Small" if abs(cohens_d) < 0.5 else "Medium" if abs(cohens_d) < 0.8 else "Large"
                                except Exception as e:
                                    st.error(f"❌ Statistical calculation error for {marker}: {str(e)}")
                                    continue
                                
                                # Create missing data note
                                missing_note = ""
                                if group1_missing > 0 or group2_missing > 0:
                                    missing_note = f"(Missing: G1:{group1_missing}, G2:{group2_missing})"
                                
                                results.append({
                                    dimension_col.replace('_', ' ').title(): marker,
                                    'Comparison': f"{groups[0]} vs {groups[1]}",
                                    'Group 1 N': len(group1_data),
                                    'Group 2 N': len(group2_data),
                                    'Group 1 Mean': round(group1_data.mean(), 3),
                                    'Group 2 Mean': round(group2_data.mean(), 3),
                                    'Group 1 SD': round(group1_data.std(), 3),
                                    'Group 2 SD': round(group2_data.std(), 3),
                                    'T-statistic': round(stat, 4),
                                    'P-value': round(p_value, 6),
                                    "Cohen's d": round(cohens_d, 3),
                                    'Effect Size': effect_size,
                                    f'Significant (p<{alpha_level})': '✅ Yes' if p_value < alpha_level else '❌ No',
                                    'Missing Data': missing_note
                                })
                    
                    if results:
                        results_df = pd.DataFrame(results)
                        st.dataframe(results_df, width='stretch')
                        
                        # Show missing data summary
                        if any('Missing Data' in res and res['Missing Data'] for res in results):
                            st.info("ℹ️ **Missing Data Note**: Analyses performed on complete cases only. Missing values were excluded from calculations.")
                    else:
                        st.info("📝 No statistical comparisons available")
                
            elif stat_method in ["ANOVA Analysis"] and group_cols and dimension_cols and primary_endpoints:
                    st.subheader("🔬 ANOVA Analysis")
                    
                    # Use dynamic columns
                    measurement_col = primary_endpoints[0]
                    group_col = group_cols[0]
                    dimension_col = dimension_cols[0]
                    
                    anova_results = []
                    for marker in df_filtered[dimension_col].unique():
                        marker_data = df_filtered[df_filtered[dimension_col] == marker]
                        groups = marker_data[group_col].unique()
                        
                        if len(groups) > 2:
                            # Track missing data for each group
                            group_data_clean = []
                            missing_by_group = {}
                            
                            for group in groups:
                                raw_data = marker_data[marker_data[group_col] == group][measurement_col]
                                clean_data = raw_data.dropna()
                                if len(clean_data) > 0:
                                    group_data_clean.append(clean_data)
                                    missing_by_group[group] = len(raw_data) - len(clean_data)
                            
                            if len(group_data_clean) > 2 and all(len(data) > 1 for data in group_data_clean):
                                f_stat, p_value = stats.f_oneway(*group_data_clean)
                                
                                # Eta-squared (effect size) using cleaned data
                                all_clean_data = pd.concat(group_data_clean, ignore_index=True)
                                overall_mean = all_clean_data.mean()
                                ss_between = sum(len(data) * (data.mean() - overall_mean)**2 
                                               for data in group_data_clean)
                                ss_total = ((all_clean_data - overall_mean)**2).sum()
                                eta_squared = ss_between / ss_total if ss_total > 0 else 0
                                
                                # Create missing data summary
                                total_missing = sum(missing_by_group.values())
                                missing_summary = ", ".join([f"{group}:{count}" for group, count in missing_by_group.items() if count > 0])
                                missing_note = f"(Missing: {missing_summary})" if missing_summary else "(No missing data)"
                                
                                anova_results.append({
                                    'Biomarker': marker,
                                    'Groups': len(groups),
                                    'Total N': sum(len(data) for data in group_data_clean),
                                    'F-statistic': round(f_stat, 4),
                                    'P-value': round(p_value, 6),
                                    'Eta-squared': round(eta_squared, 3),
                                    f'Significant (p<{alpha_level})': '✅ Yes' if p_value < alpha_level else '❌ No',
                                    'Missing Data': missing_note
                                })
                    
                    if anova_results:
                        anova_df = pd.DataFrame(anova_results)
                        st.dataframe(anova_df, width='stretch')
                        
                        # Show missing data info if any
                        if any('Missing Data' in res and 'Missing:' in res['Missing Data'] for res in anova_results):
                            st.info("ℹ️ **Missing Data Note**: ANOVA performed on complete cases only. Missing values were excluded from all calculations.")
                    else:
                        st.info("📝 ANOVA requires 3+ groups")
                
            if stat_method in ["Non-parametric Tests", "All Methods"]:
                    st.subheader("📈 Non-parametric Tests")
                    
                    nonparam_results = []
                    # Use dynamic marker column detection
                    marker_col = dimension_cols[0] if dimension_cols else None
                    if marker_col and marker_col in df_filtered.columns:
                        for marker in df_filtered[marker_col].unique():
                            marker_data = df_filtered[df_filtered[marker_col] == marker]
                            groups = marker_data[group_cols[0]].unique() if group_cols else []
                            
                            if len(groups) >= 2:
                                if len(groups) == 2:
                                    # Mann-Whitney U test
                                    group1_data = marker_data[marker_data[group_cols[0]] == groups[0]][primary_endpoints[0]].dropna()
                                    group2_data = marker_data[marker_data[group_cols[0]] == groups[1]][primary_endpoints[0]].dropna()
                                    
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
                                    group_data = [marker_data[marker_data[group_cols[0]] == group][primary_endpoints[0]].dropna() 
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
                    
                    if not (group_cols and dimension_cols and primary_endpoints):
                        st.info("💡 Normality tests work best with grouping, biomarker, and measurement columns")
                        # Basic normality test with just measurement columns
                        if primary_endpoints:
                            for endpoint in primary_endpoints[:2]:
                                col_data = df_filtered[endpoint].dropna()
                                if len(col_data) >= 3:
                                    shapiro_stat, shapiro_p = shapiro(col_data[:5000])  # Limit for Shapiro-Wilk
                                    st.write(f"**{endpoint}**: Shapiro-Wilk p = {shapiro_p:.6f} {'(Normal)' if shapiro_p > 0.05 else '(Non-normal)'}")
                    else:
                        normality_results = []
                        for marker in df_filtered[dimension_cols[0]].unique():
                            marker_data = df_filtered[df_filtered[dimension_cols[0]] == marker]
                            
                            for group in marker_data[group_cols[0]].unique():
                                group_data = marker_data[marker_data[group_cols[0]] == group][primary_endpoints[0]].dropna()
                            
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
                        
                        for marker in df_filtered[dimension_cols[0]].unique():
                            marker_data = df_filtered[df_filtered[dimension_cols[0]] == marker]
                            groups = marker_data[group_cols[0]].unique()
                            
                            if len(groups) >= 2:
                                group_data = [marker_data[marker_data[group_cols[0]] == group][primary_endpoints[0]].dropna() 
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
                    
                    if not (group_cols and dimension_cols and primary_endpoints):
                        st.info("💡 Effect size analysis works best with grouping, biomarker, and measurement columns")
                        # Basic coefficient of variation
                        if primary_endpoints:
                            st.write("**Basic Variability Analysis:**")
                            for endpoint in primary_endpoints[:2]:
                                col_data = df_filtered[endpoint].dropna()
                                if len(col_data) > 1:
                                    cv = (col_data.std() / col_data.mean()) * 100 if col_data.mean() != 0 else 0
                                    st.write(f"• **{endpoint}**: CV = {cv:.1f}%")
                    else:
                        effect_results = []
                        for marker in df_filtered[dimension_cols[0]].unique():
                            marker_data = df_filtered[df_filtered[dimension_cols[0]] == marker]
                            groups = marker_data[group_cols[0]].unique()
                            
                            if len(groups) >= 2:
                                group1_data = marker_data[marker_data[group_cols[0]] == groups[0]][primary_endpoints[0]].dropna()
                                group2_data = marker_data[marker_data[group_cols[0]] == groups[1]][primary_endpoints[0]].dropna()
                            
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
                # Handle different analysis types based on available columns
            elif stat_method == "Normality & Assumptions":
                st.subheader("📊 Normality & Assumptions Testing")
                
                for endpoint in primary_endpoints[:3]:  # Limit to first 3 endpoints
                        col_data = df_filtered[endpoint].dropna()
                        
                        if len(col_data) >= 3:
                            st.write(f"**Analysis for {endpoint}:**")
                            
                            # Shapiro-Wilk test for normality
                            try:
                                if len(col_data) <= 5000:  # Shapiro-Wilk limitation
                                    stat, p_value = shapiro(col_data)
                                    interpretation = "normally distributed" if p_value > 0.05 else "not normally distributed"
                                    
                                    st.write(f"• **Shapiro-Wilk Test**: W = {stat:.4f}, p = {p_value:.6f}")
                                    st.write(f"• **Interpretation**: Data appears {interpretation} (α = 0.05)")
                                else:
                                    st.write("• **Note**: Sample too large for Shapiro-Wilk test")
                                
                                # Basic descriptive statistics
                                st.write(f"• **Mean**: {col_data.mean():.3f}")
                                st.write(f"• **Std Dev**: {col_data.std():.3f}")
                                st.write(f"• **Skewness**: {col_data.skew():.3f}")
                                st.write(f"• **Kurtosis**: {col_data.kurtosis():.3f}")
                                
                            except ImportError:
                                st.write(f"• **Basic Stats**: Mean = {col_data.mean():.3f}, SD = {col_data.std():.3f}")
                            
                            st.write("---")
                
            elif stat_method == "Correlation Analysis" and len(primary_endpoints) >= 2:
                    st.subheader("🔗 Correlation Analysis")
                    
                    correlation_data = df_filtered[primary_endpoints].corr()
                    st.dataframe(correlation_data, width='stretch')
                    
                    # Heatmap visualization
                    try:
                        fig_corr = px.imshow(
                            correlation_data.values,
                            x=correlation_data.columns,
                            y=correlation_data.index,
                            color_continuous_scale='RdBu',
                            title="Correlation Matrix"
                        )
                        st.plotly_chart(fig_corr, width='stretch')
                    except:
                        pass
                
            else:
                    # Provide helpful guidance for different scenarios
                    available = []
                    if primary_endpoints:
                        available.append(f"Measurements: {', '.join(primary_endpoints[:2])}")
                    if group_cols:
                        available.append(f"Groups: {', '.join(group_cols[:2])}")
                    if dimension_cols:
                        available.append(f"Biomarkers: {', '.join(dimension_cols[:2])}")
                    
                    if available:
                        st.info(f"✅ Available columns: {' | '.join(available)}")
                    
                    # Provide specific guidance based on what's missing
                    if stat_method in ["Group Comparisons", "ANOVA Analysis", "Non-parametric Tests"]:
                        if not group_cols:
                            st.warning(f"⚠️ {stat_method} requires grouping columns for comparisons")
                            
                            # Offer manual group column selection
                            categorical_cols = df_filtered.select_dtypes(include=['object', 'category']).columns.tolist()
                            if categorical_cols:
                                st.info("💡 **Manual Group Selection:**")
                                manual_group_col = st.selectbox(
                                    "Select a column to use for group comparisons:",
                                    options=["None"] + categorical_cols,
                                    help="Choose a categorical column that represents different groups or conditions"
                                )
                                
                                if manual_group_col != "None":
                                    # Perform group analysis with manually selected column
                                    group_col = manual_group_col
                                    unique_groups = df_filtered[group_col].unique()
                                    
                                    if len(unique_groups) >= 2:
                                        st.success(f"✅ Using '{group_col}' for group comparisons ({len(unique_groups)} groups: {', '.join(map(str, unique_groups))})")
                                        
                                        # Perform basic group comparison analysis
                                        if primary_endpoints:
                                            measurement_col = primary_endpoints[0]
                                            
                                            # Group statistics
                                            group_stats = df_filtered.groupby(group_col)[measurement_col].agg(['count', 'mean', 'std', 'median']).round(3)
                                            st.subheader(f"📊 Group Statistics: {measurement_col}")
                                            st.dataframe(group_stats, width='stretch')
                                            
                                            # Visualization
                                            try:
                                                fig_box = px.box(
                                                    df_filtered,
                                                    x=group_col,
                                                    y=measurement_col,
                                                    title=f"Distribution by {group_col}",
                                                    points="all"
                                                )
                                                st.plotly_chart(fig_box, width='stretch')
                                            except Exception as e:
                                                st.warning(f"Visualization error: {e}")
                                    else:
                                        st.warning(f"Column '{group_col}' has only {len(unique_groups)} unique value(s). Need at least 2 groups for comparison.")
                            else:
                                st.info("💡 Try 'Normality & Assumptions' or 'Correlation Analysis' for single-group analyses")
                        elif not dimension_cols:
                            st.warning(f"⚠️ {stat_method} works best with biomarker columns for comprehensive analysis")
                    
                    elif stat_method == "Correlation Analysis" and len(primary_endpoints) < 2:
                        st.warning("⚠️ Correlation analysis requires at least 2 measurement columns")
                    
                    elif stat_method == "All Methods":
                        if not (group_cols and dimension_cols):
                            st.info("💡 'All Methods' provides most comprehensive analysis with both grouping and biomarker columns")
                            st.info("📊 Try individual analysis methods based on your available data")
        else:
            st.warning("⚠️ Statistical analysis requires measurement columns")
            st.info("💡 Upload data with numeric measurement columns to enable statistical analysis")
        
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
                        group_col = group_cols[0] if group_cols else 'Group'
                        if group_col in df_filtered.columns:
                            flag_group = pd.crosstab(df_filtered[group_col], df_filtered['flag'])
                        
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
            # Use dynamic group column detection
            group_col_local = group_cols[0] if group_cols else None
            groups = df_filtered[group_col_local].unique() if group_col_local and group_col_local in df_filtered.columns else None
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
        
        # Use dynamic column detection for 3D analysis
        primary_endpoints = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'primary_endpoint']
        group_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'stratification_factor']
        dimension_cols = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping == 'analysis_dimension']
        
        # Fallback to legacy column names
        if not group_cols:
            group_cols = [col for col in df_filtered.columns if col in ['Group', 'Treatment', 'Arm', 'Cohort']]
        if not dimension_cols:
            dimension_cols = [col for col in df_filtered.columns if col in ['Marker', 'Biomarker', 'Analyte']]
        
        if primary_endpoints and group_cols and dimension_cols:
            
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
                
                # Create biomarker comparison matrix in 3D using dynamic column detection
                marker_col = dimension_cols[0] if dimension_cols else None
                markers = df_filtered[marker_col].unique() if marker_col and marker_col in df_filtered.columns else []
                if len(markers) >= 2:
                    
                    # Prepare data for 3D biomarker space
                    biomarker_3d_data = []
                    
                    # Use dynamic concentration column detection
                    conc_col = primary_endpoints[0] if primary_endpoints else 'Concentration'
                    
                    for i, marker1 in enumerate(markers):
                        for j, marker2 in enumerate(markers):
                            if i != j:
                                data1 = df_filtered[df_filtered[marker_col] == marker1][conc_col]
                                data2 = df_filtered[df_filtered[marker_col] == marker2][conc_col]
                                
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
                
                time_cols_3d = [col for col, patterns in column_analysis.get('column_patterns', {}).items() if 'timepoint' in patterns]
                if not time_cols_3d:
                    time_cols_3d = [col for col in df_filtered.columns if col in ['NominalTime', 'ActualTime', 'Time', 'Timepoint', 'Visit']]
                
                if time_cols_3d:
                    time_col_3d = time_cols_3d[0]
                    measurement_col_3d = primary_endpoints[0]
                    group_col_3d = group_cols[0]
                    dimension_col_3d = dimension_cols[0]
                    
                    # Find best z-axis column
                    subject_cols_3d = [col for col, mapping in column_analysis.get('potential_mappings', {}).items() if mapping in ['grouping_variable', 'subject_identifier']]
                    if not subject_cols_3d:
                        subject_cols_3d = [col for col in df_filtered.columns if col in ['SubjectID', 'Subject_ID', 'PatientID', 'Patient_ID']]
                    
                    z_col = subject_cols_3d[0] if subject_cols_3d else dimension_col_3d
                    
                    # Create 3D time series plot
                    fig_time_3d = px.scatter_3d(
                        df_filtered,
                        x=time_col_3d,
                        y=measurement_col_3d,
                        z=z_col,
                        color=group_col_3d,
                        hover_data=[dimension_col_3d] if dimension_col_3d else [],
                        title=f"⏰ 3D Temporal {measurement_col_3d.replace('_', ' ').title()} Evolution",
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
                # Use dynamic columns for info display
                biomarker_col = dimension_cols[0] if dimension_cols else None
                group_col = group_cols[0] if group_cols else None
                time_cols_display = [col for col, patterns in column_analysis.get('column_patterns', {}).items() if 'timepoint' in patterns]
                if not time_cols_display:
                    time_cols_display = [col for col in df_filtered.columns if col in ['NominalTime', 'ActualTime', 'Time', 'Timepoint', 'Visit']]
                time_col = time_cols_display[0] if time_cols_display else None
                
                st.info(
                    f"📊 **Data Points**: {len(df_filtered)}\n\n"
                    f"🧬 **Biomarkers**: {df_filtered[biomarker_col].nunique() if biomarker_col else 'N/A'}\n\n"
                    f"👥 **Groups**: {df_filtered[group_col].nunique() if group_col else 'N/A'}\n\n"
                    f"⏰ **Timepoints**: {df_filtered[time_col].nunique() if time_col else 'N/A'}"
                )
        else:
            missing_components = []
            if not primary_endpoints:
                missing_components.append("measurement columns")
            if not group_cols:
                missing_components.append("group columns")
            if not dimension_cols:
                missing_components.append("biomarker columns")
            
            if missing_components:
                st.warning(f"⚠️ 3D analysis requires: {', '.join(missing_components)}")
                
            available = []
            if primary_endpoints:
                available.append(f"Measurements: {', '.join(primary_endpoints[:2])}")
            if group_cols:
                available.append(f"Groups: {', '.join(group_cols[:2])}")
            if dimension_cols:
                available.append(f"Biomarkers: {', '.join(dimension_cols[:2])}")
            
            if available:
                st.info(f"✅ Available: {' | '.join(available)}")
            else:
                st.info("💡 Upload data with measurement values, groups, and biomarker identifiers for 3D analysis")

    with tab7:
        st.header("🔬 Data Insights & Summary")
        
        if df_filtered is not None and not df_filtered.empty:
            # Data quality insights
            st.subheader("📊 Data Quality Assessment")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Missing data analysis
                missing_data = df_filtered.isnull().sum()
                total_missing = missing_data.sum()
                missing_percentage = (total_missing / (len(df_filtered) * len(df_filtered.columns))) * 100
                
                st.metric("💔 Missing Data Points", f"{total_missing:,}")
                st.write(f"**{missing_percentage:.1f}%** of total data")
                
            with col2:
                # Duplicate analysis
                duplicates = df_filtered.duplicated().sum()
                duplicate_percentage = (duplicates / len(df_filtered)) * 100
                
                st.metric("🔄 Duplicate Rows", f"{duplicates:,}")
                st.write(f"**{duplicate_percentage:.1f}%** of total rows")
                
            with col3:
                # Data completeness
                completeness = ((len(df_filtered) * len(df_filtered.columns) - total_missing) / 
                               (len(df_filtered) * len(df_filtered.columns))) * 100
                
                st.metric("✅ Data Completeness", f"{completeness:.1f}%")
                
            # Column-wise missing data breakdown
            if total_missing > 0:
                st.subheader("🔍 Missing Data by Column")
                missing_cols = missing_data[missing_data > 0].sort_values(ascending=False)
                
                if len(missing_cols) > 0:
                    fig_missing = px.bar(
                        x=missing_cols.values,
                        y=missing_cols.index,
                        orientation='h',
                        title="Missing Data Count by Column",
                        labels={'x': 'Missing Values', 'y': 'Columns'}
                    )
                    fig_missing.update_layout(height=400)
                    st.plotly_chart(fig_missing, width='stretch')
            
            # Data types summary
            st.subheader("📋 Column Types Summary")
            
            col_types = df_filtered.dtypes.value_counts()
            type_summary = []
            
            for dtype, count in col_types.items():
                type_summary.append({
                    'Data Type': str(dtype),
                    'Column Count': count,
                    'Percentage': f"{(count/len(df_filtered.columns)*100):.1f}%"
                })
            
            st.dataframe(pd.DataFrame(type_summary), width='stretch')
            
        else:
            st.warning("⚠️ Upload data to view insights and summary statistics")

    with tab8:
        st.header("📋 Pivot Tables & Column Analysis")
        
        if df_filtered is not None and not df_filtered.empty:
            # Column selection interface
            st.subheader("📊 Column Analysis Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Available Columns:**")
                
                # Group columns by type for better organization
                numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
                categorical_cols = df_filtered.select_dtypes(include=['object', 'category']).columns.tolist()
                datetime_cols = df_filtered.select_dtypes(include=['datetime64']).columns.tolist()
                
                st.markdown(f"**Numeric Columns ({len(numeric_cols)}):**")
                if numeric_cols:
                    for i, col in enumerate(numeric_cols[:10]):  # Show first 10
                        unique_vals = df_filtered[col].nunique()
                        missing_vals = df_filtered[col].isnull().sum()
                        st.markdown(f"• `{col}` - {unique_vals} unique, {missing_vals} missing")
                    if len(numeric_cols) > 10:
                        st.markdown(f"... and {len(numeric_cols) - 10} more")
                else:
                    st.markdown("None found")
                
                st.markdown(f"**Categorical Columns ({len(categorical_cols)}):**")
                if categorical_cols:
                    for i, col in enumerate(categorical_cols[:10]):  # Show first 10
                        unique_vals = df_filtered[col].nunique()
                        missing_vals = df_filtered[col].isnull().sum()
                        st.markdown(f"• `{col}` - {unique_vals} unique, {missing_vals} missing")
                    if len(categorical_cols) > 10:
                        st.markdown(f"... and {len(categorical_cols) - 10} more")
                else:
                    st.markdown("None found")
                
                if datetime_cols:
                    st.markdown(f"**DateTime Columns ({len(datetime_cols)}):**")
                    for col in datetime_cols[:5]:
                        st.markdown(f"• `{col}`")
            
            with col2:
                st.markdown("**Quick Column Stats:**")
                
                # Dataset shape
                st.metric("📊 Total Columns", len(df_filtered.columns))
                st.metric("📈 Total Rows", len(df_filtered))
                st.metric("🔢 Numeric Columns", len(numeric_cols))
                st.metric("📝 Categorical Columns", len(categorical_cols))
                
                # Data quality metrics
                total_cells = len(df_filtered) * len(df_filtered.columns)
                missing_cells = df_filtered.isnull().sum().sum()
                completeness = ((total_cells - missing_cells) / total_cells * 100) if total_cells > 0 else 0
                st.metric("🎯 Data Completeness", f"{completeness:.1f}%")
            
            # Pivot Table Generator
            st.subheader("📋 Interactive Pivot Table Generator")
            
            if len(df_filtered.columns) >= 2:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # Index (rows)
                    index_options = [None] + list(df_filtered.columns)
                    pivot_index = st.selectbox(
                        "📈 Rows (Index)",
                        options=index_options,
                        format_func=lambda x: "Select column" if x is None else x,
                        help="Column to use for pivot table rows"
                    )
                
                with col2:
                    # Columns
                    columns_options = [None] + list(df_filtered.columns)
                    pivot_columns = st.selectbox(
                        "📊 Columns",
                        options=columns_options,
                        format_func=lambda x: "Select column" if x is None else x,
                        help="Column to use for pivot table columns"
                    )
                
                with col3:
                    # Values (should be numeric)
                    values_options = [None] + numeric_cols
                    pivot_values = st.selectbox(
                        "🔢 Values",
                        options=values_options,
                        format_func=lambda x: "Select column" if x is None else x,
                        help="Numeric column to aggregate in pivot table"
                    )
                
                with col4:
                    # Aggregation function
                    agg_func = st.selectbox(
                        "⚙️ Aggregation",
                        options=['mean', 'sum', 'count', 'median', 'min', 'max', 'std'],
                        help="How to aggregate the values"
                    )
                
                # Generate pivot table if all required fields are selected
                if pivot_index and pivot_values:
                    try:
                        st.subheader(f"📋 Generated Pivot Table")
                        
                        # Create pivot table
                        if pivot_columns:
                            pivot_table = df_filtered.pivot_table(
                                index=pivot_index,
                                columns=pivot_columns,
                                values=pivot_values,
                                aggfunc=agg_func,
                                fill_value=0
                            )
                        else:
                            # Simple groupby if no columns specified
                            pivot_table = df_filtered.groupby(pivot_index)[pivot_values].agg(agg_func).to_frame()
                        
                        # Display pivot table
                        st.dataframe(pivot_table, width='stretch')
                        
                        # Add download option
                        csv = pivot_table.to_csv()
                        st.download_button(
                            label="💾 Download Pivot Table as CSV",
                            data=csv,
                            file_name=f"pivot_table_{pivot_index}_{pivot_values}_{agg_func}.csv",
                            mime="text/csv"
                        )
                        
                        # Visualize pivot table if it's small enough
                        if pivot_table.shape[0] <= 20 and pivot_table.shape[1] <= 10:
                            st.subheader("📈 Pivot Table Visualization")
                            
                            viz_col1, viz_col2 = st.columns(2)
                            
                            with viz_col1:
                                if pivot_columns and len(pivot_table.columns) > 1:
                                    # Heatmap for multi-column pivot
                                    fig_heatmap = px.imshow(
                                        pivot_table.values,
                                        x=pivot_table.columns,
                                        y=pivot_table.index,
                                        color_continuous_scale='RdYlBu_r',
                                        title=f"Heatmap: {pivot_values} by {pivot_index} & {pivot_columns}"
                                    )
                                    st.plotly_chart(fig_heatmap, width='stretch')
                                else:
                                    # Bar chart for single column pivot
                                    fig_bar = px.bar(
                                        x=pivot_table.index,
                                        y=pivot_table.iloc[:, 0] if len(pivot_table.columns) == 1 else pivot_table.sum(axis=1),
                                        title=f"Bar Chart: {agg_func.title()} of {pivot_values} by {pivot_index}"
                                    )
                                    st.plotly_chart(fig_bar, width='stretch')
                            
                            with viz_col2:
                                # Summary statistics
                                st.markdown("**Pivot Table Summary:**")
                                st.markdown(f"• **Shape**: {pivot_table.shape[0]} rows × {pivot_table.shape[1]} columns")
                                st.markdown(f"• **Total Values**: {pivot_table.size:,}")
                                
                                if pivot_table.size > 0:
                                    flat_values = pivot_table.values.flatten()
                                    flat_values = flat_values[~np.isnan(flat_values)]  # Remove NaN values
                                    
                                    if len(flat_values) > 0:
                                        st.markdown(f"• **Min Value**: {flat_values.min():.3f}")
                                        st.markdown(f"• **Max Value**: {flat_values.max():.3f}")
                                        st.markdown(f"• **Mean Value**: {flat_values.mean():.3f}")
                                        st.markdown(f"• **Std Dev**: {flat_values.std():.3f}")
                        else:
                            st.info("📊 Pivot table is too large for visualization. Use the download button to get the data.")
                    
                    except Exception as e:
                        st.error(f"⚠️ Error creating pivot table: {str(e)}")
                        st.info("💡 Try selecting different columns or check for data type compatibility")
            else:
                st.warning("⚠️ Not enough columns available for pivot table creation")
            
            # Column-wise Analysis
            st.subheader("🔍 Individual Column Analysis")
            
            # Column selector for detailed analysis
            analysis_col = st.selectbox(
                "📋 Select Column for Detailed Analysis",
                options=df_filtered.columns,
                help="Choose a column to analyze in detail"
            )
            
            if analysis_col:
                col_data = df_filtered[analysis_col]
                
                analysis_col1, analysis_col2, analysis_col3 = st.columns(3)
                
                with analysis_col1:
                    st.markdown(f"**Column: `{analysis_col}`**")
                    st.markdown(f"**Data Type**: {col_data.dtype}")
                    st.markdown(f"**Unique Values**: {col_data.nunique():,}")
                    st.markdown(f"**Missing Values**: {col_data.isnull().sum():,} ({col_data.isnull().sum()/len(col_data)*100:.1f}%)")
                    st.markdown(f"**Memory Usage**: {col_data.memory_usage(deep=True)} bytes")
                
                with analysis_col2:
                    if pd.api.types.is_numeric_dtype(col_data):
                        st.markdown("**Numeric Statistics:**")
                        col_stats = col_data.describe()
                        for stat_name, stat_value in col_stats.items():
                            st.markdown(f"• **{stat_name.title()}**: {stat_value:.3f}")
                    else:
                        st.markdown("**Categorical Statistics:**")
                        st.markdown(f"• **Most Common**: {col_data.mode().iloc[0] if not col_data.mode().empty else 'N/A'}")
                        st.markdown(f"• **Least Common**: {col_data.value_counts().idxmin() if len(col_data.value_counts()) > 0 else 'N/A'}")
                        value_counts = col_data.value_counts().head(5)
                        st.markdown("**Top 5 Values:**")
                        for value, count in value_counts.items():
                            st.markdown(f"  - {value}: {count} ({count/len(col_data)*100:.1f}%)")
                
                with analysis_col3:
                    # Column visualization
                    st.markdown("**Column Distribution:**")
                    
                    if pd.api.types.is_numeric_dtype(col_data):
                        # Histogram for numeric data
                        fig_hist = px.histogram(
                            x=col_data.dropna(),
                            nbins=30,
                            title=f"Distribution of {analysis_col}"
                        )
                        fig_hist.update_layout(height=300)
                        st.plotly_chart(fig_hist, width='stretch')
                    else:
                        # Bar chart for categorical data
                        value_counts = col_data.value_counts().head(10)
                        if len(value_counts) > 0:
                            fig_bar = px.bar(
                                x=value_counts.values,
                                y=value_counts.index,
                                orientation='h',
                                title=f"Top Values in {analysis_col}"
                            )
                            fig_bar.update_layout(height=300)
                            st.plotly_chart(fig_bar, width='stretch')
        else:
            st.info("📊 Upload data to access pivot table and column analysis features")

    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🌐 **Dashboard URL**: http://localhost:8507")
    with col2:
        st.info(f"🎨 **Color Scheme**: {color_scheme}")
    with col3:
        animation_status = "🎥 Enabled" if enable_animations else "⏹️ Disabled"
        st.info(f"🎬 **Animations**: {animation_status}")

    # Live data monitoring footer (if enabled)
    if st.session_state.auto_refresh_enabled and hasattr(st.session_state, 'data_source'):
        # Add a footer for live updates
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("🔴 Live monitoring active - Dashboard will auto-update when data changes")
            current_time = datetime.now().strftime("%H:%M:%S")
            st.caption(f"Last check: {current_time}")

if __name__ == "__main__":
    main()
