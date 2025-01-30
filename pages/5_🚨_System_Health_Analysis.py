import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from utils.data_loader import load_all_data

def categorize_alarm(message):
    """Categorize alarms into main groups"""
    msg = str(message).lower()
    if 'water pump flow' in msg:
        subcategory = 'Flow Rate'
        if 'high' in msg or 'above' in msg:
            detail = 'High Flow'
        elif 'low' in msg or 'below' in msg:
            detail = 'Low Flow'
        else:
            detail = 'Flow Issue'
        return 'Water Flow', subcategory, detail
    elif 'water pump' in msg and 'pressure' in msg:
        subcategory = 'Pressure'
        if 'high' in msg or 'above' in msg:
            detail = 'High Pressure'
        elif 'low' in msg or 'below' in msg:
            detail = 'Low Pressure'
        else:
            detail = 'Pressure Issue'
        return 'Water Pressure', subcategory, detail
    elif 'membrane' in msg or 'filtrate' in msg:
        if 'scour' in msg:
            subcategory = 'Membrane Scour'
            detail = 'Scour Issue'
        else:
            subcategory = 'Filtration'
            detail = 'Filtration Issue'
        return 'Membrane & Filtration', subcategory, detail
    elif 'uv chamber' in msg or 'ultraviolet' in msg:
        subcategory = 'UV System'
        if 'dose' in msg:
            detail = 'Dosage Issue'
        else:
            detail = 'UV Issue'
        return 'UV Treatment', subcategory, detail
    return 'Other Systems', 'General', 'System Issue'

def categorize_warning(message):
    """Categorize warnings into main groups"""
    msg = str(message).lower()
    if 'water pump flow' in msg:
        subcategory = 'Flow Rate'
        if 'high' in msg:
            detail = 'High Flow'
        elif 'low' in msg:
            detail = 'Low Flow'
        else:
            detail = 'Flow Issue'
        return 'Water Flow', subcategory, detail
    elif 'water pump' in msg and 'pressure' in msg:
        subcategory = 'Pressure'
        if 'high' in msg:
            detail = 'High Pressure'
        elif 'low' in msg:
            detail = 'Low Pressure'
        else:
            detail = 'Pressure Issue'
        return 'Water Pressure', subcategory, detail
    elif 'membrane scour' in msg:
        subcategory = 'Membrane Scour'
        if 'high' in msg:
            detail = 'High Pressure'
        elif 'low' in msg:
            detail = 'Low Pressure'
        else:
            detail = 'Pressure Issue'
        return 'Membrane & Filtration', subcategory, detail
    elif 'clean-in-place' in msg:
        subcategory = 'CIP System'
        if 'high' in msg:
            detail = 'High Level'
        elif 'low' in msg:
            detail = 'Low Level'
        else:
            detail = 'Level Issue'
        return 'CIP System', subcategory, detail
    elif 'verify' in msg:
        subcategory = 'Verification'
        if 'uvm101' in msg:
            detail = 'UV System'
        elif 'vbl101' in msg:
            detail = 'Valve System'
        else:
            detail = 'General Verification'
        return 'System Verification', subcategory, detail
    return 'Other Systems', 'General', 'System Issue'

def determine_severity(msg):
    """Determine severity/impact level"""
    msg = str(msg).lower()
    if 'high' in msg or 'above' in msg or 'failed' in msg:
        return 3  # High severity
    elif 'low' in msg or 'below' in msg:
        return 2  # Medium severity
    return 1  # Low severity

def process_data(df, data_type='alarms'):
    """Process alarm/warning data with categories and severity"""
    # Add categorization based on data type
    categorize_func = categorize_alarm if data_type == 'alarms' else categorize_warning
    categories = df['message'].apply(categorize_func)
    df['category'] = [x[0] for x in categories]
    df['subcategory'] = [x[1] for x in categories]
    df['detail'] = [x[2] for x in categories]
    
    # Add severity/impact
    df['severity_score'] = df['message'].apply(determine_severity)
    severity_label = 'severity' if data_type == 'alarms' else 'impact'
    df[severity_label] = df['severity_score'].map({
        3: 'High',
        2: 'Medium',
        1: 'Low'
    })
    
    return df

