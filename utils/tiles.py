import streamlit as st
import pandas as pd

def format_parameter_value(value, min_val=None, max_val=None, unit=''):
    try:
        # Handle string values like '<0.1'
        if isinstance(value, str):
            if value == 'N/R' or value == 'Not Tested':
                return value
            if value.startswith('<'):
                value = float(value.replace('<', ''))
            elif 'LINT' in value:
                value = float(value.split()[0].replace('<', ''))
            else:
                value = float(value)

        # If value is None or not a number, return as is
        if pd.isna(value):
            return 'Not Tested'

        value = float(value)
        unit_text = f" {unit}" if unit else ""
        
        # Determine decimal places based on value
        value_format = '.3f' if value <= 1 else '.1f'
        
        # Format with range if min and max are provided
        if pd.notna(min_val) and pd.notna(max_val):
            min_val = float(min_val)
            max_val = float(max_val)
            
            # Determine decimal places for min and max
            min_max_format = '.3f' if max_val <= 1 else '.1f'

            return f"{value:{value_format}} ({min_val:{min_max_format}}-{max_val:{min_max_format}}){unit_text}"
        
        # If no range, just return formatted value with unit
        return f"{value:{value_format}}{unit_text}"
        
    except (ValueError, TypeError):
        return str(value)

def create_parameter_tile(param_name, param_value, status='neutral', min_val=None, max_val=None, unit='', log_reduction=None):
    # Define status colors and icons
    status_config = {
        'positive': ('✅', '#28a745'),  # Green
        'negative': ('⚠️', '#dc3545'),  # Red
        'neutral': ('', 'white'),      # White, no icon
        'untested': ('', '#6c757d')    # Grey, no icon
    }
    
    icon, color = status_config.get(status, status_config['untested'])
    
    # If this is a comparison tile with log reduction, we'll only show the value on top row
    # and the detailed comparison with log reduction in the bottom row
    if log_reduction:
        log_icon, log_color = status_config.get(log_reduction.get('status', 'neutral'), status_config['neutral'])
        log_text = log_reduction.get('text', '')
        
        # For untested values, show formatted value + unit
        if param_value == "Not Tested":
            formatted_value = "Not Tested"
        # For numeric values in comparison mode, just show the treated value 
        # (the full comparison is shown in the log reduction section)
        elif isinstance(param_value, (int, float)):
            value_format = '.3f' if param_value <= 1 else '.1f'
            formatted_value = f"{param_value:{value_format}} {unit}".strip()
        else:
            formatted_value = f"{param_value} {unit}".strip()
        
        tile_html = f"""
        <div style="margin: 10px 0; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="width: 100%;">
                    <div style="font-size: 0.9em; color: white;">{param_name}</div>
                    <div style="font-size: 1.2em; color: {color}; margin-top: 5px;">
                        {icon} {formatted_value}
                    </div>
                    <div style="font-size: 0.9em; color: {log_color}; margin-top: 5px; border-top: 1px solid #555; padding-top: 5px;">
                        {log_icon} {log_text}
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        # For non-comparison tiles, show the full formatted value
        formatted_value = format_parameter_value(param_value, min_val, max_val, unit)
        
        tile_html = f"""
        <div style="margin: 10px 0; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.9em; color: white;">{param_name}</div>
                    <div style="font-size: 1.2em; color: {color}; margin-top: 5px;">
                        {icon} {formatted_value}
                    </div>
                </div>
            </div>
        </div>
        """
    
    st.markdown(tile_html, unsafe_allow_html=True)

def calculate_log_reduction(influent_value, treated_value, unit=''):
    """
    Calculate log reduction between influent and treated values.
    
    Args:
        influent_value: Value in influent water
        treated_value: Value in treated water
        unit: Unit of measurement
        
    Returns:
        Dictionary with log reduction text and status
    """
    try:
        # Handle None, NaN, and string values
        if (pd.isna(influent_value) or pd.isna(treated_value) or
            influent_value == 'Not Tested' or treated_value == 'Not Tested'):
            return {'text': "Log reduction: N/A", 'status': 'untested'}
        
        # Convert string values if needed
        if isinstance(influent_value, str):
            if influent_value.startswith('<'):
                influent_value = float(influent_value.replace('<', ''))
            elif 'LINT' in influent_value:
                influent_value = float(influent_value.split()[0].replace('<', ''))
            else:
                try:
                    influent_value = float(influent_value)
                except ValueError:
                    return {'text': "Log reduction: N/A", 'status': 'untested'}
        
        if isinstance(treated_value, str):
            if treated_value.startswith('<'):
                treated_value = float(treated_value.replace('<', ''))
            elif 'LINT' in treated_value:
                treated_value = float(treated_value.split()[0].replace('<', ''))
            else:
                try:
                    treated_value = float(treated_value)
                except ValueError:
                    return {'text': "Log reduction: N/A", 'status': 'untested'}
        
        # Ensure we're working with floats
        try:
            influent_value = float(influent_value)
            treated_value = float(treated_value)
        except (ValueError, TypeError):
            return {'text': "Log reduction: N/A", 'status': 'untested'}
        
        # Format influent and treated values with appropriate precision 
        # (3 decimal places for values <= 1, 1 decimal place for larger values)
        inf_format = '.3f' if influent_value <= 1 else '.1f'
        treat_format = '.3f' if treated_value <= 1 else '.1f'
        
        # Add unit if provided
        unit_text = f" {unit}" if unit else ""
        
        # Format the values to display
        inf_display = f"{influent_value:{inf_format}}"
        treat_display = f"{treated_value:{treat_format}}"
        
        # Check if this is a week-to-week comparison
        if hasattr(st, 'session_state') and st.session_state.get('current_tab') == 'week_comparison':
            # Week comparison mode - using colors for base and comparison weeks
            base_week = st.session_state.get('base_week', '?')
            comp_week = st.session_state.get('comparison_week', '?')
            values_display = f"<span style='color: #8B4513;'>⬤</span> {inf_display} / <span style='color: #1E90FF;'>⬤</span> {treat_display}{unit_text}"
        else:
            # Standard influent/treated comparison
            values_display = f"🚱 {inf_display} / 🚰 {treat_display}{unit_text}"
        
        # Check for zero treated value (complete removal)
        if treated_value == 0:
            if influent_value > 0:
                return {'text': f"{values_display}, >6 Log", 'status': 'positive'}
            else:
                return {'text': f"{values_display}, N/A", 'status': 'untested'}
        # Check for zero influent value (can't calculate reduction)
        elif influent_value == 0:
            if treated_value > 0:
                return {'text': f"{values_display}, N/A (↑)", 'status': 'negative'}
            else:
                return {'text': f"{values_display}, N/A", 'status': 'untested'}
        # Normal calculation
        else:
            reduction_ratio = influent_value / treated_value
            
            if reduction_ratio < 1:  # Value increased after treatment
                increase_ratio = treated_value / influent_value
                return {'text': f"{values_display}, ↑ {increase_ratio:.1f}x", 'status': 'negative'}
            else:
                # For standard comparison, calculate log reduction
                if not hasattr(st, 'session_state') or st.session_state.get('current_tab') != 'week_comparison':
                    log_reduction = min(6, round(10 * (10 ** -10 + influent_value / treated_value)) / 10)
                    
                    if log_reduction >= 6:
                        return {'text': f"{values_display}, >6 Log", 'status': 'positive'}
                    else:
                        return {'text': f"{values_display}, {log_reduction:.1f} Log", 'status': 'neutral' if log_reduction < 6 else 'positive'}
                else:
                    # For week comparison, show percent change (decrease or increase)
                    percent_change = (influent_value - treated_value) / influent_value * 100
                    if percent_change > 0:
                        return {'text': f"{values_display}, ↓ {percent_change:.1f}%", 'status': 'neutral'}
                    else:
                        return {'text': f"{values_display}, ↑ {abs(percent_change):.1f}%", 'status': 'neutral'}
    
    except Exception as e:
        return {'text': f"Log reduction error: {str(e)}", 'status': 'untested'}

def create_parameter_tiles_grid(parameters, values, statuses=None, ranges_min=None, ranges_max=None, units=None, cols=3, influent_values=None):
    if statuses is None:
        statuses = ['untested'] * len(parameters)
    
    # Provide default empty lists if not provided
    ranges_min = ranges_min or [None] * len(parameters)
    ranges_max = ranges_max or [None] * len(parameters)
    units = units or [''] * len(parameters)
    
    # Create columns
    columns = st.columns(cols)
    
    # Distribute tiles across columns
    for idx, (param, value, status, min_val, max_val, unit) in enumerate(
        zip(parameters, values, statuses, ranges_min, ranges_max, units)
    ):
        # If the value is "Not Tested", override the status to 'untested'
        if value == "Not Tested":
            status = 'untested'
        
        # Calculate log reduction if influent values are provided
        log_reduction = None
        if influent_values and idx < len(influent_values):
            if value != "Not Tested" and influent_values[idx] != "Not Tested":
                log_reduction = calculate_log_reduction(influent_values[idx], value, unit)
            
        with columns[idx % cols]:
            create_parameter_tile(
                param, 
                value, 
                status, 
                min_val, 
                max_val, 
                unit,
                log_reduction
            )

def create_log_reduction_tile(param_name, influent_value, treated_value):
    """
    Create a tile showing log reduction between influent and treated values.
    
    Args:
        param_name (str): Parameter name
        influent_value: Value in influent water
        treated_value: Value in treated water
    
    Log reduction calculation:
    - 1 Log = 90% reduction
    - 2 Log = 99% reduction
    - 3 Log = 99.9% reduction, etc.
    - >6 Log will be shown for extreme reductions (>99.9999%)
    - Red tiles for negative reduction (increase from influent to treated)
    """
    try:
        # Handle None, NaN, and string values
        if (pd.isna(influent_value) or pd.isna(treated_value) or
            influent_value == 'Not Tested' or treated_value == 'Not Tested'):
            log_text = "Not Available"
            status = 'untested'
        else:
            # Convert string values if needed
            if isinstance(influent_value, str):
                if influent_value.startswith('<'):
                    influent_value = float(influent_value.replace('<', ''))
                elif 'LINT' in influent_value:
                    influent_value = float(influent_value.split()[0].replace('<', ''))
                else:
                    try:
                        influent_value = float(influent_value)
                    except ValueError:
                        return create_parameter_tile(param_name, "N/A", 'untested')
            
            if isinstance(treated_value, str):
                if treated_value.startswith('<'):
                    treated_value = float(treated_value.replace('<', ''))
                elif 'LINT' in treated_value:
                    treated_value = float(treated_value.split()[0].replace('<', ''))
                else:
                    try:
                        treated_value = float(treated_value)
                    except ValueError:
                        return create_parameter_tile(param_name, "N/A", 'untested')
            
            # Ensure we're working with floats
            try:
                influent_value = float(influent_value)
                treated_value = float(treated_value)
            except (ValueError, TypeError):
                return create_parameter_tile(param_name, "N/A", 'untested')
            
            # Check for zero treated value (complete removal)
            if treated_value == 0:
                if influent_value > 0:
                    log_text = ">6 Log"
                    status = 'positive'
                else:
                    log_text = "N/A"
                    status = 'untested'
            # Check for zero influent value (can't calculate reduction)
            elif influent_value == 0:
                if treated_value > 0:
                    log_text = "N/A (↑)"
                    status = 'negative'
                else:
                    log_text = "N/A"
                    status = 'untested'
            # Normal calculation
            else:
                reduction_ratio = influent_value / treated_value
                
                if reduction_ratio < 1:  # Value increased after treatment
                    increase_ratio = treated_value / influent_value
                    log_text = f"↑ {increase_ratio:.1f}x"
                    status = 'negative'
                else:
                    log_reduction = min(6, round(10 * (10 ** -10 + influent_value / treated_value)) / 10)
                    
                    if log_reduction >= 6:
                        log_text = ">6 Log"
                    else:
                        log_text = f"{log_reduction:.1f} Log"
                    
                    # 6 Log or >6 Log should be green, <6 Log should be white (neutral)
                    status = 'positive' if log_reduction >= 6 else 'neutral'
        
        # Custom tile creation for log reduction that uses unique styling
        status_config = {
            'positive': ('✅', '#28a745'),  # Green with checkmark
            'negative': ('⚠️', '#dc3545'),  # Red with warning
            'neutral': ('', 'white'),      # White, no icon
            'untested': ('', '#6c757d')    # Grey, no icon
        }
        
        icon, color = status_config.get(status, status_config['untested'])
        
        # Create tile HTML with enhanced styling for log reduction
        tile_html = f"""
        <div style="margin: 10px 0; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.9em; color: white;">{param_name}</div>
                    <div style="font-size: 1.2em; color: {color}; margin-top: 5px; font-weight: {'bold' if status == 'positive' or status == 'negative' else 'normal'}">
                        {icon} {log_text}
                    </div>
                </div>
            </div>
        </div>
        """
        
        st.markdown(tile_html, unsafe_allow_html=True)
    
    except Exception as e:
        # Fallback for any unexpected errors
        return create_parameter_tile(param_name, f"Error: {str(e)}", 'untested')

def create_log_reduction_tiles_grid(parameters, influent_values, treated_values, cols=3, show_values=False):
    """
    Create a grid of log reduction tiles.
    
    Args:
        parameters (list): List of parameter names
        influent_values (list): List of influent values
        treated_values (list): List of treated values
        cols (int): Number of columns in the grid
        show_values (bool): If True, show original values alongside log reduction
    """
    # Create columns
    columns = st.columns(cols)
    
    # Distribute tiles across columns
    for idx, (param, inf_val, treat_val) in enumerate(
        zip(parameters, influent_values, treated_values)
    ):
        with columns[idx % cols]:
            if show_values:
                # Format the display values nicely
                if isinstance(inf_val, (int, float)) and not pd.isna(inf_val):
                    inf_display = f"{inf_val:.3f}" if inf_val <= 1 else f"{inf_val:.1f}"
                else:
                    inf_display = str(inf_val)
                    
                if isinstance(treat_val, (int, float)) and not pd.isna(treat_val):
                    treat_display = f"{treat_val:.3f}" if treat_val <= 1 else f"{treat_val:.1f}"
                else:
                    treat_display = str(treat_val)
                
                # Create a parameter name with the values included
                param_with_values = f"{param}\nInfluent: {inf_display} → Treated: {treat_display}"
                create_log_reduction_tile(param_with_values, inf_val, treat_val)
            else:
                create_log_reduction_tile(param, inf_val, treat_val)

def create_collapsible_section(title, content_func):
    """
    Create a collapsible section with custom content.
    
    Args:
        title (str): Title of the collapsible section
        content_func (callable): Function to call to generate the content
    """
    with st.expander(title, expanded=False):
        content_func()