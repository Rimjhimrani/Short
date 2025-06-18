import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.graph-description {
    background-color: #f0f2f6;
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 20px;
    font-style: italic;
    border-left: 4px solid #1f77b4;
}

.metric-container {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.status-card {
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.status-excess {
    background-color: #ffebee;
    border-left: 4px solid #f44336;
}

.status-short {
    background-color: #fff3e0;
    border-left: 4px solid #ff9800;
}

.status-normal {
    background-color: #e8f5e8;
    border-left: 4px solid #4caf50;
}

.vendor-filter {
    background-color: #e3f2fd;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
    border-left: 4px solid #2196f3;
}

.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin: 10px 0;
}

.tab-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 20px;
    text-align: center;
    font-size: 24px;
    font-weight: bold;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    background-color: #f0f2f6;
    border-radius: 10px;
    color: #1f77b4;
    font-weight: bold;
    padding: 0 20px;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}
</style>
""", unsafe_allow_html=True)

class InventoryAnalyzer:
    """Enhanced inventory analysis with comprehensive reporting"""
    
    def __init__(self):
        self.status_colors = {
            'Within Norms': '#4CAF50',    # Green
            'Excess Inventory': '#2196F3', # Blue
            'Short Inventory': '#F44336'   # Red
        }
    
    def safe_float_convert(self, value):
        """Enhanced safe float conversion with better error handling"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        
        try:
            str_value = str(value).strip()
            # Remove common formatting
            str_value = str_value.replace(',', '').replace(' ', '').replace('₹', '').replace('$', '')
            
            if str_value.endswith('%'):
                str_value = str_value[:-1]
            
            # Handle negative values in parentheses
            if str_value.startswith('(') and str_value.endswith(')'):
                str_value = '-' + str_value[1:-1]
            
            return float(str_value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert '{value}' to float: {e}")
            return 0.0
    
    def safe_int_convert(self, value):
        """Enhanced safe int conversion"""
        return int(self.safe_float_convert(value))
    
    def load_sample_data(self):
        """Load sample inventory data"""
        sample_data = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", 5.230, 4.000, 496, "Vendor_A"],
            ["AC0303020105", "RAIN GUTTER PROFILE", 8.360, 6.000, 1984, "Vendor_B"],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", 12.500, 10.000, 2356, "Vendor_A"],
            ["AC0203020077", "Bulb beading LV battery flap", 3.500, 3.000, 248, "Vendor_C"],
            ["AC0303020104", "L- PROFILE JAM PILLAR", 15.940, 20.000, 992, "Vendor_A"],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", 25, 30, 1248, "Vendor_B"],
            ["AA0115120001", "HVPDU ms", 18, 12, 1888, "Vendor_D"],
            ["AA0119020017", "REAR TURN INDICATOR", 35, 40, 1512, "Vendor_C"],
            ["AA0119020019", "REVERSING LAMP", 28, 20, 1152, "Vendor_A"],
            ["AA0822010800", "SIDE DISPLAY BOARD", 42, 50, 2496, "Vendor_B"],
            ["BB0101010001", "ENGINE OIL FILTER", 65, 45, 1300, "Vendor_E"],
            ["BB0202020002", "BRAKE PAD SET", 22, 25, 880, "Vendor_C"],
            ["CC0303030003", "CLUTCH DISC", 8, 12, 640, "Vendor_D"],
            ["DD0404040004", "SPARK PLUG", 45, 35, 450, "Vendor_A"],
            ["EE0505050005", "AIR FILTER", 30, 28, 600, "Vendor_B"],
            ["FF0606060006", "FUEL FILTER", 55, 50, 1100, "Vendor_E"],
            ["GG0707070007", "TRANSMISSION OIL", 40, 35, 800, "Vendor_C"],
            ["HH0808080008", "COOLANT", 22, 30, 660, "Vendor_D"],
            ["II0909090009", "BRAKE FLUID", 15, 12, 300, "Vendor_A"],
            ["JJ1010101010", "WINDSHIELD WASHER", 33, 25, 495, "Vendor_B"]
        ]
        
        return [{'Material': row[0], 'Description': row[1], 'QTY': self.safe_float_convert(row[2]), 
                'RM_IN_QTY': self.safe_float_convert(row[3]), 'Stock_Value': self.safe_int_convert(row[4]), 
                'Vendor': row[5]} for row in sample_data]
    
    def standardize_inventory_data(self, df):
        """Standardize inventory data from uploaded file"""
        if df is None or df.empty:
            return []
        
        # Column mapping with variations
        column_mappings = {
            'material': ['material', 'part_no', 'part_number', 'item_code', 'code'],
            'description': ['description', 'item_description', 'part_description', 'desc'],
            'qty': ['qty', 'quantity', 'current_qty', 'stock_qty'],
            'rm_in_qty': ['rm_in_qty', 'rm_qty', 'required_qty', 'target_qty'],
            'stock_value': ['stock_value', 'value', 'total_value', 'inventory_value'],
            'vendor': ['vendor', 'vendor_name', 'supplier', 'supplier_name']
        }
        
        # Find matching columns
        df_columns = [col.lower().strip() for col in df.columns]
        mapped_columns = {}
        
        for key, variations in column_mappings.items():
            for variation in variations:
                if variation in df_columns:
                    original_col = df.columns[df_columns.index(variation)]
                    mapped_columns[key] = original_col
                    break
        
        if 'material' not in mapped_columns or 'qty' not in mapped_columns or 'rm_in_qty' not in mapped_columns:
            st.error("❌ Required columns not found. Please ensure your file has Material, QTY, and RM IN QTY columns.")
            return []
        
        standardized_data = []
        for _, row in df.iterrows():
            item = {
                'Material': str(row[mapped_columns['material']]).strip(),
                'Description': str(row.get(mapped_columns.get('description', ''), '')).strip(),
                'QTY': self.safe_float_convert(row[mapped_columns['qty']]),
                'RM_IN_QTY': self.safe_float_convert(row[mapped_columns['rm_in_qty']]),
                'Stock_Value': self.safe_int_convert(row.get(mapped_columns.get('stock_value', ''), 0)),
                'Vendor': str(row.get(mapped_columns.get('vendor', ''), 'Unknown')).strip()
            }
            standardized_data.append(item)
        
        return standardized_data
    
    def analyze_inventory(self, inventory_data, tolerance=30):
        """Analyze inventory with given tolerance"""
        results = []
        
        for item in inventory_data:
            current_qty = item['QTY']
            rm_qty = item['RM_IN_QTY']
            
            # Calculate variance
            if rm_qty > 0:
                variance_pct = ((current_qty - rm_qty) / rm_qty) * 100
            else:
                variance_pct = 0
            
            variance_value = current_qty - rm_qty
            
            # Determine status
            if abs(variance_pct) <= tolerance:
                status = 'Within Norms'
            elif variance_pct > tolerance:
                status = 'Excess Inventory'
            else:
                status = 'Short Inventory'
            
            result = {
                'Material': item['Material'],
                'Description': item['Description'],
                'QTY': current_qty,
                'RM_IN_QTY': rm_qty,
                'Stock_Value': item['Stock_Value'],
                'Variance_%': variance_pct,
                'Variance_Value': variance_value,
                'Status': status,
                'Vendor': item['Vendor']
            }
            results.append(result)
        
        return results
    
    def calculate_summary(self, analyzed_data):
        """Calculate summary statistics"""
        summary = {
            'Within Norms': {'count': 0, 'value': 0},
            'Excess Inventory': {'count': 0, 'value': 0},
            'Short Inventory': {'count': 0, 'value': 0}
        }
        
        for item in analyzed_data:
            status = item['Status']
            summary[status]['count'] += 1
            summary[status]['value'] += item['Stock_Value']
        
        return summary

