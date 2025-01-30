import streamlit as st
import pandas as pd
from utils.data_loader import load_all_data

def display_dataframe_info(df, name):
    """Helper function to display information about a dataframe"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Rows", f"{len(df):,}")
    
    with col2:
        if 'timestamp' in df.columns:
            first_timestamp = df['timestamp'].min()
            st.metric("First Timestamp", first_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
    
    with col3:
        if 'timestamp' in df.columns:
            last_timestamp = df['timestamp'].max()
            st.metric("Last Timestamp", last_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
    
    # Create tabs for head and tail
    tab1, tab2 = st.tabs(["First 5 Rows", "Last 5 Rows"])
    
    with tab1:
        st.dataframe(df.head(), use_container_width=True)
    
    with tab2:
        st.dataframe(df.tail(), use_container_width=True)

def main():
    st.set_page_config(layout="wide", page_title="Data Overview", page_icon="📊")
    
    # Page title
    st.title("📊 Data Overview")
    
    # Load all data
    try:
        data = load_all_data()
        
        # Add description
        st.markdown("""
        This page provides an overview of all data loaded in the dashboard. For each dataset, you can see:
        - Total number of rows
        - Timestamp range (where applicable)
        - First and last 5 rows of data
        """)
        
        # Time series data section
        st.header("🕒 Time Series Data")
        
        # Show time series datasets
        time_series_data = {
            "System Events (Info)": data['info'],
            "Alarms": data['alarms'],
            "Warnings": data['warnings'],
            "Sequences": data['sequences'],
            "Telemetry": data['telemetry']
        }
        
        for name, df in time_series_data.items():
            with st.expander(f"{name} Overview"):
                display_dataframe_info(df, name)
        
        # Static data section
        st.header("📋 Reference Data")
        
        # Show static datasets
        static_data = {
            "Assets": data['assets'],
            "Thresholds": data['thresholds']
        }
        
        for name, df in static_data.items():
            with st.expander(f"{name} Overview"):
                display_dataframe_info(df, name)
        
        # Water quality data section
        st.header("💧 Water Quality Data")
        
        water_quality_data = {
            "Influent Water": data['influent_data'],
            "Treated Water": data['treated_data'],
            "Influent Parameters": data['influent_ranges'],
            "Treated Parameters": data['treated_ranges']
        }
        
        for name, df in water_quality_data.items():
            with st.expander(f"{name} Overview"):
                display_dataframe_info(df, name)
        
        # Add summary statistics
        st.header("📈 Summary Statistics")
        
        total_events = len(data['info'])
        total_alarms = len(data['alarms'])
        total_warnings = len(data['warnings'])
        total_sequences = len(data['sequences'])
        total_telemetry = len(data['telemetry'])
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Events", f"{total_events:,}")
        with col2:
            st.metric("Total Alarms", f"{total_alarms:,}")
        with col3:
            st.metric("Total Warnings", f"{total_warnings:,}")
        with col4:
            st.metric("Total Sequences", f"{total_sequences:,}")
        with col5:
            st.metric("Total Telemetry", f"{total_telemetry:,}")
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()