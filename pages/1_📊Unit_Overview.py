import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
from utils.data_loader import load_all_data
from utils.functions import (
    calculate_change, process_sequence_states, 
    calculate_state_metrics, prepare_state_distribution_data,
    calculate_state_transitions, calculate_state_durations
)

# Page config
st.set_page_config(page_title="Overview Dashboard", page_icon="📊", layout="wide")

def calculate_change(current, previous):
    """Calculate percentage change between periods"""
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def generate_dummy_energy_data(start_date, days=30):
    """Generate dummy energy consumption data"""
    # Use pd.date_range for more efficient date generation
    hourly_dates = pd.date_range(start=start_date, periods=days*24, freq='H')
    hourly_usage = []
    
    for dt in hourly_dates:
        hour = dt.hour
        base_load = random.uniform(80, 120)
        time_factor = 1.0
        if 9 <= hour <= 17:  # Higher usage during working hours
            time_factor = 1.5
        elif 0 <= hour <= 5:  # Lower usage during night
            time_factor = 0.6
        hourly_usage.append(base_load * time_factor)
    
    return pd.DataFrame({
        'datetime': hourly_dates,
        'kw_usage': hourly_usage,
        'date': hourly_dates.date
    })

def generate_dummy_production_data(start_date, days=30):
    """Generate dummy water production data"""
    dates = [start_date + timedelta(days=x) for x in range(days)]
    return pd.DataFrame({
        'date': dates,
        'water_treated': [random.uniform(8000, 12000) for _ in range(days)],
        'water_consumed': [random.uniform(200, 400) for _ in range(days)],
        'water_quality': [random.uniform(90, 99) for _ in range(days)],
        'pressure': [random.uniform(45, 55) for _ in range(days)]
    })