def display_overview_tab(analyzer, processed_data, summary_data, tolerance):
    """Display overview tab content"""
    st.markdown('<div class="tab-header">📈 Overview Dashboard</div>', unsafe_allow_html=True)
    
    # Display status criteria
    st.info(f"""
    **Status Criteria (Tolerance: ±{tolerance}%)**
    - 🟢 **Within Norms**: QTY = RM IN QTY ± {tolerance}%
    - 🔵 **Excess Inventory**: QTY > RM IN QTY + {tolerance}%
    - 🔴 **Short Inventory**: QTY < RM IN QTY - {tolerance}%
    """)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="status-card status-normal">', unsafe_allow_html=True)
        st.metric(
            label="🟢 Within Norms",
            value=f"{summary_data['Within Norms']['count']} parts",
            delta=f"₹{summary_data['Within Norms']['value']:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="status-card status-excess">', unsafe_allow_html=True)
        st.metric(
            label="🔵 Excess Inventory",
            value=f"{summary_data['Excess Inventory']['count']} parts",
            delta=f"₹{summary_data['Excess Inventory']['value']:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="status-card status-short">', unsafe_allow_html=True)
        st.metric(
            label="🔴 Short Inventory",
            value=f"{summary_data['Short Inventory']['count']} parts",
            delta=f"₹{summary_data['Short Inventory']['value']:,}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Status distribution pie chart
        status_counts = [summary_data[status]['count'] for status in summary_data.keys()]
        status_labels = list(summary_data.keys())
        colors = ['#4CAF50', '#2196F3', '#F44336']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=status_labels,
            values=status_counts,
            marker_colors=colors,
            hole=0.4
        )])
        fig_pie.update_layout(
            title="Inventory Status Distribution",
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Value distribution bar chart
        status_values = [summary_data[status]['value'] for status in summary_data.keys()]
        
        fig_bar = go.Figure(data=[go.Bar(
            x=status_labels,
            y=status_values,
            marker_color=colors
        )])
        fig_bar.update_layout(
            title="Inventory Value by Status (₹)",
            xaxis_title="Status",
            yaxis_title="Value (₹)",
            height=400
        )
        st.plotly_chart(fig_bar, use_container_width=True)

def display_detailed_analysis_tab(processed_data, tolerance):
    """Display detailed analysis tab content"""
    st.markdown('<div class="tab-header">🔍 Detailed Analysis</div>', unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=['All'] + list(set(item['Status'] for item in processed_data)),
            key="detailed_status_filter"
        )
    
    with col2:
        vendor_filter = st.selectbox(
            "Filter by Vendor",
            options=['All'] + sorted(list(set(item['Vendor'] for item in processed_data))),
            key="detailed_vendor_filter"
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=['Material', 'Variance_%', 'Stock_Value', 'QTY'],
            key="detailed_sort"
        )
    
    # Apply filters
    filtered_data = processed_data.copy()
    
    if status_filter != 'All':
        filtered_data = [item for item in filtered_data if item['Status'] == status_filter]
    
    if vendor_filter != 'All':
        filtered_data = [item for item in filtered_data if item['Vendor'] == vendor_filter]
    
    # Sort data
    filtered_data = sorted(filtered_data, key=lambda x: x[sort_by], reverse=True)
    
    st.info(f"Showing {len(filtered_data)} items out of {len(processed_data)} total items")
    
    # Display table
    if filtered_data:
        df = pd.DataFrame(filtered_data)
        
        # Format the dataframe for better display
        df['Variance_%'] = df['Variance_%'].round(2)
        df['QTY'] = df['QTY'].round(2)
        df['RM_IN_QTY'] = df['RM_IN_QTY'].round(2)
        df['Stock_Value'] = df['Stock_Value'].apply(lambda x: f"₹{x:,}")
        
        # Color code based on status
        def highlight_status(row):
            if row['Status'] == 'Within Norms':
                return ['background-color: #e8f5e8'] * len(row)
            elif row['Status'] == 'Excess Inventory':
                return ['background-color: #e3f2fd'] * len(row)
            else:
                return ['background-color: #ffebee'] * len(row)
        
        styled_df = df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=600)

