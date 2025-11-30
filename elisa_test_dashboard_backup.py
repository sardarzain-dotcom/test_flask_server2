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

def handle_missing_columns(df, expected_columns, column_mappings):
    """Handle missing columns by creating defaults or suggesting alternatives"""
    handled_columns = []
    suggestions = []
    
    for expected_col in expected_columns:
        if expected_col not in column_mappings:
            # Try to create reasonable defaults
            if expected_col == 'subject_id':
                # Create sequential subject IDs
                df[f'auto_{expected_col}'] = [f'Subject_{i+1}' for i in range(len(df))]
                handled_columns.append(f'auto_{expected_col}')
                suggestions.append(f"Created automatic subject IDs as 'auto_{expected_col}'")
            
            elif expected_col == 'group':
                # Create single group if missing
                df[f'auto_{expected_col}'] = 'Group_1'
                handled_columns.append(f'auto_{expected_col}')
                suggestions.append(f"Created default group as 'auto_{expected_col}'")
            
            elif expected_col == 'timepoint':
                # Create baseline timepoint
                df[f'auto_{expected_col}'] = 'Baseline'
                handled_columns.append(f'auto_{expected_col}')
                suggestions.append(f"Created default timepoint as 'auto_{expected_col}'")
            
            elif expected_col == 'qc_flag':
                # Default to 'Pass' for QC
                df[f'auto_{expected_col}'] = 'Pass'
                handled_columns.append(f'auto_{expected_col}')
                suggestions.append(f"Created default QC flags as 'auto_{expected_col}'")
            
            else:
                suggestions.append(f"Warning: Could not create default for missing column '{expected_col}'")
    
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
    
    # Concentration analysis - needs concentration mapping
    if 'concentration' in column_mappings:
        conc_col = column_mappings['concentration']
        if conc_col in df.columns and pd.api.types.is_numeric_dtype(df[conc_col]):
            capabilities['concentration_analysis'] = True
    
    # Group comparison - needs group and concentration
    if 'group' in column_mappings and 'concentration' in column_mappings:
        group_col = column_mappings['group']
        if group_col in df.columns and df[group_col].nunique() >= 2:
            capabilities['group_comparison'] = True
    
    # Longitudinal analysis - needs timepoint and concentration
    if 'timepoint' in column_mappings and 'concentration' in column_mappings:
        time_col = column_mappings['timepoint']
        if time_col in df.columns and df[time_col].nunique() >= 2:
            capabilities['longitudinal_analysis'] = True
    
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
    
    # Assess column mapping success
    essential_mappings = ['concentration']  # Must have concentration
    recommended_mappings = ['subject_id', 'group', 'timepoint']  # Should have these
    
    essential_mapped = sum(1 for col in essential_mappings if col in mapped_columns)
    recommended_mapped = sum(1 for col in recommended_mappings if col in mapped_columns)
    
    if essential_mapped == 0:
        readiness_score -= 30
        issues.append("No essential columns mapped (concentration required)")
    
    if recommended_mapped < 2:
        readiness_score -= 10
        issues.append(f"Only {recommended_mapped}/3 recommended columns mapped")
    
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

