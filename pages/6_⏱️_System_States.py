import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from utils.data_loader import load_all_data

# Page config
st.set_page_config(page_title="System States Dashboard", page_icon="⚙️", layout="wide")

# Define color map
COLOR_MAP = {
    'START': '#2ecc71',
    'INITIALIZATION': '#2ecc71',
    'PRODUCTION': '#3498db',
    'WAIT': '#f39c12',
    'TAGOUT': '#e74c3c',
    'MEMBRANE_AIRSOUR': '#9b59b6',
    'MEMBRANE_DIT': '#1abc9c',
    'SLEEP': '#95a5a6'
}

def process_sequence_data(sequences_df):
    """Process sequence data for visualization"""
    # Create a copy to avoid warnings
    processed_df = sequences_df.copy()
    
    # Convert timestamps, dropping only invalid ones
    processed_df['timestamp'] = pd.to_datetime(processed_df['timestamp'], errors='coerce')
    processed_df = processed_df.dropna(subset=['timestamp'])
    
    # Map states
    state_map = {
        '2000': 'INITIALIZATION',
        '2002': 'PRODUCTION',
        '2020': 'TAGOUT',
        '2021': 'WAIT',
        '2022': 'MEMBRANE_DIT',
        '2035': 'SLEEP',
        '2076': 'SLEEP',
        'START': 'START',
        'WAIT': 'WAIT',
        'TAGOUT': 'TAGOUT',
        'PRODUCTION': 'PRODUCTION',
        'MEMBRANEAIRSCOUR': 'MEMBRANE_AIRSOUR',
        'MEMBRANEDIRECTINTEGRITYTEST': 'MEMBRANE_DIT'
    }
    
    sequences_df['state'] = sequences_df['code'].astype(str).map(lambda x: state_map.get(x, x))
    sequences_df = sequences_df[sequences_df['state'].isin(state_map.values())]
    
    # Calculate duration
    sequences_df['duration'] = sequences_df['timestamp'].diff().shift(-1).dt.total_seconds() / 60
    
    return sequences_df

def create_state_timeline(df):
    """Create timeline visualization"""
    df_timeline = []

    for _, row in df.iterrows():
        try:
            end_time = row['timestamp'] + pd.Timedelta(minutes=row['duration']) if pd.notna(row['duration']) else row['timestamp']
            color = COLOR_MAP.get(row['state'], '#95a5a6')

            df_timeline.append(dict(
                Task='System State',
                Start=row['timestamp'],
                Finish=end_time,
                State=row['state'],
                Description=row['message'],
                Color=color
            ))
        except Exception:
            continue  # Skip any problematic rows
    
    if not df_timeline:
        return None
        
    fig = ff.create_gantt(
        df_timeline,
        colors=[item['Color'] for item in df_timeline],
        index_col='State',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True
    )
    
    fig.update_layout(
        title='System State Timeline',
        height=400,
        xaxis_title='Time'
    )
    
    return fig

def create_state_summary(df):
    """Create summary statistics"""
    summary = df.groupby('state').agg({
        'duration': ['count', 'sum', 'mean']
    }).round(2)
    
    summary.columns = ['Count', 'Total Duration (min)', 'Avg Duration (min)']
    return summary

def create_transition_sankey(df):
    """Create state transition visualization"""
    try:
        transitions = pd.DataFrame({
            'source': df['state'].iloc[:-1].values,
            'target': df['state'].iloc[1:].values
        })
        
        transition_counts = transitions.groupby(['source', 'target']).size().reset_index(name='value')
        states = pd.unique(transitions[['source', 'target']].values.ravel('K'))
        
        if len(states) < 2:
            return None
            
        node_map = {state: idx for idx, state in enumerate(states)}
        node_colors = [COLOR_MAP.get(state, '#95a5a6') for state in states]
        link_colors = [COLOR_MAP.get(source, '#95a5a6') for source in transition_counts['source']]
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=states,
                color=node_colors
            ),
            link=dict(
                source=[node_map[s] for s in transition_counts['source']],
                target=[node_map[t] for t in transition_counts['target']],
                value=transition_counts['value'],
                color=link_colors
            )
        )])
        
        fig.update_layout(
            title="State Transitions",
            height=500
        )
        
        return fig
    except Exception:
        return None

def create_duration_distribution(df):
    """Create duration distribution visualization"""
    fig = go.Figure()
    
    for state in df['state'].unique():
        state_data = df[df['state'] == state]
        fig.add_trace(go.Box(
            y=state_data['duration'],
            name=state,
            boxpoints='outliers',
            marker_color=COLOR_MAP.get(state, '#95a5a6')
        ))
    
    fig.update_layout(
        title='State Duration Distribution',
        yaxis_title='Duration (minutes)',
        height=400,
        showlegend=True
    )
    
    return fig