def create_metrics_row(df, data_type):
    """Create metrics row for either alarms or warnings"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(f"Total {data_type.title()}", len(df))
    
    with col2:
        st.metric(f"Unique {data_type.title()} Types", df['message'].nunique())
    
    with col3:
        st.metric("Most Common Category", df['category'].mode()[0] if not df.empty else "N/A")
    
    with col4:
        days_span = (df['timestamp'].max() - df['timestamp'].min()).days if not df.empty else 0
        avg_per_day = len(df) / max(days_span, 1)
        st.metric(f"Avg {data_type.title()}/Day", f"{avg_per_day:.1f}")

def create_detailed_view(df, data_type):
    """Create detailed view for either alarms or warnings"""
    col1, col2 = st.columns([2, 1])
    
    severity_label = 'severity' if data_type == 'alarms' else 'impact'
    
    with col1:
        # Create hierarchy
        hierarchy = df.groupby(
            ['category', 'subcategory', 'detail', severity_label]
        ).size().reset_index(name='count')
        
        fig_sunburst = px.sunburst(
            hierarchy,
            path=['category', 'subcategory', 'detail', severity_label],
            values='count',
            title=f'Detailed {data_type.title()} Hierarchy',
            color='count',
            color_continuous_scale='Viridis' if data_type == 'alarms' else 'YlOrRd'
        )
        fig_sunburst.update_layout(height=600)
        st.plotly_chart(fig_sunburst, use_container_width=True)
    
    with col2:
        # Category-specific metrics
        st.markdown("### Category Metrics")
        category_metrics = df.groupby('category').agg({
            'severity_score': ['mean', 'max'],
            'message': 'count'
        }).round(2)
        metric_label = 'Severity' if data_type == 'alarms' else 'Impact'
        category_metrics.columns = [f'Avg {metric_label}', f'Max {metric_label}', 'Count']
        st.dataframe(category_metrics)
        
        # Show severity/impact distribution
        st.markdown(f"### {metric_label} Distribution")
        dist = df[severity_label].value_counts()
        fig_dist = px.pie(
            values=dist.values,
            names=dist.index,
            title=f'{data_type.title()} {metric_label} Distribution',
            color_discrete_sequence=px.colors.sequential.RdBu if data_type == 'alarms' else px.colors.sequential.YlOrRd
        )
        st.plotly_chart(fig_dist, use_container_width=True)

def create_summary_view(df, data_type):
    """Create summary view for either alarms or warnings"""
    col1, col2 = st.columns([3, 2])
    severity_label = 'severity' if data_type == 'alarms' else 'impact'
    
    with col1:
        st.subheader(f"{data_type.title()} Distribution Over Time")
        daily_data = df.groupby(['timestamp', 'category']).size().reset_index(name='count')
        fig_time = px.line(
            daily_data,
            x='timestamp',
            y='count',
            color='category',
            title=f'{data_type.title()} by Category Over Time'
        )
        fig_time.update_layout(height=400)
        st.plotly_chart(fig_time, use_container_width=True)
    
    with col2:
        st.subheader("Category Distribution")
        basic_sunburst = df.groupby(['category', severity_label]).size().reset_index(name='count')
        fig_basic_sunburst = px.sunburst(
            basic_sunburst,
            path=['category', severity_label],
            values='count',
            title=f'{data_type.title()} Categories and {severity_label.title()}'
        )
        fig_basic_sunburst.update_layout(height=400)
        st.plotly_chart(fig_basic_sunburst, use_container_width=True)

def main():
    # Page config
    st.set_page_config(page_title="System Health Analysis", page_icon="🚨", layout="wide")
    
    # Title
    st.title('🚨️ System Health Analysis')
    st.markdown("""
    This dashboard provides comprehensive monitoring of system alarms and warnings.
    Use the tabs below to switch between Alarms and Warnings views.
    """)
    
    try:
        # Load data
        data = load_all_data()
        alarms_df = process_data(data['alarms'], 'alarms')
        warnings_df = process_data(data['warnings'], 'warnings')
        
        # Add engineer view toggle in sidebar
        st.sidebar.title('Dashboard Settings')
        view_mode = st.sidebar.toggle('Engineer View', value=False)
        
        # Create tabs
        tab1, tab2 = st.tabs(["🚨 Alarms", "⚠️ Warnings"])
        
        with tab1:
            st.header("Alarm Analysis")
            create_metrics_row(alarms_df, 'alarms')
            
            if view_mode:
                st.markdown("---")
                st.subheader("Detailed Alarm Analysis")
                create_detailed_view(alarms_df, 'alarms')
            else:
                create_summary_view(alarms_df, 'alarms')
        
        with tab2:
            st.header("Warning Analysis")
            create_metrics_row(warnings_df, 'warnings')
            
            if view_mode:
                st.markdown("---")
                st.subheader("Detailed Warning Analysis")
                create_detailed_view(warnings_df, 'warnings')
            else:
                create_summary_view(warnings_df, 'warnings')
        
        # Footer
        st.markdown("---")
        st.markdown("""
            💡 **Tips:**
            - Toggle Engineer View in the sidebar for detailed analysis
            - In Technical view, click on categories in the sunburst chart to drill down
            - Hover over charts for detailed information
            - Use the severity/impact distributions to identify critical areas
        """)
    
    except Exception as e:
        st.error(f"Error loading or processing data: {str(e)}")
        st.write("Error details:", str(e))

if __name__ == "__main__":
    main()