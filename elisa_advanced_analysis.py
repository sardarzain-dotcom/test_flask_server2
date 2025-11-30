#!/usr/bin/env python3
"""
Advanced ELISA Data Analysis
===========================
Comprehensive statistical analysis, visualizations, and machine learning
for ELISA biomarker data with pandas and advanced analytics.
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
from pathlib import Path
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings('ignore')

class AdvancedELISAAnalyzer:
    """
    Advanced analytics class for ELISA biomarker data
    """
    
    def __init__(self, processed_data_file, config_file):
        """Initialize with processed data and configuration"""
        self.processed_data_file = processed_data_file
        self.config_file = config_file
        self.data = None
        self.config = None
        self.results = {}
        
    def load_data(self):
        """Load processed data and configuration"""
        print("Loading processed data and configuration...")
        
        # Load processed data
        self.data = pd.read_csv(self.processed_data_file)
        
        # Load configuration
        with open(self.config_file, 'r') as f:
            self.config = json.load(f)
            
        print(f"✓ Data loaded: {self.data.shape}")
        print(f"✓ Configuration loaded with {len(self.config)} sections")
        
        # Convert datetime columns
        datetime_cols = ['MeasurementTime', 'CollectionDateTime']
        for col in datetime_cols:
            if col in self.data.columns:
                self.data[col] = pd.to_datetime(self.data[col])
        
        return True
    
    def statistical_analysis(self):
        """Comprehensive statistical analysis"""
        print("\n" + "="*60)
        print("STATISTICAL ANALYSIS")
        print("="*60)
        
        # 1. Descriptive Statistics by Group
        print("\n1. DESCRIPTIVE STATISTICS BY GROUP")
        print("-" * 50)
        
        desc_stats = self.data.groupby(['Group', 'Marker', 'NominalTime'])['Concentration'].agg([
            'count', 'mean', 'std', 'min', 'max', 'median',
            lambda x: np.percentile(x, 25),  # Q1
            lambda x: np.percentile(x, 75)   # Q3
        ]).round(3)
        
        desc_stats.columns = ['Count', 'Mean', 'Std', 'Min', 'Max', 'Median', 'Q1', 'Q3']
        print(desc_stats)
        
        # 2. Statistical Tests
        print("\n2. STATISTICAL TESTS")
        print("-" * 50)
        
        # T-tests between groups for each biomarker and timepoint
        stat_results = {}
        
        for marker in self.data['Marker'].unique():
            stat_results[marker] = {}
            for timepoint in self.data['NominalTime'].unique():
                # Get data for each group
                active_data = self.data[
                    (self.data['Marker'] == marker) & 
                    (self.data['NominalTime'] == timepoint) & 
                    (self.data['Group'] == 'Active')
                ]['Concentration']
                
                placebo_data = self.data[
                    (self.data['Marker'] == marker) & 
                    (self.data['NominalTime'] == timepoint) & 
                    (self.data['Group'] == 'Placebo')
                ]['Concentration']
                
                # Perform t-test
                t_stat, p_value = stats.ttest_ind(active_data, placebo_data)
                
                # Effect size (Cohen's d)
                pooled_std = np.sqrt(((len(active_data)-1)*active_data.var() + 
                                    (len(placebo_data)-1)*placebo_data.var()) / 
                                   (len(active_data) + len(placebo_data) - 2))
                cohens_d = (active_data.mean() - placebo_data.mean()) / pooled_std
                
                stat_results[marker][timepoint] = {
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'cohens_d': cohens_d,
                    'significant': p_value < 0.05
                }
                
                print(f"{marker} at {timepoint}:")
                print(f"  T-statistic: {t_stat:.3f}")
                print(f"  P-value: {p_value:.3f}")
                print(f"  Cohen's d: {cohens_d:.3f}")
                print(f"  Significant: {'Yes' if p_value < 0.05 else 'No'}")
                print()
        
        self.results['statistical_tests'] = stat_results
        self.results['descriptive_stats'] = desc_stats
        
        # 3. Correlation Analysis
        print("3. CORRELATION ANALYSIS")
        print("-" * 50)
        
        # Create correlation matrix for numeric variables
        numeric_cols = ['Concentration', 'RawSignal', 'age', 'bmi']
        corr_matrix = self.data[numeric_cols].corr()
        print("Correlation Matrix:")
        print(corr_matrix.round(3))
        
        self.results['correlations'] = corr_matrix
        
        return True
    
    def longitudinal_analysis(self):
        """Analyze changes over time"""
        print("\n4. LONGITUDINAL ANALYSIS")
        print("-" * 50)
        
        # Calculate individual subject changes
        baseline_data = self.data[self.data['NominalTime'] == 'Baseline']
        week4_data = self.data[self.data['NominalTime'] == 'Week 4']
        
        # Merge to calculate changes
        changes = week4_data.merge(
            baseline_data[['SubjectID', 'Marker', 'Concentration', 'Group']], 
            on=['SubjectID', 'Marker', 'Group'], 
            suffixes=('_week4', '_baseline')
        )
        changes['Absolute_Change'] = changes['Concentration_week4'] - changes['Concentration_baseline']
        changes['Percent_Change'] = (changes['Absolute_Change'] / changes['Concentration_baseline']) * 100
        
        # Summary of changes by group and marker
        change_summary = changes.groupby(['Group', 'Marker']).agg({
            'Absolute_Change': ['mean', 'std', 'min', 'max'],
            'Percent_Change': ['mean', 'std', 'min', 'max']
        }).round(2)
        
        print("Changes from Baseline to Week 4:")
        print(change_summary)
        
        # Statistical test for changes
        print("\nStatistical Tests for Changes:")
        for marker in changes['Marker'].unique():
            active_changes = changes[
                (changes['Marker'] == marker) & (changes['Group'] == 'Active')
            ]['Absolute_Change']
            
            placebo_changes = changes[
                (changes['Marker'] == marker) & (changes['Group'] == 'Placebo')
            ]['Absolute_Change']
            
            t_stat, p_value = stats.ttest_ind(active_changes, placebo_changes)
            print(f"{marker} - Change comparison (Active vs Placebo):")
            print(f"  T-statistic: {t_stat:.3f}, P-value: {p_value:.3f}")
        
        self.results['longitudinal_changes'] = changes
        self.results['change_summary'] = change_summary
        
        return True
    
    def demographic_analysis(self):
        """Analyze demographic factors"""
        print("\n5. DEMOGRAPHIC ANALYSIS")
        print("-" * 50)
        
        # Age group analysis
        self.data['Age_Group'] = pd.cut(self.data['age'], 
                                       bins=[0, 55, 65, 100], 
                                       labels=['<55', '55-65', '>65'])
        
        # BMI categories
        self.data['BMI_Category'] = pd.cut(self.data['bmi'], 
                                          bins=[0, 25, 30, 100], 
                                          labels=['Normal', 'Overweight', 'Obese'])
        
        # Analysis by demographics
        demo_analysis = self.data.groupby(['Age_Group', 'BMI_Category', 'Marker'])['Concentration'].agg([
            'count', 'mean', 'std'
        ]).round(2)
        
        print("Biomarker concentrations by demographics:")
        print(demo_analysis)
        
        # Correlation with demographics
        print("\nCorrelations with demographics:")
        for marker in self.data['Marker'].unique():
            marker_data = self.data[self.data['Marker'] == marker]
            age_corr = marker_data['Concentration'].corr(marker_data['age'])
            bmi_corr = marker_data['Concentration'].corr(marker_data['bmi'])
            print(f"{marker}: Age correlation = {age_corr:.3f}, BMI correlation = {bmi_corr:.3f}")
        
        self.results['demographic_analysis'] = demo_analysis
        
        return True
    
    def machine_learning_analysis(self):
        """Apply machine learning techniques"""
        print("\n6. MACHINE LEARNING ANALYSIS")
        print("-" * 50)
        
        # Prepare data for ML
        ml_data = self.data.pivot_table(
            values='Concentration',
            index=['SubjectID', 'Group', 'age', 'sex', 'bmi'],
            columns=['Marker', 'NominalTime'],
            aggfunc='mean'
        ).reset_index()
        
        # Flatten column names
        ml_data.columns = ['_'.join(col).strip() if col[1] else col[0] for col in ml_data.columns.values]
        ml_data = ml_data.dropna()
        
        print(f"ML dataset shape: {ml_data.shape}")
        
        # 1. Principal Component Analysis
        print("\n6.1 PRINCIPAL COMPONENT ANALYSIS")
        print("-" * 30)
        
        # Select numeric features for PCA
        feature_cols = [col for col in ml_data.columns if 'IL-6' in col or 'CRP' in col or col in ['age', 'bmi']]
        X = ml_data[feature_cols]
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Apply PCA
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        
        print(f"PCA explained variance ratio: {pca.explained_variance_ratio_}")
        print(f"Total variance explained: {sum(pca.explained_variance_ratio_):.3f}")
        
        # Add PCA results to dataframe
        ml_data['PC1'] = X_pca[:, 0]
        ml_data['PC2'] = X_pca[:, 1]
        
        # 2. Clustering Analysis
        print("\n6.2 K-MEANS CLUSTERING")
        print("-" * 30)
        
        # Apply K-means clustering
        kmeans = KMeans(n_clusters=2, random_state=42)
        ml_data['Cluster'] = kmeans.fit_predict(X_scaled)
        
        # Analyze clusters
        cluster_analysis = ml_data.groupby('Cluster').agg({
            'age': 'mean',
            'bmi': 'mean',
            'Group_': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Unknown'
        })
        
        print("Cluster characteristics:")
        print(cluster_analysis)
        
        # 3. Classification Analysis
        print("\n6.3 CLASSIFICATION ANALYSIS")
        print("-" * 30)
        
        # Prepare for classification (predict Group)
        y = ml_data['Group_'].map({'Active': 1, 'Placebo': 0})
        X_class = X_scaled
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_class, y, test_size=0.3, random_state=42, stratify=y
        )
        
        # Train Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        
        # Predictions
        y_pred = rf.predict(X_test)
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("Feature importance for group classification:")
        print(feature_importance)
        
        print(f"\nClassification Accuracy: {rf.score(X_test, y_test):.3f}")
        
        self.results['ml_analysis'] = {
            'pca_variance': pca.explained_variance_ratio_.tolist(),
            'cluster_analysis': cluster_analysis,
            'feature_importance': feature_importance,
            'classification_accuracy': rf.score(X_test, y_test)
        }
        
        return ml_data
    
    def create_visualizations(self, ml_data):
        """Create comprehensive visualizations"""
        print("\n7. CREATING VISUALIZATIONS")
        print("-" * 50)
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create output directory for plots
        plot_dir = Path("elisa_plots")
        plot_dir.mkdir(exist_ok=True)
        
        # 1. Biomarker Distribution by Group
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Biomarker Distributions by Group and Time', fontsize=16)
        
        markers = ['IL-6', 'CRP']
        timepoints = ['Baseline', 'Week 4']
        
        for i, marker in enumerate(markers):
            for j, timepoint in enumerate(timepoints):
                ax = axes[i, j]
                subset = self.data[(self.data['Marker'] == marker) & 
                                 (self.data['NominalTime'] == timepoint)]
                
                sns.boxplot(data=subset, x='Group', y='Concentration', ax=ax)
                ax.set_title(f'{marker} - {timepoint}')
                ax.set_ylabel('Concentration')
        
        plt.tight_layout()
        plt.savefig(plot_dir / 'biomarker_distributions.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Longitudinal Changes
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        for i, marker in enumerate(markers):
            changes_data = self.results['longitudinal_changes']
            marker_changes = changes_data[changes_data['Marker'] == marker]
            
            sns.scatterplot(data=marker_changes, 
                          x='Concentration_baseline', 
                          y='Concentration_week4', 
                          hue='Group', 
                          ax=axes[i])
            
            # Add diagonal line
            min_val = min(marker_changes['Concentration_baseline'].min(), 
                         marker_changes['Concentration_week4'].min())
            max_val = max(marker_changes['Concentration_baseline'].max(), 
                         marker_changes['Concentration_week4'].max())
            axes[i].plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5)
            
            axes[i].set_title(f'{marker} - Baseline vs Week 4')
            axes[i].set_xlabel('Baseline Concentration')
            axes[i].set_ylabel('Week 4 Concentration')
        
        plt.tight_layout()
        plt.savefig(plot_dir / 'longitudinal_changes.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. PCA Visualization
        plt.figure(figsize=(10, 8))
        scatter = plt.scatter(ml_data['PC1'], ml_data['PC2'], 
                            c=ml_data['Group_'].map({'Active': 1, 'Placebo': 0}), 
                            cmap='viridis', alpha=0.7)
        plt.xlabel(f'PC1 ({self.results["ml_analysis"]["pca_variance"][0]:.2%} variance)')
        plt.ylabel(f'PC2 ({self.results["ml_analysis"]["pca_variance"][1]:.2%} variance)')
        plt.title('Principal Component Analysis - Group Separation')
        plt.colorbar(scatter, label='Group (0=Placebo, 1=Active)')
        plt.savefig(plot_dir / 'pca_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. Correlation Heatmap
        plt.figure(figsize=(10, 8))
        mask = np.triu(np.ones_like(self.results['correlations'], dtype=bool))
        sns.heatmap(self.results['correlations'], 
                   mask=mask, 
                   annot=True, 
                   cmap='coolwarm', 
                   center=0,
                   square=True)
        plt.title('Correlation Matrix - Numeric Variables')
        plt.tight_layout()
        plt.savefig(plot_dir / 'correlation_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 5. Demographics Analysis
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Age distribution by group
        sns.histplot(data=self.data.drop_duplicates('SubjectID'), 
                    x='age', hue='Group', kde=True, ax=axes[0,0])
        axes[0,0].set_title('Age Distribution by Group')
        
        # BMI distribution by group
        sns.histplot(data=self.data.drop_duplicates('SubjectID'), 
                    x='bmi', hue='Group', kde=True, ax=axes[0,1])
        axes[0,1].set_title('BMI Distribution by Group')
        
        # Sex distribution
        sex_counts = self.data.drop_duplicates('SubjectID').groupby(['Group', 'sex']).size().unstack()
        sex_counts.plot(kind='bar', ax=axes[1,0])
        axes[1,0].set_title('Sex Distribution by Group')
        axes[1,0].tick_params(axis='x', rotation=0)
        
        # Biomarker vs Age
        sns.scatterplot(data=self.data, x='age', y='Concentration', 
                       hue='Marker', style='Group', ax=axes[1,1])
        axes[1,1].set_title('Biomarker Concentration vs Age')
        
        plt.tight_layout()
        plt.savefig(plot_dir / 'demographics_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Visualizations saved to: {plot_dir}")
        return True
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("\n8. GENERATING COMPREHENSIVE REPORT")
        print("-" * 50)
        
        # Create detailed results summary
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_summary': {
                'total_subjects': int(self.data['SubjectID'].nunique()),
                'total_measurements': len(self.data),
                'biomarkers': list(self.data['Marker'].unique()),
                'groups': list(self.data['Group'].unique())
            },
            'statistical_analysis': {
                'descriptive_statistics': self.results['descriptive_stats'].to_dict(),
                'statistical_tests': self.results['statistical_tests'],
                'correlations': self.results['correlations'].to_dict()
            },
            'longitudinal_analysis': {
                'change_summary': self.results['change_summary'].to_dict()
            },
            'machine_learning': self.results['ml_analysis'],
            'key_findings': [
                "Statistical analysis completed with group comparisons",
                "Longitudinal changes analyzed for both biomarkers",
                "Demographics show age and BMI correlations",
                "Machine learning reveals group separation patterns",
                "Comprehensive visualizations generated"
            ],
            'files_generated': [
                'elisa_advanced_results.json',
                'elisa_plots/biomarker_distributions.png',
                'elisa_plots/longitudinal_changes.png',
                'elisa_plots/pca_analysis.png',
                'elisa_plots/correlation_heatmap.png',
                'elisa_plots/demographics_analysis.png'
            ]
        }
        
        # Save comprehensive results
        results_file = 'elisa_advanced_results.json'
        with open(results_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✓ Advanced analysis report saved to: {results_file}")
        
        # Print summary
        print(f"\n" + "="*60)
        print("ADVANCED ANALYSIS COMPLETED!")
        print("="*60)
        print(f"📊 Statistical tests performed for {len(self.data['Marker'].unique())} biomarkers")
        print(f"📈 Longitudinal analysis with {len(self.results['longitudinal_changes'])} subject changes")
        print(f"🧬 Machine learning analysis with PCA and clustering")
        print(f"📱 {len(report['files_generated'])} visualization files created")
        print(f"📋 Comprehensive report generated: {results_file}")
        
        return report

def main():
    """Main function to run advanced analysis"""
    print("="*60)
    print("ADVANCED ELISA DATA ANALYSIS")
    print("="*60)
    
    # Initialize analyzer
    processed_data_file = r"c:\Users\sarda\Git\test_flask_server2\elisa_processed_data.csv"
    config_file = r"c:\Users\sarda\Git\test_flask_server2\elisa_configuration.json"
    
    analyzer = AdvancedELISAAnalyzer(processed_data_file, config_file)
    
    # Run complete analysis pipeline
    try:
        # Load data
        analyzer.load_data()
        
        # Statistical analysis
        analyzer.statistical_analysis()
        
        # Longitudinal analysis
        analyzer.longitudinal_analysis()
        
        # Demographic analysis  
        analyzer.demographic_analysis()
        
        # Machine learning analysis
        ml_data = analyzer.machine_learning_analysis()
        
        # Create visualizations
        analyzer.create_visualizations(ml_data)
        
        # Generate final report
        report = analyzer.generate_report()
        
        print(f"\n🎉 Advanced analysis pipeline completed successfully!")
        return analyzer, report
        
    except Exception as e:
        print(f"❌ Error in analysis pipeline: {e}")
        return None, None

if __name__ == "__main__":
    analyzer, report = main()