#!/usr/bin/env python3
"""
Complete ELISA Data Processing with Pandas and JSON
=================================================
Processes ELISA biomarker data, expands JSON columns, and creates comprehensive analysis
"""

import pandas as pd
import json
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def main():
    print("="*60)
    print("ELISA DATA PROCESSOR - PANDAS & JSON CONFIGURATION")
    print("="*60)

    # Step 1: Load the CSV data
    csv_file_path = r"c:\Users\sarda\Downloads\ELISA15_Combined.csv"
    print(f"\n1. Loading data from: {csv_file_path}")

    try:
        raw_data = pd.read_csv(csv_file_path)
        print(f"SUCCESS: Data loaded. Shape: {raw_data.shape}")
        print(f"SUCCESS: Columns: {len(raw_data.columns)} total")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    # Step 2: Parse JSON columns
    print(f"\n2. Parsing JSON columns...")

    # Parse Demographics JSON
    demographics_list = []
    for idx, json_str in enumerate(raw_data['Demographics_JSON']):
        try:
            demo_data = json.loads(json_str)
            demo_data['row_index'] = idx
            demographics_list.append(demo_data)
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing demographics JSON at row {idx}")
            demographics_list.append({'row_index': idx, 'age': None, 'sex': None, 'bmi': None})

    demographics_expanded = pd.DataFrame(demographics_list)

    # Parse Measurement Metadata JSON
    metadata_list = []
    for idx, json_str in enumerate(raw_data['MeasurementMetadata_JSON']):
        try:
            meta_data = json.loads(json_str)
            meta_data['row_index'] = idx
            metadata_list.append(meta_data)
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing metadata JSON at row {idx}")
            metadata_list.append({'row_index': idx, 'well': None, 'flag': None})

    measurement_metadata_expanded = pd.DataFrame(metadata_list)

    print(f"SUCCESS: Demographics expanded: {demographics_expanded.shape}")
    print(f"SUCCESS: Metadata expanded: {measurement_metadata_expanded.shape}")

    # Step 3: Merge all data
    print(f"\n3. Merging data...")

    # Add row index to main data for merging
    raw_data['row_index'] = range(len(raw_data))

    # Merge demographics
    processed_data = raw_data.merge(demographics_expanded, on='row_index', how='left')

    # Merge measurement metadata
    processed_data = processed_data.merge(measurement_metadata_expanded, on='row_index', how='left')

    # Clean up - remove original JSON columns and row_index
    columns_to_drop = ['Demographics_JSON', 'MeasurementMetadata_JSON', 'row_index']
    processed_data = processed_data.drop(columns=columns_to_drop)

    print(f"SUCCESS: Data merged. Final shape: {processed_data.shape}")
    print(f"SUCCESS: Final columns: {len(processed_data.columns)} total")

    # Step 4: Data type conversions
    print(f"\n4. Converting data types...")

    # Convert datetime columns
    datetime_columns = ['MeasurementTime', 'CollectionDateTime']
    for col in datetime_columns:
        if col in processed_data.columns:
            processed_data[col] = pd.to_datetime(processed_data[col])

    # Convert numeric columns
    numeric_columns = ['RawSignal', 'Concentration', 'age', 'bmi']
    for col in numeric_columns:
        if col in processed_data.columns:
            processed_data[col] = pd.to_numeric(processed_data[col], errors='coerce')

    print("SUCCESS: Data types converted")

    # Step 5: Summary Statistics
    print(f"\n5. SUMMARY STATISTICS")
    print("-" * 40)
    print(f"Dataset shape: {processed_data.shape}")
    print(f"Number of subjects: {processed_data['SubjectID'].nunique()}")
    print(f"Number of unique markers: {processed_data['Marker'].nunique()}")
    print(f"Markers: {list(processed_data['Marker'].unique())}")
    print(f"Study groups: {list(processed_data['Group'].unique())}")
    print(f"Time points: {list(processed_data['NominalTime'].unique())}")

    # Demographics summary
    print(f"\nDEMOGRAPHICS SUMMARY:")
    print(f"Age - Mean: {processed_data['age'].mean():.1f}, Std: {processed_data['age'].std():.1f}")
    print(f"Sex distribution: {dict(processed_data['sex'].value_counts())}")
    print(f"BMI - Mean: {processed_data['bmi'].mean():.1f}, Std: {processed_data['bmi'].std():.1f}")

    # Step 6: Advanced Analysis - Pivot Tables
    print("="*60)
    print("ADVANCED ANALYSIS - PIVOT TABLES & EXPORTS")
    print("="*60)

    # 1. Concentration by Subject and Marker
    print("\n1. PIVOT TABLE: Concentration by Subject and Marker")
    print("-" * 50)
    pivot_conc_subject = processed_data.pivot_table(
        values='Concentration',
        index=['SubjectID', 'Group'],
        columns=['Marker', 'NominalTime'],
        aggfunc='mean'
    )
    print(pivot_conc_subject.head(10))

    # 2. Demographics by Group
    print("\n2. PIVOT TABLE: Demographics by Group")
    print("-" * 50)
    demographics_by_group = processed_data.drop_duplicates('SubjectID').pivot_table(
        values=['age', 'bmi'],
        index='Group',
        aggfunc=['mean', 'std', 'count']
    )
    print(demographics_by_group)

    # 3. Biomarker changes from Baseline to Week 4
    print("\n3. BIOMARKER CHANGES (Baseline to Week 4)")
    print("-" * 50)

    # Reshape data to calculate changes
    baseline_data = processed_data[processed_data['NominalTime'] == 'Baseline'].set_index(['SubjectID', 'Marker'])['Concentration']
    week4_data = processed_data[processed_data['NominalTime'] == 'Week 4'].set_index(['SubjectID', 'Marker'])['Concentration']

    changes = week4_data - baseline_data
    changes_df = changes.reset_index()
    changes_df['Change'] = changes_df[0]
    changes_df = changes_df.drop(columns=[0])

    # Merge with group information
    subject_groups = processed_data[['SubjectID', 'Group']].drop_duplicates().set_index('SubjectID')
    changes_df = changes_df.merge(subject_groups, left_on='SubjectID', right_index=True)

    print("Changes in biomarker concentrations (Week 4 - Baseline):")
    change_summary = changes_df.groupby(['Group', 'Marker'])['Change'].agg(['mean', 'std', 'count']).round(2)
    print(change_summary)

    # Step 7: Save processed data
    print("\n4. SAVING PROCESSED DATA")
    print("-" * 50)

    output_file = r"c:\Users\sarda\Git\test_flask_server2\elisa_processed_data.csv"
    processed_data.to_csv(output_file, index=False)
    print(f"Processed data saved to: {output_file}")

    # Save pivot tables
    pivot_file = r"c:\Users\sarda\Git\test_flask_server2\elisa_pivot_tables.csv"
    pivot_conc_subject.to_csv(pivot_file)
    print(f"Pivot table saved to: {pivot_file}")

    # Create configuration JSON
    config = {
        'processing_timestamp': datetime.now().isoformat(),
        'original_file': csv_file_path,
        'output_file': output_file,
        'processed_shape': processed_data.shape,
        'columns': list(processed_data.columns),
        'summary_stats': {
            'subjects': int(processed_data['SubjectID'].nunique()),
            'markers': list(processed_data['Marker'].unique()),
            'groups': list(processed_data['Group'].unique()),
            'time_points': list(processed_data['NominalTime'].unique()),
            'demographics': {
                'age_mean': float(processed_data['age'].mean()),
                'age_std': float(processed_data['age'].std()),
                'bmi_mean': float(processed_data['bmi'].mean()),
                'bmi_std': float(processed_data['bmi'].std()),
                'sex_distribution': {k: int(v) for k, v in processed_data['sex'].value_counts().items()}
            }
        },
        'biomarker_changes': {
            'active_group': {
                'IL-6_change_mean': float(change_summary.loc[('Active', 'IL-6'), 'mean']),
                'CRP_change_mean': float(change_summary.loc[('Active', 'CRP'), 'mean'])
            },
            'placebo_group': {
                'IL-6_change_mean': float(change_summary.loc[('Placebo', 'IL-6'), 'mean']),
                'CRP_change_mean': float(change_summary.loc[('Placebo', 'CRP'), 'mean'])
            }
        }
    }

    config_file = r"c:\Users\sarda\Git\test_flask_server2\elisa_processing_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, default=str)
    print(f"Configuration saved to: {config_file}")

    print("\n" + "="*60)
    print("DATA PROCESSING COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("SUMMARY:")
    print(f"- Original data: {raw_data.shape[0]} rows, {raw_data.shape[1]} columns")
    print(f"- Processed data: {processed_data.shape[0]} rows, {processed_data.shape[1]} columns")
    print(f"- JSON columns expanded: Demographics and Metadata")
    print(f"- Subjects: {processed_data['SubjectID'].nunique()}")
    print(f"- Biomarkers: {', '.join(processed_data['Marker'].unique())}")
    print(f"- Study groups: {', '.join(processed_data['Group'].unique())}")
    print(f"- Files created:")
    print(f"  * elisa_processed_data.csv")
    print(f"  * elisa_pivot_tables.csv")
    print(f"  * elisa_processing_config.json")
    
    print(f"\nSAMPLE PROCESSED DATA:")
    print("-" * 40)
    print(processed_data[['SubjectID', 'Marker', 'Concentration', 'Group', 'age', 'sex', 'bmi', 'well', 'flag']].head(8))
    
    return True

if __name__ == "__main__":
    main()