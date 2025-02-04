import plotly.graph_objects as go
import pandas as pd
import numpy as np
import streamlit as st

def normalize_parameter(value, param_name, min_val, max_val):
    """
    Normalize parameter values with special handling for pH and UVT
    """
    try:
        # Convert string values like '<0.1' to floats
        if isinstance(value, str):
            if value.startswith('<'):
                value = float(value.replace('<', ''))
            elif value == 'N/R':
                return 0
            elif 'LINT' in value:
                value = float(value.split()[0].replace('<', ''))
            else:
                value = float(value)
                
        value = float(value) if value is not None else 0
        min_val = float(min_val) if pd.notna(min_val) else 0
        max_val = float(max_val) if pd.notna(max_val) else 1
        
        param_upper = str(param_name).upper()
        
        if param_upper == 'PH':
            # For pH, calculate difference from 7.5 (optimal)
            optimal_ph = 7.5
            diff_from_optimal = abs(value - optimal_ph)
            max_deviation = max(abs(max_val - optimal_ph), abs(min_val - optimal_ph))
            return diff_from_optimal / max_deviation if max_deviation != 0 else 0
        elif 'UVT' in param_upper:
            # For UVT, invert the normalization since higher is better
            value_range = max_val - min_val
            if value_range == 0:
                return 0
            # Invert the normalization so 100% is at center (0) and 50% is at edge (1)
            normalized = (value - min_val) / value_range
            return 1 - normalized
        else:
            # For all other parameters, use standard normalization
            value_range = max_val - min_val
            if value_range == 0:
                return 0
            return (value - min_val) / value_range
            
    except (ValueError, TypeError):
        return 0

def format_parameter_label(param_name, value, max_val, min_val, unit=""):
    try:
        # Handle string values like '<0.1'
        if isinstance(value, str):
            if value.startswith('<'):
                value = float(value.replace('<', ''))
            elif value == 'N/R':
                return f"{param_name}{unit}"
            elif 'LINT' in value:
                value = float(value.split()[0].replace('<', ''))
            else:
                value = float(value)

        if pd.isna(value) or pd.isna(max_val):
            return f"{param_name}{unit}"

        value = float(value)
        max_val = float(max_val)
        min_val = float(min_val)
        
        unit_text = f" {unit}" if unit else ""
        
        # Determine decimal places based on value
        value_format = '.4f' if value <= 1 else '.1f'
        max_val_format = '.4f' if max_val <= 1 else '.1f'
        
        # Check if value is out of range and add warning icon if needed
        warning_icon = "⚠️ " if (value > max_val or value < min_val) else ""
        
        # Format the base label with current value and max value
        label = f"{warning_icon}{param_name} {value:{value_format}} ({min_val:{max_val_format}} - {max_val:{max_val_format}}) {unit_text}"
        
        return label
        
    except (ValueError, TypeError):
        return f"{param_name}{unit}"

def create_microbial_display(week_num, als_lookups, data_df, ranges_df):
    """Create a display for microbial parameters showing change from initial values"""
    # Get all week columns
    week_cols = [col for col in data_df.columns if col.startswith('Week')]
    week_cols.sort()  # Ensure weeks are in order
    
    # Filter for microbial parameters
    micro_data = data_df[data_df['ALS Lookup'].isin(als_lookups)].copy()
    micro_ranges = ranges_df[ranges_df['ALS Lookup'].isin(als_lookups)].copy()
    
    # Create display for each parameter
    for _, range_row in micro_ranges.iterrows():
        als_lookup = range_row['ALS Lookup']
        param_name = range_row['Parameter']
        unit = range_row['Unit'] if pd.notna(range_row['Unit']) else ''
        max_val = float(range_row['Max']) if pd.notna(range_row['Max']) else None
        min_val = float(range_row['Min']) if pd.notna(range_row['Min']) else None
        
        param_data = micro_data[micro_data['ALS Lookup'] == als_lookup]
        if not param_data.empty:
            # Get values for all weeks
            values = []
            for week in week_cols:
                try:
                    val = param_data[week].iloc[0]
                    if isinstance(val, str):
                        if val.startswith('<'):
                            val = float(val.replace('<', ''))
                        elif val == 'N/R':
                            val = None
                        else:
                            val = float(val)
                    values.append(val)
                except (ValueError, TypeError, IndexError):
                    values.append(None)
            
            # Create metrics display
            if values[0] is not None:  # If we have an initial value
                initial_value = values[0]
                current_value = values[week_num - 1] if week_num <= len(values) else None
                
                if current_value is not None:
                    reduction = ((initial_value - current_value) / initial_value * 100 
                               if initial_value != 0 else 0)
                    
                    # Add warning icon if value is out of range
                    warning_icon = "⚠️ " if (max_val is not None and min_val is not None and 
                                           (current_value > max_val or current_value < min_val)) else ""
                    
                    st.metric(
                        label=f"{warning_icon}{param_name} ({unit})",
                        value=f"{current_value:,.1f}",
                        delta=f"{reduction:,.1f}% reduction" if reduction > 0 else "No reduction",
                        delta_color="normal" if reduction > 0 else "off"
                    )
                else:
                    st.metric(
                        label=f"{param_name} ({unit})",
                        value="No data",
                        delta=None
                    )
            else:
                st.metric(
                    label=f"{param_name} ({unit})",
                    value="No initial data",
                    delta=None
                )

