import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging
import pickle
import base64
import uuid
import io
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

.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 5px;
    padding: 15px;
    margin: 10px 0;
}

.lock-button {
    background-color: #28a745;
    color: white;
    padding: 10px 20px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
}

.switch-user-button {
    background-color: #007bff;
    color: white;
    padding: 8px 16px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

class DataPersistence:
    """Handle data persistence across sessions"""
    
    @staticmethod
    def save_data_to_session_state(key, data):
        """Save data with timestamp to session state"""
        st.session_state[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'saved': True
        }
    
    @staticmethod
    def load_data_from_session_state(key):
        """Load data from session state if it exists"""
        if key in st.session_state and isinstance(st.session_state[key], dict):
            return st.session_state[key].get('data')
        return None
    
    @staticmethod
    def is_data_saved(key):
        """Check if data is saved"""
        if key in st.session_state and isinstance(st.session_state[key], dict):
            return st.session_state[key].get('saved', False)
        return False
    
    @staticmethod
    def get_data_timestamp(key):
        """Get data timestamp"""
        if key in st.session_state and isinstance(st.session_state[key], dict):
            return st.session_state[key].get('timestamp')
        return None

class InventoryAnalyzer:
    """Enhanced inventory analysis with comprehensive reporting"""
    
    def __init__(self):
        self.status_colors = {
            'Within Norms': '#4CAF50',    # Green
            'Excess Inventory': '#2196F3', # Blue
            'Short Inventory': '#F44336'   # Red
        }
        
    def analyze_inventory(self, pfep_data, current_inventory, tolerance=30):
        """Analyze ONLY inventory parts that exist in PFEP"""
        if tolerance is None:
            tolerance = st.session_state.get("admin_tolerance", 30)  # default fallback
        results = []
        # Create lookup dictionaries
        pfep_dict = {str(item['Part_No']).strip().upper(): item for item in pfep_data}
        inventory_dict = {str(item['Part_No']).strip().upper(): item for item in current_inventory}
        
        # ✅ Loop over inventory only
        for part_no, inventory_item in inventory_dict.items():
            pfep_item = pfep_dict.get(part_no)
            if not pfep_item:
                continue  # Skip inventory parts not found in PFEP
            current_qty = inventory_item.get('Current_QTY', 0)
            stock_value = inventory_item.get('Stock_Value', 0)
            rm_qty = pfep_item.get('RM_IN_QTY', 0)
            
            # Calculate variance
            # 
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
                'Material': part_no,
                'Description': pfep_item.get('Description', ''),
                'QTY': current_qty,
                'RM IN QTY': rm_qty,
                'Stock_Value': stock_value,
                'Variance_%': variance_pct,
                'Variance_Value': variance_value,
                'Status': status,
                'Vendor': pfep_item.get('Vendor_Name', 'Unknown'),
                'Vendor_Code': pfep_item.get('Vendor_Code', ''),
                'City': pfep_item.get('City', ''),
                'State': pfep_item.get('State', '')
            }
            results.append(result)
        return results
    def get_vendor_summary(self, processed_data):
        """Get summary data by vendor"""
        vendor_summary = {}
        for item in processed_data:
            vendor = item['Vendor']
            if vendor not in vendor_summary:
                vendor_summary[vendor] = {
                    'total_parts': 0,
                    'total_qty': 0,
                    'total_rm': 0,
                    'total_value': 0,
                    'short_parts': 0,
                    'excess_parts': 0,
                    'normal_parts': 0,
                    'short_value': 0,
                    'excess_value': 0,
                    'normal_value': 0
                }
            vendor_summary[vendor]['total_parts'] += 1
            vendor_summary[vendor]['total_qty'] += item['QTY']
            vendor_summary[vendor]['total_rm'] += item['RM IN QTY']
            vendor_summary[vendor]['total_value'] += item['Stock_Value']
            if item['Status'] == 'Short Inventory':
                vendor_summary[vendor]['short_parts'] += 1
                vendor_summary[vendor]['short_value'] += item['Stock_Value']
            elif item['Status'] == 'Excess Inventory':
                vendor_summary[vendor]['excess_parts'] += 1
                vendor_summary[vendor]['excess_value'] += item['Stock_Value']
            else:
                vendor_summary[vendor]['normal_parts'] += 1
                vendor_summary[vendor]['normal_value'] += item['Stock_Value']
        return vendor_summary

