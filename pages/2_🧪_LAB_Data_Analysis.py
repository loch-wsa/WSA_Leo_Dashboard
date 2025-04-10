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
    create_log_reduction_tiles_grid
)

# Page config
st.set_page_config(
    page_title="Lab Data Analysis",
    page_icon="🧪",
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

def display_microbial_section(data_df, ranges_df, week_num, view_type='treated', influent_data=None):
    """Display microbial parameters in tiles with optional log reduction"""
    # Get all microbial parameters
    microbial_params = ranges_df[ranges_df['Category'] == 'Microbial']
    
    if not microbial_params.empty:
        params = []
        values = []
        statuses = []
        
        # For log reduction calculation
        influent_values = []
        treated_values = []
        
        week_col = f'Week {week_num}'
        
        for _, row in microbial_params.iterrows():
            params.append(row['Parameter'])
            
            # Check if parameter has ALS Lookup and data
            if pd.notna(row['ALS Lookup']) and row['ALS Lookup'] != '':
                param_data = data_df[data_df['ALS Lookup'] == row['ALS Lookup']]
                
                if not param_data.empty:
                    value = param_data[week_col].iloc[0]
                    if pd.isna(value) or value == 'N/R':
                        values.append("Not Tested")
                        statuses.append('untested')
                        treated_values.append("Not Tested")  # For log reduction
                    else:
                        try:
                            float_value = float(str(value).replace('<', ''))
                            values.append(f"{float_value:.1f} {row['Unit']}")
                            statuses.append('neutral')
                            treated_values.append(float_value)  # For log reduction
                        except ValueError:
                            values.append(str(value))
                            statuses.append('neutral')
                            treated_values.append(value)  # For log reduction
                else:
                    values.append("Not Tested")
                    statuses.append('untested')
                    treated_values.append("Not Tested")  # For log reduction
                
                # Get influent values for log reduction if in comparison mode
                if view_type == 'comparison' and influent_data is not None:
                    inf_param_data = influent_data[influent_data['ALS Lookup'] == row['ALS Lookup']]
                    if not inf_param_data.empty:
                        inf_value = inf_param_data[week_col].iloc[0]
                        if pd.isna(inf_value) or inf_value == 'N/R':
                            influent_values.append("Not Tested")
                        else:
                            try:
                                inf_float_value = float(str(inf_value).replace('<', ''))
                                influent_values.append(inf_float_value)
                            except ValueError:
                                influent_values.append(inf_value)
                    else:
                        influent_values.append("Not Tested")
            else:
                values.append("Not Tested")
                statuses.append('untested')
                treated_values.append("Not Tested")  # For log reduction
                if view_type == 'comparison' and influent_data is not None:
                    influent_values.append("Not Tested")
        
        # Always show parameter values
        create_parameter_tiles_grid(params, values, statuses)
        
        # Display log reduction tiles if in comparison mode, with values shown
        if view_type == 'comparison' and influent_data is not None:
            st.markdown("#### Log Reduction Values")
            st.markdown("*1 Log = 90% removal, 2 Log = 99% removal, 3 Log = 99.9% removal, etc. ✅ = 6 Log or greater (99.9999%)*")
            create_log_reduction_tiles_grid(params, influent_values, treated_values, cols=2, show_values=True)

def display_category_section(category, data_df, treated_data, ranges_df, treated_ranges, week_num, view_type='treated', influent_data=None, influent_ranges=None):
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
            
            # Use appropriate data sources based on view type
            source_data = influent_data if view_type == 'comparison' and influent_data is not None else data_df
            source_ranges = influent_ranges if view_type == 'comparison' and influent_ranges is not None else ranges_df
            
            fig, _ = create_radar_chart(
                week_num,
                als_lookups,
                source_data,
                treated_data,
                source_ranges,
                treated_ranges,
                view_type,
                category
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # We'll move log reduction display to the expander below
        
        with st.expander(f"View {category} Parameters", expanded=False):
            week_col = f'Week {week_num}'
            params = []
            values = []
            statuses = []
            ranges_min = []
            ranges_max = []
            units = []
            
            # For log reduction calculation
            influent_values = []
            treated_values = []
            
            for _, row in category_params.iterrows():
                params.append(row['Parameter'])
                units.append(row['Unit'] if pd.notna(row['Unit']) else '')
                ranges_min.append(row['Min'] if pd.notna(row['Min']) else None)
                ranges_max.append(row['Max'] if pd.notna(row['Max']) else None)
                
                if pd.notna(row['ALS Lookup']) and row['ALS Lookup'] != '':
                    param_data = data_df[data_df['ALS Lookup'] == row['ALS Lookup']]
                    
                    if not param_data.empty:
                        value = param_data[week_col].iloc[0]
                        if pd.isna(value) or value == 'N/R':
                            values.append("Not Tested")
                            statuses.append('untested')
                            treated_values.append("Not Tested")  # For log reduction
                        else:
                            try:
                                float_value = float(str(value).replace('<', ''))
                                values.append(float_value)
                                treated_values.append(float_value)  # For log reduction
                                
                                min_val = float(row['Min']) if pd.notna(row['Min']) else None
                                max_val = float(row['Max']) if pd.notna(row['Max']) else None
                                
                                if (min_val is not None and float_value < min_val) or \
                                   (max_val is not None and float_value > max_val):
                                    statuses.append('negative')
                                else:
                                    statuses.append('positive')
                            except ValueError:
                                values.append(str(value))
                                statuses.append('neutral')
                                treated_values.append(value)  # For log reduction
                    else:
                        values.append("Not Tested")
                        statuses.append('untested')
                        treated_values.append("Not Tested")  # For log reduction
                    
                    # Get influent values for log reduction if in comparison mode
                    if view_type == 'comparison' and influent_data is not None:
                        inf_param_data = influent_data[influent_data['ALS Lookup'] == row['ALS Lookup']]
                        if not inf_param_data.empty:
                            inf_value = inf_param_data[week_col].iloc[0]
                            if pd.isna(inf_value) or inf_value == 'N/R':
                                influent_values.append("Not Tested")
                            else:
                                try:
                                    inf_float_value = float(str(inf_value).replace('<', ''))
                                    influent_values.append(inf_float_value)
                                except ValueError:
                                    influent_values.append(inf_value)
                        else:
                            influent_values.append("Not Tested")
                else:
                    values.append("Not Tested")
                    statuses.append('untested')
                    treated_values.append("Not Tested")  # For log reduction
                    if view_type == 'comparison' and influent_data is not None:
                        influent_values.append("Not Tested")
            
            # Create parameter tiles
            create_parameter_tiles_grid(
                parameters=params, 
                values=values, 
                statuses=statuses,
                ranges_min=ranges_min,
                ranges_max=ranges_max,
                units=units
            )
            
            # Create log reduction tiles if in comparison mode
            if view_type == 'comparison' and influent_data is not None:
                st.markdown("#### Log Reduction Values")
                st.markdown("*1 Log = 90% removal, 2 Log = 99% removal, 3 Log = 99.9% removal, etc. ✅ = 6 Log or greater (99.9999%)*")
                create_log_reduction_tiles_grid(params, influent_values, treated_values, cols=2, show_values=True)

def render_water_analysis(data_df, treated_data, ranges_df, treated_ranges, week_num, view_type, influent_data=None, influent_ranges=None):
    """Render water analysis content for a specific view"""
    
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
                treated_data,
                ranges_df,
                treated_ranges,
                week_num,
                view_type,
                influent_data,
                influent_ranges
            )

    # Microbial section
    st.subheader('Microbial Parameters')
    display_microbial_section(data_df, ranges_df, week_num, view_type, influent_data)

    # Additional categories
    for category in ['Radiological', 'Disinfection By-Products', 'Algae Toxins']:
        st.subheader(f'{category} Parameters')
        display_category_section(
            category,
            data_df,
            treated_data,
            ranges_df,
            treated_ranges,
            week_num,
            view_type,
            influent_data,
            influent_ranges
        )

def main():
    try:
        # Load data
        influent_data, treated_data, influent_ranges, treated_ranges = get_water_data()

        # Main page title
        st.title('🧪 Lab Data Analysis')
        st.markdown("""
        Weekly lab testing analysis for water quality assessment and machine performance monitoring.
        Use the tabs below to view different aspects of the water treatment process.
        """)

        # Sidebar controls
        st.sidebar.title('Control Panel')
        
        # Determine available weeks from the data
        week_cols = [col for col in treated_data.columns if col.startswith('Week')]
        max_week = len(week_cols)
        
        # Week selector with dynamic range
        week_num = st.sidebar.slider('Select Week', 1, max_week, 1)

        # Create tabs
        tab1, tab2, tab3 = st.tabs([
            "🚱 Influent Water",
            "🚰 Treated Water",
            "📊 Comparison"
        ])
        
        # Track current tab for conditional sidebar content
        if 'current_tab' not in st.session_state:
            st.session_state['current_tab'] = 'treated'  # Default

        # Influent Water Tab
        with tab1:
            st.session_state['current_tab'] = 'influent'
            st.header("Influent Water Analysis")
            st.markdown(f"""
            Analyzing raw water characteristics for Week {week_num}.  
            The data represents untreated water entering the Brolga system.
            """)
            render_water_analysis(
                influent_data,
                treated_data,
                influent_ranges,
                treated_ranges,
                week_num,
                'influent'
            )

        # Treated Water Tab
        with tab2:
            st.session_state['current_tab'] = 'treated'
            st.header("Treated Water Analysis")
            st.markdown(f"""
            Showing treated water quality parameters for Week {week_num}.  
            This represents the Brolga system's output water quality after full treatment.
            """)
            render_water_analysis(
                treated_data,
                treated_data,
                treated_ranges,
                treated_ranges,
                week_num,
                'treated'
            )

        # Comparison Tab
        with tab3:
            st.session_state['current_tab'] = 'comparison'
            st.header("Water Quality Comparison")
            st.markdown(f"""
            Week {week_num} comparison between influent and treated water.  
            The smaller radar plot area for treated water demonstrates the effectiveness of the Brolga treatment process.
            
            **Log Reduction Values** show the order of magnitude reduction achieved by the treatment process:
            *1 Log = 90% removal, 2 Log = 99% removal, 3 Log = 99.9% removal, etc.*
            """)
            render_water_analysis(
                treated_data,
                treated_data,
                treated_ranges,
                treated_ranges,
                week_num,
                'comparison',
                influent_data,
                influent_ranges
            )

        # Info messages
        st.sidebar.markdown('---')
        st.sidebar.warning('Note: Values below detection limits are shown as the detection limit value. Actual values may be lower.')
        
        # Add log reduction explanation in comparison mode tab
        if st.session_state.get('current_tab') == 'comparison':
            st.sidebar.markdown('---')
            st.sidebar.info("""
            ### Log Reduction Values
            - **1 Log** = 90% removal
            - **2 Log** = 99% removal
            - **3 Log** = 99.9% removal
            - **4 Log** = 99.99% removal
            - **5 Log** = 99.999% removal
            - **≥6 Log ✅** = 99.9999% or greater removal
            
            Negative values (⚠️) indicate an increase after treatment.
            """)

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.warning("Please check that all required data files are present in the data directory.")

if __name__ == "__main__":
    main()