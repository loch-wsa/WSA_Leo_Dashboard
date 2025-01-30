import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Add the root directory to Python path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from utils.data_loader import load_data, RELEVANT_PARAMS

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Brolga Water Treatment Trial - Point Leo",
    page_icon="💧"
)

# Load data
influent_data, treated_data, influent_ranges, treated_ranges = load_data()

# Project Overview Section
st.title('Brolga Water Treatment System - Point Leo Trial')

# Define column layout
col1, col2 = st.columns([1.5, 1])

# First column with main project description
with col1:
    st.info(
    '''
        ### Project Description
        
        The Point Leo trial demonstrates Water Source Australia's Brolga water treatment system in a real-world application.
        This pilot project processes pond water through a multi-barrier treatment approach to achieve potable water quality standards.  
    '''
    )

# Second column with key project details
with col2:
    st.info(
    '''
        ### Key Details  
        
        - **Trial Location**: Point Leo Farm, Frankston-Flinders Road  
        - **Source Water**: Farm Pond  
        - **Treatment Goal**: Potable Water Quality  
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



# Load Telemetry data
telemetry_df = pd.read_csv("data/Telemetry.csv")
telemetry_df['TIMESTAMP'] = pd.to_datetime(telemetry_df['TIMESTAMP'], dayfirst=True)

# Calculate min and max dates for Telemetry
min_date_telemetry = telemetry_df['TIMESTAMP'].min()
max_date_telemetry = telemetry_df['TIMESTAMP'].max()

# Load Point Leo data
point_leo_df = pd.read_csv("data/Point Leo Treated Water.csv")

# Extrapolate weekly dates for Point Leo based on Week 1 date
start_date = datetime(2024, 8, 9)  # August 9, 2024, as the starting point
week_columns = [col for col in point_leo_df.columns[3:] if "Week" in col]  # Exclude first 3 detail columns
point_leo_dates = [start_date + timedelta(weeks=i) for i in range(len(week_columns))]

# Get the min and max dates for Point Leo
min_date_point_leo = min(point_leo_dates)
max_date_point_leo = max(point_leo_dates)

# Sidebar with date information
st.sidebar.title("Data Availability")
st.sidebar.write("### Telemetry Data Date Range")
st.sidebar.write(f"Min Date: {min_date_telemetry.strftime('%Y-%m-%d')}")
st.sidebar.write(f"Max Date: {max_date_telemetry.strftime('%Y-%m-%d')}")

st.sidebar.write("### Point Leo Data Date Range")
st.sidebar.write(f"Min Date: {min_date_point_leo.strftime('%Y-%m-%d')}")
st.sidebar.write(f"Max Date: {max_date_point_leo.strftime('%Y-%m-%d')}")

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
