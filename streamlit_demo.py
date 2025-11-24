import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Set page config
st.set_page_config(
    page_title="Streamlit Demo App",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-header">🚀 Streamlit Demo Application</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    
    # User input controls
    user_name = st.text_input("Enter your name:", value="User")
    favorite_color = st.selectbox("Choose your favorite color:", 
                                 ["Blue", "Red", "Green", "Purple", "Orange"])
    
    # Slider for data generation
    data_points = st.slider("Number of data points:", 10, 1000, 100)
    
    # Date picker
    selected_date = st.date_input("Select a date:", datetime.now())
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    st.metric("Total Users", "1,234", "12%")
    st.metric("Revenue", "$45.2K", "8.2%")
    st.metric("Growth Rate", "15.3%", "-2.1%")

# Main content area with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Charts", "📊 Data", "🎮 Interactive", "🗺️ Maps", "🎯 Widgets"])

with tab1:
    st.header(f"📈 Charts for {user_name}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Random Data Visualization")
        
        # Generate random data
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=data_points, freq='D')
        values = np.cumsum(np.random.randn(data_points)) * 10 + 100
        
        df = pd.DataFrame({
            'Date': dates,
            'Value': values,
            'Category': np.random.choice(['A', 'B', 'C'], data_points)
        })
        
        # Line chart
        fig_line = px.line(df, x='Date', y='Value', 
                          title=f"Trend Analysis ({data_points} points)",
                          color_discrete_sequence=[favorite_color.lower()])
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col2:
        st.subheader("🍰 Category Distribution")
        
        # Pie chart
        category_counts = df['Category'].value_counts()
        fig_pie = px.pie(values=category_counts.values, 
                        names=category_counts.index,
                        title="Category Distribution")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Bar chart spanning full width
    st.subheader("📊 Monthly Summary")
    monthly_data = df.groupby(df['Date'].dt.month)['Value'].mean().reset_index()
    monthly_data['Month'] = monthly_data['Date'].apply(lambda x: pd.to_datetime(f"2024-{x:02d}-01").strftime('%B'))
    
    fig_bar = px.bar(monthly_data, x='Month', y='Value',
                    title="Average Values by Month",
                    color='Value',
                    color_continuous_scale='viridis')
    st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.header("📊 Data Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Sample Dataset")
        
        # Create sample data
        sample_data = pd.DataFrame({
            'Name': [f'Person {i}' for i in range(1, 21)],
            'Age': np.random.randint(20, 65, 20),
            'Salary': np.random.randint(30000, 120000, 20),
            'Department': np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR'], 20),
            'Experience': np.random.randint(0, 20, 20)
        })
        
        # Display data with search and filtering
        st.dataframe(sample_data, use_container_width=True)
        
        # Download button
        csv = sample_data.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f'sample_data_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv'
        )
    
    with col2:
        st.subheader("📈 Data Statistics")
        
        # Statistics
        st.metric("Average Age", f"{sample_data['Age'].mean():.1f} years")
        st.metric("Average Salary", f"${sample_data['Salary'].mean():,.0f}")
        st.metric("Total Records", len(sample_data))
        
        # Department breakdown
        st.subheader("🏢 Department Breakdown")
        dept_counts = sample_data['Department'].value_counts()
        for dept, count in dept_counts.items():
            st.write(f"**{dept}:** {count} people")