def create_radar_chart(week_num, als_lookups, data_df, treated_data, ranges_df, treated_ranges, chart_type='comparison', category=None):
    """
    Create a radar chart based on the specified type (influent, treated, or comparison)
    """
    week_cols = [col for col in data_df.columns if col.startswith('Week')]
    week_col = f'Week {week_num}'
    
    # Filter data and ranges
    ranges_filtered = ranges_df[ranges_df['ALS Lookup'].isin(als_lookups)].copy()
    data_filtered = data_df[data_df['ALS Lookup'].isin(als_lookups)].copy()
    treated_filtered = treated_data[treated_data['ALS Lookup'].isin(als_lookups)].copy()
    treated_ranges_filtered = treated_ranges[treated_ranges['ALS Lookup'].isin(als_lookups)].copy()
    
    def create_hover_text(param_name, value, min_val, max_val, unit):
        """Create hover text with special handling for pH and UVT"""
        if value is None:
            return f"{param_name}: No data available"
            
        value_format = '.4f' if value <= 1 else '.1f'
        unit_text = f" {unit}" if unit else ""
        
        param_upper = str(param_name).upper()
        
        # Add special notes for pH and UVT
        special_note = ""
        if param_upper == 'PH':
            special_note = "<br>Note: Optimal pH is 7.5"
        elif 'UVT' in param_upper:
            special_note = "<br>Note: Higher UVT % is better"
            
        hover_text = (
            f"{param_name}<br>" +
            f"Value: {value:{value_format}}{unit_text}<br>" +
            f"Range: {min_val:.2f} - {max_val:.2f}{unit_text}" +
            special_note
        )
        
        return hover_text
        
    def process_parameter_data(param_data, param_ranges):
        """Process data for a single dataset"""
        values = []
        normalized_values = []
        labels = []
        hover_texts = []
        
        for _, range_row in param_ranges.iterrows():
            als_lookup = range_row['ALS Lookup']
            param_name = range_row['Parameter']
            unit = range_row['Unit'] if pd.notna(range_row['Unit']) else ""
            
            # Get parameter data
            row_data = param_data[param_data['ALS Lookup'] == als_lookup]
            if not row_data.empty and week_col in row_data.columns:
                value = row_data[week_col].iloc[0]
                min_val = float(range_row['Min']) if pd.notna(range_row['Min']) else 0
                max_val = float(range_row['Max']) if pd.notna(range_row['Max']) else 1
                
                # Format value with appropriate decimal places
                if value is not None:
                    if isinstance(value, str):
                        if value.startswith('<'):
                            value = float(value.replace('<', ''))
                        elif value == 'N/R':
                            value = None
                        elif 'LINT' in value:
                            value = float(value.split()[0].replace('<', ''))
                        else:
                            value = float(value)
                    
                    if value is not None:
                        value_format = '.4f' if value <= 1 else '.1f'
                        value_text = f"{value:{value_format}}"
                    else:
                        value_text = "N/A"
                else:
                    value_text = "N/A"
                
                # Create range text with unit
                range_text = f"({min_val:.2f} - {max_val:.2f})"
                if unit:
                    range_text += f" {unit}"
                
                # Check if value is out of range and add warning icon if needed
                warning_icon = "⚠️ " if (value is not None and (value > max_val or value < min_val)) else ""
                
                # Create label based on chart type and availability of comparison data
                if chart_type == 'comparison' and 'raw_treated' in locals():
                    # Calculate improvement percentage for comparison charts
                    treated_val = raw_treated[len(values)] if raw_treated else None
                    if value is not None and treated_val is not None and value != 0:
                        improvement = ((value - treated_val) / value) * 100
                        label = [
                            f"{warning_icon}{param_name}",
                            f"{improvement:.1f}% improvement",
                            f"{value_text} {range_text}"
                        ]
                    else:
                        label = [
                            f"{warning_icon}{param_name}",
                            f"{value_text} {range_text}"
                        ]
                else:
                    label = [
                        f"{warning_icon}{param_name}",
                        f"{value_text} {range_text}"
                    ]
                
                # Join with HTML line breaks for proper multi-line display
                label_text = '<br>'.join(label)
                labels.append(label_text)
                
                # Process and normalize value
                try:
                    if isinstance(value, str):
                        if value.startswith('<'):
                            value = float(value.replace('<', ''))
                        elif value == 'N/R':
                            value = None
                        elif 'LINT' in value:
                            value = float(value.split()[0].replace('<', ''))
                        else:
                            value = float(value)
                except (ValueError, TypeError):
                    value = None
                
                values.append(value)
                norm_val = normalize_parameter(value, param_name, min_val, max_val)
                normalized_values.append(norm_val)
                
                # Create hover text with warning icon if needed
                if value is None:
                    hover_text = f"{warning_icon}{param_name}: No data available"
                else:
                    value_format = '.4f' if value <= 1 else '.1f'
                    unit_text = f" {unit}" if unit else ""
                    
                    if chart_type == 'comparison' and 'raw_treated' in locals():
                        treated_val = raw_treated[len(values)] if raw_treated else None
                        if treated_val is not None and value != 0:
                            improvement = ((value - treated_val) / value) * 100
                            hover_text = (
                                f"{warning_icon}{param_name}<br>" +
                                f"Improvement: {improvement:.1f}%<br>" +
                                f"Influent: {value:{value_format}}{unit_text}<br>" +
                                f"Treated: {treated_val:{value_format}}{unit_text}<br>" +
                                f"Range: {min_val:.2f} - {max_val:.2f}{unit_text}"
                            )
                        else:
                            hover_text = (
                                f"{warning_icon}{param_name}<br>" +
                                f"Value: {value:{value_format}}{unit_text}<br>" +
                                f"Range: {min_val:.2f} - {max_val:.2f}{unit_text}"
                            )
                    else:
                        hover_text = (
                            f"{warning_icon}{param_name}<br>" +
                            f"Value: {value:{value_format}}{unit_text}<br>" +
                            f"Range: {min_val:.2f} - {max_val:.2f}{unit_text}"
                        )
                hover_texts.append(hover_text)
        
        return labels, normalized_values, hover_texts, values
    
    # Process both datasets
    influent_labels, influent_values, influent_hovers, raw_influent = process_parameter_data(
        data_filtered, ranges_filtered
    )
    treated_labels, treated_values, treated_hovers, raw_treated = process_parameter_data(
        treated_filtered, treated_ranges_filtered
    )
    
    # Create the figure
    fig = go.Figure()
    
    # Add traces based on chart type
    if chart_type in ['influent', 'comparison']:
        # Add influent trace
        fig.add_trace(go.Scatterpolar(
            r=influent_values,
            theta=influent_labels,
            name='Influent Water',
            fill='toself',
            line=dict(color='#8B4513', shape='spline', smoothing=1.3),
            connectgaps=True,
            hovertemplate="%{text}<br>Quality: %{customdata:.0%}<extra></extra>",
            customdata=[1 - v if v is not None else 0 for v in influent_values],
            text=influent_hovers,
            opacity=0.6
        ))
    
    if chart_type in ['treated', 'comparison']:
        # Add treated trace
        fig.add_trace(go.Scatterpolar(
            r=treated_values,
            theta=treated_labels if chart_type == 'treated' else influent_labels,
            name='Treated Water',
            fill='toself',
            line=dict(color='#1E90FF', shape='spline', smoothing=1.3),
            connectgaps=True,
            hovertemplate="%{text}<br>Quality: %{customdata:.0%}<extra></extra>",
            customdata=[1 - v if v is not None else 0 for v in treated_values],
            text=treated_hovers,
            opacity=0.8
        ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickmode='array',
                ticktext=['Ideal', 'Good', 'Fair', 'Poor', 'Critical'],
                tickvals=[0, 0.25, 0.5, 0.75, 1]
            ),
            angularaxis=dict(
                direction="clockwise",
                period=len(influent_labels),
                rotation=90,
                tickangle=0,  # Keep text horizontal
                tickmode='array',
                ticktext=influent_labels,
                tickfont=dict(size=10),  # Adjust font size
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        height=500,  # Increased height
        title="",
        margin=dict(t=50, b=50, l=80, r=80),  # Increased margins
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig, None