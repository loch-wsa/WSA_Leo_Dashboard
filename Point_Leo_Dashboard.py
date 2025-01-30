import streamlit as st
import sys
from pathlib import Path

# Add the root directory to Python path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from utils.data_loader import load_all_data

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Brolga Water Treatment Trial - Point Leo",
    page_icon="💧"
)

# Load all data using the new function
try:
    data = load_all_data()
    
    # Extract specific dataframes needed for this page
    influent_data = data['influent_data']
    treated_data = data['treated_data']
    influent_ranges = data['influent_ranges']
    treated_ranges = data['treated_ranges']
    
    # Extract latest info data for potential use in metrics
    info_df = data['info']
    
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# Project Overview Section
st.title('Brolga Water Treatment System - Point Leo Trial')

# Define column layout
col1, col2 = st.columns([1.5, 1])

# First column with main project description
with col1:
    st.info(
    '''
        ### Project Description
        
        The Flinders trial demonstrates Water Source Australia's Brolga water treatment system in a real-world application.
        This pilot project processes pond water through a multi-barrier treatment approach to achieve potable water quality standards.  
    '''
    )

# Second column with key project details
with col2:
    st.info(
    '''
        ### Key Details  
        
        - **Trial Location**: Point Leo
        - **Source Water**: Farm Pond  
        - **Treatment Goal**: Potable Water Quality  
        - **Data Timezone**: Melbourne, Australia
    '''
    )

# System Overview
st.header('System Overview')
st.markdown("""
    The Brolga treatment system employs multiple barriers for water treatment:
    - Pre-filtration for large particle removal
    - Mixed media filtration for iron and manganese removal
    - Ultrafiltration for pathogen and particle removal
    - Carbon filtration for taste, odor, and color removal
    - UV disinfection for final pathogen inactivation
""")

# System Performance Metrics
st.header('Treatment System Performance')

# Define column layout for performance metrics
col1, col2, col3 = st.columns(3)

# First column for Pathogen Removal details
with col1:
    st.info(
    '''
        ### Pathogen Removal
        
        **✓** >7 log bacteria removal  
        **✓** >6.5 log virus removal  
        **✓** >7 log protozoa removal  
    '''
    )

# Second column for Physical Treatment details
with col2:
    st.info(
    '''
        ### Physical Treatment  
        
        **✓** Turbidity < 0.1 NTU  
        **✓** Color reduction to < 15 HU  
        **✓** TDS reduction to spec  
    '''
    )

# Third column for Chemical Treatment details
with col3:
    st.info(
    '''
        ### Chemical Treatment  
        
        **✓** Iron/Manganese removal  
        **✓** pH correction  
        **✓** Organic carbon reduction  
    '''
    )

# Data Overview Section
st.header('Data Overview')
col1, col2, col3 = st.columns(3)

with col1:
    if 'info' in data:
        total_events = len(data['info'])
        latest_event = data['info']['timestamp'].max()
        st.metric("Total System Events", f"{total_events:,}")
        st.metric("Latest Event Time", latest_event.strftime('%Y/%m/%d %H:%M'))

with col2:
    if 'alarms' in data:
        total_alarms = len(data['alarms'])
        st.metric("Total Alarms Recorded", f"{total_alarms:,}")
        if not data['alarms'].empty:
            latest_alarm = data['alarms']['timestamp'].max()
            st.metric("Latest Alarm Time", latest_alarm.strftime('%Y/%m/%d %H:%M'))

with col3:
    if 'telemetry' in data:
        total_readings = len(data['telemetry'])
        st.metric("Total Telemetry Readings", f"{total_readings:,}")
        if not data['telemetry'].empty:
            latest_reading = data['telemetry']['timestamp'].max()
            st.metric("Latest Reading Time", latest_reading.strftime('%Y/%m/%d %H:%M'))

# Sidebar
st.sidebar.title('Control Panel')
st.sidebar.markdown('Navigate through the pages to view detailed analysis of:')
st.sidebar.markdown('- Influent Water Analysis')
st.sidebar.markdown('- Treated Water Analysis')
st.sidebar.markdown('- Water Quality Comparison')
st.sidebar.markdown('---')
st.sidebar.warning('Note: Values below detection limits are shown as the detection limit value. Actual values may be lower.')

# Add timezone information
st.sidebar.info('All times shown are in Melbourne, Australia timezone')