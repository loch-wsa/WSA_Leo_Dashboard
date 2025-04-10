import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils.data_loader import load_all_data

# Page config
st.set_page_config(page_title="Performance Analytics", page_icon="📈", layout="wide")

def calculate_uptime_metrics(sequences_df):
    """Calculate system states and durations"""
    states = ['PRODUCTION', 'WAIT', 'TAGOUT', 'SLEEP']
    state_durations = {}
    
    for state in states:
        state_events = sequences_df[sequences_df['message'].str.contains(state, na=False)]
        duration = len(state_events) * 10  # Assuming 10-second intervals between readings
        state_durations[state] = duration
        
    total_time = sum(state_durations.values())
    uptime_percentage = (state_durations.get('PRODUCTION', 0) / total_time * 100) if total_time > 0 else 0
    
    return state_durations, uptime_percentage

def main():
    st.title('📈 Performance Analytics')
    st.markdown("""
        This page provides detailed analysis of system performance, maintenance cycles, and operational efficiency.
        Data is analyzed from system events, alarms, and telemetry to provide insights into operation.
    """)

    try:
        # Load all data using the new data loader
        data = load_all_data()
        
        # Extract specific dataframes
        info_df = data['info']
        alarms_df = data['alarms']
        warnings_df = data['warnings']
        sequences_df = data['sequences']
        telemetry_df = data['telemetry']
        
        # Create tabs for different analyses
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "System Uptime", 
            "Production Efficiency",
            "Maintenance Cycles",
            "CIP Analysis",
            "Power Cycles"
        ])

        with tab1:
            st.header("System Uptime Analysis")
            
            state_durations, uptime_percentage = calculate_uptime_metrics(sequences_df)
            
            # Create metrics display
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("System Uptime", f"{uptime_percentage:.1f}%")
            with col2:
                total_alarms = len(alarms_df)
                st.metric("Total Alarms", total_alarms)
            with col3:
                total_warnings = len(warnings_df)
                st.metric("Total Warnings", total_warnings)
            
            # Create state distribution pie chart
            fig_states = go.Figure(data=[go.Pie(
                labels=list(state_durations.keys()),
                values=list(state_durations.values()),
                hole=.3
            )])
            fig_states.update_layout(title="System State Distribution")
            st.plotly_chart(fig_states, use_container_width=True)

        with tab2:
            st.header("Production Efficiency Metrics")
            
            # Calculate production metrics from telemetry
            production_metrics = {
                'Average Flow Rate': telemetry_df['FTR102_FLOWRATE'].mean() if 'FTR102_FLOWRATE' in telemetry_df.columns else 0,
                'Max Flow Rate': telemetry_df['FTR102_FLOWRATE'].max() if 'FTR102_FLOWRATE' in telemetry_df.columns else 0,
                'Average TMP': telemetry_df['FLU101_TMP'].mean() if 'FLU101_TMP' in telemetry_df.columns else 0,
                'Average UV Dose': telemetry_df['UVM101_DOSE'].mean() if 'UVM101_DOSE' in telemetry_df.columns else 0
            }
            
            # Display production metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Avg Flow Rate", f"{production_metrics['Average Flow Rate']:.1f} L/min")
            with col2:
                st.metric("Max Flow Rate", f"{production_metrics['Max Flow Rate']:.1f} L/min")
            with col3:
                st.metric("Avg TMP", f"{production_metrics['Average TMP']:.2f} bar")
            with col4:
                st.metric("Avg UV Dose", f"{production_metrics['Average UV Dose']:.1f} mJ/cm²")
            
            # Create flow rate over time chart
            if 'FTR102_FLOWRATE' in telemetry_df.columns:
                fig_flow = px.line(telemetry_df, x='timestamp', y='FTR102_FLOWRATE',
                                 title='System Flow Rate Over Time')
                fig_flow.update_layout(yaxis_title="Flow Rate (L/min)")
                st.plotly_chart(fig_flow, use_container_width=True)

        with tab3:
            st.header("Maintenance Cycle Tracking")
            
            # Analyze maintenance-related sequences
            maintenance_sequences = sequences_df[
                sequences_df['message'].str.contains('MEMBRANEDIRECTINTEGRITYTEST|MEMBRANEAIRSCOUR|PREFILTERFLUSHCLEAN', na=False)
            ]
            
            # Group maintenance events by type
            maintenance_counts = maintenance_sequences.groupby(
                maintenance_sequences['message'].apply(
                    lambda x: 'Membrane DIT' if 'MEMBRANEDIRECTINTEGRITYTEST' in str(x)
                    else 'Membrane Air Scour' if 'MEMBRANEAIRSCOUR' in str(x)
                    else 'Pre-filter Flush'
                )
            ).size()
            
            # Create maintenance events bar chart
            if not maintenance_counts.empty:
                fig_maintenance = go.Figure(data=[
                    go.Bar(x=maintenance_counts.index, y=maintenance_counts.values)
                ])
                fig_maintenance.update_layout(
                    title="Maintenance Events by Type",
                    xaxis_title="Maintenance Type",
                    yaxis_title="Number of Events"
                )
                st.plotly_chart(fig_maintenance, use_container_width=True)
            
            # Display maintenance timeline
            if not maintenance_sequences.empty:
                maintenance_sequences['Type'] = maintenance_sequences['message'].apply(
                    lambda x: 'Membrane DIT' if 'MEMBRANEDIRECTINTEGRITYTEST' in str(x)
                    else 'Membrane Air Scour' if 'MEMBRANEAIRSCOUR' in str(x)
                    else 'Pre-filter Flush'
                )
                
                fig_timeline = px.scatter(maintenance_sequences, x='timestamp', y='Type',
                                        title='Maintenance Event Timeline')
                st.plotly_chart(fig_timeline, use_container_width=True)

        with tab4:
            st.header("Clean-in-Place (CIP) Cycle Analysis")
            
            # Analyze CIP sequences and outcomes
            cip_sequences = sequences_df[
                sequences_df['message'].str.contains('CLEAN|CIP|FLUSH', na=False)
            ]
            
            # Calculate CIP metrics
            total_cip = len(cip_sequences)
            
            # Display CIP metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total CIP Cycles", total_cip)
            with col2:
                if not cip_sequences.empty:
                    avg_duration = (cip_sequences['timestamp'].diff().mean().total_seconds() / 60)
                    st.metric("Avg CIP Duration", f"{avg_duration:.0f} min")
            
            # Create CIP timeline visualization
            if not cip_sequences.empty:
                fig_cip = px.scatter(cip_sequences, x='timestamp', y='message',
                                    title='CIP Event Timeline')
                st.plotly_chart(fig_cip, use_container_width=True)
            
                # Display alarms during CIP
                cip_alarms = alarms_df[
                    alarms_df['timestamp'].isin(cip_sequences['timestamp'])
                ]
                
                if not cip_alarms.empty:
                    st.subheader("Alarms During CIP Cycles")
                    st.dataframe(cip_alarms[['timestamp', 'message']], use_container_width=True)

            # Add line chart for pressure differences
            st.subheader("Pressure Trends During CIP Cycles")
            
            pressure_cols = ['FLM101_PRESSUREDIFF', 'FLM102_PRESSUREDIFF']
            if all(col in telemetry_df.columns for col in pressure_cols):
                fig_pressure = go.Figure()
                for col in pressure_cols:
                    fig_pressure.add_trace(go.Scatter(
                        x=telemetry_df['timestamp'],
                        y=telemetry_df[col],
                        mode='lines',
                        name=col,
                        line=dict(width=2)
                    ))
                
                fig_pressure.update_layout(
                    title="Pressure Differences Over Time",
                    xaxis_title="Timestamp",
                    yaxis_title="Pressure (bar)",
                    legend_title="Pressure Sensor",
                    height=400
                )
                
                st.plotly_chart(fig_pressure, use_container_width=True)

        with tab5:
            st.header("Power Cycle Analysis")
            
            # Define what constitutes a cycle for each component
            components = {
                'UV System': ['START', 'WAIT', 'PRODUCTION'],
                'Membrane': ['MEMBRANEDIRECTINTEGRITYTEST', 'MEMBRANEREFILL'],
                'Pre-filter': ['PREFILTERFLUSH'],
                'Feed Pump': ['PRODUCTION', 'WAIT'],
                'System': ['START', 'TAGOUT']
            }
            
            # Calculate cycle metrics for each component
            cycle_metrics = []
            
            for component, states in components.items():
                component_sequences = sequences_df[
                    sequences_df['message'].str.contains('|'.join(states), na=False)
                ].copy()
                
                if len(component_sequences) > 0:
                    time_diffs = component_sequences['timestamp'].diff()
                    time_diffs_minutes = time_diffs.dt.total_seconds() / 60
                    period_duration = (component_sequences['timestamp'].max() - 
                                     component_sequences['timestamp'].min()).total_seconds() / (24 * 60 * 60)
                    
                    cycle_metrics.append({
                        'Component': component,
                        'Total Cycles': len(component_sequences),
                        'Min Time Between (min)': time_diffs_minutes.min() if not time_diffs_minutes.empty else 0,
                        'Max Time Between (min)': time_diffs_minutes.max() if not time_diffs_minutes.empty else 0,
                        'Avg Time Between (min)': time_diffs_minutes.mean() if not time_diffs_minutes.empty else 0,
                        'Cycles per Day': len(component_sequences) / period_duration if period_duration > 0 else 0
                    })
                else:
                    cycle_metrics.append({
                        'Component': component,
                        'Total Cycles': 0,
                        'Min Time Between (min)': 0,
                        'Max Time Between (min)': 0,
                        'Avg Time Between (min)': 0,
                        'Cycles per Day': 0
                    })

            # Display summary metrics
            cols = st.columns(len(components))
            for i, data in enumerate(cycle_metrics):
                with cols[i]:
                    st.metric(
                        f"{data['Component']}", 
                        f"{int(data['Total Cycles'])} cycles",
                        f"{data['Cycles per Day']:.1f}/day"
                    )

            # Create detailed metrics table
            st.markdown("### Detailed Cycle Metrics")
            cycle_df = pd.DataFrame(cycle_metrics)
            formatted_df = cycle_df.copy()
            for col in ['Min Time Between (min)', 'Max Time Between (min)', 
                        'Avg Time Between (min)', 'Cycles per Day']:
                formatted_df[col] = formatted_df[col].round(1)
            st.dataframe(formatted_df.set_index('Component'), use_container_width=True)

            # Create timeline visualization
            st.markdown("### Component Cycling Timeline")
            timeline_data = []
            for component, states in components.items():
                component_sequences = sequences_df[
                    sequences_df['message'].str.contains('|'.join(states), na=False)
                ]
                
                for _, row in component_sequences.iterrows():
                    timeline_data.append({
                        'Component': component,
                        'Timestamp': row['timestamp'],
                        'State': row['message']
                    })
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                fig_timeline = px.scatter(
                    timeline_df, 
                    x='Timestamp', 
                    y='Component',
                    hover_data=['State'],
                    title='Component Power Cycles Over Time'
                )
                fig_timeline.update_traces(marker=dict(size=10))
                fig_timeline.update_layout(height=400)
                st.plotly_chart(fig_timeline, use_container_width=True)

                # Add insights about cycling patterns
                st.markdown("### Cycling Pattern Insights")
                for component, data in zip(components.keys(), cycle_metrics):
                    if data['Total Cycles'] > 0:
                        st.markdown(f"""
                        - **{component}**: {int(data['Total Cycles'])} cycles total, averaging 
                        {data['Cycles per Day']:.1f} cycles per day. Typical time between cycles: 
                        {data['Avg Time Between (min)']:.1f} minutes.
                        """)
            else:
                st.warning("No cycle data available for visualization")

    except Exception as e:
        st.error(f"Error loading or processing data: {str(e)}")
        st.write("Error details:", str(e))

if __name__ == "__main__":
    main()