def extract_and_analyze_data(df, file_name):
    """Extract meaningful data from newly imported files and prepare for analysis using column mapping"""
    analysis_results = {
        'original_shape': df.shape,
        'columns': list(df.columns),
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
    
    # Generate recommendations based on data structure
    if len(numeric_cols) > 0:
        analysis_results['recommendations'].append("✅ Numeric data detected - suitable for statistical analysis")
    
    if 'concentration' in analysis_results['mapped_columns']:
        conc_col = analysis_results['mapped_columns']['concentration']
        if conc_col in df.columns:
            conc_stats = df[conc_col].describe()
            analysis_results['concentration_stats'] = conc_stats.to_dict()
            analysis_results['recommendations'].append(f"🧬 Concentration data found in '{conc_col}' - ready for biomarker analysis")
    
    if 'group' in analysis_results['mapped_columns']:
        group_col = analysis_results['mapped_columns']['group']
        if group_col in df.columns:
            unique_groups = df[group_col].unique()
            analysis_results['unique_groups'] = list(unique_groups)
            analysis_results['recommendations'].append(f"👥 {len(unique_groups)} treatment groups detected: {', '.join(unique_groups)}")
    
    if 'timepoint' in analysis_results['mapped_columns']:
        time_col = analysis_results['mapped_columns']['timepoint']
        if time_col in df.columns:
            unique_times = df[time_col].unique()
            analysis_results['unique_timepoints'] = list(unique_times)
            analysis_results['recommendations'].append(f"⏰ {len(unique_times)} timepoints detected - suitable for longitudinal analysis")
    
    # Data preprocessing suggestions
    missing_data = df.isnull().sum()
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
    
    # Initialize session state for data management and adaptive features
    if 'current_df' not in st.session_state:
        # Load default data
        data_file = "elisa_processed_data.csv"
        if os.path.exists(data_file):
            st.session_state.current_df = pd.read_csv(data_file)
            st.session_state.data_source = "elisa_processed_data.csv"
            st.session_state.last_data_hash = hash(str(st.session_state.current_df.values.tobytes()))
        else:
            # Generate sample data if no default file exists
            st.warning("⚠️ Default data file not found. Loading sample data.")
            st.session_state.current_df = generate_sample_elisa_data()
            st.session_state.data_source = "Sample Demo Data"
            st.session_state.last_data_hash = hash(str(st.session_state.current_df.values.tobytes()))
    
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
    
    # Check for data changes and adapt if needed
    current_data_hash = hash(str(st.session_state.current_df.values.tobytes()))
    if hasattr(st.session_state, 'last_data_hash') and current_data_hash != st.session_state.last_data_hash:
        st.session_state.data_update_count += 1
        st.session_state.last_update_time = datetime.now()
        st.session_state.last_data_hash = current_data_hash
        
        # Re-analyze data and update adaptive configuration
        if st.session_state.current_df is not None and not st.session_state.current_df.empty:
            analysis_results = extract_and_analyze_data(st.session_state.current_df, st.session_state.data_source)
            st.session_state.adaptive_config = adapt_dashboard_to_data(st.session_state.current_df, analysis_results)
            st.session_state.data_analysis = analysis_results
    
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
            if hasattr(st.session_state, 'data_analysis') and 'statistical_readiness' in st.session_state.data_analysis:
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
                expected_cols = ['subject_id', 'group', 'biomarker', 'concentration']
                mappings = getattr(st.session_state, 'column_mappings', {})
                
                repaired_df, handled_cols, repair_suggestions = handle_missing_columns(
                    df.copy(), expected_cols, mappings
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
    data_option = st.sidebar.selectbox(
        "🔄 Choose Data Source",
        options=[
            "Current Dataset (elisa_processed_data.csv)",
            "Upload New File (Multi-format)",
            "Load Different Existing File",
            "Sample Demo Data"
        ],
        index=0
    )
    
    # Handle different data loading options
    if data_option == "Upload New File (Multi-format)":
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
                                st.dataframe(new_df.head(3), use_container_width=True)
                                
                            # Intelligent data extraction and analysis
                            analysis_results = extract_and_analyze_data(new_df, uploaded_file.name)
                            
                            # Show column info with intelligent mapping
                            with st.sidebar.expander("📋 Data Analysis Preview", expanded=True):
                                st.write("**📊 Data Overview:**")
                                st.write(f"• Rows: {analysis_results['original_shape'][0]}")
                                st.write(f"• Columns: {analysis_results['original_shape'][1]}")
                                
                                if analysis_results['mapped_columns']:
                                    st.write("**🎯 Detected ELISA Columns:**")
                                    for standard, original in analysis_results['mapped_columns'].items():
                                        st.write(f"• {standard.title()}: `{original}`")
                                
                                st.write("**💡 Analysis Recommendations:**")
                                for rec in analysis_results['recommendations']:
                                    st.write(f"• {rec}")
                                
                                if analysis_results.get('concentration_stats'):
                                    conc_stats = analysis_results['concentration_stats']
                                    st.write(f"**🧬 Concentration Stats:**")
                                    st.write(f"• Mean: {conc_stats.get('mean', 0):.2f}")
                                    st.write(f"• Range: {conc_stats.get('min', 0):.2f} - {conc_stats.get('max', 0):.2f}")
                            
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
                                    
                                    # Intelligent column mapping and structure adaptation
                                    column_mappings, mapping_suggestions = intelligent_column_mapping(
                                        processed_data, getattr(st.session_state, 'column_mappings', {})
                                    )
                                    
                                    # Handle missing essential columns
                                    expected_columns = ['subject_id', 'group', 'biomarker', 'concentration']
                                    enhanced_df, handled_columns, handle_suggestions = handle_missing_columns(
                                        processed_data.copy(), expected_columns, column_mappings
                                    )
                                    
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
                                ', '.join(df_filtered['Group'].unique()) if 'Group' in df_filtered.columns else 'N/A',
                                ', '.join(df_filtered['Marker'].unique()) if 'Marker' in df_filtered.columns else 'N/A'
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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏠 Overview",
        "📊 Concentrations",
        "📈 Longitudinal", 
        "🔬 Statistics",
        "🔬 Quality Control",
        "🌍 3D Analysis",
        "🔬 Data Insights"
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
        st.info("🌐 **Dashboard URL**: http://localhost:5807")
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