import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
from scipy import stats
from scipy.stats import entropy

# Page config
st.set_page_config(
    page_title="Data Visualization Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin: 1rem 0;
    }
    .viz-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .metric-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-title">📊 Data Visualization Dashboard</h1>', unsafe_allow_html=True)

# Sidebar for data source selection
st.sidebar.header("📥 Data Source")
data_source = st.sidebar.selectbox(
    "Choose data source:",
    ["Sample Sales Data", "Stock Market Data", "Weather Data", "Upload CSV", "Generate Random Data"]
)

# Function to generate sample data
@st.cache_data
def generate_sales_data():
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    products = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
    regions = ['North', 'South', 'East', 'West', 'Central']
    
    data = []
    for date in dates[:365]:  # One year of data
        for _ in range(np.random.randint(1, 10)):  # Random number of sales per day
            data.append({
                'Date': date,
                'Product': np.random.choice(products),
                'Region': np.random.choice(regions),
                'Sales': np.random.randint(100, 1000),
                'Quantity': np.random.randint(1, 20),
                'Discount': np.random.uniform(0, 0.3)
            })
    
    df = pd.DataFrame(data)
    df['Revenue'] = df['Sales'] * df['Quantity'] * (1 - df['Discount'])
    return df

@st.cache_data
def generate_stock_data():
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=252, freq='D')  # Trading days
    stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    data = []
    base_prices = {'AAPL': 150, 'GOOGL': 2800, 'MSFT': 300, 'AMZN': 3200, 'TSLA': 800}
    
    for stock in stocks:
        price = base_prices[stock]
        for date in dates:
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            price = price * (1 + change)
            volume = np.random.randint(1000000, 50000000)
            
            data.append({
                'Date': date,
                'Stock': stock,
                'Price': round(price, 2),
                'Volume': volume,
                'Change': round(change * 100, 2)
            })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_weather_data():
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
    cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
    
    data = []
    base_temps = {'New York': 15, 'Los Angeles': 22, 'Chicago': 10, 'Houston': 25, 'Phoenix': 28}
    
    for city in cities:
        base_temp = base_temps[city]
        for i, date in enumerate(dates):
            # Seasonal variation
            seasonal = 10 * np.sin(2 * np.pi * i / 365)
            temp = base_temp + seasonal + np.random.normal(0, 5)
            humidity = max(0, min(100, 60 + np.random.normal(0, 15)))
            precipitation = max(0, np.random.exponential(2))
            
            data.append({
                'Date': date,
                'City': city,
                'Temperature': round(temp, 1),
                'Humidity': round(humidity, 1),
                'Precipitation': round(precipitation, 2)
            })
    
    return pd.DataFrame(data)

# Concentration Analysis Functions
def calculate_hhi(market_shares):
    """Calculate Herfindahl-Hirschman Index"""
    return sum(share**2 for share in market_shares)

def calculate_concentration_ratio(market_shares, n=4):
    """Calculate concentration ratio for top N firms"""
    sorted_shares = sorted(market_shares, reverse=True)
    return sum(sorted_shares[:n])

def calculate_gini_coefficient(values):
    """Calculate Gini coefficient for inequality measurement"""
    values = np.array(values)
    values = values[values > 0]  # Remove zeros
    n = len(values)
    if n == 0:
        return 0
    
    values = np.sort(values)
    cumsum = np.cumsum(values)
    return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n

def create_lorenz_curve(values):
    """Create data for Lorenz curve"""
    values = np.array(values)
    values = values[values > 0]  # Remove zeros
    values = np.sort(values)
    n = len(values)
    
    if n == 0:
        return np.array([0, 1]), np.array([0, 1])
    
    cumulative_pop = np.arange(1, n + 1) / n
    cumulative_value = np.cumsum(values) / np.sum(values)
    
    # Add origin point
    cumulative_pop = np.insert(cumulative_pop, 0, 0)
    cumulative_value = np.insert(cumulative_value, 0, 0)
    
    return cumulative_pop, cumulative_value

def calculate_entropy_index(market_shares):
    """Calculate entropy index for market concentration"""
    shares = np.array(market_shares)
    shares = shares[shares > 0]  # Remove zeros
    if len(shares) == 0:
        return 0
    return entropy(shares, base=2)

# Load data based on selection
if data_source == "Sample Sales Data":
    df = generate_sales_data()
    st.sidebar.success("✅ Sales data loaded!")
    
