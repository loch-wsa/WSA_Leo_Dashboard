import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add the root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from utils.data_loader import load_all_data
from utils.charts import create_radar_chart
from utils.tiles import (
    create_parameter_tiles_grid,
    create_collapsible_section,
    calculate_log_reduction
)

# Page config
st.set_page_config(
    page_title="Week Comparison",
    page_icon="📈",
    layout="wide"
)

# Cache data loading at the page level
@st.cache_data(ttl=3600)
def get_water_data():
    """Load and prepare water quality data"""
    all_data = load_all_data()
    return (
        all_data['influent_data'],
        all_data['treated_data'],
        all_data['influent_ranges'],
        all_data['treated_ranges']
    )

def display_microbial_section(data_df, ranges_df, base_week_num, comparison_week_num):
    """Display microbial parameters in tiles with integrated comparison between weeks"""
    # Get all microbial parameters
    microbial_params = ranges_df[ranges_df['Category'] == 'Microbial']
    
    if not microbial_params.empty:
        params = []
        base_values = []
        comp_values = []
        statuses = []
        units = []
        
        base_week_col = f'Week {base_week_num}'
        comp_week_col = f'Week {comparison_week_num}'
        
        for _, row in microbial_params.iterrows():
            params.append(row['Parameter'])
            units.append(row['Unit'] if pd.notna(row['Unit']) else '')
            
            # Check if parameter has ALS Lookup and data
            if pd.notna(row['ALS Lookup']) and row['ALS Lookup'] != '':
                param_data = data_df[data_df['ALS Lookup'] == row['ALS Lookup']]
                
                if not param_data.empty:
                    # Get base week value
                    base_value = param_data[base_week_col].iloc[0] if base_week_col in param_data.columns else 'N/R'
                    if pd.isna(base_value) or base_value == 'N/R':
                        base_values.append("Not Tested")
                        statuses.append('untested')
                    else:
                        try:
                            float_value = float(str(base_value).replace('<', ''))
                            base_values.append(float_value)
                            statuses.append('neutral')
                        except ValueError:
                            base_values.append(str(base_value))
                            statuses.append('neutral')
                    
                    # Get comparison week value
                    comp_value = param_data[comp_week_col].iloc[0] if comp_week_col in param_data.columns else 'N/R'
                    if pd.isna(comp_value) or comp_value == 'N/R':
                        comp_values.append("Not Tested")
                    else:
                        try:
                            float_value = float(str(comp_value).replace('<', ''))
                            comp_values.append(float_value)
                        except ValueError:
                            comp_values.append(str(comp_value))
                else:
                    base_values.append("Not Tested")
                    comp_values.append("Not Tested")
                    statuses.append('untested')
            else:
                base_values.append("Not Tested")
                comp_values.append("Not Tested")
                statuses.append('untested')
        
        # Display parameter tiles with integrated week comparison
        st.markdown(f"""
        *<span style='color: #8B4513;'>⬤</span> Week {base_week_num} / <span style='color: #1E90FF;'>⬤</span> Week {comparison_week_num} comparison*
        """)
        create_parameter_tiles_grid(params, base_values, statuses, units=units, influent_values=comp_values, cols=2)

