import pandas as pd
from datetime import datetime, timedelta

def calculate_change(current, previous):
    """Calculate percentage change between periods"""
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def calculate_durations(sequences_df):
    """Calculate durations between state changes"""
    # Sort by timestamp
    sequences_df = sequences_df.sort_values('timestamp')
    
    # Convert timestamp to datetime if not already
    sequences_df['timestamp'] = pd.to_datetime(sequences_df['timestamp'])
    
    # Calculate duration until next state change in minutes
    sequences_df['duration'] = sequences_df['timestamp'].diff(-1).dt.total_seconds().abs() / 60
    
    # Handle the last row (use median duration as an estimate)
    sequences_df['duration'] = sequences_df['duration'].fillna(sequences_df['duration'].median())
    
    return sequences_df

def process_sequence_states(sequences_df, state_mapping_df):
    """Process sequence states with mapping from the CSV"""
    try:
        # Calculate durations between state changes
        sequences_df = calculate_durations(sequences_df)
        
        # Ensure code and State ID are integers for mapping
        sequences_df['code'] = pd.to_numeric(sequences_df['code'], errors='coerce').fillna(0).astype(int)
        state_mapping_df['State ID'] = pd.to_numeric(state_mapping_df['State ID'], errors='coerce').fillna(0).astype(int)
        
        # Create mappings from Sequence States
        name_mapping = dict(zip(state_mapping_df['State ID'], state_mapping_df['Sequence Name']))
        type_mapping = dict(zip(state_mapping_df['State ID'], state_mapping_df['State Type']))
        
        # Map codes to names and types
        sequences_df['state_name'] = sequences_df['code'].map(name_mapping).fillna('Unknown')
        sequences_df['state_type'] = sequences_df['code'].map(type_mapping).fillna('Other')
        
        # Define state categories based on the State Type
        state_categories = {
            'Production': ['Water Production'],
            'System': ['System Management'],
            'Cleaning': ['Cleaning & Disinfection'],
            'Other': ['Other']
        }
        
        # Map state types to categories
        def map_to_category(state_type):
            for category, types in state_categories.items():
                if state_type in types:
                    return category
            return 'Other'
        
        sequences_df['category'] = sequences_df['state_type'].apply(map_to_category)
        
        return sequences_df, state_categories
        
    except Exception as e:
        print(f"Error in process_sequence_states: {str(e)}")
        print("Sequences DataFrame Info:")
        print(sequences_df.info())
        print("\nState Mapping DataFrame Info:")
        print(state_mapping_df.info())
        raise

def calculate_state_metrics(sequences_df, days=7):
    """Calculate metrics for different state categories"""
    current_date = sequences_df['timestamp'].max()
    previous_period_start = current_date - timedelta(days=days*2)
    current_period_start = current_date - timedelta(days=days)
    
    # Split into current and previous periods
    current_period = sequences_df[sequences_df['timestamp'] >= current_period_start]
    previous_period = sequences_df[(sequences_df['timestamp'] >= previous_period_start) & 
                                 (sequences_df['timestamp'] < current_period_start)]
    
    # Calculate metrics for each period
    def calculate_period_metrics(df):
        total_duration = df['duration'].sum()
        return {
            'production_time': df[df['category'] == 'Production']['duration'].sum(),
            'system_time': df[df['category'] == 'System']['duration'].sum(),
            'cleaning_time': df[df['category'] == 'Cleaning']['duration'].sum(),
            'total_time': total_duration
        }
    
    current_metrics = calculate_period_metrics(current_period)
    previous_metrics = calculate_period_metrics(previous_period)
    
    # Calculate efficiency percentages
    current_efficiency = (current_metrics['production_time'] / current_metrics['total_time'] * 100 
                         if current_metrics['total_time'] > 0 else 0)
    previous_efficiency = (previous_metrics['production_time'] / previous_metrics['total_time'] * 100 
                          if previous_metrics['total_time'] > 0 else 0)
    
    return {
        'current_efficiency': current_efficiency,
        'previous_efficiency': previous_efficiency,
        'current_system': current_metrics['system_time'] / days,
        'previous_system': previous_metrics['system_time'] / days,
        'current_cleaning': current_metrics['cleaning_time'] / days,
        'previous_cleaning': previous_metrics['cleaning_time'] / days
    }

def prepare_state_distribution_data(sequences_df):
    """Prepare data for state distribution visualization"""
    sequences_df['date'] = sequences_df['timestamp'].dt.date
    daily_states = sequences_df.groupby(['date', 'category'])['duration'].sum().reset_index()
    
    # Pivot the data for plotting
    daily_distribution = daily_states.pivot(index='date', 
                                          columns='category', 
                                          values='duration').fillna(0)
    
    return daily_distribution

def calculate_state_transitions(sequences_df):
    """Calculate state transitions for visualization"""
    # Sort by timestamp to ensure correct transition order
    sequences_df = sequences_df.sort_values('timestamp')
    
    transitions = pd.DataFrame({
        'from_state': sequences_df['state_name'].iloc[:-1],
        'to_state': sequences_df['state_name'].iloc[1:],
        'from_category': sequences_df['category'].iloc[:-1],
        'to_category': sequences_df['category'].iloc[1:]
    })
    
    return transitions.groupby(['from_category', 'to_category']).size().reset_index(name='count')

def calculate_state_durations(sequences_df):
    """Calculate average duration by state"""
    return sequences_df.groupby(['category', 'state_name'])['duration'].mean().reset_index()