def display_vendor_analysis_tab(processed_data):
    """Display vendor analysis tab content"""
    st.markdown('<div class="tab-header">🏭 Vendor Analysis</div>', unsafe_allow_html=True)
    
    # Vendor summary
    vendor_summary = {}
    for item in processed_data:
        vendor = item['Vendor']
        if vendor not in vendor_summary:
            vendor_summary[vendor] = {
                'Total Parts': 0,
                'Within Norms': 0,
                'Excess Inventory': 0,
                'Short Inventory': 0,
                'Total Value': 0
            }
        
        vendor_summary[vendor]['Total Parts'] += 1
        vendor_summary[vendor][item['Status']] += 1
        vendor_summary[vendor]['Total Value'] += item['Stock_Value']
    
    # Convert to DataFrame for display
    vendor_df = pd.DataFrame.from_dict(vendor_summary, orient='index').reset_index()
    vendor_df.columns = ['Vendor'] + list(vendor_df.columns[1:])
    vendor_df['Total Value'] = vendor_df['Total Value'].apply(lambda x: f"₹{x:,}")
    
    st.subheader("📊 Vendor Summary")
    st.dataframe(vendor_df, use_container_width=True)
    
    # Vendor selection for detailed view
    selected_vendor = st.selectbox(
        "Select Vendor for Detailed Analysis",
        options=sorted(list(vendor_summary.keys())),
        key="vendor_detail_select"
    )
    
    if selected_vendor:
        st.markdown(f'<div class="vendor-filter">🏢 <strong>Vendor Focus:</strong> {selected_vendor}</div>', unsafe_allow_html=True)
        
        vendor_items = [item for item in processed_data if item['Vendor'] == selected_vendor]
        
        # Vendor metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_parts = len(vendor_items)
            st.metric("Total Parts", total_parts)
        
        with col2:
            short_items = len([item for item in vendor_items if item['Status'] == 'Short Inventory'])
            st.metric("Short Inventory", short_items, delta=f"{(short_items/total_parts)*100:.1f}%")
        
        with col3:
            excess_items = len([item for item in vendor_items if item['Status'] == 'Excess Inventory'])
            st.metric("Excess Inventory", excess_items, delta=f"{(excess_items/total_parts)*100:.1f}%")
        
        with col4:
            normal_items = len([item for item in vendor_items if item['Status'] == 'Within Norms'])
            st.metric("Within Norms", normal_items, delta=f"{(normal_items/total_parts)*100:.1f}%")
        
        # Vendor items chart
        status_counts = {}
        for item in vendor_items:
            status = item['Status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        fig = px.bar(
            x=list(status_counts.keys()),
            y=list(status_counts.values()),
            color=list(status_counts.keys()),
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            },
            title=f"Status Distribution for {selected_vendor}"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Vendor items table
        if vendor_items:
            df = pd.DataFrame(vendor_items)
            df['Variance_%'] = df['Variance_%'].round(2)
            df['Stock_Value'] = df['Stock_Value'].apply(lambda x: f"₹{x:,}")
            st.dataframe(df, use_container_width=True)