elif data_source == "Stock Market Data":
    df = generate_stock_data()
    st.sidebar.success("✅ Stock data loaded!")
    
elif data_source == "Weather Data":
    df = generate_weather_data()
    st.sidebar.success("✅ Weather data loaded!")
    
elif data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.sidebar.success(f"✅ File '{uploaded_file.name}' loaded!")
    else:
        st.sidebar.info("👆 Please upload a CSV file")
        df = generate_sales_data()  # Default fallback
        
elif data_source == "Generate Random Data":
    rows = st.sidebar.slider("Number of rows:", 100, 10000, 1000)
    cols = st.sidebar.slider("Number of columns:", 3, 10, 5)
    
    df = pd.DataFrame(np.random.randn(rows, cols), 
                     columns=[f'Column_{i+1}' for i in range(cols)])
    df['Category'] = np.random.choice(['A', 'B', 'C'], rows)
    df['Date'] = pd.date_range(start='2024-01-01', periods=rows, freq='H')
    st.sidebar.success(f"✅ Generated {rows}×{cols} random dataset!")

# Data overview
st.header("📋 Data Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f'<div class="metric-box"><h3>{len(df)}</h3><p>Total Rows</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-box"><h3>{len(df.columns)}</h3><p>Columns</p></div>', unsafe_allow_html=True)
with col3:
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    st.markdown(f'<div class="metric-box"><h3>{len(numeric_cols)}</h3><p>Numeric Columns</p></div>', unsafe_allow_html=True)
with col4:
    missing_values = df.isnull().sum().sum()
    st.markdown(f'<div class="metric-box"><h3>{missing_values}</h3><p>Missing Values</p></div>', unsafe_allow_html=True)

# Display data sample
with st.expander("🔍 View Data Sample", expanded=False):
    st.dataframe(df.head(100), width='stretch')

# Chart type selection
st.sidebar.header("📈 Visualization Options")
chart_type = st.sidebar.selectbox(
    "Select chart type:",
    ["Line Chart", "Bar Chart", "Scatter Plot", "Histogram", "Box Plot", 
     "Heatmap", "Pie Chart", "Area Chart", "Violin Plot", "3D Scatter", "Concentration Analysis"]
)

# Column selection based on data
numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
datetime_columns = df.select_dtypes(include=['datetime64']).columns.tolist()

# Main visualization area
st.header(f"📊 {chart_type} Visualization")

if chart_type == "Line Chart":
    col1, col2 = st.columns(2)
    with col1:
        x_col = st.selectbox("X-axis:", datetime_columns + numeric_columns + categorical_columns)
    with col2:
        y_col = st.selectbox("Y-axis:", numeric_columns)
    
    if len(categorical_columns) > 0:
        color_col = st.selectbox("Color by (optional):", [None] + categorical_columns)
    else:
        color_col = None
    
    if x_col and y_col:
        fig = px.line(df, x=x_col, y=y_col, color=color_col,
                     title=f"{y_col} over {x_col}")
        st.plotly_chart(fig, width='stretch')

elif chart_type == "Bar Chart":
    col1, col2 = st.columns(2)
    with col1:
        x_col = st.selectbox("X-axis:", categorical_columns + numeric_columns)
    with col2:
        y_col = st.selectbox("Y-axis:", numeric_columns)
    
    if len(categorical_columns) > 0:
        color_col = st.selectbox("Color by (optional):", [None] + categorical_columns)
    else:
        color_col = None
    
    if x_col and y_col:
        fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                    title=f"{y_col} by {x_col}")
        st.plotly_chart(fig, width='stretch')

elif chart_type == "Scatter Plot":
    col1, col2, col3 = st.columns(3)
    with col1:
        x_col = st.selectbox("X-axis:", numeric_columns)
    with col2:
        y_col = st.selectbox("Y-axis:", numeric_columns)
    with col3:
        size_col = st.selectbox("Size by (optional):", [None] + numeric_columns)
    
    if len(categorical_columns) > 0:
        color_col = st.selectbox("Color by (optional):", [None] + categorical_columns)
    else:
        color_col = None
    
    if x_col and y_col:
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col, size=size_col,
                        title=f"{y_col} vs {x_col}")
        st.plotly_chart(fig, width='stretch')

