import streamlit as st
import pandas as pd
import os
from glob import glob
from functools import lru_cache
from datetime import datetime
import pytz

@lru_cache(maxsize=None)
def process_data(value):
    """Process data values with caching for better performance"""
    try:
        if isinstance(value, str):
            if value.startswith('<'):
                return float(value.strip('<'))
            elif value.startswith('>'):
                value = value.strip('>')
                if value.isdigit():
                    return float(value)
                return 2000
            elif value == 'N/R':
                return 0
            elif value.endswith('LINT'):
                return float(value.split()[0].strip('<'))
            try:
                return float(value)
            except ValueError:
                return 0
        elif value is None:
            return 0
        else:
            return float(value)
    except Exception:
        return 0

def normalize_parameter(value, param, min_val, max_val):
    """Normalize parameter values with special handling for pH"""
    param_str = str(param).upper()
    
    if param_str == 'PH':
        try:
            value = float(value)
            diff_from_neutral = abs(value - 7.0)
            max_deviation = max(abs(max_val - 7), abs(min_val - 7))
            return diff_from_neutral / max_deviation if max_deviation != 0 else 0
        except (ValueError, TypeError):
            return 0
    else:
        try:
            value = float(value)
            range_size = max_val - min_val
            return (value - min_val) / range_size if range_size != 0 else 0
        except (ValueError, TypeError):
            return 0

def prepare_ranges_data(ranges_df):
    """Prepare ranges data by processing min/max values"""
    processed_df = ranges_df.copy()
    
    # Convert Min/Max to numeric values
    processed_df['Min'] = processed_df['Min'].apply(lambda x: 0 if x == 'N/A' else process_data(x))
    processed_df['Max'] = processed_df['Max'].apply(lambda x: process_data(x) if x != 'Varies By Compound' else 1)
    
    # Keep all rows, whether they have ALS Lookup or not
    processed_df = processed_df.copy()
    
    return processed_df

@st.cache_data(ttl=3600)
def load_all_data():
    """
    Load all data files with caching.
    Returns a dictionary containing all the loaded dataframes.
    """
    try:
        data = {}
        
        # Load info data
        data['info'] = load_csv_directory('data/info', 'Info *.csv')
        data['alarms'] = load_csv_directory('data/alarms', 'Alarms *.csv')
        data['warnings'] = load_csv_directory('data/warnings', 'Warnings *.csv')
        data['telemetry'] = load_csv_directory('data/telemetry', 'Telemetry *.csv')
        
        # Load sequences data
        data['sequences'] = load_sequence_files()
        data['sequence_states'] = load_sequence_states()
        
        # Load static data files
        data['assets'] = pd.read_csv('data/Assets.csv')
        data['thresholds'] = pd.read_csv('data/Thresholds.csv')
        
        # Load water quality data
        data['influent_data'] = pd.read_csv('data/Influent Water.csv')
        data['treated_data'] = pd.read_csv('data/Treated Water.csv')
        
        # Load parameter ranges
        influent_ranges = pd.read_csv('data/Influent Parameters.csv')
        treated_ranges = pd.read_csv('data/Treated Parameters.csv')
        
        # Process ranges data and remove empty ALS Lookup entries
        data['influent_ranges'] = prepare_ranges_data(influent_ranges)
        data['treated_ranges'] = prepare_ranges_data(treated_ranges)
        
        return data
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        raise e

def load_sequence_files(directory_path="data/sequences"):
    """Load and combine all sequence CSV files"""
    csv_files = glob(os.path.join(directory_path, "Sequences *.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No Sequence CSV files found in {directory_path}")
    
    dfs = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, low_memory=False)
            df['_source_file'] = os.path.basename(file)
            dfs.append(df)
        except Exception as e:
            st.warning(f"Error loading {file}: {str(e)}")
            continue
    
    if not dfs:
        raise ValueError(f"No valid Sequence CSV files could be loaded from {directory_path}")
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Convert timestamp to datetime
    combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], format="mixed", dayfirst=False, utc=True)
    
    # Sort by timestamp and remove duplicates
    combined_df = combined_df.sort_values('timestamp')
    combined_df = combined_df.drop_duplicates(
        subset=[col for col in combined_df.columns if col != '_source_file'], 
        keep='last'
    )
    
    combined_df = combined_df.drop('_source_file', axis=1)
    return combined_df

def load_sequence_states(file_path="data/Sequence States.csv"):
    """Load sequence states mapping file"""
    try:
        states_df = pd.read_csv(file_path)
        # Ensure State ID is numeric for matching
        states_df['State ID'] = pd.to_numeric(states_df['State ID'], errors='coerce')
        return states_df
    except Exception as e:
        st.error(f"Error loading sequence states: {str(e)}")
        raise
        
def get_chart_data(week_num, params, data_type='influent', show_comparison=False):
    """Get processed data ready for charting"""
    # Load data
    influent_data, treated_data, influent_ranges, treated_ranges = load_data()
    
    # Filter and prepare primary data
    primary_df = treated_data if data_type == 'treated' else influent_data
    primary_ranges = treated_ranges if data_type == 'treated' else influent_ranges
    
    # Match parameters using ALS Lookup
    matched_params = primary_ranges[primary_ranges['ALS Lookup'].isin(params)]
    
    result = {
        'primary': prepare_chart_data(
            primary_df,
            matched_params,
            'ALS Lookup',
            week_num
        )
    }
    
    if show_comparison:
        comparison_df = influent_data if data_type == 'treated' else treated_data
        comparison_ranges = influent_ranges if data_type == 'treated' else treated_ranges
        
        result['comparison'] = prepare_chart_data(
            comparison_df,
            matched_params,
            'ALS Lookup',
            week_num
        )
    
    return result

def load_csv_directory(directory_path, pattern="*.csv"):
    # Get list of all matching CSV files
    csv_files = glob(os.path.join(directory_path, pattern))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {directory_path} matching pattern {pattern}")
    
    # Load each CSV file
    dfs = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, low_memory=False)
            df['_source_file'] = os.path.basename(file)
            dfs.append(df)
        except Exception as e:
            st.warning(f"Error loading {file}: {str(e)}")
            continue
    
    if not dfs:
        raise ValueError(f"No valid CSV files could be loaded from {directory_path}")
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    if 'timestamp' in combined_df.columns:
        combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], format="mixed", dayfirst=False, utc=True)
        melbourne_tz = pytz.timezone('Australia/Melbourne')
        combined_df['timestamp'] = combined_df['timestamp'].dt.tz_convert(melbourne_tz)
        combined_df = combined_df.sort_values('timestamp')
        combined_df = combined_df.drop_duplicates(
            subset=[col for col in combined_df.columns if col != '_source_file'], 
            keep='last'
        )
    
    combined_df = combined_df.drop('_source_file', axis=1)
    return combined_df