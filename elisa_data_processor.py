#!/usr/bin/env python3
"""
ELISA Data Processor
===================
A comprehensive script to process ELISA biomarker data using pandas and JSON.
This script handles data loading, JSON parsing, data transformation, and analysis.
"""

import pandas as pd
import json
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class ELISADataProcessor:
    """
    A class to process and analyze ELISA biomarker data with JSON metadata.
    """
    
    def __init__(self, csv_file_path):
        """
        Initialize the processor with the CSV file path.
        
        Args:
            csv_file_path (str): Path to the ELISA CSV file
        """
        self.csv_file_path = csv_file_path
        self.raw_data = None
        self.processed_data = None
        self.demographics_expanded = None
        self.measurement_metadata_expanded = None
        
    def load_data(self):
        """Load the CSV data into a pandas DataFrame."""
        try:
            print(f"Loading data from: {self.csv_file_path}")
            self.raw_data = pd.read_csv(self.csv_file_path)
            print(f"Data loaded successfully. Shape: {self.raw_data.shape}")
            print(f"Columns: {list(self.raw_data.columns)}")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def parse_json_columns(self):
        """Parse JSON columns (Demographics_JSON and MeasurementMetadata_JSON)."""
        if self.raw_data is None:
            print("No data loaded. Please run load_data() first.")
            return False
        
        try:
            print("Parsing JSON columns...")
            
            # Parse Demographics JSON
            demographics_list = []
            for idx, json_str in enumerate(self.raw_data['Demographics_JSON']):
                try:
                    demo_data = json.loads(json_str)
                    demo_data['row_index'] = idx
                    demographics_list.append(demo_data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing demographics JSON at row {idx}: {e}")
                    demographics_list.append({'row_index': idx, 'age': None, 'sex': None, 'bmi': None})
            
            self.demographics_expanded = pd.DataFrame(demographics_list)
            
            # Parse Measurement Metadata JSON
            metadata_list = []
            for idx, json_str in enumerate(self.raw_data['MeasurementMetadata_JSON']):
                try:
                    meta_data = json.loads(json_str)
                    meta_data['row_index'] = idx
                    metadata_list.append(meta_data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing metadata JSON at row {idx}: {e}")
                    metadata_list.append({'row_index': idx, 'well': None, 'flag': None})
            
            self.measurement_metadata_expanded = pd.DataFrame(metadata_list)
            
            print("JSON parsing completed successfully.")
            print(f"Demographics columns: {list(self.demographics_expanded.columns)}")
            print(f"Metadata columns: {list(self.measurement_metadata_expanded.columns)}")
            return True
            
        except Exception as e:
            print(f"Error parsing JSON columns: {e}")
            return False
    
    def merge_data(self):
        """Merge the main data with expanded JSON data."""
        if self.raw_data is None or self.demographics_expanded is None:
            print("Data not properly loaded or JSON not parsed. Please run previous steps first.")
            return False
        
        try:
            print("Merging data with expanded JSON columns...")
            
            # Add row index to main data for merging
            self.raw_data['row_index'] = range(len(self.raw_data))
            
            # Merge demographics
            self.processed_data = self.raw_data.merge(
                self.demographics_expanded, 
                on='row_index', 
                how='left'
            )
            
            # Merge measurement metadata
            self.processed_data = self.processed_data.merge(
                self.measurement_metadata_expanded, 
                on='row_index', 
                how='left'
            )
            
            # Clean up - remove original JSON columns and row_index
            columns_to_drop = ['Demographics_JSON', 'MeasurementMetadata_JSON', 'row_index']
            self.processed_data = self.processed_data.drop(columns=columns_to_drop)
            
            print(f"Data merged successfully. New shape: {self.processed_data.shape}")
            print(f"New columns: {list(self.processed_data.columns)}")
            return True
            
        except Exception as e:
            print(f"Error merging data: {e}")
            return False
    
    def convert_data_types(self):
        """Convert data types for better analysis."""
        if self.processed_data is None:
            print("No processed data available. Please run previous steps first.")
            return False
        
        try:
            print("Converting data types...")
            
            # Convert datetime columns
            datetime_columns = ['MeasurementTime', 'CollectionDateTime']
            for col in datetime_columns:
                if col in self.processed_data.columns:
                    self.processed_data[col] = pd.to_datetime(self.processed_data[col])
            
            # Convert numeric columns
            numeric_columns = ['RawSignal', 'Concentration', 'age', 'bmi']
            for col in numeric_columns:
                if col in self.processed_data.columns:
                    self.processed_data[col] = pd.to_numeric(self.processed_data[col], errors='coerce')
            
            # Convert categorical columns
            categorical_columns = ['Marker', 'Group', 'sex', 'flag', 'Matrix', 'Units']
            for col in categorical_columns:
                if col in self.processed_data.columns:
                    self.processed_data[col] = self.processed_data[col].astype('category')
            
            print("Data type conversion completed.")
            return True
            
        except Exception as e:
            print(f"Error converting data types: {e}")
            return False
    
    def generate_summary_statistics(self):
        """Generate comprehensive summary statistics."""
        if self.processed_data is None:
            print("No processed data available.")
            return None
        
        print("\n" + "="*50)
        print("DATA SUMMARY STATISTICS")
        print("="*50)
        
        # Basic info
        print(f"Dataset shape: {self.processed_data.shape}")
        print(f"Number of subjects: {self.processed_data['SubjectID'].nunique()}")
        print(f"Number of unique markers: {self.processed_data['Marker'].nunique()}")
        print(f"Markers: {list(self.processed_data['Marker'].unique())}")
        print(f"Study groups: {list(self.processed_data['Group'].unique())}")
        
        # Demographics summary
        print("\nDEMOGRAPHICS SUMMARY:")
        print("-" * 30)
        if 'age' in self.processed_data.columns:
            print(f"Age - Mean: {self.processed_data['age'].mean():.1f}, "
                  f"Std: {self.processed_data['age'].std():.1f}, "
                  f"Range: {self.processed_data['age'].min():.0f}-{self.processed_data['age'].max():.0f}")
        
        if 'sex' in self.processed_data.columns:
            print(f"Sex distribution: {dict(self.processed_data['sex'].value_counts())}")
        
        if 'bmi' in self.processed_data.columns:
            print(f"BMI - Mean: {self.processed_data['bmi'].mean():.1f}, "
                  f"Std: {self.processed_data['bmi'].std():.1f}, "
                  f"Range: {self.processed_data['bmi'].min():.1f}-{self.processed_data['bmi'].max():.1f}")
        
        # Biomarker concentrations by group
        print("\nBIOMARKER CONCENTRATIONS BY GROUP:")
        print("-" * 40)
        concentration_summary = self.processed_data.groupby(['Group', 'Marker', 'NominalTime'])['Concentration'].agg(['mean', 'std', 'count']).round(2)
        print(concentration_summary)
        
        # Quality control summary
        print("\nQUALITY CONTROL SUMMARY:")
        print("-" * 30)
        if 'flag' in self.processed_data.columns:
            print(f"Flag distribution: {dict(self.processed_data['flag'].value_counts())}")
        
        return {
            'shape': self.processed_data.shape,
            'subjects': self.processed_data['SubjectID'].nunique(),
            'markers': list(self.processed_data['Marker'].unique()),
            'groups': list(self.processed_data['Group'].unique()),
            'concentration_summary': concentration_summary
        }
    
    def create_pivot_tables(self):
        """Create pivot tables for different analyses."""
        if self.processed_data is None:
            print("No processed data available.")
            return {}
        
        print("\nCreating pivot tables...")
        
        pivot_tables = {}
        
        # 1. Concentration by Subject and Marker
        pivot_tables['conc_by_subject_marker'] = self.processed_data.pivot_table(
            values='Concentration',
            index=['SubjectID', 'Group'],
            columns=['Marker', 'NominalTime'],
            aggfunc='mean'
        )
        
        # 2. Demographics by Group
        if all(col in self.processed_data.columns for col in ['age', 'sex', 'bmi']):
            pivot_tables['demographics_by_group'] = self.processed_data.drop_duplicates('SubjectID').pivot_table(
                values=['age', 'bmi'],
                index='Group',
                aggfunc=['mean', 'std', 'count']
            )
        
        # 3. Raw Signal vs Concentration
        pivot_tables['signal_vs_conc'] = self.processed_data.pivot_table(
            values=['RawSignal', 'Concentration'],
            index=['Marker', 'Group'],
            columns='NominalTime',
            aggfunc='mean'
        )
        
        print(f"Created {len(pivot_tables)} pivot tables.")
        return pivot_tables
    
    def export_processed_data(self, output_dir="./processed_data"):
        """Export processed data in multiple formats."""
        if self.processed_data is None:
            print("No processed data to export.")
            return False
        
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Export as CSV
            csv_file = output_path / "elisa_processed_data.csv"
            self.processed_data.to_csv(csv_file, index=False)
            print(f"Processed data exported to: {csv_file}")
            
            # Export as Excel with multiple sheets
            excel_file = output_path / "elisa_analysis_workbook.xlsx"
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                self.processed_data.to_excel(writer, sheet_name='ProcessedData', index=False)
                
                # Add pivot tables if they exist
                pivot_tables = self.create_pivot_tables()
                for name, table in pivot_tables.items():
                    table.to_excel(writer, sheet_name=name[:31])  # Excel sheet name limit
            
            print(f"Excel workbook exported to: {excel_file}")
            
            # Export configuration as JSON
            config = {
                'processing_timestamp': datetime.now().isoformat(),
                'original_file': str(self.csv_file_path),
                'processed_shape': self.processed_data.shape,
                'columns': list(self.processed_data.columns),
                'data_types': self.processed_data.dtypes.astype(str).to_dict(),
                'summary_stats': {
                    'subjects': int(self.processed_data['SubjectID'].nunique()),
                    'markers': list(self.processed_data['Marker'].unique()),
                    'groups': list(self.processed_data['Group'].unique()),
                    'time_points': list(self.processed_data['NominalTime'].unique())
                }
            }
            
            config_file = output_path / "processing_config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            print(f"Configuration exported to: {config_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False
    
    def run_complete_analysis(self):
        """Run the complete data processing pipeline."""
        print("Starting complete ELISA data analysis...")
        print("="*60)
        
        steps = [
            ("Loading data", self.load_data),
            ("Parsing JSON columns", self.parse_json_columns),
            ("Merging data", self.merge_data),
            ("Converting data types", self.convert_data_types),
            ("Generating summary statistics", self.generate_summary_statistics),
            ("Exporting processed data", self.export_processed_data)
        ]
        
        for step_name, step_function in steps:
            print(f"\nStep: {step_name}")
            print("-" * 40)
            success = step_function()
            if not success and step_name != "Generating summary statistics":
                print(f"Failed at step: {step_name}")
                return False
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETED SUCCESSFULLY!")
        print("="*60)
        return True


def main():
    """Main function to demonstrate the ELISA data processor."""
    
    # Configuration
    csv_file_path = r"c:\Users\sarda\Downloads\ELISA15_Combined.csv"
    
    # Initialize processor
    processor = ELISADataProcessor(csv_file_path)
    
    # Run complete analysis
    success = processor.run_complete_analysis()
    
    if success:
        print("\nProcessed data preview:")
        print("-" * 30)
        print(processor.processed_data.head())
        print(f"\nColumns in processed data: {list(processor.processed_data.columns)}")
        
        # Show some example JSON parsing results
        if processor.demographics_expanded is not None:
            print(f"\nExpanded demographics preview:")
            print(processor.demographics_expanded.head())
        
        if processor.measurement_metadata_expanded is not None:
            print(f"\nExpanded measurement metadata preview:")
            print(processor.measurement_metadata_expanded.head())
    
    return processor


if __name__ == "__main__":
    # Run the main analysis
    elisa_processor = main()