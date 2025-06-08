import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import altair as alt
import time 

# --- Page Configuration ---
st.set_page_config(
    page_title="Company Email Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- UI/CSS Styling ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css");
    :root { /* Default: Dark Theme */
        --primary-accent-color: #00CFE8;
        --text-on-accent: #000000;
        --success-color: #23D5AB;
        --warning-color: #FFC107;
        --danger-color: #F93154;
        --font-family: 'Inter', sans-serif;
        --border-radius: 20px;
        --background-gradient: linear-gradient(-45deg, #1d2b3c, #2c3e50, #1e3c72, #2a5298);
        --glass-bg: rgba(44, 62, 80, 0.65);
        --glass-border: rgba(255, 255, 255, 0.1);
        --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        --text-color-primary: #FFFFFF;
        --text-color-secondary: #bdc3c7;
        --input-bg: rgba(0,0,0,0.2);
        --input-border: rgba(255, 255, 255, 0.2);
    }
    body[data-theme="light"] {
        --primary-accent-color: #007AFF;
        --text-on-accent: #FFFFFF;
        --background-gradient: linear-gradient(-45deg, #e0eafc, #cfdef3, #a7bfe8, #6190e8);
        --glass-bg: rgba(255, 255, 255, 0.6);
        --glass-border: rgba(50, 50, 93, 0.2);
        --glass-shadow: 0 8px 32px 0 rgba(50, 50, 93, 0.1);
        --text-color-primary: #2c3e50;
        --text-color-secondary: #34495e;
        --input-bg: rgba(255,255,255,0.5);
        --input-border: rgba(50, 50, 93, 0.3);
    }
    @keyframes gradient { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
    .stApp { background: var(--background-gradient); background-size: 400% 400%; animation: gradient 25s ease infinite; color: var(--text-color-primary); }
    body { font-family: var(--font-family); }
    h1, h2, h3 { font-weight: 700; color: var(--text-color-primary); }
    h1 { text-align: center; }
    h3 { display: flex; align-items: center; gap: 0.75rem; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
    .glass-card { background: var(--glass-bg) !important; backdrop-filter: blur(12px) saturate(150%) !important; -webkit-backdrop-filter: blur(12px) saturate(150%) !important; border-radius: var(--border-radius) !important; border: 1px solid var(--glass-border) !important; box-shadow: var(--glass-shadow) !important; padding: 30px !important; margin-bottom: 25px !important; animation: fadeIn 0.6s ease-out forwards; transition: transform 0.3s ease, box-shadow 0.3s ease; }
    .glass-card:hover { transform: translateY(-5px); box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.15) !important; }
    div[data-testid="stExpander"], div[data-testid="stDataFrame"], div[data-testid="stMetric"], div[data-testid="stForm"] { background: var(--glass-bg) !important; backdrop-filter: blur(12px) saturate(150%) !important; -webkit-backdrop-filter: blur(12px) saturate(150%) !important; border-radius: var(--border-radius) !important; border: 1px solid var(--glass-border) !important; box-shadow: var(--glass-shadow) !important; padding: 30px !important; margin-bottom: 25px !important; }
    .stTextInput > div > div > input, .stDateInput > div > div > input, .stSelectbox > div > div { background-color: var(--input-bg) !important; color: var(--text-color-primary) !important; border-radius: 10px !important; border: 1px solid var(--input-border) !important; }
    .stButton > button, .stDownloadButton > button { border: none; border-radius: 12px; font-weight: 600; padding: 12px 24px; transition: all 0.3s ease; background: var(--primary-accent-color); color: var(--text-on-accent); box-shadow: 0 4px 15px rgba(0, 207, 232, 0.3); }
    .stButton > button:hover { transform: translateY(-3px) scale(1.05); box-shadow: 0 7px 25px rgba(0, 207, 232, 0.4); }
    div[data-testid="stMetric"] label { color: var(--text-color-secondary) !important; font-weight: 500; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 2.5em; font-weight: 700; color: var(--text-color-primary) !important; }
    .stDataFrame .data-grid-header { background-color: transparent !important; color: var(--primary-accent-color); font-weight: 600; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

# --- Connection Manager with built-in Verifier ---
@st.cache_resource
def connect_to_gsheet():
    """Connects to Google Sheets and returns a worksheet object and a status dictionary."""
    status = {
        "secrets_found": False, "creds_parsed": False, "authorized": False, 
        "sheet_opened": False, "error_message": None
    }
    try:
        creds_dict = st.secrets["gcp_service_account"]
        status["secrets_found"] = True
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        status["creds_parsed"] = True
        
        gc = gspread.authorize(creds)
        status["authorized"] = True

        spreadsheet = gc.open_by_key("1snHjynQb3ecyXMgbP4d7WrhAtPoJpzNNC7moZTEW6FM")
        worksheet = spreadsheet.sheet1
        status["sheet_opened"] = True
        
        return worksheet, status
    except Exception as e:
        status["error_message"] = str(e)
        return None, status

# --- Backend Functions ---
ALL_COLUMNS = ["companyName", "emailAccount", "password", "accountHolder", "remarks", "subscriptionPlatform", "purchaseDate", "expiryDate", "mailType", "status"]
def load_data(worksheet):
    try:
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 2: return pd.DataFrame(columns=ALL_COLUMNS)
        header = all_values[0]; data = all_values[1:]
        df = pd.DataFrame(data, columns=header)
        for col in ALL_COLUMNS:
            if col not in df.columns: df[col] = ""
        df = df[ALL_COLUMNS].astype(str).fillna("")
        df.replace(['nan', 'None', '<NA>'], '', inplace=True)
        return df
    except Exception as e:
        st.error(f"Failed to read data from the sheet. Error: {e}")
        return pd.DataFrame(columns=ALL_COLUMNS)
def save_data(worksheet, df):
    with st.spinner(f"Saving {len(df)} rows..."):
        worksheet.clear(); time.sleep(1)
        values = [df.columns.values.tolist()] + df.astype(str).values.tolist()
        batch_size = 500
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            worksheet.update(batch, f'A{i+1}'); time.sleep(1.5)

# --- Other Constants and Functions ---
COMPANY_OPTIONS = ["", "Rewardoo Private Limited", "Eseries Sports Private Limited", "Heksa Skills Private Limited", "Softscience Tech Private Limited"]
PLATFORM_OPTIONS = ["", "Hostinger", "GoDaddy", "Google Console (Workspace)", "Zoho Mail", "Microsoft 365 (Exchange)"]
MAIL_TYPE_OPTIONS = ["", "Gmail Regular", "Gmail Paid (Workspace)", "Hostinger Webmail", "GoDaddy Webmail", "Zoho Standard", "Microsoft Exchange"]
STATUS_OPTIONS = ["Active", "Inactive", "On Hold", "Closed"]
COLUMN_CONFIG = { "companyName": st.column_config.SelectboxColumn("Company", options=COMPANY_OPTIONS[1:], required=True), "emailAccount": st.column_config.TextColumn("Email", required=True), "accountHolder": st.column_config.TextColumn("Account Holder", required=True), "subscriptionPlatform": st.column_config.SelectboxColumn("Platform", options=PLATFORM_OPTIONS[1:], required=True), "purchaseDate": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD", required=True), "expiryDate": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD", required=True), "mailType": st.column_config.SelectboxColumn("Mail Type", options=MAIL_TYPE_OPTIONS[1:], required=True), "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, default="Active", required=True), "remarks": st.column_config.TextColumn("Remarks"),}
def calculate_metrics(df):
    if df.empty: return 0, 0, 0
    total = len(df); active = len(df[df['status'].str.lower() == 'active'])
    today = datetime.now()
    exp_dates = pd.to_datetime(df['expiryDate'], errors='coerce')
    expiring = df[(exp_dates.notna()) & (exp_dates >= today) & (exp_dates <= today + timedelta(days=30))].shape[0]
    return total, active, expiring
def get_status_chart(df):
    if df.empty or df['status'].str.strip().eq('').all():
        return alt.Chart(pd.DataFrame({'status': ['No Data'], 'count': [1]})).mark_arc(color='#444').properties(title="No status data")
    status_counts = df[df['status'].str.strip() != '']['status'].value_counts().reset_index()
    chart = alt.Chart(status_counts).mark_arc(innerRadius=60, outerRadius=100).encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(field="status", type="nominal", scale=alt.Scale(domain=['Active', 'Inactive', 'On Hold', 'Closed'], range=['#23D5AB', '#F93154', '#FFC107', '#808B96']), legend=None),
        tooltip=['status', 'count']
    ).properties(width=300, height=300)
    return chart
def process_csv_upload(worksheet):
    if 'csv_uploader' in st.session_state and st.session_state.csv_uploader is not None:
        try:
            new_data_df = pd.read_csv(st.session_state.csv_uploader)
            if not set(ALL_COLUMNS).issubset(new_data_df.columns):
                st.error(f"Upload Failed: CSV is missing columns."); return
            new_data_df = new_data_df[ALL_COLUMNS].astype(str).fillna("")
            combined_df = pd.concat([st.session_state.email_data, new_data_df], ignore_index=True)
            combined_df.drop_duplicates(subset=['emailAccount'], keep='last', inplace=True)
            save_data(worksheet, combined_df)
            st.success(f"✅ Success! Merged {len(new_data_df)} rows."); 
            if 'email_data' in st.session_state: del st.session_state.email_data
        except Exception as e:
            st.error(f"An error occurred during import: {e}")

# --- App Pages ---
def show_login_page():
    st.title("🔐 Company Email Dashboard")
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.header("Welcome Back")
            username = st.text_input("Username", placeholder="Admin")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if username == st.secrets["app_credentials"]["username"] and password == st.secrets["app_credentials"]["password"]:
                    st.session_state.logged_in = True; st.rerun()
                else:
                    st.error("Incorrect username or password")
        st.markdown("</div>", unsafe_allow_html=True)

def show_main_app(worksheet, connection_status):
    with st.sidebar:
        st.success(f"Logged in as **{st.secrets['app_credentials']['username']}**")
        def theme_changed():
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.toggle("Light Mode", value=(st.session_state.theme == 'light'), on_change=theme_changed, key="theme_toggle")
        
        st.markdown("---")
        # --- Connection Status Verifier ---
        st.subheader("Connection Status")
        status_ok = connection_status["sheet_opened"]
        st.write(f"{'✅' if status_ok else '❌'} Google Sheets Connection")
        with st.expander("Show Details"):
            st.write(f"{'✅' if connection_status['secrets_found'] else '❌'} Secrets Loaded")
            st.write(f"{'✅' if connection_status['creds_parsed'] else '❌'} Credentials Parsed")
            st.write(f"{'✅' if connection_status['authorized'] else '❌'} Google Authorized")
            st.write(f"{'✅' if connection_status['sheet_opened'] else '❌'} Spreadsheet Opened")
            if connection_status['error_message']:
                st.error(connection_status['error_message'])
        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    
    if st.session_state.theme == "light":
        components.html("""<script>window.parent.document.body.setAttribute('data-theme', 'light');</script>""", height=0, width=0)
    else:
        components.html("""<script>window.parent.document.body.removeAttribute('data-theme');</script>""", height=0, width=0)

    st.title("Company Email Dashboard")

    if not worksheet:
        st.error("DATABASE OFFLINE: Could not connect to Google Sheets. Please check the 'Connection Status' in the sidebar.")
        st.stop()

    if 'email_data' not in st.session_state:
        st.session_state.email_data = load_data(worksheet)

    # The rest of the page layout
    st.markdown("<h3 class='glass-card'><i class='bi bi-bar-chart-line-fill'></i> At a Glance</h3>", unsafe_allow_html=True)
    total, active, expiring = calculate_metrics(st.session_state.email_data)
    cols = st.columns(3)
    with cols[0]: st.metric("Total Accounts", total)
    with cols[1]: st.metric("Active Accounts", active, delta=f"{round((active/total)*100) if total > 0 else 0}% Active")
    with cols[2]: st.metric("Expiring Soon", expiring, delta=f"{expiring} within 30 days", delta_color="inverse")
    
    with st.expander("Add a Single Entry", icon="➕"):
        with st.form("new_entry_form", clear_on_submit=True):
            cols = st.columns((1, 1, 1)); companyName = cols[0].selectbox("Company Name*", options=COMPANY_OPTIONS[1:]); emailAccount = cols[1].text_input("Email Account*"); password = cols[2].text_input("Password*", type="password")
            cols = st.columns((1, 1, 1)); accountHolder = cols[0].text_input("Account Holder*"); subscriptionPlatform = cols[1].selectbox("Subscription Platform*", options=PLATFORM_OPTIONS[1:]); mailType = cols[2].selectbox("Mail Type*", options=MAIL_TYPE_OPTIONS[1:])
            cols = st.columns((1, 1, 1)); purchaseDate = cols[0].date_input("Purchase Date*", value=None); expiryDate = cols[1].date_input("Expiry Date*", value=None); status = cols[2].selectbox("Status", options=STATUS_OPTIONS)
            remarks = st.text_area("Remarks")
            if st.form_submit_button("Add Entry", use_container_width=True, type="primary"):
                if not all([companyName, emailAccount, password, accountHolder, subscriptionPlatform, mailType, purchaseDate, expiryDate]): st.error("Please fill in all required (*) fields.")
                else:
                    new_row = pd.DataFrame([{"companyName": companyName, "emailAccount": emailAccount, "password": password, "accountHolder": accountHolder, "remarks": remarks, "subscriptionPlatform": subscriptionPlatform, "purchaseDate": str(purchaseDate), "expiryDate": str(expiryDate), "mailType": mailType, "status": status}])
                    st.session_state.email_data = pd.concat([st.session_state.email_data, new_row], ignore_index=True)
                    save_data(worksheet, st.session_state.email_data)
                    st.success("✅ Entry added successfully!"); st.rerun()
    
    with st.expander("Bulk Import from CSV File", icon="📁"):
        st.info("Download the template, fill it out, and upload the file. If an email in your CSV already exists, its entry will be updated.")
        template_df = pd.DataFrame(columns=ALL_COLUMNS)
        st.download_button("Download CSV Template", template_df.to_csv(index=False).encode('utf-8'), "import_template.csv", "text/csv", use_container_width=True)
        st.file_uploader("Upload your completed CSV Template", type="csv", key="csv_uploader", on_change=process_csv_upload, args=(worksheet,))

    st.markdown("<h3 class='glass-card'><i class='bi bi-table'></i> Email Account Records</h3>", unsafe_allow_html=True)
    selected_company = st.selectbox("Filter by Company", options=["Show All Companies"] + st.session_state.email_data["companyName"].dropna().unique().tolist())
    display_df = st.session_state.email_data[st.session_state.email_data["companyName"] == selected_company].copy() if selected_company != "Show All Companies" else st.session_state.email_data.copy()
    if display_df.empty:
        st.info("No data to display. Add an entry or import a CSV to get started!")
    else:
        df_for_editor = display_df.copy()
        df_for_editor['purchaseDate'] = pd.to_datetime(df_for_editor['purchaseDate'], errors='coerce')
        df_for_editor['expiryDate'] = pd.to_datetime(df_for_editor['expiryDate'], errors='coerce')
        edited_df = st.data_editor(df_for_editor.drop(columns=['password'], errors='ignore'), column_config=COLUMN_CONFIG, num_rows="dynamic", use_container_width=True, key="data_editor", hide_index=True)

    st.markdown("<h3 class='glass-card'><i class='bi bi-pie-chart-fill'></i> Account Status & Export</h3>", unsafe_allow_html=True)
    cols = st.columns([0.6, 0.4])
    with cols[0]: st.altair_chart(get_status_chart(st.session_state.email_data), use_container_width=True)
    with cols[1]:
        st.markdown(" ") 
        st.download_button(label="Export Displayed Data to CSV", data=display_df.drop(columns=['password'], errors='ignore').to_csv(index=False).encode('utf-8'), file_name=f'email_data_{datetime.now().strftime("%Y%m%d")}.csv', mime='text/csv', use_container_width=True)

# --- Main App Execution Logic ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'theme' not in st.session_state: st.session_state.theme = "dark"

load_css()
if st.session_state.logged_in:
    worksheet, connection_status = connect_to_gsheet()
    show_main_app(worksheet, connection_status)
else:
    show_login_page()