elif chart_type == "Histogram":
    col1, col2 = st.columns(2)
    with col1:
        hist_col = st.selectbox("Column for histogram:", numeric_columns)
    with col2:
        bins = st.slider("Number of bins:", 10, 100, 30)
    
    if len(categorical_columns) > 0:
        color_col = st.selectbox("Color by (optional):", [None] + categorical_columns)
    else:
        color_col = None
    
    if hist_col:
        fig = px.histogram(df, x=hist_col, nbins=bins, color=color_col,
                          title=f"Distribution of {hist_col}")
        st.plotly_chart(fig, width='stretch')

elif chart_type == "Box Plot":
    col1, col2 = st.columns(2)
    with col1:
        y_col = st.selectbox("Y-axis (numeric):", numeric_columns)
    with col2:
        x_col = st.selectbox("X-axis (categorical):", [None] + categorical_columns)
    
    if y_col:
        fig = px.box(df, x=x_col, y=y_col,
                    title=f"Box Plot of {y_col}" + (f" by {x_col}" if x_col else ""))
        st.plotly_chart(fig, width='stretch')

elif chart_type == "Heatmap":
    # Correlation heatmap for numeric columns
    if len(numeric_columns) > 1:
        corr_matrix = df[numeric_columns].corr()
        fig = px.imshow(corr_matrix, 
                       title="Correlation Heatmap",
                       color_continuous_scale="RdBu_r",
                       aspect="auto")
        st.plotly_chart(fig, width='stretch')
    else:
        st.warning("⚠️ Need at least 2 numeric columns for correlation heatmap")

elif chart_type == "Pie Chart":
    if len(categorical_columns) > 0:
        pie_col = st.selectbox("Column for pie chart:", categorical_columns)
        if len(numeric_columns) > 0:
            values_col = st.selectbox("Values (optional):", [None] + numeric_columns)
        else:
            values_col = None
        
        if pie_col:
            if values_col:
                pie_data = df.groupby(pie_col)[values_col].sum().reset_index()
                fig = px.pie(pie_data, names=pie_col, values=values_col,
                           title=f"{values_col} by {pie_col}")
            else:
                pie_data = df[pie_col].value_counts().reset_index()
                fig = px.pie(pie_data, names='index', values=pie_col,
                           title=f"Distribution of {pie_col}")
            st.plotly_chart(fig, width='stretch')
    else:
        st.warning("⚠️ Need categorical columns for pie chart")

elif chart_type == "Area Chart":
    col1, col2 = st.columns(2)
    with col1:
        x_col = st.selectbox("X-axis:", datetime_columns + numeric_columns)
    with col2:
        y_col = st.selectbox("Y-axis:", numeric_columns)
    
    if len(categorical_columns) > 0:
        color_col = st.selectbox("Color by (optional):", [None] + categorical_columns)
    else:
        color_col = None
    
    if x_col and y_col:
        fig = px.area(df, x=x_col, y=y_col, color=color_col,
                     title=f"{y_col} over {x_col}")
        st.plotly_chart(fig, width='stretch')

elif chart_type == "Violin Plot":
    col1, col2 = st.columns(2)
    with col1:
        y_col = st.selectbox("Y-axis (numeric):", numeric_columns)
    with col2:
        x_col = st.selectbox("X-axis (categorical):", [None] + categorical_columns)
    
    if y_col:
        fig = px.violin(df, x=x_col, y=y_col,
                       title=f"Violin Plot of {y_col}" + (f" by {x_col}" if x_col else ""))
        st.plotly_chart(fig, width='stretch')

elif chart_type == "3D Scatter":
    if len(numeric_columns) >= 3:
        col1, col2, col3 = st.columns(3)
        with col1:
            x_col = st.selectbox("X-axis:", numeric_columns)
        with col2:
            y_col = st.selectbox("Y-axis:", numeric_columns)
        with col3:
            z_col = st.selectbox("Z-axis:", numeric_columns)
        
        if len(categorical_columns) > 0:
            color_col = st.selectbox("Color by (optional):", [None] + categorical_columns)
        else:
            color_col = None
        
        if x_col and y_col and z_col:
            fig = px.scatter_3d(df, x=x_col, y=y_col, z=z_col, color=color_col,
                               title=f"3D Scatter: {x_col}, {y_col}, {z_col}")
            st.plotly_chart(fig, width='stretch')
    else:
        st.warning("⚠️ Need at least 3 numeric columns for 3D scatter plot")

