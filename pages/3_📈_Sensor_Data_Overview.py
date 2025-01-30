import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from utils.data_loader import load_all_data
import pytz

@st.cache_data(ttl=3600)
def remove_outliers(data, column):
    """Remove outliers using the IQR method"""
    Q1 = data[column].quantile(0.25)
    Q3 = data[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return data[(data[column] >= lower_bound) & (data[column] <= upper_bound)]

def plot_sensor_data(df, component, thresholds, remove_outliers_enabled=False):
    """Plot sensor data with thresholds"""
    # Create figure
    fig = go.Figure()
    
    # Prepare data
    plot_data = df[['timestamp', component]].copy()
    if remove_outliers_enabled:
        original_count = len(plot_data)
        plot_data = remove_outliers(plot_data, component)
        removed_count = original_count - len(plot_data)
        if removed_count > 0:
            st.caption(f"Removed {removed_count} outliers from {component}")
    
    # Add main line
    fig.add_trace(
        go.Scatter(
            x=plot_data['timestamp'],
            y=plot_data[component],
            name=component,
            mode='lines',
            line=dict(color='blue')
        )
    )
    
    # Add threshold lines if they exist
    if thresholds.get('HighHigh') is not None:
        fig.add_hline(y=thresholds['HighHigh'], line_dash="dash", line_color="red", 
                     annotation_text="High High", annotation_position="right")
    if thresholds.get('High') is not None:
        fig.add_hline(y=thresholds['High'], line_dash="dash", line_color="orange",
                     annotation_text="High", annotation_position="right")
    if thresholds.get('Low') is not None:
        fig.add_hline(y=thresholds['Low'], line_dash="dash", line_color="orange",
                     annotation_text="Low", annotation_position="right")
    if thresholds.get('LowLow') is not None:
        fig.add_hline(y=thresholds['LowLow'], line_dash="dash", line_color="red",
                     annotation_text="Low Low", annotation_position="right")
    
    # Update layout
    fig.update_layout(
        title=f"{component} Readings Over Time",
        xaxis_title="Timestamp",
        yaxis_title="Value",
        height=500,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig

def get_melbourne_timezone():
    """Get Melbourne timezone"""
    return pytz.timezone('Australia/Melbourne')

def main():
    st.set_page_config(layout="wide", page_title="Sensor Data Overview", page_icon="📊")
    
    # Title and description
    st.title("📊 Sensor Data Overview")
    st.markdown("""
        This page provides line charts for various sensor measurements over time. Each chart represents data from a specific sensor.
        Use the controls below to adjust the time range and view specific periods of interest.
    """)
    
    try:
        # Load all data
        data = load_all_data()
        telemetry_df = data['telemetry']
        thresholds_df = data['thresholds']
        
        melbourne_tz = get_melbourne_timezone()
        
        # Sidebar controls
        with st.sidebar:
            st.header("Configuration")
            
            # Time range selector
            st.subheader("Time Range")
            time_range = st.radio(
                "Select Time Range",
                ["Last 24 Hours", "Last Week", "Last Month", "Custom Range"]
            )
            
            # Handle custom date range
            if time_range == "Custom Range":
                min_date = telemetry_df['timestamp'].min()
                max_date = telemetry_df['timestamp'].max()
                
                start_date = st.date_input("Start Date", 
                                         value=max_date.date() - timedelta(days=7),
                                         min_value=min_date.date(),
                                         max_value=max_date.date())
                end_date = st.date_input("End Date",
                                       value=max_date.date(),
                                       min_value=min_date.date(),
                                       max_value=max_date.date())
                
                # Convert dates to timezone-aware datetime objects
                start_datetime = melbourne_tz.localize(datetime.combine(start_date, datetime.min.time()))
                end_datetime = melbourne_tz.localize(datetime.combine(end_date, datetime.max.time()))
                
            else:
                end_datetime = telemetry_df['timestamp'].max()
                if time_range == "Last 24 Hours":
                    start_datetime = end_datetime - timedelta(days=1)
                elif time_range == "Last Week":
                    start_datetime = end_datetime - timedelta(days=7)
                else:  # Last Month
                    start_datetime = end_datetime - timedelta(days=30)
            
            # Outlier removal toggle
            remove_outliers_enabled = st.toggle("Remove Outliers", value=False)
            
            if remove_outliers_enabled:
                st.info("""
                    **Outlier Removal Formula:**
                    - Calculate Q1 (25th percentile) and Q3 (75th percentile)
                    - Calculate IQR = Q3 - Q1
                    - Remove data points outside range:
                      - Lower bound = Q1 - 1.5 × IQR
                      - Upper bound = Q3 + 1.5 × IQR
                """)
            
            # Raw data hiding toggle
            hide_raw_enabled = st.toggle("Hide RAW Components", value=True)
            if hide_raw_enabled:
                st.info("Hiding components that end with 'RAW'")
        
        # Filter telemetry data by time range
        mask = (telemetry_df['timestamp'] >= start_datetime) & (telemetry_df['timestamp'] <= end_datetime)
        filtered_telemetry = telemetry_df[mask].copy()
        
        # Get available components (excluding system columns)
        system_columns = ['timestamp', 'ORGANISATIONID', 'DEVICEID', 'FLOWSEQUENCE', 'PACKETNO', 'UNITSERIALNUMBER']
        available_components = [col for col in filtered_telemetry.columns if col not in system_columns]
        
        # Filter out RAW components if enabled
        if hide_raw_enabled:
            available_components = [col for col in available_components if not col.endswith('RAW')]
        
        # Component selector
        selected_components = st.multiselect(
            'Select Components to Display',
            options=available_components,
            default=available_components[:1] if available_components else []  # Select first component by default if available
        )
        
        if not filtered_telemetry.empty:
            # Display charts for selected components
            for component in selected_components:
                # Get thresholds for component
                component_thresholds = thresholds_df[thresholds_df['Component'] == component].iloc[0].to_dict() if not thresholds_df[thresholds_df['Component'] == component].empty else {}
                
                # Create and display plot
                fig = plot_sensor_data(filtered_telemetry, component, component_thresholds, remove_outliers_enabled)
                st.plotly_chart(fig, use_container_width=True)
            
            # Toggle for raw data visibility
            show_raw_data = st.toggle('Show Raw Data', value=False)
            
            if show_raw_data:
                st.write("Telemetry Data Sample (last 5 records):")
                st.dataframe(
                    filtered_telemetry[['timestamp'] + selected_components].tail(),
                    use_container_width=True
                )
                
                if selected_components:
                    st.write("\nThreshold Settings for Selected Components:")
                    st.dataframe(
                        thresholds_df[thresholds_df['Component'].isin(selected_components)],
                        use_container_width=True
                    )
        else:
            st.warning("No data available for the selected time range. Please adjust the time range.")
    
    except Exception as e:
        st.error(f"Error loading or processing data: {str(e)}")
        st.write("Error details:", str(e))

if __name__ == "__main__":
    main()