with tab3:
    st.header("🎮 Interactive Elements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Real-time Updates")
        
        # Placeholder for real-time data
        placeholder = st.empty()
        
        if st.button("🔄 Start Real-time Updates"):
            for i in range(10):
                # Simulate real-time data
                current_time = datetime.now().strftime("%H:%M:%S")
                random_value = np.random.randint(1, 100)
                
                placeholder.metric(
                    label="Live Data",
                    value=f"{random_value}%",
                    delta=f"{np.random.randint(-10, 10)}%"
                )
                time.sleep(1)
        
        # Progress bar
        st.subheader("📊 Progress Tracking")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        if st.button("▶️ Run Progress Demo"):
            for i in range(101):
                progress_bar.progress(i)
                status_text.text(f'Progress: {i}%')
                time.sleep(0.05)
            st.success("✅ Process completed!")
    
    with col2:
        st.subheader("🎨 Interactive Widgets")
        
        # Multiple choice
        options = st.multiselect(
            "Choose your interests:",
            ["Technology", "Sports", "Music", "Travel", "Food", "Art"],
            default=["Technology", "Music"]
        )
        
        if options:
            st.write(f"You selected: {', '.join(options)}")
        
        # Number input
        number = st.number_input("Enter a number:", min_value=0, max_value=1000, value=42, step=1)
        st.write(f"Square of {number} is {number**2}")
        
        # Color picker
        color = st.color_picker("Pick a color:", "#FF6B6B")
        st.markdown(f'<div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: white; font-weight: bold;">Selected Color: {color}</div>', unsafe_allow_html=True)
        
        # Rating
        rating = st.select_slider(
            "Rate this app:",
            options=[1, 2, 3, 4, 5],
            value=4,
            format_func=lambda x: "⭐" * x
        )
        st.write(f"Thanks for rating: {'⭐' * rating}")

with tab4:
    st.header("🗺️ Maps and Geospatial Data")
    
    # Generate random coordinates around major cities
    cities_data = pd.DataFrame({
        'city': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego'],
        'lat': [40.7128, 34.0522, 41.8781, 29.7604, 33.4484, 39.9526, 29.4241, 32.7157],
        'lon': [-74.0060, -118.2437, -87.6298, -95.3698, -112.0740, -75.1652, -98.4936, -117.1611],
        'population': [8175000, 3971000, 2695000, 2320000, 1680000, 1584000, 1547000, 1423000]
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 City Locations")
        st.map(cities_data[['lat', 'lon']])
    
    with col2:
        st.subheader("🏙️ Population Data")
        fig_scatter = px.scatter_mapbox(
            cities_data,
            lat='lat',
            lon='lon',
            size='population',
            hover_name='city',
            hover_data={'population': ':,'},
            zoom=3,
            height=400,
            mapbox_style='open-street-map'
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab5:
    st.header("🎯 Advanced Widgets & Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Text Analysis")
        
        text_input = st.text_area(
            "Enter some text to analyze:",
            value="Streamlit is an amazing framework for building data applications!",
            height=100
        )
        
        if text_input:
            word_count = len(text_input.split())
            char_count = len(text_input)
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Words", word_count)
            with col_b:
                st.metric("Characters", char_count)
            with col_c:
                st.metric("Lines", text_input.count('\n') + 1)
        
        # File uploader
        st.subheader("📂 File Upload")
        uploaded_file = st.file_uploader("Choose a file", type=['csv', 'txt', 'json'])
        
        if uploaded_file is not None:
            st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")
            st.write(f"File size: {uploaded_file.size} bytes")
    
    with col2:
        st.subheader("🎛️ Advanced Controls")
        
        # Time input
        time_value = st.time_input("Select a time:", datetime.now().time())
        st.write(f"Selected time: {time_value}")
        
        # JSON input
        json_input = st.text_area(
            "Enter JSON data:",
            value='{"name": "John", "age": 30}',
            height=100
        )
        
        try:
            import json
            parsed_json = json.loads(json_input)
            st.json(parsed_json)
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON format")
        
        # Code input
        st.subheader("💻 Code Editor")
        code = st.text_area(
            "Enter Python code:",
            value="print('Hello, Streamlit!')\nx = 5 + 3\nprint(f'Result: {x}')",
            height=100
        )
        
        if st.button("▶️ Show Code"):
            st.code(code, language='python')

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🚀 Built with Streamlit • Made with ❤️ • © 2025</p>
        <p>Select different options in the sidebar to see the app change in real-time!</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Session state example
if 'counter' not in st.session_state:
    st.session_state.counter = 0

st.sidebar.markdown("---")
st.sidebar.subheader("🔢 Session Counter")
if st.sidebar.button("➕ Increment Counter"):
    st.session_state.counter += 1

st.sidebar.write(f"Counter value: {st.session_state.counter}")

# Show some info about the current session
st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ Session Info")
st.sidebar.write(f"Date: {selected_date}")
st.sidebar.write(f"User: {user_name}")
st.sidebar.write(f"Favorite Color: {favorite_color}")