class InventoryManagementSystem:
    """Main application class"""
    
    def __init__(self):
        self.analyzer = InventoryAnalyzer()
        self.persistence = DataPersistence()
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
        
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                'default_tolerance': 30,
                'chart_theme': 'plotly'
            }
        
        # Initialize persistent data keys
        self.persistent_keys = [
            'persistent_pfep_data',
            'persistent_pfep_locked',
            'persistent_inventory_data', 
            'persistent_inventory_locked',
            'persistent_analysis_results'
        ]
        
        # Initialize persistent data if not exists
        for key in self.persistent_keys:
            if key not in st.session_state:
                st.session_state[key] = None
    def safe_print(self, message):
        """Safely print to streamlit or console"""
        try:
            st.write(message)
        except NameError:
            print(message)
    
    def safe_error(self, message):
        """Safely show error in streamlit or console"""
        try:
            st.error(message)
        except NameError:
            print(f"ERROR: {message}")
    
    def safe_warning(self, message):
        """Safely show warning in streamlit or console"""
        try:
            st.warning(message)
        except NameError:
            print(f"WARNING: {message}")
    
    def safe_float_convert(self, value):
       """Enhanced safe float conversion with better error handling"""
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    try:
        # Handle different input types
        if isinstance(value, (int, float)):
            return float(value)
        
        str_value = str(value).strip()
        
        # Skip empty or invalid strings
        if not str_value or str_value.lower() in ['nan', 'none', 'null', '']:
            return 0.0
        
        # Remove common formatting
        str_value = str_value.replace(',', '').replace(' ', '').replace('₹', '').replace('$', '').replace('€', '')
        
        # Handle percentage
        if str_value.endswith('%'):
            str_value = str_value[:-1]
        
        # Handle negative values in parentheses
        if str_value.startswith('(') and str_value.endswith(')'):
            str_value = '-' + str_value[1:-1]
        
        # Handle scientific notation
        if 'e' in str_value.lower():
            return float(str_value)
        
        return float(str_value)
        
    except (ValueError, TypeError) as e:
        print(f"Failed to convert '{value}' to float: {e}")
        return 0.0
            
    def safe_int_convert(self, value):
        """Enhanced safe int conversion"""
        return int(self.safe_float_convert(value))
    def create_top_parts_chart(self, data, status_type, color, key):
        # Filter top 10 parts of the given status type
        top_items = [item for item in data if item['Status'] == status_type]
        top_items = sorted(top_items, key=lambda x: abs(x['Variance_%']), reverse=True)[:10]

        if not top_items:
            st.info(f"No parts found for status: {status_type}")
            return

        materials = [item['Material'] for item in top_items]
        variances = [item['Variance_%'] for item in top_items]

        fig = go.Figure(data=[
            go.Bar(x=variances, y=materials, orientation='h', marker_color=color)
        ])

        fig.update_layout(
            title=f"Top 10 Parts - {status_type}",
            xaxis_title="Variance %",
            yaxis_title="Material Code",
            yaxis=dict(autorange='reversed')
        )

        st.plotly_chart(fig, use_container_width=True, key=key)
    
    def safe_int_convert(self, value):
        """Enhanced safe int conversion"""
        return int(self.safe_float_convert(value))
    
    def authenticate_user(self):
        """Enhanced authentication system with better UX and user switching"""
        st.sidebar.markdown("### 🔐 Authentication")
        
        if st.session_state.user_role is None:
            role = st.sidebar.selectbox(
                "Select Role", 
                ["Select Role", "Admin", "User"],
                help="Choose your role to access appropriate features"
            )
            
            if role == "Admin":
                with st.sidebar.container():
                    st.markdown("**Admin Login**")
                    password = st.text_input("Admin Password", type="password", key="admin_pass")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔑 Login", key="admin_login"):
                            if password == "Agilomatrix@1234":
                                st.session_state.user_role = "Admin"
                                st.success("✅ Admin authenticated!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid password")
                    with col2:
                        if st.button("🏠 Demo", key="admin_demo"):
                            st.session_state.user_role = "Admin"
                            st.info("🎮 Demo mode activated!")
                            st.rerun()
            
            elif role == "User":
                if st.sidebar.button("👤 Enter as User", key="user_login"):
                    st.session_state.user_role = "User"
                    st.sidebar.success("✅ User access granted!")
                    st.rerun()
        else:
            # User info and controls
            st.sidebar.success(f"✅ **{st.session_state.user_role}** logged in")
            
            # Display data status
            self.display_data_status()
            
            # User switching option for Admin
            if st.session_state.user_role == "Admin":
                # ✅ Show PFEP lock status
                pfep_locked = st.session_state.get("persistent_pfep_locked", False)
                st.sidebar.markdown(f"🔒 PFEP Locked: **{pfep_locked}**")
                # ✅ Always show switch role if PFEP is locked
                if pfep_locked:
                    st.sidebar.markdown("### 🔄 Switch Role")
                    if st.sidebar.button("👤 Switch to User View", key="switch_to_user"):
                        st.session_state.user_role = "User"
                        st.sidebar.success("✅ Switched to User view!")
                        st.rerun()
                else:
                    st.sidebar.info("ℹ️ PFEP is not locked. Lock PFEP to allow switching to User.")

            
            # User preferences (for Admin only)
            if st.session_state.user_role == "Admin":
                with st.sidebar.expander("⚙️ Preferences"):
                    st.session_state.user_preferences['default_tolerance'] = st.selectbox(
                        "Default Tolerance", [10, 20, 30, 40, 50], 
                        index=2, key="pref_tolerance"
                    )
                    st.session_state.user_preferences['chart_theme'] = st.selectbox(
                        "Chart Theme", ['plotly', 'plotly_white', 'plotly_dark'],
                        key="pref_theme"
                    )
            
            # Logout button
            st.sidebar.markdown("---")
            if st.sidebar.button("🚪 Logout", key="logout_btn"):
                # Only clear user session, not persistent data
                keys_to_keep = self.persistent_keys + ['user_preferences']
                session_copy = {k: v for k, v in st.session_state.items() if k in keys_to_keep}
                
                # Clear all session state
                st.session_state.clear()
                
                # Restore persistent data
                for k, v in session_copy.items():
                    st.session_state[k] = v
                
                st.rerun()
    
    def display_data_status(self):
        """Display current data loading status in sidebar"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Data Status")
        
        # Check persistent PFEP data
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        pfep_locked = st.session_state.get('persistent_pfep_locked', False)
        
        if pfep_data:
            pfep_count = len(pfep_data)
            lock_icon = "🔒" if pfep_locked else "🔓"
            st.sidebar.success(f"✅ PFEP Data: {pfep_count} parts {lock_icon}")
            timestamp = self.persistence.get_data_timestamp('persistent_pfep_data')
            if timestamp:
                st.sidebar.caption(f"Loaded: {timestamp.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.sidebar.error("❌ PFEP Data: Not loaded")
        
        # Check persistent inventory data
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        inventory_locked = st.session_state.get('persistent_inventory_locked', False)
        
        if inventory_data:
            inv_count = len(inventory_data)
            lock_icon = "🔒" if inventory_locked else "🔓"
            st.sidebar.success(f"✅ Inventory: {inv_count} parts {lock_icon}")
            timestamp = self.persistence.get_data_timestamp('persistent_inventory_data')
            if timestamp:
                st.sidebar.caption(f"Loaded: {timestamp.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.sidebar.error("❌ Inventory: Not loaded")
        
        # Analysis results status
        analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
        if analysis_data:
            st.sidebar.info(f"📈 Analysis: {len(analysis_data)} parts analyzed")
    
    def load_sample_pfep_data(self):
        """Load enhanced sample PFEP master data"""
        pfep_sample = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", 4.000, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AC0303020105", "RAIN GUTTER PROFILE", 6.000, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", 10.000, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AC0203020077", "Bulb beading LV battery flap", 3.000, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["AC0303020104", "L- PROFILE JAM PILLAR", 20.000, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", 30, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["AA0115120001", "HVPDU ms", 12, "V004", "Vendor_D", "Bangalore", "Karnataka"],
            ["AA0119020017", "REAR TURN INDICATOR", 40, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["AA0119020019", "REVERSING LAMP", 20, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AA0822010800", "SIDE DISPLAY BOARD", 50, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["BB0101010001", "ENGINE OIL FILTER", 45, "V005", "Vendor_E", "Pune", "Maharashtra"],
            ["BB0202020002", "BRAKE PAD SET", 25, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["CC0303030003", "CLUTCH DISC", 12, "V004", "Vendor_D", "Bangalore", "Karnataka"],
            ["DD0404040004", "SPARK PLUG", 35, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["EE0505050005", "AIR FILTER", 28, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["FF0606060006", "FUEL FILTER", 50, "V005", "Vendor_E", "Pune", "Maharashtra"],
            ["GG0707070007", "TRANSMISSION OIL", 35, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["HH0808080008", "COOLANT", 30, "V004", "Vendor_D", "Bangalore", "Karnataka"],
            ["II0909090009", "BRAKE FLUID", 12, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["JJ1010101010", "WINDSHIELD WASHER", 25, "V002", "Vendor_B", "Delhi", "Delhi"]
        ]
        
        pfep_data = []
        for row in pfep_sample:
            pfep_data.append({
                'Part_No': row[0],
                'Description': row[1],
                'RM_IN_QTY': self.safe_float_convert(row[2]),
                'Vendor_Code': row[3],
                'Vendor_Name': row[4],
                'City': row[5],
                'State': row[6]
            })
        
        return pfep_data
    
    def load_sample_current_inventory(self):
        """Load enhanced sample current inventory data with more realistic variances"""
        current_sample = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", 5.230, 496],
            ["AC0303020105", "RAIN GUTTER PROFILE", 8.360, 1984],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", 12.500, 2356],
            ["AC0203020077", "Bulb beading LV battery flap", 3.500, 248],
            ["AC0303020104", "L- PROFILE JAM PILLAR", 15.940, 992],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", 25, 1248],
            ["AA0115120001", "HVPDU ms", 18, 1888],
            ["AA0119020017", "REAR TURN INDICATOR", 35, 1512],
            ["AA0119020019", "REVERSING LAMP", 28, 1152],
            ["AA0822010800", "SIDE DISPLAY BOARD", 42, 2496],
            ["BB0101010001", "ENGINE OIL FILTER", 65, 1300],
            ["BB0202020002", "BRAKE PAD SET", 22, 880],
            ["CC0303030003", "CLUTCH DISC", 8, 640],
            ["DD0404040004", "SPARK PLUG", 45, 450],
            ["EE0505050005", "AIR FILTER", 30, 600],
            ["FF0606060006", "FUEL FILTER", 55, 1100],
            ["GG0707070007", "TRANSMISSION OIL", 40, 800],
            ["HH0808080008", "COOLANT", 22, 660],
            ["II0909090009", "BRAKE FLUID", 15, 300],
            ["JJ1010101010", "WINDSHIELD WASHER", 33, 495]
        ]
        
        return [{'Part_No': row[0], 'Description': row[1], 
                'Current_QTY': self.safe_float_convert(row[2]), 
                'Stock_Value': self.safe_int_convert(row[3])} for row in current_sample]
    
    def standardize_pfep_data(self, df):
        """Enhanced PFEP data standardization with better error handling"""
        if df is None or df.empty:
            return []
        
        # Column mapping with more variations
        column_mappings = {
            'part_no': ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code', 'part no', 'partno'],
            'description': ['description', 'item_description', 'part_description', 'desc', 'part description', 'material_description', 'item desc'],
            'rm_qty': ['rm_in_qty', 'rm_qty', 'required_qty', 'norm_qty', 'target_qty', 'rm', 'ri_in_qty', 'rm in qty'],
            'vendor_code': ['vendor_code', 'vendor_id', 'supplier_code', 'supplier_id', 'vendor id', 'Vendor Code', 'vendor code'],
            'vendor_name': ['vendor_name', 'vendor', 'supplier_name', 'supplier','Vendor Name', 'vendor name'],
            'city': ['city', 'location', 'place'],
            'state': ['state', 'region', 'province']
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
        
        if 'part_no' not in mapped_columns or 'rm_qty' not in mapped_columns:
            st.error("❌ Required columns not found. Please ensure your file has Part Number and RM Quantity columns.")
            return []
        
        standardized_data = []
        for _, row in df.iterrows():
            item = {
                'Part_No': str(row[mapped_columns['part_no']]).strip(),
                'Description': str(row.get(mapped_columns.get('description', ''), '')).strip(),
                'RM_IN_QTY': self.safe_float_convert(row[mapped_columns['rm_qty']]),
                'Vendor_Code': str(row.get(mapped_columns.get('vendor_code', ''), '')).strip(),
                'Vendor_Name': str(row.get(mapped_columns.get('vendor_name', ''), 'Unknown')).strip(),
                'City': str(row.get(mapped_columns.get('city', ''), '')).strip(),
                'State': str(row.get(mapped_columns.get('state', ''), '')).strip()
            }
            standardized_data.append(item)
        
        return standardized_data
    
    def standardize_current_inventory(self, df):
        """Standardize current inventory data"""
        if df is None or df.empty:
            return []
        
        column_mappings = {
            'part_no': ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code'],
            'description': ['description', 'item_description', 'part_description', 'desc'],
            'current_qty': ['current_qty', 'qty', 'quantity', 'stock_qty', 'available_qty'],
            'stock_value': ['stock_value', 'value', 'total_value', 'inventory_value','stock value','Stock Value']
        }
        
        df_columns_lower = {}
        for col in df.columns:
            if col is not None:  # Add safety check
                df_columns_lower[col.lower().strip()] = col
        mapped_columns = {}
        for key, variations in column_mappings.items():
            for variation in variations:
                if variation.lower() in df_columns_lower:
                    mapped_columns[key] = df_columns_lower[variation.lower()]
                    break
        # Debug: Print found columns
        print("Found column mappings:")
        for key, col in mapped_columns.items():
            print(f"  {key} -> {col}")
            
        if 'part_no' not in mapped_columns or 'current_qty' not in mapped_columns:
            st.error("❌ Required columns not found. Please ensure your file has Part Number and Current Quantity columns.")
            return []
        standardized_data = []
        # Process each row with better error handling
        for i, row in df.iterrows():
            try:
                part_no = str(row[mapped_columns['part_no']]).strip()
                if part_no == 'nan' or part_no == '':
                    continue
                description = str(row.get(mapped_columns.get('description', ''), '')).strip()
                current_qty = self.safe_float_convert(row[mapped_columns['current_qty']])
            
                # Improved stock value extraction
                stock_value = 0.0
                if 'stock_value' in mapped_columns:
                    stock_value_col = mapped_columns['stock_value']
                    if stock_value_col in row.index:
                        raw_stock_value = row[stock_value_col]
                        
                        # Debug print for first few rows with detailed conversion
                        if i < 10:  # Show more rows for debugging
                            st.write(f"🔍 Row {i+1} DEBUG:")
                            st.write(f"   Part: {part_no}")
                            st.write(f"   Column: {stock_value_col}")
                            st.write(f"   Raw Value: '{raw_stock_value}' (type: {type(raw_stock_value)})")
                            
                            # Use debug mode for conversion
                            stock_value = self.safe_float_convert(raw_stock_value, debug=True)
                            st.write(f"   Final Stock Value: {stock_value}")
                            st.write("   ---")
                        else:
                            stock_value = self.safe_float_convert(raw_stock_value, debug=False)
                else:
                    if i < 5:
                        st.write(f"⚠️ No stock_value column found for row {i+1}")
                        st.write(f"   Available mapped columns: {list(mapped_columns.keys())}")
                
                item = {
                    'Part_No': part_no,
                    'Description': description,
                    'Current_QTY': current_qty,
                    'Stock_Value': stock_value
                }
                standardized_data.append(item)
                # Debug print for first few items
                if i < 5:
                    print(f"Processed item {i+1}: {item}")
            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                st.warning(f"⚠️ Skipping row {i+1} due to error: {e}")
                continue
        # Final debug inf
        print(f"Total items processed: {len(standardized_data)}")
        if standardized_data:
             total_stock_value = sum(item['Stock_Value'] for item in standardized_data)
             print(f"Total stock value: {total_stock_value}")
             non_zero_values = [item for item in standardized_data if item['Stock_Value'] > 0]
             print(f"Items with non-zero stock value: {len(non_zero_values)}")
        return standardized_data
    
    def validate_inventory_against_pfep(self, inventory_data):
        """Validate inventory data against PFEP master data"""
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if not pfep_data:
            return {'is_valid': False, 'issues': ['No PFEP data available'], 'warnings': []}
        
        pfep_df = pd.DataFrame(pfep_data)
        inventory_df = pd.DataFrame(inventory_data)
        
        pfep_parts = set(pfep_df['Part_No'])
        inventory_parts = set(inventory_df['Part_No'])
        
        issues = []
        warnings = []
        
        # Check for missing parts in inventory
        missing_parts = pfep_parts - inventory_parts
        
        # Check for extra parts in inventory (not in PFEP)
        extra_parts = inventory_parts - pfep_parts
        
        # Check for data quality issues
        zero_qty_parts = inventory_df[inventory_df['Current_QTY'] == 0]['Part_No'].tolist()
        if zero_qty_parts:
            warnings.append(f"Parts with zero quantity: {len(zero_qty_parts)} parts")
        
        is_valid = len(issues) == 0
        
        return {
            'is_valid': is_valid,
            'issues': issues,
            'warnings': warnings,
            'pfep_parts_count': len(pfep_parts),
            'inventory_parts_count': len(inventory_parts),
            'matching_parts_count': len(pfep_parts & inventory_parts),
            'missing_parts_count': len(missing_parts),
            'extra_parts_count': len(extra_parts)
        }
    
    def admin_data_management(self):
        """Admin-only PFEP data management interface"""
        st.header("🔧 Admin Dashboard - PFEP Data Management")
        
        # Check if PFEP data is locked
        pfep_locked = st.session_state.get('persistent_pfep_locked', False)
        
        if pfep_locked:
            st.warning("🔒 PFEP data is currently locked. Users are working with this data.")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.info("To modify PFEP data, first unlock it. This will reset all user analysis.")
            with col2:
                if st.button("🔓 Unlock Data", type="secondary"):
                    st.session_state.persistent_pfep_locked = False
                    # Clear related data when PFEP is unlocked
                    st.session_state.persistent_inventory_data = None
                    st.session_state.persistent_inventory_locked = False
                    st.session_state.persistent_analysis_results = None
                    st.success("✅ PFEP data unlocked. Users need to re-upload inventory data.")
                    st.rerun()
            with col3:
                if st.button("👤 Go to User View", type="primary", help="Switch to user interface"):
                    st.session_state.user_role = "User"
                    st.rerun()
            
            # Display current PFEP data if available
            pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
            if pfep_data:
                self.display_pfep_data_preview(pfep_data)
            return
        # Tolerance Setting for Admin
        st.subheader("📐 Set Analysis Tolerance (Admin Only)")
        # Initialize admin_tolerance if not exists
        if "admin_tolerance" not in st.session_state:
            st.session_state.admin_tolerance = 30
    
        # Create selectbox with proper callback
        new_tolerance = st.selectbox(
            "Tolerance Zone (+/-)",
            options=[10, 20, 30, 40, 50],
            index=[10, 20, 30, 40, 50].index(st.session_state.admin_tolerance),
            format_func=lambda x: f"{x}%",
            key="tolerance_selector"
        )
        # Update tolerance if changed
        if new_tolerance != st.session_state.admin_tolerance:
            st.session_state.admin_tolerance = new_tolerance
            # Clear analysis results to force re-analysis with new tolerance
            st.session_state.persistent_analysis_results = None
            st.session_state.persistent_inventory_locked = False
            # If inventory data exists, automatically re-run analysis with new tolerance
            inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
            pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
            if inventory_data and pfep_data:
                with st.spinner(f"Re-analyzing inventory with new tolerance ±{new_tolerance}%..."):
                    analysis_results = self.analyzer.analyze_inventory(pfep_data, inventory_data, new_tolerance)
                    self.persistence.save_data_to_session_state('persistent_analysis_results', analysis_results)
                    st.session_state.persistent_inventory_locked = True
            st.success(f"✅ Tolerance updated to ±{new_tolerance}% and analysis refreshed!")
            st.rerun()
        # Display current tolerance
        st.info(f"Current tolerance: ±{st.session_state.admin_tolerance}%")
 
        data_source = st.radio(
            "Choose data source:",
            ["Upload Excel/CSV File", "Use Sample Data"],
            key="pfep_data_source",
            help="Select how you want to load PFEP master data"
        )
        
        if data_source == "Upload Excel/CSV File":
            self.handle_pfep_file_upload()
        else:
            self.handle_pfep_sample_data()
        
        # Display current PFEP data if available
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data:
            self.display_pfep_data_preview(pfep_data)
    
    def handle_pfep_file_upload(self):
        """Handle PFEP file upload with validation"""
        uploaded_file = st.file_uploader(
            "Upload PFEP Master Data",
            type=['xlsx', 'xls', 'csv'],
            help="Upload Excel or CSV file containing PFEP master data",
            key="pfep_file_uploader"
        )
        
        if uploaded_file:
            try:
                # Read file based on type
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.info(f"📄 File loaded: {uploaded_file.name} ({df.shape[0]} rows, {df.shape[1]} columns)")
                
                # Preview raw data
                with st.expander("👀 Preview Raw Data"):
                    st.dataframe(df.head(), use_container_width=True)
                
                # Process and standardize data
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("🔄 Process & Load PFEP Data", type="primary", key="process_pfep_file"):
                        with st.spinner("Processing PFEP data..."):
                            standardized_data = self.standardize_pfep_data(df)
                            
                            if standardized_data:
                                self.persistence.save_data_to_session_state('persistent_pfep_data', standardized_data)
                                st.success(f"✅ Successfully processed {len(standardized_data)} PFEP records!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to process PFEP data. Please check file format.")
                                
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        # Show lock button if data is loaded
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data and not st.session_state.get('persistent_pfep_locked', False):
            with col2:
                if st.button("🔒 Lock PFEP Data", type="secondary", key="lock_pfep_data"):
                    st.session_state.persistent_pfep_locked = True
                    st.success("✅ PFEP data locked! Users can now upload inventory data.")
                    st.rerun()
    
    def handle_pfep_sample_data(self):
        """Handle loading sample PFEP data"""
        st.info("📋 Using sample PFEP master data with 20 parts from various vendors")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("📥 Load Sample PFEP Data", type="primary", key="load_sample_pfep"):
                sample_data = self.load_sample_pfep_data()
                self.persistence.save_data_to_session_state('persistent_pfep_data', sample_data)
                st.success(f"✅ Loaded {len(sample_data)} sample PFEP records!")
                st.rerun()
        
        # Show lock button if data is loaded
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data and not st.session_state.get('persistent_pfep_locked', False):
            with col2:
                if st.button("🔒 Lock PFEP Data", type="secondary", key="lock_sample_pfep"):
                    st.session_state.persistent_pfep_locked = True
                    st.success("✅ PFEP data locked! Users can now upload inventory data.")
                    st.rerun()
    
    def display_pfep_data_preview(self, pfep_data):
        """Display PFEP data preview with enhanced statistics"""
        st.subheader("📊 PFEP Master Data Overview")
        
        df = pd.DataFrame(pfep_data)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Parts", len(df))
        with col2:
            st.metric("Unique Vendors", df['Vendor_Name'].nunique())
        with col3:
            st.metric("Total RM Quantity", f"{df['RM_IN_QTY'].sum():.0f}")
        with col4:
            st.metric("Avg RM per Part", f"{df['RM_IN_QTY'].mean():.1f}")
        
        # Vendor distribution
        vendor_dist = df.groupby('Vendor_Name').agg({
            'Part_No': 'count',
            'RM_IN_QTY': 'sum'
        }).reset_index()
        vendor_dist.columns = ['Vendor', 'Parts Count', 'Total RM Qty']
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏭 Vendor Distribution")
            fig = px.pie(vendor_dist, values='Parts Count', names='Vendor', 
                        title="Parts Distribution by Vendor")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📦 RM Quantity by Vendor")
            fig = px.bar(vendor_dist, x='Vendor', y='Total RM Qty',
                        title="Total RM Quantity by Vendor")
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Data preview table
        with st.expander("🔍 View PFEP Data Details"):
            st.dataframe(
                df.style.format({'RM_IN_QTY': '{:.2f}'}),
                use_container_width=True,
                height=300
            )
    
    def user_inventory_upload(self):
        """User interface for inventory data upload and analysis"""
        st.header("📦 Inventory Analysis Dashboard")
        
        # Check if PFEP data is available and locked
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        pfep_locked = st.session_state.get('persistent_pfep_locked', False)
        
        if not pfep_data or not pfep_locked:
            st.warning("⚠️ PFEP master data is not available or not locked by admin.")
            st.info("Please contact admin to load and lock PFEP master data first.")
            return
        
        # Display PFEP status
        st.success(f"✅ PFEP master data loaded: {len(pfep_data)} parts available")
        
        # Check if inventory is already loaded and locked
        inventory_locked = st.session_state.get('persistent_inventory_locked', False)
        
        if inventory_locked:
            st.info("🔒 Inventory data is locked. Analysis results are available below.")
            analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
            if analysis_data:
                self.display_analysis_results()
            return
        
        # Inventory upload section
        st.subheader("📊 Upload Current Inventory Data")
        
        inventory_source = st.radio(
            "Choose inventory data source:",
            ["Upload Excel/CSV File", "Use Sample Data"],
            key="inventory_data_source"
        )
        
        if inventory_source == "Upload Excel/CSV File":
            uploaded_file = st.file_uploader(
                "Upload Current Inventory Data",
                type=['xlsx', 'xls', 'csv'],
                help="Upload Excel or CSV file containing current inventory data",
                key="inventory_file_uploader"
            )
            
            if uploaded_file:
                try:
                    # Read file
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    df.columns = df.columns.str.strip().str.replace(" ", "_")
                    # ✅ Ensure 'Stock_Value' is numeric
                    if 'Stock_Value' in df.columns:
                        df['Stock_Value'] = pd.to_numeric(df['Stock_Value'], errors='coerce').fillna(0)
                    else:
                        st.warning("⚠️ 'Stock_Value' column not found in uploaded file.")
                    
                    st.info(f"📄 File loaded: {uploaded_file.name} ({df.shape[0]} rows, {df.shape[1]} columns)")
                    
                    # Preview raw data
                    with st.expander("👀 Preview Raw Data"):
                        st.dataframe(df.head(), use_container_width=True)
                    
                    # Process inventory data
                    if st.button("🔄 Process & Analyze Inventory", type="primary", key="process_inventory_file"):
                        with st.spinner("Processing inventory data..."):
                            standardized_data = self.standardize_current_inventory(df)
                            
                            if standardized_data:
                                # Validate against PFEP
                                validation = self.validate_inventory_against_pfep(standardized_data)
                                self.display_validation_results(validation)
                                
                                if validation['is_valid'] or st.button("⚠️ Continue Despite Issues", key="force_continue"):
                                    # Save inventory data and perform analysis
                                    self.persistence.save_data_to_session_state('persistent_inventory_data', standardized_data)
                                    self.perform_inventory_analysis()
                                    st.session_state.persistent_inventory_locked = True
                                    st.rerun()
                            else:
                                st.error("❌ Failed to process inventory data.")
                                
                except Exception as e:
                    st.error(f"❌ Error reading file: {str(e)}")
        
        else:  # Sample data
            st.info("📋 Using sample current inventory data")
            if st.button("📥 Load Sample Inventory & Analyze", type="primary", key="load_sample_inventory"):
                sample_data = self.load_sample_current_inventory()
                self.persistence.save_data_to_session_state('persistent_inventory_data', sample_data)
                self.perform_inventory_analysis()
                st.session_state.persistent_inventory_locked = True
                st.success("✅ Sample inventory loaded and analyzed!")
                st.rerun()
    
    def display_validation_results(self, validation):
        """Display inventory validation results"""
        st.subheader("🔍 Data Validation Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PFEP Parts", validation['pfep_parts_count'])
        with col2:
            st.metric("Inventory Parts", validation['inventory_parts_count'])
        with col3:
            st.metric("Matching Parts", validation['matching_parts_count'])
        with col4:
            match_percentage = (validation['matching_parts_count'] / validation['pfep_parts_count']) * 100
            st.metric("Match %", f"{match_percentage:.1f}%")
        
        # Issues and warnings
        if validation['issues']:
            st.error("❌ **Issues Found:**")
            for issue in validation['issues']:
                st.error(f"• {issue}")
        
        if validation['warnings']:
            st.warning("⚠️ **Warnings:**")
            for warning in validation['warnings']:
                st.warning(f"• {warning}")
        
        if validation['is_valid']:
            st.success("✅ **Validation Passed:** Inventory data is compatible with PFEP master data.")
    
    def perform_inventory_analysis(self):
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        if not pfep_data or not inventory_data:
            st.error("❌ Missing data for analysis")
            return
        # Get tolerance from admin setting (FIXED)
        tolerance = st.session_state.get('admin_tolerance', 30)
        # Perform analysis
        with st.spinner(f"Analyzing inventory with ±{tolerance}% tolerance..."):
            analysis_results = self.analyzer.analyze_inventory(pfep_data, inventory_data, tolerance)
            self.persistence.save_data_to_session_state('persistent_analysis_results', analysis_results)
            # Track which tolerance was used for this analysis
            st.session_state.last_analysis_tolerance = tolerance
        st.success(f"✅ Analysis completed for {len(analysis_results)} parts with ±{tolerance}% tolerance!")
    
    def display_analysis_results(self):
        """Display comprehensive inventory analysis results"""
        analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
        
        if not analysis_data:
            st.error("❌ No analysis results available")
            return
        # Check if tolerance has changed since last analysis
        current_tolerance = st.session_state.get('admin_tolerance', 30)
        last_analysis_tolerance = st.session_state.get('last_analysis_tolerance', None)
    
        # If tolerance changed, automatically re-run analysis
        if last_analysis_tolerance != current_tolerance:
            pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
            inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
            if pfep_data and inventory_data:
                st.info(f"🔄 Tolerance changed from ±{last_analysis_tolerance}% to ±{current_tolerance}%. Re-analyzing...")
                with st.spinner(f"Re-analyzing with new tolerance ±{current_tolerance}%..."):
                    analysis_results = self.analyzer.analyze_inventory(pfep_data, inventory_data, current_tolerance)
                    self.persistence.save_data_to_session_state('persistent_analysis_results', analysis_results)
                    st.session_state.last_analysis_tolerance = current_tolerance
                st.success("✅ Analysis updated with new tolerance!")
                st.rerun()
                
        analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
        df = pd.DataFrame(analysis_data)

        st.info(f"🔒 Analysis performed with tolerance: ±{current_tolerance}% (set by Admin)")

        # Summary Dashboard
        st.header("📈 Summary Dashboard")
        
        processed_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
        if processed_data:
            analyzer = InventoryAnalyzer()
            from collections import Counter
            # Ensure processed_data is a list of dicts from the analysis DataFrame
            df_processed = pd.DataFrame(processed_data)
            # Derive summary_data
            status_counter = Counter(df_processed['Status'])
            summary_data = {status: {"count": count} for status, count in status_counter.items()}
        
            # Calculate total value for each status
            for status in summary_data:
                status_data = df_processed[df_processed['Status'] == status]
                summary_data[status]['value'] = status_data['Stock_Value'].sum() if 'Stock_Value' in status_data.columns else 0
            # Calculate total value
            total_value = sum(data['value'] for data in summary_data.values())
            col1, col2, col3, col4 = st.columns(4)
        
            with col1:
                st.markdown('<div class="metric-card status-normal">', unsafe_allow_html=True)
                st.metric(
                    label="🟢 Within Norms",
                    value=f"{summary_data.get('Within Norms', {'count': 0})['count']} parts",
                    delta=f"₹{summary_data.get('Within Norms', {'value': 0})['value']:,}"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
               st.markdown('<div class="metric-card status-excess">', unsafe_allow_html=True)
               st.metric(
                   label="🔵 Excess Inventory",
                   value=f"{summary_data.get('Excess Inventory', {'count': 0})['count']} parts",
                   delta=f"₹{summary_data.get('Excess Inventory', {'value': 0})['value']:,}"
               )
               st.markdown('</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="metric-card status-short">', unsafe_allow_html=True)
                st.metric(
                    label="🔴 Short Inventory",
                    value=f"{summary_data.get('Short Inventory', {'count': 0})['count']} parts",
                    delta=f"₹{summary_data.get('Short Inventory', {'value': 0})['value']:,}"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            with col4:
                st.markdown('<div class="metric-card status-total">', unsafe_allow_html=True)
                st.metric(
                    label="📊 Total Value",
                    value=f"{len(processed_data)} parts",
                    delta=f"₹{total_value:,}"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            # Vendor Summary
            if processed_data:
                analyzer = InventoryAnalyzer()  # Make sure this is initialize
                from collections import Counter
                # Ensure processed_data is a list of dicts from the analysis DataFram
                df_processed = pd.DataFrame(processed_data)
                # Derive summary_data
                status_counter = Counter(df_processed['Status'])
                summary_data = {status: {"count": count} for status, count in status_counter.items()}

                # Calculate total value for each status
                for status in summary_data:
                    status_data = df_processed[df_processed['Status'] == status]
                    summary_data[status]['value'] = status_data['Stock_Value'].sum() if 'Stock_Value' in status_data.columns else 0

                # Vendor Summary - FIX THIS PART:
                if hasattr(analyzer, 'get_vendor_summary'):
                    vendor_summary = analyzer.get_vendor_summary(processed_data)
                else:
                    st.error("❌ 'get_vendor_summary' method not found in InventoryAnalyzer.")
                    logger.error("Missing method 'get_vendor_summary' in InventoryAnalyzer.")
                    return
                st.header("🏢 Vendor Summary")
                vendor_df = pd.DataFrame([
                    {
                        'Vendor': vendor,
                        'Total Parts': data['total_parts'],
                        'Total QTY': round(data['total_qty'], 2),
                        'Total RM': round(data['total_rm'], 2),
                        'Short Inventory': data['short_parts'],
                        'Excess Inventory': data['excess_parts'],
                        'Within Norms': data['normal_parts'],
                        'Total Value': f"₹{data['total_value']:,}"
                    }
                    for vendor, data in vendor_summary.items()
                ])
                st.dataframe(vendor_df, use_container_width=True, hide_index=True)
        # Analysis controls
        # TABS: Graphs | Tables | Vendor | Export
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Graphical Analysis", "📋 Data Table Analysis", "🏭 Vendor Analysis", "📤 Export Data"])
        with tab1:
            st.header("📊 Graphical Analysis")
            
            processed_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
            if not processed_data:
                st.error("No analysis data available. Please upload inventory and perform analysis first.")
            else:
                analyzer = InventoryAnalyzer()
                from collections import Counter
            
            # Ensure processed_data is a list of dicts from the analysis DataFrame
            df_processed = pd.DataFrame(processed_data)

            # Derive summary_data
            status_counter = Counter(df_processed['Status'])
            summary_data = {status: {"count": count} for status, count in status_counter.items()}

            # Derive vendor_summary
            vendor_summary = {}
            for item in processed_data:
                vendor = item.get('Vendor', 'Unknown')
                vendor_summary.setdefault(vendor, {'total_qty': 0})
                vendor_summary[vendor]['total_qty'] += item.get('QTY', 0)
            # Use default tolerance
            tolerance = st.session_state.user_preferences.get('default_tolerance', 30)

            # UI for selecting which charts to show
            st.subheader("Select Graphs to Display")

            col1, col2, col3 = st.columns(3)

            with col1:
                show_pie = st.checkbox("Status Distribution (Pie)", value=True)
                show_excess = st.checkbox("Top Excess Parts", value=True)
                show_comparison = st.checkbox("QTY vs RM Comparison", value=True)
                show_variance_hist = st.checkbox("Variance Distribution", value=False)

            with col2:
                show_short = st.checkbox("Top Short Parts", value=True)
                show_scatter = st.checkbox("QTY vs RM Scatter", value=False)

            with col3:
                show_normal = st.checkbox("Top Normal Parts", value=False)
                show_variance_top = st.checkbox("Top Variance Parts", value=True)
                show_vendor_qty = st.checkbox("Top 10 Vendors by QTY", value=True)
            # 1. Pie Chart - Status Distribution
            if show_pie:
                st.subheader("📊 Status Distribution")
                st.markdown('<div class="graph-description">This pie chart shows the overall distribution of inventory items across different status categories...</div>', unsafe_allow_html=True)

                status_counts = {status: data['count'] for status, data in summary_data.items() if data['count'] > 0}
                if status_counts:
                    fig_pie = px.pie(
                        values=list(status_counts.values()),
                        names=list(status_counts.keys()),
                        color=list(status_counts.keys()),
                        color_discrete_map=analyzer.status_colors,
                        title="Inventory Status Distribution"
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True, key="status_dist_pie")
            # 2. Bar Chart - QTY vs RM IN QTY
            if show_comparison:
                st.subheader("📊 QTY vs RM Comparison")
                st.markdown('<div class="graph-description">This bar chart compares current quantity (QTY) against required minimum quantity (RM IN QTY)...</div>', unsafe_allow_html=True)
                top_items = sorted(processed_data, key=lambda x: x['Stock_Value'], reverse=True)[:10]
                materials = [item['Material'] for item in top_items]
                qty_values = [item['QTY'] for item in top_items]
                rm_values = [item['RM IN QTY'] for item in top_items]
                
                fig_comparison = go.Figure()
                fig_comparison.add_trace(go.Bar(name='Current QTY', x=materials, y=qty_values, marker_color='#1f77b4'))
                fig_comparison.add_trace(go.Bar(name='RM IN QTY', x=materials, y=rm_values, marker_color='#ff7f0e'))
                
                fig_comparison.update_layout(
                    title="QTY vs RM IN QTY Comparison (Top 10 by Stock Value)",
                    xaxis_title="Material Code",
                    yaxis_title="Quantity",
                    barmode='group'
                )
                st.plotly_chart(fig_comparison, use_container_width=True, key="qty_vs_rm_comparison")
            # 3. Bar - Top Vendors by QTY
            if show_vendor_qty:
                st.subheader("🏢 Top 10 Vendors by Total QTY")
                st.markdown('<div class="graph-description">This chart displays the top 10 vendors ranked by their total quantity contribution to your inventory...</div>', unsafe_allow_html=True)
                sorted_vendors = sorted(vendor_summary.items(), key=lambda x: x[1]['total_qty'], reverse=True)[:10]
                vendor_names = [vendor for vendor, _ in sorted_vendors]
                total_qtys = [data['total_qty'] for _, data in sorted_vendors]
                
                fig_vendor = go.Figure()
                fig_vendor.add_trace(go.Bar(name='Total QTY', x=vendor_names, y=total_qtys, marker_color='#1f77b4'))
                
                fig_vendor.update_layout(
                    title="Top 10 Vendors by Total QTY",
                    xaxis_title="Vendor",
                    yaxis_title="Quantity",
                    showlegend=False
                )
                st.plotly_chart(fig_vendor, use_container_width=True, key="vendor_qty_bar")
            # 4. Top Parts Charts (Assumes function exists
            if show_excess:
                st.subheader("🔵 Top 10 Excess Inventory Parts")
                st.markdown('<div class="graph-description">These items represent tied-up capital and storage costs...</div>', unsafe_allow_html=True)
                self.create_top_parts_chart(processed_data, 'Excess Inventory', analyzer.status_colors['Excess Inventory'], key="top_excess")
            
            if show_short:
                st.subheader("🔴 Top 10 Short Inventory Parts")
                st.markdown('<div class="graph-description">These items pose the greatest risk to operations and require immediate attention...</div>', unsafe_allow_html=True)
                self.create_top_parts_chart(processed_data, 'Short Inventory', analyzer.status_colors['Short Inventory'], key="top_short")

            if show_normal:
                st.subheader("🟢 Top 10 Within Norms Parts")
                st.markdown('<div class="graph-description">These items represent well-managed inventory levels and serve as benchmarks...</div>', unsafe_allow_html=True)
                self.create_top_parts_chart(processed_data, 'Within Norms', analyzer.status_colors['Within Norms'], key="top_normal")
                
            # 5. Variance Top Chart
            if show_variance_top:
                st.subheader("📊 Top 10 Materials by Variance")
                st.markdown('<div class="graph-description">Shows materials with the highest absolute variance...</div>', unsafe_allow_html=True)
                sorted_variance = sorted(processed_data, key=lambda x: abs(x['Variance_%']), reverse=True)[:10]
                materials = [item['Material'] for item in sorted_variance]
                variances = [item['Variance_%'] for item in sorted_variance]
                colors = [analyzer.status_colors[item['Status']] for item in sorted_variance]
                
                fig_variance = go.Figure(data=[
                    go.Bar(x=materials, y=variances, marker_color=colors)
                ])
                
                fig_variance.update_layout(
                    title="Top 10 Materials by Variance %",
                    xaxis_title="Material Code",
                    yaxis_title="Variance %"
                )
                fig_variance.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
                st.plotly_chart(fig_variance, use_container_width=True, key="variance_top_bar")
            # 6. Scatter - QTY vs RM
            if show_scatter:
                st.subheader("📊 QTY vs RM Scatter Plot")
                st.markdown('<div class="graph-description">This scatter plot shows the relationship between current quantity and required minimum quantity for all items...</div>', unsafe_allow_html=True)
                fig_scatter = px.scatter(
                    df_processed,
                    x='RM IN QTY',
                    y='QTY',
                    color='Status',
                    color_discrete_map=analyzer.status_colors,
                    title="QTY vs RM IN QTY Scatter Plot",
                    hover_data=['Material', 'Variance_%', 'Vendor']
                )
                max_val = max(df_processed['QTY'].max(), df_processed['RM IN QTY'].max())
                fig_scatter.add_trace(go.Scatter(
                    x=[0, max_val],
                    y=[0, max_val],
                    mode='lines',
                    name='Perfect Match',
                    line=dict(dash='dash', color='black')
                ))
                st.plotly_chart(fig_scatter, use_container_width=True, key="scatter_qty_rm")
            # 7. Histogram - Variance Distribution
            if show_variance_hist:
                st.subheader("📊 Variance Distribution")
                st.markdown('<div class="graph-description">This histogram shows the distribution of variance percentages across all inventory items...</div>', unsafe_allow_html=True)
                variances = [item['Variance_%'] for item in processed_data]
                fig_hist = px.histogram(
                    x=variances,
                    nbins=30,
                    title="Variance Distribution",
                    labels={'x': 'Variance %', 'y': 'Count'},
                    color_discrete_sequence=['#1f77b4']
                )
                fig_hist.add_vline(x=tolerance, line_dash="dash", line_color="red", annotation_text=f"+{tolerance}%")
                fig_hist.add_vline(x=-tolerance, line_dash="dash", line_color="red", annotation_text=f"-{tolerance}%")
                fig_hist.add_vline(x=0, line_dash="solid", line_color="green", annotation_text="Target")
                st.plotly_chart(fig_hist, use_container_width=True, key="variance_hist")
                
        with tab2:
            st.header("📋 Detailed Inventory Data")
            # Ensure 'analyzer' and 'processed_data' exist before this block
            analyzer = InventoryAnalyzer()
            vendors = sorted({item['Vendor'] for item in processed_data if item.get('Vendor')})

            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=['All'] + list(analyzer.status_colors.keys()),
                    key="tab2_status_filter"
                )
            with col2:
                vendor_filter = st.selectbox(
                    "Filter by Vendor",
                    options=['All'] + vendors,
                    key="tab2_vendor_filter"
                )
            # Apply filters
            filtered_data = processed_data.copy()
            if status_filter != 'All':
                filtered_data = [item for item in filtered_data if item['Status'] == status_filter]
            if vendor_filter != 'All':
                filtered_data = [item for item in filtered_data if item['Vendor'] == vendor_filter]
            if filtered_data:
                # Convert to DataFrame for display
                df_display = pd.DataFrame(filtered_data)
                # Format the display
                df_display['Variance_%'] = df_display['Variance_%'].round(2)
                df_display['Variance_Value'] = df_display['Variance_Value'].round(2)
                df_display['Stock_Value'] = df_display['Stock_Value'].apply(lambda x: f"₹{x:,}")
                # Reorder columns for better display
                column_order = ['Material', 'Description', 'Vendor', 'QTY', 'RM IN QTY',
                        'Variance_%', 'Variance_Value', 'Status', 'Stock_Value']
                df_display = df_display[column_order]
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.info(f"Showing {len(filtered_data)} items")
            else:
                st.warning("No data matches the selected filters.")

        with tab3:
            st.subheader("🏭 Vendor Analysis")
            # Load and process analysis data
            analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
            if not analysis_data:
                st.warning("No analysis data available.")
            else:
                analyzer = InventoryAnalyzer()
                df = pd.DataFrame(analysis_data)
                # ✅ Filter options
                vendors = sorted(df['Vendor'].dropna().unique().tolist())
                statuses = sorted(df['Status'].dropna().unique().tolist())

                st.markdown("### 🔍 Filter Options")
                col1, col2 = st.columns(2)

                with col1:
                    status_filter = st.selectbox(
                        "Filter by Status",
                        options=['All'] + statuses,
                        index=0,
                        key="vendor_tab3_status"
                    )
                with col2:
                    vendor_filter = st.selectbox(
                        "Filter by Vendor",
                        options=['All'] + vendors,
                        index=0,
                        key="vendor_tab3_vendor"
                    )
                # ✅ Apply filters
                filtered_df = df.copy()
                if status_filter != 'All':
                    filtered_df = filtered_df[filtered_df['Status'] == status_filter]
                if vendor_filter != 'All':
                    filtered_df = filtered_df[filtered_df['Vendor'] == vendor_filter]
                # ✅ Show filtered part-level table
                if not filtered_df.empty:
                    df_display = filtered_df.copy()
                    df_display['Variance_%'] = df_display['Variance_%'].round(2)
                    df_display['Variance_Value'] = df_display['Variance_Value'].round(2)
                    df_display['Stock_Value'] = df_display['Stock_Value'].apply(lambda x: f"₹{x:,}")
                    column_order = ['Material', 'Description', 'Vendor', 'QTY', 'RM IN QTY',
                            'Variance_%', 'Variance_Value', 'Status', 'Stock_Value']
                    df_display = df_display[column_order]
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    st.info(f"Showing {len(df_display)} parts")
                    # ✅ Chart: Inventory Value by Vendor
                    st.markdown("### 📊 Inventory Value by Vendor")
                    chart_df = filtered_df.copy()
                    chart_df['Stock_Value'] = pd.to_numeric(chart_df['Stock_Value'], errors='coerce')
                    vendor_totals = chart_df.groupby('Vendor')['Stock_Value'].sum().reset_index()
                    if not vendor_totals.empty and vendor_totals['Stock_Value'].sum() > 0:
                        fig = px.bar(
                            vendor_totals,
                            x='Vendor',
                            y='Stock_Value',
                            title="Total Stock Value per Vendor",
                            labels={'Stock_Value': 'Stock Value (₹)'},
                            template=st.session_state.user_preferences.get('chart_theme', 'plotly')
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No data available for chart.")
                else:
                    st.warning("No data matches the selected filters.")
            with tab4:
                st.header("📤 Export & Email Report")
                # ✅ INSERT SUMMARY REPORT PREVIEW BLOCK HERE
                st.markdown("### 📊 Summary Report Preview")
                
                # Export options
                col1, col2 = st.columns(2)
                with col1:
                    export_format = st.radio(
                        "Select Export Format",
                        options=['CSV', 'Excel'],
                        key="export_format"
                    )
                with col2:
                    export_data_type = st.radio(
                        "Select Data to Export",
                        options=['All Data', 'Short Inventory Only', 'Excess Inventory Only', 'Summary Only'],
                        key="export_data_type"
                    )
                summary_table = pd.DataFrame()
                if export_data_type == 'Summary Only':
                    df_export_preview = pd.DataFrame(processed_data)
                    if not df_export_preview.empty and 'Status' in df_export_preview.columns:
                        summary_table = df_export_preview.groupby('Status')['Stock_Value'].agg(['count', 'sum']).reset_index()
                        summary_table.columns = ['Status', 'Count', 'Total Value (₹)']

                # Prepare export data
                if export_data_type == 'All Data':
                    export_data = processed_data
                elif export_data_type == 'Short Inventory Only':
                    export_data = [item for item in processed_data if item['Status'] == 'Short Inventory']
                elif export_data_type == 'Excess Inventory Only':
                    export_data = [item for item in processed_data if item['Status'] == 'Excess Inventory']
                else:  # Summary Only
                    export_data = summary_table.to_dict(orient='records') if not summary_table.empty else []
                if export_data:
                    df_export = pd.DataFrame(export_data)
                    # Email input field
                    st.markdown("### 📧 Send Report via Email")
                    recipient_email = st.text_input("Enter recipient email address")
                    if export_format == 'CSV':
                        csv = df_export.to_csv(index=False)
                        filename = f"inventory_analysis_{export_data_type.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=filename,
                            mime="text/csv"
                        )
                        # Simulate sending
                        if st.button("📧 Send CSV Report"):
                            if recipient_email:
                                st.success(f"📤 Simulated sending of CSV report to {recipient_email}")
                            else:
                                st.warning("Please enter a valid email address.")
                    else:  # Excel
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_export.to_excel(writer, sheet_name='Inventory Analysis', index=False)
                        filename = f"inventory_analysis_{export_data_type.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        st.download_button(
                            label="📥 Download Excel",
                            data=output.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        # Simulate sending
                        if st.button("📧 Send Excel Report"):
                            if recipient_email:
                                st.success(f"📤 Simulated sending of Excel report to {recipient_email}")
                            else:
                                st.warning("Please enter a valid email address.")
                else:
                   st.warning("No data available for export with current selection.")
    
    def run(self):
        """Main application runner"""
        # Page header
        st.title("📊 Inventory Analyzer")
        st.markdown("---")
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.info("👋 Please select your role and authenticate to access the system.")
            st.markdown("""
            ### System Features:
            - **Admin Dashboard**: Load and manage PFEP master data
            - **User Interface**: Upload inventory data and view analysis
            - **Real-time Analysis**: Compare current inventory with PFEP requirements
            - **Interactive Visualizations**: Charts and graphs for better insights
            - **Export Capabilities**: Download results in multiple formats
            """)
            return
        
        # Main application logic based on user role
        if st.session_state.user_role == "Admin":
            self.admin_data_management()
        else:  # User role
            self.user_inventory_upload()

# Application entry point
if __name__ == "__main__":
    try:
        app = InventoryManagementSystem()
        app.run()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        logger.error(f"Application crashed: {str(e)}", exc_info=True)