def create_energy_metrics(energy_df):
    """Create energy consumption metrics and charts"""
    # Calculate period metrics
    current_daily_avg = energy_df.loc[energy_df['datetime'] >= (energy_df['datetime'].max() - timedelta(days=7)), 'kw_usage'].mean()
    previous_daily_avg = energy_df.loc[(energy_df['datetime'] >= (energy_df['datetime'].max() - timedelta(days=14))) & 
                                     (energy_df['datetime'] < (energy_df['datetime'].max() - timedelta(days=7))), 'kw_usage'].mean()
    change = calculate_change(current_daily_avg, previous_daily_avg)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Average Usage", 
                 f"{current_daily_avg:.1f} kW",
                 f"{change:+.1f}% vs previous week",
                 delta_color="inverse")
    
    peak_usage = energy_df['kw_usage'].max()
    previous_peak = energy_df.loc[energy_df['datetime'] < (energy_df['datetime'].max() - timedelta(days=7)), 'kw_usage'].max()
    peak_change = calculate_change(peak_usage, previous_peak)
    
    with col2:
        st.metric("Peak Usage",
                 f"{peak_usage:.1f} kW",
                 f"{peak_change:+.1f}% vs previous week",
                 delta_color="inverse")
    
    with col3:
        # Fix: Combine ranges properly using list
        off_peak_hours = list(range(22, 24)) + list(range(0, 6))
        off_peak_avg = energy_df.loc[energy_df['datetime'].dt.hour.isin(off_peak_hours), 'kw_usage'].mean()
        st.metric("Off-Peak Average",
                 f"{off_peak_avg:.1f} kW")

    # Daily usage column chart
    daily_usage = energy_df.groupby('date')['kw_usage'].mean().reset_index()
    fig_daily = go.Figure(data=[
        go.Bar(x=daily_usage['date'],
               y=daily_usage['kw_usage'],
               name='Daily Usage',
               marker_color='#2E86C1')
    ])
    fig_daily.update_layout(
        title='Daily Energy Usage',
        xaxis_title='Date',
        yaxis_title='Average kW',
        height=400
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    # Hourly usage pattern
    col1, col2 = st.columns(2)
    
    with col1:
        # 24-hour usage pattern
        hourly_avg = energy_df.groupby(energy_df['datetime'].dt.hour)['kw_usage'].mean()
        fig_hourly = go.Figure(data=[
            go.Scatter(x=hourly_avg.index,
                      y=hourly_avg.values,
                      fill='tozeroy',
                      name='Average Usage',
                      line=dict(color='#2E86C1'))
        ])
        fig_hourly.update_layout(
            title='24-Hour Usage Pattern',
            xaxis_title='Hour of Day',
            yaxis_title='Average kW',
            height=300
        )
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    with col2:
        # Usage by day of week
        dow_avg = energy_df.groupby(energy_df['datetime'].dt.day_name())['kw_usage'].mean()
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_avg = dow_avg.reindex(days_order)
        
        fig_dow = go.Figure(data=[
            go.Bar(x=dow_avg.index,
                  y=dow_avg.values,
                  marker_color='#2E86C1')
        ])
        fig_dow.update_layout(
            title='Usage by Day of Week',
            xaxis_title='Day',
            yaxis_title='Average kW',
            height=300
        )
        st.plotly_chart(fig_dow, use_container_width=True)

def create_efficiency_metrics(sequences_df, sequence_states_df):
    """Create and display system efficiency metrics and visualizations based on sequence data"""
    
    # Merge sequences with state information
    sequences_df['code'] = pd.to_numeric(sequences_df['code'], errors='coerce')
    analysis_df = pd.merge(
        sequences_df,
        sequence_states_df,
        left_on='code',
        right_on='State ID',
        how='left'
    )
    
    # Calculate durations between state changes
    analysis_df['duration'] = analysis_df['timestamp'].diff(-1).dt.total_seconds().abs() / 60
    analysis_df['duration'] = analysis_df['duration'].fillna(analysis_df['duration'].median())
    analysis_df['date'] = analysis_df['timestamp'].dt.date
    analysis_df['hour'] = analysis_df['timestamp'].dt.hour
    
    # Setup visualization controls in sidebar only
    st.sidebar.header("Visualization Settings")
    view_type = st.sidebar.radio("View Type", ["Hours", "Ratio"])
    show_manufacturing = st.sidebar.checkbox("Show Manufacturing States", value=False)

    # Process state categories
    state_categories = {
        'Water Production': 'Production',
        'Cleaning & Disinfection': 'Maintenance',
        'Testing': 'Testing',
        'System Management': 'System',
        'Manufacturing': 'Manufacturing',
        'In-Field Self Test': 'Testing'
    }
    
    # Apply state categories
    analysis_df['State Type'] = analysis_df['State Type'].map(state_categories)
    
    # Filter out manufacturing states if not selected
    filtered_df = analysis_df.copy()
    if not show_manufacturing:
        filtered_df = filtered_df[~filtered_df['State Type'].isin(['Manufacturing', 'Testing'])]
    
    # Add option for handling days over 24 hours
    st.sidebar.subheader("Time Handling")
    time_handling = st.sidebar.radio(
        "Days Over 24 Hours",
        ["Hide", "Clean Split", "Raw Split", "Show All"],
        help="Hide: Remove days over 24h\nClean Split: Split and validate state logic\nRaw Split: Basic chronological split\nShow All: Show actual durations"
    )
    
    # Process daily durations based on selected handling method
    if time_handling != "Show All":
        # Calculate daily totals
        daily_totals = filtered_df.groupby('date')['duration'].sum().reset_index()
        
        if time_handling == "Hide":
            # Filter out days over 24 hours
            valid_days = daily_totals[daily_totals['duration'] <= 24 * 60]['date']
            filtered_df = filtered_df[filtered_df['date'].isin(valid_days)]
        
        elif time_handling in ["Clean Split", "Raw Split"]:
            # Sort by timestamp to maintain chronological order
            filtered_df = filtered_df.sort_values('timestamp')
            
            # Initialize new dataframe for split states
            split_states = []
            current_day_duration = 0
            current_date = filtered_df['date'].iloc[0]
            prev_state_type = None
            
            for _, row in filtered_df.iterrows():
                state_duration = row['duration']
                remaining_time = (24 * 60) - current_day_duration
                
                if current_day_duration + state_duration <= 24 * 60:
                    # State fits in current day
                    if time_handling == "Clean Split":
                        # Validate state transition
                        if prev_state_type == row['State Type'] and prev_state_type in ['Maintenance', 'System']:
                            # Skip duplicate maintenance/system states
                            continue
                    split_states.append(row)
                    current_day_duration += state_duration
                    prev_state_type = row['State Type']
                else:
                    # Split state across days
                    if remaining_time > 0:
                        # Add portion to current day
                        first_part = row.copy()
                        first_part['duration'] = remaining_time
                        if time_handling == "Clean Split":
                            if not (prev_state_type == row['State Type'] and prev_state_type in ['Maintenance', 'System']):
                                split_states.append(first_part)
                                prev_state_type = row['State Type']
                        else:
                            split_states.append(first_part)
                    
                    # Add remaining duration to next day(s)
                    remaining_duration = state_duration - remaining_time
                    while remaining_duration > 0:
                        current_date = current_date + pd.Timedelta(days=1)
                        current_day_duration = 0
                        
                        next_part = row.copy()
                        next_part['date'] = current_date
                        next_duration = min(24 * 60, remaining_duration)
                        
                        if time_handling == "Clean Split":
                            # For clean split, don't allow maintenance/system states to span multiple days
                            if row['State Type'] in ['Maintenance', 'System']:
                                next_duration = min(next_duration, 8 * 60)  # Max 8 hours for maintenance/system
                            if not (prev_state_type == row['State Type'] and prev_state_type in ['Maintenance', 'System']):
                                next_part['duration'] = next_duration
                                split_states.append(next_part)
                                prev_state_type = row['State Type']
                        else:
                            next_part['duration'] = next_duration
                            split_states.append(next_part)
                        
                        remaining_duration -= next_duration
                        current_day_duration = next_duration
                
                # Check if we need to start a new day
                if row['date'] != current_date:
                    current_date = row['date']
                    current_day_duration = state_duration if time_handling == "Raw Split" else min(state_duration, 8 * 60)
                    prev_state_type = None  # Reset state type at day boundary
            
            filtered_df = pd.DataFrame(split_states)
            
            # Post-processing for Clean Split
            if time_handling == "Clean Split":
                # Group by date and calculate daily totals
                daily_totals = filtered_df.groupby(['date', 'State Type'])['duration'].sum().reset_index()
                daily_sum = daily_totals.groupby('date')['duration'].sum()
                
                # Remove days that still exceed 24 hours
                valid_days = daily_sum[daily_sum <= 24 * 60].index
                filtered_df = filtered_df[filtered_df['date'].isin(valid_days)]
                
                # Additional validation to remove impossible state combinations
                filtered_df = filtered_df.sort_values(['date', 'timestamp'])
                filtered_df['prev_state'] = filtered_df.groupby('date')['State Type'].shift(1)
                filtered_df = filtered_df[
                    ~((filtered_df['State Type'] == filtered_df['prev_state']) & 
                      (filtered_df['State Type'].isin(['Maintenance', 'System'])))
                ]
    
    # Calculate metrics for display
    total_runtime = filtered_df['duration'].sum()
    avg_duration = filtered_df['duration'].mean()
    state_changes = len(filtered_df)
    
    # Calculate production vs cleaning metrics
    production_time = filtered_df[filtered_df['State Type'] == 'Production']['duration'].sum()
    cleaning_time = filtered_df[filtered_df['State Type'] == 'Maintenance']['duration'].sum()
    total_time = production_time + cleaning_time
    
    production_percent = (production_time / total_time * 100) if total_time > 0 else 0
    cleaning_percent = (cleaning_time / total_time * 100) if total_time > 0 else 0
    
    # Production vs Cleaning Summary
    st.subheader("Production vs Maintenance Time")
    cols = st.columns(4)
    
    # Production metrics
    with cols[0]:
        st.metric(
            "Production Time",
            f"{production_time/60:.1f} hours",
            f"{production_percent:.1f}% of total"
        )
    
    # Cleaning metrics
    with cols[1]:
        st.metric(
            "Maintenance Time",
            f"{cleaning_time/60:.1f} hours",
            f"{cleaning_percent:.1f}% of total"
        )
    
    # Production Ratio
    with cols[2]:
        ratio = production_time / cleaning_time if cleaning_time > 0 else float('inf')
        st.metric(
            "Production/Maintenance Ratio",
            f"{ratio:.1f}",
            "Higher is better"
        )
    
    # Total runtime
    with cols[3]:
        st.metric(
            "Total Runtime",
            f"{total_runtime/60:.1f} hours",
            f"{state_changes:,} state changes"
        )

    # Define color scheme for all visualizations
    colors = {
        'Production': '#2ECC71',
        'Maintenance': '#E74C3C',
        'System': '#3498DB',
        'Testing': '#F1C40F',
        'Manufacturing': '#95A5A6'
    }

    # 1. Daily State Distribution
    st.subheader("Daily State Distribution")
    
    daily_states = filtered_df.groupby(['date', 'State Type'])['duration'].sum().reset_index()
    
    if view_type == "Hours":
        daily_pivot = daily_states.pivot(
            index='date',
            columns='State Type',
            values='duration'
        ).fillna(0)
        
        fig_daily = go.Figure()
        colors = {
            'Production': '#2ECC71',
            'Maintenance': '#E74C3C',
            'System': '#3498DB',
            'Testing': '#F1C40F',
            'Manufacturing': '#95A5A6'
        }
        
        for state in daily_pivot.columns:
            fig_daily.add_trace(go.Bar(
                name=state,
                x=daily_pivot.index,
                y=daily_pivot[state] / 60,  # Convert to hours
                marker_color=colors.get(state, '#95A5A6')
            ))
        
        fig_daily.update_layout(
            barmode='stack',
            title='Daily State Distribution (Hours)',
            xaxis_title='Date',
            yaxis_title='Hours',
            height=400,
            hovermode='x unified'
        )
    else:
        # Calculate percentages
        daily_total = daily_states.groupby('date')['duration'].sum().reset_index()
        daily_states = daily_states.merge(daily_total, on='date', suffixes=('', '_total'))
        daily_states['percentage'] = (daily_states['duration'] / daily_states['duration_total']) * 100
        
        daily_pivot = daily_states.pivot(
            index='date',
            columns='State Type',
            values='percentage'
        ).fillna(0)
        
        fig_daily = go.Figure()
        for state in daily_pivot.columns:
            fig_daily.add_trace(go.Bar(
                name=state,
                x=daily_pivot.index,
                y=daily_pivot[state],
                marker_color=colors.get(state, '#95A5A6')
            ))
            
        fig_daily.update_layout(
            barmode='stack',
            title='Daily State Distribution (%)',
            xaxis_title='Date',
            yaxis_title='Percentage',
            height=400,
            hovermode='x unified',
            yaxis_range=[0, 100]
        )
    
    st.plotly_chart(fig_daily, use_container_width=True)

    # 2. Average Day Pattern
    st.subheader("Average Day State Distribution")
    
    hourly_states = filtered_df.groupby(['hour', 'State Type'])['duration'].sum().reset_index()
    hourly_total = hourly_states.groupby('hour')['duration'].sum().reset_index()
    hourly_states = hourly_states.merge(hourly_total, on='hour', suffixes=('', '_total'))
    hourly_states['percentage'] = (hourly_states['duration'] / hourly_states['duration_total']) * 100
    
    hourly_pivot = hourly_states.pivot(
        index='State Type',
        columns='hour',
        values='percentage'
    ).fillna(0)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=hourly_pivot.values,
        x=[f"{hour:02d}:00" for hour in range(24)],
        y=hourly_pivot.index,
        colorscale='Viridis',
        hovertemplate="Hour: %{x}<br>State: %{y}<br>Percentage: %{z:.1f}%<extra></extra>"
    ))
    
    fig_heatmap.update_layout(
        title="Hourly State Distribution",
        xaxis_title="Hour of Day",
        yaxis_title="State Type",
        height=400
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # 3. State Transition Flow (Sankey)
    st.subheader("State Transition Flow")
    
    transitions = filtered_df[['State Type', 'timestamp']].copy()
    transitions['next_state'] = transitions['State Type'].shift(-1)
    transitions = transitions.dropna()
    
    transition_counts = transitions.groupby(['State Type', 'next_state']).size().reset_index(name='value')
    
    # Create node lists and map indices
    unique_states = list(set(transition_counts['State Type'].unique()) | 
                        set(transition_counts['next_state'].unique()))
    state_to_index = {state: idx for idx, state in enumerate(unique_states)}
    
    sankey_data = dict(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=unique_states,
            color=[colors.get(state, '#95A5A6') for state in unique_states]
        ),
        link=dict(
            source=[state_to_index[row['State Type']] for _, row in transition_counts.iterrows()],
            target=[state_to_index[row['next_state']] for _, row in transition_counts.iterrows()],
            value=transition_counts['value'],
            color=[f"rgba{tuple(int(colors.get(row['State Type'], '#95A5A6').lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.4,)}"
                  for _, row in transition_counts.iterrows()]
        )
    )
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node=sankey_data['node'],
        link=sankey_data['link']
    )])
    
    fig_sankey.update_layout(
        title="State Transition Flow",
        height=400
    )
    
    st.plotly_chart(fig_sankey, use_container_width=True)

