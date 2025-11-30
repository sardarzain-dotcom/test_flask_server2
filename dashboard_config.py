#!/usr/bin/env python3
"""
🧬 ELISA Enhanced Dashboard Configuration
========================================
Version: 2.0.0
Date: November 27, 2025
Author: GitHub Copilot Assistant
"""

# Dashboard Configuration
DASHBOARD_CONFIG = {
    "version": "2.0.0",
    "title": "🧬 ELISA Biomarker Analysis Dashboard",
    "subtitle": "📊 Complete Analysis with Advanced Visualizations",
    
    # File Configuration
    "main_file": "elisa_test_dashboard.py",
    "backup_file": "elisa_enhanced_dashboard_20251127_135304.py",
    "data_file": "elisa_processed_data.csv",
    "documentation": "ELISA_DASHBOARD_FEATURES.md",
    
    # Server Configuration
    "default_port": 8507,
    "fallback_ports": [8508, 8509, 8510],
    "host": "localhost",
    "network_host": "192.168.2.29",
    
    # Feature Flags
    "features": {
        "statistical_analysis": True,
        "advanced_stats": True,
        "three_d_analysis": True,
        "animation_support": True,
        "background_customization": True,
        "color_schemes": True,
        "data_management": True,
        "export_functionality": True,
        "quality_control": True,
        "longitudinal_analysis": True
    },
    
    # Animation Configuration
    "animation": {
        "enabled_by_default": False,
        "default_speed": 1000,
        "speed_range": [500, 3000],
        "default_transition": "linear",
        "available_transitions": [
            "linear", "quad", "cubic", "sin", 
            "exp", "circle", "elastic", "back", "bounce"
        ],
        "auto_play": True,
        "show_controls": True
    },
    
    # Statistical Analysis Configuration
    "statistics": {
        "default_alpha": 0.05,
        "alpha_range": [0.001, 0.1],
        "available_methods": [
            "Group Comparisons",
            "ANOVA Analysis", 
            "Non-parametric Tests",
            "Normality & Assumptions",
            "Effect Size Analysis",
            "Correlation Analysis",
            "All Methods"
        ],
        "correlation_methods": ["Pearson", "Spearman", "Kendall"]
    },
    
    # Color Schemes
    "color_schemes": [
        "Default (Plotly)",
        "Set1", "Set2", "Dark2", "Paired",
        "Pastel1", "Pastel2", "Viridis", "Plasma",
        "Custom"
    ],
    
    # Background Themes
    "background_themes": {
        "available": ["Default", "Dark", "Light", "Colorful", "Custom"],
        "presets": {
            "ocean": {"bg": "#0066cc", "sidebar": "#004499", "text": "#ffffff"},
            "forest": {"bg": "#228b22", "sidebar": "#006400", "text": "#ffffff"},
            "sunset": {"bg": "#ff7f50", "sidebar": "#ff6347", "text": "#ffffff"},
            "night": {"bg": "#191970", "sidebar": "#0f0f23", "text": "#ffffff"}
        }
    },
    
    # 3D Analysis Configuration
    "three_d_analysis": {
        "available_types": [
            "3D Scatter Plot",
            "3D Surface Plot", 
            "3D Biomarker Space",
            "3D Time Series",
            "3D Correlation Volume",
            "3D Statistical Distribution"
        ],
        "camera_angles": ["Default", "Top View", "Side View", "Isometric", "Custom"],
        "plot_styles": ["Default", "Dark", "Presentation", "Scientific"]
    },
    
    # Data Processing
    "data_processing": {
        "supported_formats": [".csv", ".xlsx", ".xls"],
        "max_file_size": "200MB",
        "auto_validation": True,
        "sample_data_generation": True
    },
    
    # Performance Settings
    "performance": {
        "max_data_points": 10000,
        "animation_threshold": 1000,
        "memory_optimization": True,
        "session_state": True
    }
}

# Installation Requirements
REQUIREMENTS = [
    "streamlit>=1.51.0",
    "pandas>=2.0.0", 
    "plotly>=5.0.0",
    "scipy>=1.9.0",
    "numpy>=1.23.0",
    "openpyxl>=3.0.0",
    "xlsxwriter>=3.0.0"
]

# Usage Instructions
USAGE_INSTRUCTIONS = """
🚀 Quick Start:
1. Run: Launch_Enhanced_ELISA_Dashboard.bat
2. Open: http://localhost:8507
3. Upload your ELISA data or use sample data
4. Explore all 6 analysis tabs
5. Enable animations for dynamic visualizations

📊 Key Features:
- Statistical Analysis (6 method categories)
- 3D Interactive Visualizations
- Animation Support (9 transition styles)  
- Background Customization (5 themes + custom)
- Color Schemes (10+ options)
- Data Export (CSV/Excel)
"""

if __name__ == "__main__":
    print("🧬 ELISA Enhanced Dashboard Configuration")
    print("=" * 50)
    print(f"Version: {DASHBOARD_CONFIG['version']}")
    print(f"Main File: {DASHBOARD_CONFIG['main_file']}")
    print(f"Default Port: {DASHBOARD_CONFIG['default_port']}")
    print(f"Features Enabled: {sum(DASHBOARD_CONFIG['features'].values())}")
    print("\n📋 Requirements:")
    for req in REQUIREMENTS:
        print(f"  - {req}")
    print("\n" + USAGE_INSTRUCTIONS)