def display_category_section(category, data_df, ranges_df, base_week_num, comparison_week_num):
    """Display a category section with radar chart and parameter tiles"""
    # Handle different spellings of Disinfection By-Products
    if category == 'Disinfection By-Products':
        category_params = ranges_df[ranges_df['Category'].isin(['Disinfection By-Products', 'Dysenfection Bi-Products'])]
    else:
        category_params = ranges_df[ranges_df['Category'] == category]
    
    if not category_params.empty:
        params_with_lookup = category_params[pd.notna(category_params['ALS Lookup']) & 
                                          (category_params['ALS Lookup'] != '')]
        
        if not params_with_lookup.empty and (len(params_with_lookup) > 1 or category == 'Organic Compound'):
            als_lookups = params_with_lookup['ALS Lookup'].tolist()
            
            # Create radar chart with both week's data
            # For color customization, we create a custom view type
            view_type = 'week_comparison'
            base_week_col = f'Week {base_week_num}'
            comp_week_col = f'Week {comparison_week_num}'
            
            # We need to create "fake" treated_data with comparison week's data
            # to use the existing radar chart function
            base_data = data_df.copy()
            comp_data = data_df.copy()
            
            # Rename the comparison week column to match the base week
            # This is needed because the radar chart function expects week_col to be the same
            if comp_week_col in comp_data.columns:
                comp_data = comp_data.rename(columns={comp_week_col: base_week_col})
            
            fig, _ = create_radar_chart(
                base_week_num,
                als_lookups,
                base_data,
                comp_data,
                ranges_df,
                ranges_df,
                view_type,
                category
            )
            
            # Custom legend to explain colors - moved above the chart
            st.markdown(f"""
            <div style='display: flex; justify-content: center; gap: 20px;'>
                <div><span style='color: #8B4513;'>●</span> Week {base_week_num} (Base)</div>
                <div><span style='color: #1E90FF;'>●</span> Week {comparison_week_num} (Comparison)</div>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
        
        with st.expander(f"View {category} Parameters", expanded=False):
            base_week_col = f'Week {base_week_num}'
            comp_week_col = f'Week {comparison_week_num}'
            
            params = []
            base_values = []
            comp_values = []
            statuses = []
            ranges_min = []
            ranges_max = []
            units = []
            
            for _, row in category_params.iterrows():
                params.append(row['Parameter'])
                units.append(row['Unit'] if pd.notna(row['Unit']) else '')
                ranges_min.append(row['Min'] if pd.notna(row['Min']) else None)
                ranges_max.append(row['Max'] if pd.notna(row['Max']) else None)
                
                if pd.notna(row['ALS Lookup']) and row['ALS Lookup'] != '':
                    param_data = data_df[data_df['ALS Lookup'] == row['ALS Lookup']]
                    
                    if not param_data.empty:
                        # Get base week value
                        base_value = param_data[base_week_col].iloc[0] if base_week_col in param_data.columns else 'N/R'
                        if pd.isna(base_value) or base_value == 'N/R':
                            base_values.append("Not Tested")
                            statuses.append('untested')
                        else:
                            try:
                                float_value = float(str(base_value).replace('<', ''))
                                base_values.append(float_value)
                                
                                min_val = float(row['Min']) if pd.notna(row['Min']) else None
                                max_val = float(row['Max']) if pd.notna(row['Max']) else None
                                
                                if (min_val is not None and float_value < min_val) or \
                                   (max_val is not None and float_value > max_val):
                                    statuses.append('negative')
                                else:
                                    statuses.append('positive')
                            except ValueError:
                                base_values.append(str(base_value))
                                statuses.append('neutral')
                        
                        # Get comparison week value
                        comp_value = param_data[comp_week_col].iloc[0] if comp_week_col in param_data.columns else 'N/R'
                        if pd.isna(comp_value) or comp_value == 'N/R':
                            comp_values.append("Not Tested")
                        else:
                            try:
                                float_value = float(str(comp_value).replace('<', ''))
                                comp_values.append(float_value)
                            except ValueError:
                                comp_values.append(str(comp_value))
                    else:
                        base_values.append("Not Tested")
                        comp_values.append("Not Tested")
                        statuses.append('untested')
                else:
                    base_values.append("Not Tested")
                    comp_values.append("Not Tested")
                    statuses.append('untested')
            
            # Display parameter tiles with integrated week comparison
            st.markdown(f"""
            *<span style='color: #8B4513;'>⬤</span> Week {base_week_num} / <span style='color: #1E90FF;'>⬤</span> Week {comparison_week_num} comparison*
            """)
            create_parameter_tiles_grid(
                parameters=params, 
                values=base_values, 
                statuses=statuses,
                ranges_min=ranges_min,
                ranges_max=ranges_max,
                units=units,
                influent_values=comp_values
            )

def render_week_comparison(data_df, ranges_df, base_week_num, comparison_week_num):
    """Render water comparison between two weeks"""
    
    # Main categories section
    st.subheader('Main Parameters')
    main_categories = ['Inorganic Compound', 'Metal', 'Organic Compound', 'Physical']
    
    cols = st.columns(2)
    for i, category in enumerate(main_categories):
        with cols[i % 2]:
            st.markdown(f"#### {category}")
            display_category_section(
                category,
                data_df,
                ranges_df,
                base_week_num,
                comparison_week_num
            )

    # Microbial section
    st.subheader('Microbial Parameters')
    display_microbial_section(data_df, ranges_df, base_week_num, comparison_week_num)

    # Additional categories
    for category in ['Radiological', 'Disinfection By-Products', 'Algae Toxins']:
        st.subheader(f'{category} Parameters')
        display_category_section(
            category,
            data_df,
            ranges_df,
            base_week_num,
            comparison_week_num
        )

def main():
    try:
        # Load data
        influent_data, treated_data, influent_ranges, treated_ranges = get_water_data()

        # Main page title
        st.title('📈 Week-to-Week Comparison')
        st.markdown("""
        Compare lab testing results between any two weeks to track changes over time.
        Use the controls below to select the weeks to compare.
        """)

        # Sidebar controls
        st.sidebar.title('Control Panel')
        
        # Create the color legend in the sidebar for clarity
        st.sidebar.markdown(f"""
        ### Color Legend
        <div style='display: flex; align-items: center; margin-bottom: 8px;'>
          <div style='width: 15px; height: 15px; background-color: #8B4513; margin-right: 10px; border-radius: 50%;'></div>
          <div>Week (Base)</div>
        </div>
        <div style='display: flex; align-items: center;'>
          <div style='width: 15px; height: 15px; background-color: #1E90FF; margin-right: 10px; border-radius: 50%;'></div>
          <div>Week (Comparison)</div>
        </div>
        """, unsafe_allow_html=True)
        st.sidebar.markdown('---')
        
        # Determine available weeks from the data
        week_cols = [col for col in treated_data.columns if col.startswith('Week')]
        max_week = len(week_cols)
        
        # Base week selector with dynamic range
        base_week_num = st.sidebar.slider('Base Week', 1, max_week, 1)
        
        # Comparison week selector with dynamic range, defaulting to the most recent week
        comparison_week_num = st.sidebar.slider('Comparison Week', 1, max_week, min(base_week_num + 1, max_week))
        
        # Store in session state for charts to access
        st.session_state['current_tab'] = 'week_comparison'
        st.session_state['base_week'] = base_week_num
        st.session_state['comparison_week'] = comparison_week_num

        # Radio buttons to select which dataset to compare
        data_type = st.sidebar.radio(
            "Select Data Type",
            ["Treated Water", "Influent Water"],
            index=0
        )
        
        # Get the appropriate data based on selection
        data_to_use = treated_data if data_type == "Treated Water" else influent_data
        ranges_to_use = treated_ranges if data_type == "Treated Water" else influent_ranges
        
        # Add the comparison explanation
        st.sidebar.markdown('---')
        st.sidebar.info(f"""
        ### Week Comparison Values
        - **Same**: Both weeks have equal values
        - **↑**: Value increased in comparison week
        - **↓**: Value decreased in comparison week
        - **N/A**: Data not available for one/both weeks
        
        ### Parameter Tiles Legend
        - <span style='color: #8B4513;'>⬤</span> Week {base_week_num} (Base)
        - <span style='color: #1E90FF;'>⬤</span> Week {comparison_week_num} (Comparison)
        """)
        
        # Display the comparison
        render_week_comparison(
            data_to_use,
            ranges_to_use,
            base_week_num,
            comparison_week_num
        )

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.warning("Please check that all required data files are present in the data directory.")

if __name__ == "__main__":
    main()