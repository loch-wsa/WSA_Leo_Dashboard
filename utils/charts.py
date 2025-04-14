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

def create_single_parameter_gauge(value, param_name, min_val, max_val, unit="", color='#1E90FF'):
    """Create a radial gauge chart for a single parameter"""
    
    # Process the value
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

    if value is None:
        return None

    # Create the gauge chart
    fig = go.Figure()

    # Add the gauge
    fig.add_trace(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0.1, 0.9], 'y': [0.1, 0.9]},
        title = {'text': f"{param_name} ({unit})" if unit else param_name},
        gauge = {
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': color},
            'steps': [
                {'range': [min_val, (min_val + max_val)/2], 'color': "lightgray"},
                {'range': [(min_val + max_val)/2, max_val], 'color': "white"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_val
            }
        }
    ))

    # Update layout
    fig.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_comparison_gauge(influent_value, treated_value, param_name, min_val, max_val, unit=""):
    """Create a comparison gauge for a single parameter showing both values"""
    
    # Process the values
    def process_value(val):
        try:
            if isinstance(val, str):
                if val.startswith('<'):
                    return float(val.replace('<', ''))
                elif val == 'N/R':
                    return None
                elif 'LINT' in val:
                    return float(val.split()[0].replace('<', ''))
                else:
                    return float(val)
        except (ValueError, TypeError):
            return None
        return val

    influent_value = process_value(influent_value)
    treated_value = process_value(treated_value)

    if influent_value is None or treated_value is None:
        return None

    # Calculate improvement percentage
    improvement = ((influent_value - treated_value) / influent_value * 100 
                  if influent_value != 0 else 0)

    # Create the comparison gauge
    fig = go.Figure()

    # Add the two indicators side by side
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=influent_value,
        domain={'x': [0, 0.45], 'y': [0, 1]},
        title={'text': f"Influent<br>{param_name}"},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': '#8B4513'},
            'steps': [
                {'range': [min_val, (min_val + max_val)/2], 'color': "lightgray"},
                {'range': [(min_val + max_val)/2, max_val], 'color': "white"}
            ]
        }
    ))

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=treated_value,
        domain={'x': [0.55, 1], 'y': [0, 1]},
        title={'text': f"Treated<br>{param_name}"},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': '#1E90FF'},
            'steps': [
                {'range': [min_val, (min_val + max_val)/2], 'color': "lightgray"},
                {'range': [(min_val + max_val)/2, max_val], 'color': "white"}
            ]
        }
    ))

    # Add improvement annotation
    fig.add_annotation(
        text=f"{abs(improvement):.1f}% {'reduction' if improvement > 0 else 'increase'}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=16)
    )

    # Update layout
    fig.update_layout(
        height=400,
        margin=dict(t=80, b=50, l=50, r=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_radar_chart(week_num, als_lookups, data_df, treated_data, ranges_df, treated_ranges, chart_type='comparison', category=None):
    """
    Create a radar chart based on the specified type (influent, treated, comparison, or week_comparison)
    """
    week_col = f'Week {week_num}'
    
    # Always use influent ranges for comparison tab
    display_ranges = ranges_df if chart_type in ['influent', 'comparison'] else treated_ranges
    
    # Filter data and ranges
    ranges_filtered = display_ranges[display_ranges['ALS Lookup'].isin(als_lookups)].copy()
    data_filtered = data_df[data_df['ALS Lookup'].isin(als_lookups)].copy()
    treated_filtered = treated_data[treated_data['ALS Lookup'].isin(als_lookups)].copy()

    # Process single value
    def process_single_value(value):
        try:
            if isinstance(value, str):
                if value.startswith('<'):
                    return float(value.replace('<', ''))
                elif value == 'N/R':
                    return None
                elif 'LINT' in value:
                    return float(value.split()[0].replace('<', ''))
                else:
                    return float(value)
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    # Special handling for single parameter cases
    if len(als_lookups) == 1:
        # Get parameter details
        param_info = ranges_filtered.iloc[0]
        param_name = param_info['Parameter']
        unit = param_info['Unit'] if pd.notna(param_info['Unit']) else ""
        min_val = float(param_info['Min']) if pd.notna(param_info['Min']) else 0
        max_val = float(param_info['Max']) if pd.notna(param_info['Max']) else 1

        # Get values
        influent_value = process_single_value(data_filtered[week_col].iloc[0])
        treated_value = process_single_value(treated_filtered[week_col].iloc[0])

        # Calculate normalized values and percent reduction
        if influent_value is not None and treated_value is not None:
            percent_diff = ((influent_value - treated_value) / influent_value * 100 
                          if influent_value != 0 else 0)
        else:
            percent_diff = None

        # Create the figure for single parameter
        fig = go.Figure()

        # Create semi-circle points
        theta = np.linspace(-np.pi/2, np.pi/2, 50)  # Creates a semicircle
        base_x = np.cos(theta)
        base_y = np.sin(theta)

        # Add traces based on chart type
        if chart_type == 'week_comparison':
            # Week comparison: base week and comparison week
            norm_base = normalize_parameter(influent_value, param_name, min_val, max_val)
            norm_comp = normalize_parameter(treated_value, param_name, min_val, max_val)
            
            if norm_base is not None:
                # Create safe hover text for influent value
                try:
                    if influent_value is not None:
                        if isinstance(influent_value, str):
                            if influent_value.startswith('>') or influent_value.startswith('<'):
                                hover_value = influent_value  # Keep original string for display
                            elif influent_value.lower() in ('n/a', 'nr', 'n/r'):
                                hover_value = 'N/A'
                            else:
                                try:
                                    hover_value = f"{float(influent_value):.4f}"
                                except (ValueError, TypeError):
                                    hover_value = str(influent_value)
                        else:
                            hover_value = f"{float(influent_value):.4f}"
                    else:
                        hover_value = "N/A"
                except Exception:
                    hover_value = "Error"
                    
                fig.add_trace(go.Scatter(
                    x=base_x * norm_base,
                    y=base_y * norm_base,
                    name=f'Week {week_num}',
                    line=dict(color='#8B4513', width=1),
                    hovertemplate=f"Week {week_num}: {hover_value} {unit}<extra></extra>"
                ))
            
            if norm_comp is not None:
                # In week_comparison mode, the "treated_value" is actually the comparison week's value
                comp_week = week_num + 1  # This is an approximation; the actual week should be passed in
                if hasattr(st, 'session_state') and 'comparison_week' in st.session_state:
                    comp_week = st.session_state['comparison_week']
                
                # Create safe hover text for treated value
                try:
                    if treated_value is not None:
                        if isinstance(treated_value, str):
                            if treated_value.startswith('>') or treated_value.startswith('<'):
                                hover_value = treated_value  # Keep original string for display
                            elif treated_value.lower() in ('n/a', 'nr', 'n/r'):
                                hover_value = 'N/A'
                            else:
                                try:
                                    hover_value = f"{float(treated_value):.4f}"
                                except (ValueError, TypeError):
                                    hover_value = str(treated_value)
                        else:
                            hover_value = f"{float(treated_value):.4f}"
                    else:
                        hover_value = "N/A"
                except Exception:
                    hover_value = "Error"
                
                fig.add_trace(go.Scatter(
                    x=base_x * norm_comp,
                    y=base_y * norm_comp,
                    name=f'Week {comp_week}',
                    line=dict(color='#1E90FF', width=1),
                    hovertemplate=f"Week {comp_week}: {hover_value} {unit}<extra></extra>"
                ))
        else:
            # Standard influent/treated comparison
            if chart_type in ['influent', 'comparison']:
                norm_influent = normalize_parameter(influent_value, param_name, min_val, max_val)
                if norm_influent is not None:
                    # Create safe hover text for influent value
                    try:
                        if influent_value is not None:
                            if isinstance(influent_value, str):
                                if influent_value.startswith('>') or influent_value.startswith('<'):
                                    hover_value = influent_value  # Keep original string for display
                                elif influent_value.lower() in ('n/a', 'nr', 'n/r'):
                                    hover_value = 'N/A'
                                else:
                                    try:
                                        hover_value = f"{float(influent_value):.4f}"
                                    except (ValueError, TypeError):
                                        hover_value = str(influent_value)
                            else:
                                hover_value = f"{float(influent_value):.4f}"
                        else:
                            hover_value = "N/A"
                    except Exception:
                        hover_value = "Error"
                        
                    fig.add_trace(go.Scatter(
                        x=base_x * norm_influent,
                        y=base_y * norm_influent,
                        name='Influent Water',
                        line=dict(color='#8B4513', width=1),
                        hovertemplate=f"Influent: {hover_value} {unit}<extra></extra>"
                    ))

            if chart_type in ['treated', 'comparison']:
                norm_treated = normalize_parameter(treated_value, param_name, min_val, max_val)
                if norm_treated is not None:
                    # Create safe hover text for treated value
                    try:
                        if treated_value is not None:
                            if isinstance(treated_value, str):
                                if treated_value.startswith('>') or treated_value.startswith('<'):
                                    hover_value = treated_value  # Keep original string for display
                                elif treated_value.lower() in ('n/a', 'nr', 'n/r'):
                                    hover_value = 'N/A'
                                else:
                                    try:
                                        hover_value = f"{float(treated_value):.4f}"
                                    except (ValueError, TypeError):
                                        hover_value = str(treated_value)
                            else:
                                hover_value = f"{float(treated_value):.4f}"
                        else:
                            hover_value = "N/A"
                    except Exception:
                        hover_value = "Error"
                        
                    fig.add_trace(go.Scatter(
                        x=base_x * norm_treated,
                        y=base_y * norm_treated,
                        name='Treated Water',
                        line=dict(color='#1E90FF', width=1),
                        hovertemplate=f"Treated: {hover_value} {unit}<extra></extra>"
                    ))

        # Add grid circles (transparent)
        for r in [0.25, 0.5, 0.75, 1.0]:
            fig.add_trace(go.Scatter(
                x=base_x * r,
                y=base_y * r,
                mode='lines',
                line=dict(color='gray', width=0.5, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))

        # Check if values are out of range
        warning_symbol = ""
        if (influent_value is not None and (influent_value < min_val or influent_value > max_val)) or \
           (treated_value is not None and (treated_value < min_val or treated_value > max_val)):
            warning_symbol = "⚠️ "

        # Create appropriate label based on chart type
        if chart_type in ['comparison', 'week_comparison']:
            # For comparison, only show parameter name and reduction once
            label_text = f"{warning_symbol}{param_name}"
            if percent_diff is not None:
                try:
                    diff_text = f"{abs(percent_diff):.1f}% {'reduction' if percent_diff > 0 else 'increase'}"
                except (ValueError, TypeError):
                    diff_text = "N/A"
                
                fig.add_annotation(
                    x=0,
                    y=1.1,
                    text=diff_text,
                    showarrow=False,
                    font=dict(size=14)
                )
        else:
            # For individual views, show value and range
            value_to_display = influent_value if chart_type == 'influent' else treated_value
            
            try:
                if value_to_display is not None:
                    # Handle special string values
                    if isinstance(value_to_display, str):
                        if value_to_display.startswith('>') or value_to_display.startswith('<'):
                            value_text = value_to_display  # Keep as is
                        elif value_to_display.lower() in ('n/a', 'nr', 'n/r'):
                            value_text = "N/A"
                        else:
                            try:
                                value_num = float(value_to_display)
                                value_format = '.4f' if value_num <= 1 else '.1f'
                                value_text = f"{value_num:{value_format}}"
                            except (ValueError, TypeError):
                                value_text = str(value_to_display)
                    else:
                        # Numeric value
                        value_format = '.4f' if float(value_to_display) <= 1 else '.1f'
                        value_text = f"{float(value_to_display):{value_format}}"
                        
                    # Format range values safely
                    try:
                        min_val_str = f"{float(min_val):.2f}" if min_val is not None else "?"
                        max_val_str = f"{float(max_val):.2f}" if max_val is not None else "?"
                        range_text = f"({min_val_str} - {max_val_str})"
                    except (ValueError, TypeError):
                        range_text = "(range unknown)"
                        
                    label_text = f"{warning_symbol}{param_name}\n{value_text} {range_text}"
                    if unit:
                        label_text += f" {unit}"
                else:
                    label_text = f"{warning_symbol}{param_name} \n No data available"
            except Exception:
                label_text = f"{warning_symbol}{param_name} \n Error formatting data"

        # Add parameter label
        fig.add_annotation(
            x=0,
            y=-0.1,
            text=label_text,
            showarrow=False,
            font=dict(size=12)
        )

        # Update layout for semicircle
        fig.update_layout(
            showlegend=True,
            height=400,
            xaxis=dict(
                range=[-1.1, 1.1],
                showgrid=False,
                zeroline=False,
                showticklabels=False
            ),
            yaxis=dict(
                range=[-0.1, 1.2],
                showgrid=False,
                zeroline=False,
                showticklabels=False
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=50, b=30, l=30, r=30)
        )

        return fig, None

    else:
        # Process datasets for multi-parameter case
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
                    
                    # Process value
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
                    
                    # Create label based on chart type
                    if chart_type == 'week_comparison':
                        # In week comparison mode
                        try:
                            treated_val = treated_filtered[treated_filtered['ALS Lookup'] == als_lookup][week_col].iloc[0]
                            
                            # Handle string values
                            if isinstance(treated_val, str):
                                if treated_val.startswith('<'):
                                    treated_val = float(treated_val.replace('<', ''))
                                elif 'LINT' in treated_val:
                                    treated_val = float(treated_val.split()[0].replace('<', ''))
                                else:
                                    try:
                                        treated_val = float(treated_val)
                                    except ValueError:
                                        treated_val = None
                            
                            comp_week = week_num + 1  # This is an approximation
                            if hasattr(st, 'session_state') and 'comparison_week' in st.session_state:
                                comp_week = st.session_state['comparison_week']
                            
                            if value is not None and treated_val is not None and value != 0:
                                percent_diff = ((float(value) - float(treated_val)) / float(value)) * 100
                                label = f"{param_name}"
                            else:
                                label = param_name
                        except (ValueError, TypeError, IndexError):
                            label = param_name
                    elif chart_type == 'comparison':
                        # Standard influent/treated comparison
                        try:
                            treated_val = treated_filtered[treated_filtered['ALS Lookup'] == als_lookup][week_col].iloc[0]
                            
                            # Handle string values
                            if isinstance(treated_val, str):
                                if treated_val.startswith('<'):
                                    treated_val = float(treated_val.replace('<', ''))
                                elif 'LINT' in treated_val:
                                    treated_val = float(treated_val.split()[0].replace('<', ''))
                                else:
                                    try:
                                        treated_val = float(treated_val)
                                    except ValueError:
                                        treated_val = None
                            
                            if value is not None and treated_val is not None and value != 0:
                                percent_diff = ((float(value) - float(treated_val)) / float(value)) * 100
                                label = f"{param_name}<br>{abs(percent_diff):.1f}% {'reduction' if percent_diff > 0 else 'increase'}"
                            else:
                                label = param_name
                        except (ValueError, TypeError, IndexError):
                            label = param_name
                    else:
                        # Standard single dataset display
                        try:
                            # Ensure value is numeric for formatting
                            if value is not None:
                                if isinstance(value, str):
                                    try:
                                        value = float(value.replace('<', ''))
                                    except ValueError:
                                        value = None
                                
                                if value is not None:
                                    try:
                                        float_value = float(value)
                                        value_format = '.4f' if float_value <= 1 else '.1f'
                                        value_text = f"{float_value:{value_format}}"
                                    except (ValueError, TypeError):
                                        value_text = "N/A"
                                else:
                                    value_text = "N/A"
                            else:
                                value_text = "N/A"
                                
                            try:
                                # Ensure min_val and max_val are not None
                                min_val_str = f"{float(min_val):.2f}" if min_val is not None else "?"
                                max_val_str = f"{float(max_val):.2f}" if max_val is not None else "?"
                                range_text = f"({min_val_str} - {max_val_str})"
                                if unit:
                                    range_text += f" {unit}"
                            except (ValueError, TypeError):
                                range_text = "(range unknown)"
                            label = f"{param_name}<br>{value_text} {range_text}"
                        except (ValueError, TypeError):
                            label = f"{param_name}<br>N/A"
                    
                    labels.append(label)
                    
                    # Create hover text
                    try:
                        if value is not None:
                            # Ensure value is numeric for formatting
                            if isinstance(value, str):
                                try:
                                    value = float(value.replace('<', ''))
                                except ValueError:
                                    value = None
                            
                            if value is not None:
                                try:
                                    float_value = float(value)
                                    value_format = '.4f' if float_value <= 1 else '.1f'
                                    unit_text = f" {unit}" if unit else ""
                                    
                                    if chart_type == 'week_comparison':
                                        # Format range values safely
                                        try:
                                            min_val_str = f"{float(min_val):.2f}" if min_val is not None else "?"
                                            max_val_str = f"{float(max_val):.2f}" if max_val is not None else "?"
                                            range_text = f"{min_val_str} - {max_val_str}"
                                        except (ValueError, TypeError):
                                            range_text = "unknown"
                                            
                                        # Custom hover text for week comparison
                                        hover_text = (
                                            f"{param_name}<br>" +
                                            f"Week {week_num}: {float_value:{value_format}}{unit_text}<br>" +
                                            f"Range: {range_text}{unit_text}"
                                        )
                                    else:
                                        # Format range values safely
                                        try:
                                            min_val_str = f"{float(min_val):.2f}" if min_val is not None else "?"
                                            max_val_str = f"{float(max_val):.2f}" if max_val is not None else "?"
                                            range_text = f"{min_val_str} - {max_val_str}"
                                        except (ValueError, TypeError):
                                            range_text = "unknown"
                                            
                                        hover_text = (
                                            f"{param_name}<br>" +
                                            f"Value: {float_value:{value_format}}{unit_text}<br>" +
                                            f"Range: {range_text}{unit_text}"
                                        )
                                except (ValueError, TypeError):
                                    hover_text = f"{param_name}: Error formatting data"
                            else:
                                hover_text = f"{param_name}: No data available"
                        else:
                            hover_text = f"{param_name}: No data available"
                    except (ValueError, TypeError):
                        hover_text = f"{param_name}: Error formatting data"
                    hover_texts.append(hover_text)
            
            return labels, normalized_values, hover_texts, values
        
        # Process both datasets
        influent_labels, influent_values, influent_hovers, raw_influent = process_parameter_data(
            data_filtered, ranges_filtered
        )
        treated_labels, treated_values, treated_hovers, raw_treated = process_parameter_data(
            treated_filtered, ranges_filtered  # Use same ranges for treated data in comparison
        )
        
        # Create the figure for multi-parameter case
        fig = go.Figure()
        
        # Customize based on chart type
        if chart_type == 'week_comparison':
            # Week comparison mode
            comp_week = week_num + 1  # Default assumption
            if hasattr(st, 'session_state') and 'comparison_week' in st.session_state:
                comp_week = st.session_state['comparison_week']
                
            # Base week data (using influent_* variables)
            fig.add_trace(go.Scatterpolar(
                r=influent_values,
                theta=influent_labels,
                name=f'Week {week_num}',
                fill='toself',
                line=dict(color='#8B4513', shape='spline', smoothing=1.3),
                connectgaps=True,
                hovertemplate="%{text}<br>Quality: %{customdata:.0%}<extra></extra>",
                customdata=[1 - v if v is not None else 0 for v in influent_values],
                text=[t.replace("Value:", f"Week {week_num}:") for t in influent_hovers],
                opacity=0.6
            ))
            
            # Comparison week data (using treated_* variables)
            fig.add_trace(go.Scatterpolar(
                r=treated_values,
                theta=influent_labels,
                name=f'Week {comp_week}',
                fill='toself',
                line=dict(color='#1E90FF', shape='spline', smoothing=1.3),
                connectgaps=True,
                hovertemplate="%{text}<br>Quality: %{customdata:.0%}<extra></extra>",
                customdata=[1 - v if v is not None else 0 for v in treated_values],
                text=[t.replace("Value:", f"Week {comp_week}:") for t in treated_hovers],
                opacity=0.8
            ))
        else:
            # Standard influent/treated comparison or single view
            if chart_type in ['influent', 'comparison']:
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
                fig.add_trace(go.Scatterpolar(
                    r=treated_values,
                    theta=influent_labels if chart_type == 'comparison' else treated_labels,
                    name='Treated Water',
                    fill='toself',
                    line=dict(color='#1E90FF', shape='spline', smoothing=1.3),
                    connectgaps=True,
                    hovertemplate="%{text}<br>Quality: %{customdata:.0%}<extra></extra>",
                    customdata=[1 - v if v is not None else 0 for v in treated_values],
                    text=treated_hovers,
                    opacity=0.8
                ))
        
        # Update layout for multi-parameter case
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
                    tickangle=0,
                    tickmode='array',
                    ticktext=influent_labels,
                    tickfont=dict(size=10),
                ),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=True,
            height=500,
            title="",
            margin=dict(t=50, b=50, l=80, r=80),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

    return fig, None