def main():
    st.title('⚙️ System States Dashboard')

    try:
        # Load data using the new data loader
        data = load_all_data()
        df = process_sequence_data(data['sequences'])
        
        # Add engineer view toggle in sidebar
        st.sidebar.title('Dashboard Settings')
        engineer_view = st.sidebar.toggle('Engineer View', value=False)
        
        # Filters in sidebar
        st.sidebar.title('Filters')
        
        # Date range filter
        if not df.empty:
            min_date = df['timestamp'].min().date()
            max_date = df['timestamp'].max().date()
            date_range = st.sidebar.date_input(
                'Select Date Range',
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
        else:
            st.error("No valid sequence data available")
            return
        
        # Filter data based on date range
        try:
            start_date = pd.to_datetime(date_range[0])
            end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            filtered_df = df[mask].copy()
            
            if filtered_df.empty:
                st.warning("No data available for the selected date range")
                return
        except Exception as e:
            st.error(f"Error filtering data by date range: {str(e)}")
            return
        
        # Basic metrics visible in both views
        col1, col2, col3 = st.columns(3)
        with col1:
            production_time = filtered_df[filtered_df['state'] == 'PRODUCTION']['duration'].sum()
            production_time = production_time / 60
            st.metric("Total Production Time", f"{production_time:.0f} hours")
        with col2:
            uptime = (production_time / filtered_df['duration'].sum() * 100) if filtered_df['duration'].sum() > 0 else 0
            st.metric("System Uptime", f"{uptime:.1f}%")
        with col3:
            state_changes = len(filtered_df)
            st.metric("State Changes", state_changes)
        
        # Create timeline visualization
        st.subheader('System State Timeline')
        timeline_fig = create_state_timeline(filtered_df)
        if timeline_fig is not None:
            st.plotly_chart(timeline_fig, use_container_width=True)
        else:
            st.warning("Not enough valid data to create timeline visualization")
        
        if engineer_view:
            # Engineer view specific content
            st.subheader('Detailed State Analysis')
            
            # State transitions
            sankey_fig = create_transition_sankey(filtered_df)
            if sankey_fig is not None:
                st.plotly_chart(sankey_fig, use_container_width=True)
            else:
                st.warning("Not enough state transitions to create Sankey diagram")
            
            # Duration distribution
            st.subheader('State Duration Distribution')
            st.plotly_chart(create_duration_distribution(filtered_df), use_container_width=True)
            
            # Detailed state metrics
            st.subheader('Detailed State Metrics')
            detailed_metrics = create_state_summary(filtered_df)
            st.dataframe(detailed_metrics, use_container_width=True)
            
            # Technical state descriptions
            st.subheader('Technical State Descriptions')
            tech_descriptions = """
            - **INITIALIZATION (2000)**: System startup and initialization sequence
            - **PRODUCTION (2002)**: Active water production state
            - **TAGOUT (2020)**: System tagged out for maintenance/errors
            - **WAIT (2021)**: Idle state, ready for operation
            - **MEMBRANE_DIT (2022)**: Direct Integrity Test of membrane
            - **SLEEP (2035/2076)**: Low-power sleep mode
            - **MEMBRANE_AIRSOUR**: Membrane air scouring maintenance
            """
            st.markdown(tech_descriptions)
            
        else:
            # Basic view content
            st.subheader('Basic State Summary')
            basic_states = ['PRODUCTION', 'WAIT', 'TAGOUT']
            basic_summary = create_state_summary(filtered_df[filtered_df['state'].isin(basic_states)])
            st.dataframe(basic_summary, use_container_width=True)
            
            # Basic state descriptions
            st.subheader('State Descriptions')
            basic_descriptions = """
            - **PRODUCTION**: System is actively producing potable water
            - **WAIT**: System is idle but ready to operate
            - **TAGOUT**: System is tagged out for maintenance or due to an error
            """
            st.markdown(basic_descriptions)
        
        # Add warning message for maintenance events
        st.sidebar.markdown('---')
        if engineer_view:
            st.sidebar.warning('Note: Monitor MEMBRANE_DIT and MEMBRANE_AIRSOUR states for maintenance patterns.')
        else:
            st.sidebar.warning('Note: Transitions to TAGOUT state may indicate system errors or maintenance events.')
    
    except Exception as e:
        st.error(f"Error loading or processing data: {str(e)}")
        st.write("Error details:", str(e))

if __name__ == "__main__":
    main()