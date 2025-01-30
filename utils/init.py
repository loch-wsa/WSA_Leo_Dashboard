import streamlit as st
import pandas as pd
from datetime import timedelta

def initialize_date_range(df, timestamp_column='TIMESTAMP', sidebar=True):
    """
    Initialize date range controls and return the filtered dataframe and display format.
    
    Parameters:
    - df (pd.DataFrame): Input dataframe containing timestamp data
    - timestamp_column (str): Name of the timestamp column (default: 'TIMESTAMP')
    - sidebar (bool): Whether to place controls in sidebar (default: True)
    
    Returns:
    - tuple: (filtered_df, display_format)
    """
    # Determine container (sidebar or main area)
    container = st.sidebar if sidebar else st

    # Add title to controls
    container.title("Time Range Controls")
    
    # Define preset time ranges
    time_ranges = {
        "Last Day": timedelta(days=1),
        "Last Week": timedelta(days=7),
        "Last Month": timedelta(days=30),
        "Last Year": timedelta(days=365),
        "Custom Range": None
    }
    
    # Store the selection in session state if not already present
    if 'selected_range' not in st.session_state:
        st.session_state.selected_range = "Last Week"
    
    # Radio button for time range selection
    selected_range = container.radio(
        "Select Time Range",
        list(time_ranges.keys()),
        key='selected_range'
    )
    
    # Ensure timestamp column is datetime type
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_column]):
        df[timestamp_column] = pd.to_datetime(df[timestamp_column], dayfirst=True)
    
    # Get the date range from the dataframe
    latest_date = pd.to_datetime(df[timestamp_column].max())
    earliest_date = pd.to_datetime(df[timestamp_column].min())
    
    # Handle custom date range
    if selected_range == "Custom Range":
        # Store custom dates in session state if not present
        if 'start_date' not in st.session_state:
            st.session_state.start_date = earliest_date.date()
        if 'end_date' not in st.session_state:
            st.session_state.end_date = latest_date.date()
        
        # Date input widgets
        start_date = container.date_input(
            "Start Date",
            value=st.session_state.start_date,
            min_value=earliest_date.date(),
            max_value=latest_date.date(),
            key='start_date'
        )
        end_date = container.date_input(
            "End Date",
            value=st.session_state.end_date,
            min_value=earliest_date.date(),
            max_value=latest_date.date(),
            key='end_date'
        )
        
        # Convert to datetime
        start_datetime = pd.to_datetime(start_date)
        end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1)
    else:
        # Calculate date range based on selection
        end_datetime = latest_date
        start_datetime = end_datetime - pd.Timedelta(time_ranges[selected_range])
    
    # Filter dataframe
    filtered_df = df[
        (df[timestamp_column] >= start_datetime) & 
        (df[timestamp_column] <= end_datetime)
    ].copy()
    
    # Determine display format based on selected range
    display_format = {
        "Last Day": '%H:%M',
        "Last Week": '%a %H:%M',
        "Last Month": '%d-%b',
        "Last Year": '%d-%b-%Y',
        "Custom Range": '%d-%b-%Y' if (end_datetime - start_datetime).days > 30 else '%d-%b'
    }[selected_range]
    
    # Add formatted display time
    filtered_df['display_time'] = filtered_df[timestamp_column].dt.strftime(display_format)
    
    # Add helper info in the sidebar
    container.info(f"Showing data from {start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%Y-%m-%d %H:%M')}")
    
    return filtered_df, display_format