def display_charts_tab(processed_data):
    """Display charts and visualizations tab content"""
    st.markdown('<div class="tab-header">📊 Charts & Visualizations</div>', unsafe_allow_html=True)
    
    df = pd.DataFrame(processed_data)
    
    # Chart selection
    chart_type = st.selectbox(
        "Select Chart Type",
        options=["Variance Analysis", "Stock Value Analysis", "Vendor Comparison", "Scatter Plot Analysis"],
        key="chart_type_select"
    )
    
    if chart_type == "Variance Analysis":
        st.subheader("📈 Variance Percentage Analysis")
        
        # Histogram of variance percentages
        fig = px.histogram(
            df, 
            x='Variance_%', 
            color='Status',
            nbins=20,
            title="Distribution of Variance Percentages",
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Box plot by status
        fig2 = px.box(
            df, 
            x='Status', 
            y='Variance_%',
            color='Status',
            title="Variance Percentage by Status",
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            }
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    elif chart_type == "Stock Value Analysis":
        st.subheader("💰 Stock Value Analysis")
        
        # Stock value by status
        fig = px.box(
            df, 
            x='Status', 
            y='Stock_Value',
            color='Status',
            title="Stock Value Distribution by Status",
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top 10 items by stock value
        top_items = df.nlargest(10, 'Stock_Value')
        fig2 = px.bar(
            top_items,
            x='Material',
            y='Stock_Value',
            color='Status',
            title="Top 10 Items by Stock Value",
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            }
        )
        fig2.update_xaxis(tickangle=45)
        st.plotly_chart(fig2, use_container_width=True)
    
    elif chart_type == "Vendor Comparison":
        st.subheader("🏭 Vendor Comparison")
        
        # Vendor performance chart
        vendor_stats = df.groupby(['Vendor', 'Status']).size().unstack(fill_value=0)
        
        fig = px.bar(
            vendor_stats.reset_index(),
            x='Vendor',
            y=['Within Norms', 'Excess Inventory', 'Short Inventory'],
            title="Vendor Performance Comparison",
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Vendor stock value
        vendor_value = df.groupby('Vendor')['Stock_Value'].sum().reset_index()
        fig2 = px.pie(
            vendor_value,
            values='Stock_Value',
            names='Vendor',
            title="Stock Value Distribution by Vendor"
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    elif chart_type == "Scatter Plot Analysis":
        st.subheader("🎯 Scatter Plot Analysis")
        
        # QTY vs RM_IN_QTY scatter plot
        fig = px.scatter(
            df,
            x='RM_IN_QTY',
            y='QTY',
            color='Status',
            size='Stock_Value',
            hover_data=['Material', 'Vendor'],
            title="Current QTY vs Required QTY (Size = Stock Value)",
            color_discrete_map={
                'Within Norms': '#4CAF50',
                'Excess Inventory': '#2196F3',
                'Short Inventory': '#F44336'
            }
        )
        
        # Add diagonal line for perfect match
        max_val = max(df['QTY'].max(), df['RM_IN_QTY'].max())
        fig.add_shape(
            type="line",
            x0=0, y0=0, x1=max_val, y1=max_val,
            line=dict(color="gray", width=2, dash="dash"),
            name="Perfect Match"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def display_reports_tab(processed_data, summary_data, tolerance):
    """Display reports tab content"""
    st.markdown('<div class="tab-header">📋 Reports & Export</div>', unsafe_allow_html=True)
    
    # Report generation options
    st.subheader("📊 Generate Reports")
    
    report_type = st.selectbox(
        "Select Report Type",
        options=["Executive Summary", "Detailed Inventory Report", "Vendor Performance Report", "Action Items Report"],
        key="report_type_select"
    )
    
    if report_type == "Executive Summary":
        st.markdown("### 📈 Executive Summary Report")
        
        # Key metrics
        total_items = len(processed_data)
        total_value = sum(item['Stock_Value'] for item in processed_data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", total_items)
        with col2:
            st.metric("Total Value", f"₹{total_value:,}")
        with col3:
            accuracy_pct = (summary_data['Within Norms']['count'] / total_items) * 100
            st.metric("Accuracy %", f"{accuracy_pct:.1f}%")
        with col4:
            problem_items = summary_data['Short Inventory']['count'] + summary_data['Excess Inventory']['count']
            st.metric("Items Needing Action", problem_items)
        
        # Summary text
        st.markdown(f"""
        **Inventory Analysis Summary (Tolerance: ±{tolerance}%)**
        
        - **Total Inventory Items:** {total_items:,}
        - **Total Inventory Value:** ₹{total_value:,}
        - **Items Within Norms:** {summary_data['Within Norms']['count']} ({(summary_data['Within Norms']['count']/total_items)*100:.1f}%)
        - **Excess Inventory Items:** {summary_data['Excess Inventory']['count']} ({(summary_data['Excess Inventory']['count']/total_items)*100:.1f}%)
        - **Short Inventory Items:** {summary_data['Short Inventory']['count']} ({(summary_data['Short Inventory']['count']/total_items)*100:.1f}%)
        
        **Key Insights:**
        - Inventory accuracy rate: {accuracy_pct:.1f}%
        - {problem_items} items require immediate attention
        - Excess inventory value: ₹{summary_data['Excess Inventory']['value']:,}
        - Short inventory value: ₹{summary_data['Short Inventory']['value']:,}
        """)
    
    elif report_type == "Detailed Inventory Report":
        st.markdown("### 📋 Detailed Inventory Report")
        
        # Generate detailed report
        df = pd.DataFrame(processed_data)
        df['Variance_%'] = df['Variance_%'].round(2)
        df['Stock_Value_Formatted'] = df['Stock_Value'].apply(lambda x: f"₹{x:,}")
        
        st.dataframe(df, use_container_width=True, height=400)
        
        # Download options
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Detailed Report (CSV)",
            data=csv,
            file_name=f"inventory_detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    elif report_type == "Vendor Performance Report":
        st.markdown("### 🏭 Vendor Performance Report")
        
        # Vendor analysis
        vendor_summary = {}
        for item in processed_data:
            vendor = item['Vendor']
            if vendor not in vendor_summary:
                vendor_summary[vendor] = {
                    'Total_Parts': 0,
                    'Within_Norms': 0,
                    'Excess_Inventory': 0,
                    'Short_Inventory': 0,
                    'Total_Value': 0,
                    'Accuracy_%': 0
                }
            
            vendor_summary[vendor]['Total_Parts'] += 1
            vendor_summary[vendor][item['Status'].replace(' ', '_')] += 1
            vendor_summary[vendor]['Total_Value'] += item['Stock_Value']
        
        # Calculate accuracy percentage
        for vendor in vendor_summary:
            total = vendor_summary[vendor]['Total_Parts']
            within_norms = vendor_summary[vendor]['Within_Norms']
            vendor_summary[vendor]['Accuracy_%'] = (within_norms / total) * 100 if total > 0 else 0
        
        # Convert to DataFrame
        vendor_df = pd.DataFrame.from_dict(vendor_summary, orient='index').reset_index()
        vendor_df.columns = ['Vendor'] + list(vendor_df.columns[1:])
        vendor_df['Total_Value'] = vendor_df['Total_Value'].apply(lambda x: f"₹{x:,}")
        vendor_df['Accuracy_%'] = vendor_df['Accuracy_%'].round(2)
        
        st.dataframe(vendor_df, use_container_width=True)
        
        # Download vendor report
        vendor_csv = vendor_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Vendor Report (CSV)",
            data=vendor_csv,
            file_name=f"vendor_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    elif report_type == "Action Items Report":
        st.markdown("### 🎯 Action Items Report")
        
        # Filter items needing action
        action_items = [item for item in processed_data if item['Status'] != 'Within Norms']
        
        if action_items:
            # Prioritize by stock value and variance
            action_items_sorted = sorted(action_items, key=lambda x: (abs(x['Variance_%']), x['Stock_Value']), reverse=True)
            
            st.markdown("#### High Priority Items (sorted by variance % and stock value)")
            
            # Display top 10 action items
            top_action_items = action_items_sorted[:10]
            action_df = pd.DataFrame(top_action_items)
            
            # Format for display
            action_df['Variance_%'] = action_df['Variance_%'].round(2)
            action_df['Stock_Value'] = action_df['Stock_Value'].apply(lambda x: f"₹{x:,}")
            action_df['Priority'] = range(1, len(action_df) + 1)
            
            # Reorder columns
            action_df = action_df[['Priority', 'Material', 'Description', 'Status', 'Variance_%', 'Stock_Value', 'Vendor']]
            
            st.dataframe(action_df, use_container_width=True)
            
            # Action recommendations
            excess_items = len([item for item in action_items if item['Status'] == 'Excess Inventory'])
            short_items = len([item for item in action_items if item['Status'] == 'Short Inventory'])
            
            st.markdown(f"""
            #### 📋 Recommended Actions:
            
            **Excess Inventory ({excess_items} items):**
            - Review demand forecasts and adjust procurement
            - Consider liquidation or transfer to other locations
            - Negotiate with vendors for returnable items
            - Implement just-in-time inventory practices
            
            **Short Inventory ({short_items} items):**
            - Expedite procurement for critical items
            - Review safety stock levels
            - Implement automatic reorder points
            - Improve demand forecasting accuracy
            """)
            
            # Download action items report
            full_action_df = pd.DataFrame(action_items_sorted)
            full_action_df['Variance_%'] = full_action_df['Variance_%'].round(2)
            action_csv = full_action_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Action Items Report (CSV)",
                data=action_csv,
                file_name=f"action_items_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.success("🎉 Excellent! No action items needed - all inventory is within norms!")

def main():
    """Main application function"""
    st.title("📊 Inventory Management System")
    st.markdown("*Advanced inventory analysis with comprehensive reporting capabilities*")
    
    # Initialize analyzer
    analyzer = InventoryAnalyzer()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # File upload
        uploaded_file = st.file_uploader(
            "📁 Upload Inventory File",
            type=['csv', 'xlsx', 'xls'],
            help="Upload your inventory data file (CSV or Excel format)"
        )
        
        # Tolerance setting
        tolerance = st.slider(
            "🎯 Tolerance Percentage",
            min_value=5,
            max_value=50,
            value=30,
            step=5,
            help="Acceptable variance percentage for inventory levels"
        )
        
        # Data source selection
        use_sample = st.checkbox(
            "📋 Use Sample Data",
            value=True,
            help="Use built-in sample data for demonstration"
        )
        
        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        
        # Process data based on selection
        if use_sample or uploaded_file is None:
            inventory_data = analyzer.load_sample_data()
            st.info("Using sample data")
        else:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                inventory_data = analyzer.standardize_inventory_data(df)
                if not inventory_data:
                    st.error("Failed to process uploaded file. Using sample data.")
                    inventory_data = analyzer.load_sample_data()
                else:
                    st.success(f"Loaded {len(inventory_data)} items from file")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                inventory_data = analyzer.load_sample_data()
        
        # Analyze inventory
        processed_data = analyzer.analyze_inventory(inventory_data, tolerance)
        summary_data = analyzer.calculate_summary(processed_data)
        
        # Display quick stats in sidebar
        total_items = len(processed_data)
        total_value = sum(item['Stock_Value'] for item in processed_data)
        
        st.metric("Total Items", total_items)
        st.metric("Total Value", f"₹{total_value:,}")
        st.metric("Within Norms", f"{summary_data['Within Norms']['count']}")
        st.metric("Need Action", f"{summary_data['Excess Inventory']['count'] + summary_data['Short Inventory']['count']}")
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview", 
        "🔍 Detailed Analysis", 
        "🏭 Vendor Analysis", 
        "📊 Charts", 
        "📋 Reports"
    ])
    
    with tab1:
        display_overview_tab(analyzer, processed_data, summary_data, tolerance)
    
    with tab2:
        display_detailed_analysis_tab(processed_data, tolerance)
    
    with tab3:
        display_vendor_analysis_tab(processed_data)
    
    with tab4:
        display_charts_tab(processed_data)
    
    with tab5:
        display_reports_tab(processed_data, summary_data, tolerance)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "📊 Inventory Management System | Built with Streamlit | "
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