def create_production_metrics(production_df):
    """Create water production metrics and charts"""
    # Calculate period metrics
    current_treated = production_df['water_treated'].tail(7).mean()
    previous_treated = production_df['water_treated'].iloc[-14:-7].mean()
    treated_change = calculate_change(current_treated, previous_treated)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Water Treated",
                 f"{current_treated:.0f} L",
                 f"{treated_change:+.1f}% vs previous week")
    
    current_consumed = production_df['water_consumed'].tail(7).mean()
    previous_consumed = production_df['water_consumed'].iloc[-14:-7].mean()
    consumed_change = calculate_change(current_consumed, previous_consumed)
    
    with col2:
        st.metric("Daily Water Consumed",
                 f"{current_consumed:.0f} L",
                 f"{consumed_change:+.1f}% vs previous week",
                 delta_color="inverse")
    
    current_quality = production_df['water_quality'].tail(7).mean()
    previous_quality = production_df['water_quality'].iloc[-14:-7].mean()
    quality_change = calculate_change(current_quality, previous_quality)
    
    with col3:
        st.metric("Water Quality",
                 f"{current_quality:.1f}%",
                 f"{quality_change:+.1f}% vs previous week")

    # Production vs Consumption Chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=production_df['date'],
        y=production_df['water_treated'],
        name='Water Treated',
        line=dict(color='#1E90FF', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=production_df['date'],
        y=production_df['water_consumed'],
        name='Water Consumed',
        line=dict(color='#8B4513', width=2)
    ))
    
    fig.update_layout(
        title='Daily Water Production vs Consumption',
        xaxis_title='Date',
        yaxis_title='Liters',
        height=400,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Additional charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Water quality trend
        fig_quality = go.Figure()
        fig_quality.add_trace(go.Scatter(
            x=production_df['date'],
            y=production_df['water_quality'],
            fill='tozeroy',
            name='Quality',
            line=dict(color='#1E90FF')
        ))
        fig_quality.update_layout(
            title='Water Quality Trend',
            xaxis_title='Date',
            yaxis_title='Quality (%)',
            height=300,
            yaxis=dict(range=[85, 100])  # Adjust range to better show quality variations
        )
        st.plotly_chart(fig_quality, use_container_width=True)
    
    with col2:
        # System pressure trend
        fig_pressure = go.Figure()
        fig_pressure.add_trace(go.Scatter(
            x=production_df['date'],
            y=production_df['pressure'],
            name='Pressure',
            line=dict(color='#2ECC71')
        ))
        fig_pressure.add_trace(go.Scatter(
            x=production_df['date'],
            y=[50] * len(production_df),  # Target pressure line
            name='Target',
            line=dict(color='#E74C3C', dash='dash')
        ))
        fig_pressure.update_layout(
            title='System Pressure Monitoring',
            xaxis_title='Date',
            yaxis_title='Pressure (PSI)',
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig_pressure, use_container_width=True)

    # Add efficiency ratio calculation
    production_df['efficiency_ratio'] = production_df['water_treated'] / (production_df['water_consumed'] + 1)  # Add 1 to avoid division by zero
    
    # Efficiency ratio trend
    fig_efficiency = go.Figure()
    fig_efficiency.add_trace(go.Scatter(
        x=production_df['date'],
        y=production_df['efficiency_ratio'],
        fill='tozeroy',
        name='Efficiency Ratio',
        line=dict(color='#9B59B6')
    ))
    fig_efficiency.update_layout(
        title='Production Efficiency Ratio Trend',
        xaxis_title='Date',
        yaxis_title='Efficiency Ratio',
        height=300
    )
    st.plotly_chart(fig_efficiency, use_container_width=True)

def main():
    """Main function to run the dashboard"""
    st.title("Water Treatment Plant Dashboard")
    st.markdown("---")
    
    # Load all data
    data = load_all_data()
    
    # Get sequence data from loaded data
    sequences_df = data['sequences']
    sequence_states_df = data['sequence_states']
    
    ### Generate dummy data for other sections ###
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    energy_df = generate_dummy_energy_data(start_date)
    production_df = generate_dummy_production_data(start_date)
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Production Metrics", "Energy Usage", "System Efficiency"])
    
    with tab1:
        st.header("Water Production Overview")
        create_production_metrics(production_df)
    
    with tab2:
        st.header("Energy Consumption Analysis")
        create_energy_metrics(energy_df)
    
    with tab3:
        st.header("System Efficiency Analysis")
        create_efficiency_metrics(sequences_df, sequence_states_df)
    
    # Add footer with last update time
    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

if __name__ == "__main__":
    main()