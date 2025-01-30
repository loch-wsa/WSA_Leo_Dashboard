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

def create_parameter_tile(param_name, param_value, status='neutral', min_val=None, max_val=None, unit=''):
    # Define status colors and icons
    status_config = {
        'positive': ('✅', '#28a745'),  # Green
        'negative': ('⚠️', '#dc3545'),  # Red
        'neutral': ('', 'white'),      # White, no icon
        'untested': ('', '#6c757d')    # Grey, no icon
    }
    
    icon, color = status_config.get(status, status_config['untested'])
    
    # Format the value, potentially including the range
    formatted_value = format_parameter_value(param_value, min_val, max_val, unit)
    
    # Create tile HTML with minimal styling
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

def create_parameter_tiles_grid(parameters, values, statuses=None, ranges_min=None, ranges_max=None, units=None, cols=3):
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
            
        with columns[idx % cols]:
            create_parameter_tile(
                param, 
                value, 
                status, 
                min_val, 
                max_val, 
                unit
            )

def create_collapsible_section(title, content_func):
    """
    Create a collapsible section with custom content.
    
    Args:
        title (str): Title of the collapsible section
        content_func (callable): Function to call to generate the content
    """
    with st.expander(title, expanded=False):
        content_func()