elif chart_type == "Concentration Analysis":
    st.header("🎯 Market Concentration Analysis")
    
    # Select columns for concentration analysis
    col1, col2 = st.columns(2)
    with col1:
        entity_col = st.selectbox("Entity/Firm Column:", categorical_columns, key="conc_entity")
    with col2:
        value_col = st.selectbox("Value Column (Market Share/Revenue):", numeric_columns, key="conc_value")
    
    if entity_col and value_col:
        # Aggregate data by entity
        concentration_data = df.groupby(entity_col)[value_col].sum().reset_index()
        concentration_data = concentration_data.sort_values(value_col, ascending=False)
        
        # Calculate market shares
        total_value = concentration_data[value_col].sum()
        concentration_data['market_share'] = (concentration_data[value_col] / total_value) * 100
        market_shares = concentration_data['market_share'].values
        
        # Concentration metrics
        st.subheader("📊 Concentration Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            hhi = calculate_hhi(market_shares)
            st.metric("HHI Index", f"{hhi:.0f}", 
                     help="Herfindahl-Hirschman Index: <1500 (competitive), 1500-2500 (moderate), >2500 (highly concentrated)")
            
            # HHI interpretation
            if hhi < 1500:
                hhi_status = "🟢 Competitive"
            elif hhi < 2500:
                hhi_status = "🟡 Moderate"
            else:
                hhi_status = "🔴 Highly Concentrated"
            st.write(hhi_status)
        
        with col2:
            cr4 = calculate_concentration_ratio(market_shares, 4)
            st.metric("CR4 Ratio", f"{cr4:.1f}%", 
                     help="4-firm concentration ratio: Percentage of market held by top 4 firms")
        
        with col3:
            gini = calculate_gini_coefficient(market_shares)
            st.metric("Gini Coefficient", f"{gini:.3f}", 
                     help="Gini coefficient: 0 (perfect equality) to 1 (perfect inequality)")
        
        with col4:
            entropy_idx = calculate_entropy_index(market_shares / 100)  # Convert to proportions
            st.metric("Entropy Index", f"{entropy_idx:.2f}", 
                     help="Entropy index: Higher values indicate more competition")
        
        # Market share visualization
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Market Share Distribution")
            fig_bar = px.bar(concentration_data, 
                           x=entity_col, y='market_share',
                           title="Market Share by Entity",
                           labels={'market_share': 'Market Share (%)'})
            fig_bar.update_xaxis(tickangle=45)
            st.plotly_chart(fig_bar, width='stretch')
        
        with col2:
            st.subheader("🥧 Market Share Pie Chart")
            # Show only top 10 to avoid clutter
            top_entities = concentration_data.head(10)
            if len(concentration_data) > 10:
                others_share = concentration_data.iloc[10:]['market_share'].sum()
                if others_share > 0:
                    others_row = pd.DataFrame({entity_col: ['Others'], 'market_share': [others_share]})
                    top_entities = pd.concat([top_entities, others_row], ignore_index=True)
            
            fig_pie = px.pie(top_entities, 
                           names=entity_col, values='market_share',
                           title="Top Market Players")
            st.plotly_chart(fig_pie, width='stretch')
        
        # Lorenz Curve
        st.subheader("📈 Lorenz Curve & Inequality Analysis")
        
        pop_cumulative, value_cumulative = create_lorenz_curve(market_shares)
        
        fig_lorenz = go.Figure()
        
        # Lorenz curve
        fig_lorenz.add_trace(go.Scatter(
            x=pop_cumulative * 100,
            y=value_cumulative * 100,
            mode='lines+markers',
            name='Lorenz Curve',
            line=dict(color='blue', width=3)
        ))
        
        # Line of equality
        fig_lorenz.add_trace(go.Scatter(
            x=[0, 100],
            y=[0, 100],
            mode='lines',
            name='Line of Equality',
            line=dict(color='red', dash='dash', width=2)
        ))
        
        fig_lorenz.update_layout(
            title="Lorenz Curve - Market Concentration",
            xaxis_title="Cumulative % of Entities",
            yaxis_title="Cumulative % of Market Share",
            showlegend=True,
            width=800,
            height=500
        )
        
        st.plotly_chart(fig_lorenz, width='stretch')
        
        # Concentration analysis table
        st.subheader("📋 Detailed Market Share Analysis")
        
        # Add rankings and cumulative shares
        concentration_data['rank'] = range(1, len(concentration_data) + 1)
        concentration_data['cumulative_share'] = concentration_data['market_share'].cumsum()
        concentration_data['cumulative_entities'] = (concentration_data['rank'] / len(concentration_data)) * 100
        
        # Display formatted table
        display_data = concentration_data.copy()
        display_data['market_share'] = display_data['market_share'].round(2)
        display_data['cumulative_share'] = display_data['cumulative_share'].round(2)
        display_data['cumulative_entities'] = display_data['cumulative_entities'].round(1)
        display_data[value_col] = display_data[value_col].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(
            display_data[[entity_col, value_col, 'market_share', 'cumulative_share', 'rank']].rename(columns={
                entity_col: 'Entity',
                value_col: 'Value',
                'market_share': 'Market Share (%)',
                'cumulative_share': 'Cumulative Share (%)',
                'rank': 'Rank'
            }),
            width='stretch'
        )
        
        # Additional concentration ratios
        st.subheader("📊 Concentration Ratios")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cr1 = calculate_concentration_ratio(market_shares, 1)
            st.metric("CR1", f"{cr1:.1f}%", help="Top 1 firm market share")
        
        with col2:
            cr3 = calculate_concentration_ratio(market_shares, 3)
            st.metric("CR3", f"{cr3:.1f}%", help="Top 3 firms market share")
        
        with col3:
            cr5 = calculate_concentration_ratio(market_shares, 5)
            st.metric("CR5", f"{cr5:.1f}%", help="Top 5 firms market share")
        
        with col4:
            cr8 = calculate_concentration_ratio(market_shares, 8)
            st.metric("CR8", f"{cr8:.1f}%", help="Top 8 firms market share")
        
        # Market structure interpretation
        st.subheader("🏛️ Market Structure Analysis")
        
        # Determine market structure based on CR4 and HHI
        if cr4 < 40 and hhi < 1500:
            market_structure = "Perfect Competition / Monopolistic Competition"
            structure_color = "🟢"
            structure_desc = "High competition, many players, low barriers to entry"
        elif cr4 < 60 and hhi < 2500:
            market_structure = "Oligopoly (Competitive)"
            structure_color = "🟡"
            structure_desc = "Moderate competition, several major players"
        elif cr4 < 80:
            market_structure = "Oligopoly (Concentrated)"
            structure_color = "🟠"
            structure_desc = "Limited competition, few dominant players"
        else:
            market_structure = "Monopoly / Duopoly"
            structure_color = "🔴"
            structure_desc = "Very limited competition, market dominated by 1-2 players"
        
        st.info(f"{structure_color} **Market Structure:** {market_structure}\n\n{structure_desc}")
        
        # Competitive dynamics
        if len(market_shares) > 1:
            st.subheader("⚔️ Competitive Dynamics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Market leader advantage
                leader_share = market_shares[0]
                second_share = market_shares[1] if len(market_shares) > 1 else 0
                leader_advantage = leader_share - second_share
                
                st.metric("Market Leader Advantage", f"{leader_advantage:.1f}%",
                         help="Difference between #1 and #2 market share")
                
                # Number of significant players (>5% market share)
                significant_players = sum(1 for share in market_shares if share >= 5)
                st.metric("Significant Players (>5%)", significant_players,
                         help="Number of entities with >5% market share")
            
            with col2:
                # Fragmentation index (inverse of HHI)
                fragmentation = 10000 / hhi if hhi > 0 else 0
                st.metric("Market Fragmentation", f"{fragmentation:.1f}",
                         help="Effective number of competitors (10000/HHI)")
                
                # Tail competition (entities with <1% share)
                tail_players = sum(1 for share in market_shares if share < 1)
                st.metric("Tail Players (<1%)", tail_players,
                         help="Number of small entities with <1% market share")
    
    else:
        st.warning("⚠️ Please select both entity and value columns for concentration analysis")

# Statistical summary
st.header("📈 Statistical Summary")
if len(numeric_columns) > 0:
    summary_stats = df[numeric_columns].describe()
    st.dataframe(summary_stats, width='stretch')
else:
    st.info("No numeric columns available for statistical summary")

# Download processed data
st.header("💾 Export Data")
col1, col2 = st.columns(2)

with col1:
    # CSV download
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name=f'{data_source.lower().replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        mime='text/csv'
    )

with col2:
    # JSON download
    json_data = df.to_json(orient='records', date_format='iso')
    st.download_button(
        label="📥 Download as JSON",
        data=json_data,
        file_name=f'{data_source.lower().replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        mime='application/json'
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <h4>📊 Data Visualization Dashboard</h4>
        <p>Built with Streamlit & Plotly • Interactive data exploration made easy</p>
        <p>Select different data sources and chart types to explore your data!</p>
    </div>
    """,
    unsafe_allow_html=True
)