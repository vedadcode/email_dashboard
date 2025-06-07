import streamlit as st
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import gspread
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="Company Email Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- UPDATED: Classy & Sassy CSS ---
def load_css():
    css_to_inject = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root { /* Default: Dark Theme */
        --primary-accent-color: #00CFE8;
        --text-on-accent: #000000;
        --bg-color: #1A1D24;
        --card-bg-color: #252A34;
        --border-color: #3A3F4B;
        --input-bg-color: #1A1D24; 
        --text-color-primary: #EAEAEA;
        --text-color-secondary: #A0AEC0;
        --text-color-headings: #FFFFFF;
        --danger-color: #F93154;
        --success-color: #4CAF50;
        --info-color: #17A2B8;
        --border-radius: 16px;
        --shadow-soft: 5px 5px 10px #15181e, -5px -5px 10px #2f364a;
        --shadow-inset: inset 2px 2px 5px #15181e, inset -2px -2px 5px #2f364a;
        --font-family: 'Inter', sans-serif;
    }

    body[data-theme="light"] {
        --primary-accent-color: #007AFF;
        --text-on-accent: #FFFFFF;
        --bg-color: #E0E5EC;
        --card-bg-color: #E0E5EC;
        --border-color: #D1D9E6;
        --input-bg-color: #dde2e9;
        --text-color-primary: #3E4A5D;
        --text-color-secondary: #748094;
        --text-color-headings: #0056b3;
        --danger-color: #dc3545;
        --success-color: #28a745;
        --info-color: #17a2b8;
        --shadow-soft: 6px 6px 12px #a3b1c6, -6px -6px 12px #ffffff;
        --shadow-inset: inset 3px 3px 6px #a3b1c6, inset -3px -3px 6px #ffffff;
    }

    /* General App Styling */
    body { font-family: var(--font-family); }
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color-primary);
        transition: background-color 0.3s ease, color 0.3s ease;
    }
    h1 {
        color: var(--primary-accent-color) !important;
        text-align: center;
        padding-bottom: 10px;
        font-weight: 700;
    }
    h2, h3 { color: var(--text-color-headings); font-weight: 600; }
    
    /* Card & Container Styling with Animation */
    @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
    .stExpander, div[data-testid="stDataFrame"], .stButton, div[data-testid="stForm"], div[data-testid="stMetric"] {
        background: var(--card-bg-color) !important;
        padding: 25px !important;
        border-radius: var(--border-radius) !important;
        box-shadow: var(--shadow-soft) !important;
        border: 1px solid transparent !important;
        margin-bottom: 25px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        animation: fadeIn 0.6s ease-out forwards;
    }
    .stExpander:hover, div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0px 10px 20px rgba(0,0,0,0.1) !important;
    }

    /* Input Styling */
    .stTextInput > div > div > input, .stDateInput > div > div > input, .stSelectbox > div > div {
        background-color: var(--input-bg-color) !important;
        color: var(--text-color-primary) !important;
        border: none !important;
        border-radius: 10px !important;
        box-shadow: var(--shadow-inset) !important;
    }
    .stTextInput > label, .stDateInput > label, .stSelectbox > label { color: var(--text-color-secondary) !important; font-weight: 500; }

    /* Button Styling */
    .stButton > button, .stDownloadButton > button {
        border: none; border-radius: 10px; font-weight: 600; padding: 10px 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        background-color: var(--primary-accent-color); color: var(--text-on-accent);
        box-shadow: var(--shadow-soft);
    }
    .stButton > button:hover { transform: scale(1.05); }
    .stButton > button:active { box-shadow: var(--shadow-inset); transform: scale(0.98); }

    /* Metric Card Styling */
    div[data-testid="stMetric"] label { color: var(--text-color-secondary) !important; font-weight: 500; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 2.2em; font-weight: 700; color: var(--text-color-primary) !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] { font-weight: 600; color: var(--primary-accent-color) !important; }

    /* Data Editor Table Styling */
    div[data-testid="stDataFrame"] { padding: 15px 10px !important; }
    .stDataFrame .data-grid-header { background-color: transparent !important; color: var(--primary-accent-color); font-weight: 600; font-size: 1.1em; }
    """
    st.markdown(f'<style>{css_to_inject}</style>', unsafe_allow_html=True)

# --- All Backend Functions and Constants (No Changes) ---
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
gc = gspread.authorize(creds)
SPREADSHEET_NAME = "Email Dashboard Data"
try:
    spreadsheet = gc.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.sheet1
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Spreadsheet '{SPREADSHEET_NAME}' not found. Please check the name and that you've shared it with the service account email.")
    st.stop()
ALL_COLUMNS = ["companyName", "emailAccount", "password", "accountHolder", "remarks", "subscriptionPlatform", "purchaseDate", "expiryDate", "mailType", "status"]
def load_data():
    df = get_as_dataframe(worksheet, evaluate_formulas=False, header=1).astype(str)
    df.dropna(how='all', inplace=True)
    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[ALL_COLUMNS].fillna("")
    df.replace(['nan', 'None', '<NA>'], '', inplace=True)
    return df
def save_data(df):
    set_with_dataframe(worksheet, df.astype(str))
COMPANY_OPTIONS = ["", "Rewardoo Private Limited", "Eseries Sports Private Limited", "Heksa Skills Private Limited", "Softscience Tech Private Limited"]
PLATFORM_OPTIONS = ["", "Hostinger", "GoDaddy", "Google Console (Workspace)", "Zoho Mail", "Microsoft 365 (Exchange)"]
MAIL_TYPE_OPTIONS = ["", "Gmail Regular", "Gmail Paid (Workspace)", "Hostinger Webmail", "GoDaddy Webmail", "Zoho Standard", "Microsoft Exchange"]
STATUS_OPTIONS = ["Active", "Inactive", "On Hold"]
COLUMN_CONFIG = { "companyName": st.column_config.SelectboxColumn("Company", options=COMPANY_OPTIONS[1:], required=True), "emailAccount": st.column_config.TextColumn("Email", required=True), "accountHolder": st.column_config.TextColumn("Account Holder", required=True), "subscriptionPlatform": st.column_config.SelectboxColumn("Platform", options=PLATFORM_OPTIONS[1:], required=True), "purchaseDate": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD", required=True), "expiryDate": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD", required=True), "mailType": st.column_config.SelectboxColumn("Mail Type", options=MAIL_TYPE_OPTIONS[1:], required=True), "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, default="Active", required=True), "remarks": st.column_config.TextColumn("Remarks"),}

# --- NEW: Metrics Calculation Function ---
def calculate_metrics(df):
    if df.empty:
        return 0, 0, 0
    total_accounts = len(df)
    active_accounts = len(df[df['status'].str.lower() == 'active'])
    today = datetime.now()
    thirty_days_from_now = today + timedelta(days=30)
    # Convert expiryDate to datetime, coercing errors
    exp_dates = pd.to_datetime(df['expiryDate'], errors='coerce')
    expiring_soon = df[(exp_dates >= today) & (exp_dates <= thirty_days_from_now)].shape[0]
    return total_accounts, active_accounts, expiring_soon

def show_login_page():
    st.title("🔐 Company Email Dashboard")
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        with st.form("login_form"):
            st.header("Please Login")
            username = st.text_input("Username", placeholder="Admin")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                if username == st.secrets["app_credentials"]["username"] and password == st.secrets["app_credentials"]["password"]:
                    st.session_state.logged_in = True; st.rerun()
                else:
                    st.error("Incorrect username or password")

def show_main_app():
    with st.sidebar:
        st.success(f"Logged in as **{st.secrets['app_credentials']['username']}**")
        def theme_changed():
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.toggle("Light Mode", value=(st.session_state.theme == 'light'), on_change=theme_changed, key="theme_toggle")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            for key in ['theme', 'email_data']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
    
    st.title("Company Email Dashboard")

    if st.session_state.theme == "light":
        components.html("""<script>window.parent.document.body.setAttribute('data-theme', 'light');</script>""", height=0, width=0)
    else:
        components.html("""<script>window.parent.document.body.removeAttribute('data-theme');</script>""", height=0, width=0)

    if 'email_data' not in st.session_state:
        st.session_state.email_data = load_data()

    # --- NEW: Display Metrics Panel ---
    st.subheader("📊 At a Glance")
    total, active, expiring = calculate_metrics(st.session_state.email_data)
    cols = st.columns(3)
    cols[0].metric("Total Accounts", total)
    cols[1].metric("Active Accounts", active, delta=f"{round((active/total)*100) if total > 0 else 0}%")
    cols[2].metric("Expiring Soon", expiring, delta=f"-{expiring} within 30 days", delta_color="inverse")
    
    with st.expander("➕ Add New Email Entry"):
        with st.form("new_entry_form", clear_on_submit=True):
            cols = st.columns((1, 1, 1)); companyName = cols[0].selectbox("Company Name*", options=COMPANY_OPTIONS[1:]); emailAccount = cols[1].text_input("Email Account*"); password = cols[2].text_input("Password*", type="password")
            cols = st.columns((1, 1, 1)); accountHolder = cols[0].text_input("Account Holder*"); subscriptionPlatform = cols[1].selectbox("Subscription Platform*", options=PLATFORM_OPTIONS[1:]); mailType = cols[2].selectbox("Mail Type*", options=MAIL_TYPE_OPTIONS[1:])
            cols = st.columns((1, 1, 1)); purchaseDate = cols[0].date_input("Purchase Date*", value=None); expiryDate = cols[1].date_input("Expiry Date*", value=None); status = cols[2].selectbox("Status", options=STATUS_OPTIONS)
            remarks = st.text_area("Remarks")
            if st.form_submit_button("Add Entry", use_container_width=True, type="primary"):
                if not all([companyName, emailAccount, password, accountHolder, subscriptionPlatform, mailType, purchaseDate, expiryDate]): st.error("Please fill in all required (*) fields.")
                else:
                    new_entry_df = pd.DataFrame([{col: "" for col in ALL_COLUMNS}]) # Create a structured row
                    new_entry_df.iloc[0] = {"companyName": companyName, "emailAccount": emailAccount, "password": password, "accountHolder": accountHolder, "remarks": remarks, "subscriptionPlatform": subscriptionPlatform, "purchaseDate": str(purchaseDate), "expiryDate": str(expiryDate), "mailType": mailType, "status": status}
                    st.session_state.email_data = pd.concat([st.session_state.email_data, new_entry_df], ignore_index=True)
                    save_data(st.session_state.email_data)
                    st.success("✅ Entry added successfully!"); st.rerun()

    st.subheader("🗂️ Email Account Entries")
    cols = st.columns([2,1])
    if not st.session_state.email_data.empty: unique_companies = ["Show All Companies"] + st.session_state.email_data["companyName"].dropna().unique().tolist()
    else: unique_companies = ["Show All Companies"]
    selected_company = cols[0].selectbox("Filter by Company", options=unique_companies, label_visibility="collapsed")
    with cols[1]:
        display_df = st.session_state.email_data[st.session_state.email_data["companyName"] == selected_company].copy() if selected_company != "Show All Companies" else st.session_state.email_data.copy()
        csv_data = display_df.drop(columns=['password'], errors='ignore').to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Export to CSV", data=csv_data, file_name=f'company_email_data_{datetime.now().strftime("%Y%m%d")}.csv', mime='text/csv', use_container_width=True)

    if display_df.empty: st.warning("No data found for the selected filter.")
    else:
        df_for_editor = display_df.copy()
        df_for_editor['purchaseDate'] = pd.to_datetime(df_for_editor['purchaseDate'], errors='coerce')
        df_for_editor['expiryDate'] = pd.to_datetime(df_for_editor['expiryDate'], errors='coerce')
        edited_df = st.data_editor(df_for_editor.drop(columns=['password'], errors='ignore'), column_config=COLUMN_CONFIG, num_rows="dynamic", use_container_width=True, key="data_editor", hide_index=True)
        if not df_for_editor.drop(columns=['password'], errors='ignore').equals(edited_df):
            edited_df['password'] = df_for_editor['password'] # Re-add password column for saving
            save_data(edited_df if selected_company != "Show All Companies" else pd.concat([st.session_state.email_data[st.session_state.email_data["companyName"] != selected_company], edited_df]).reset_index(drop=True))
            st.success("💾 Changes saved!"); st.rerun()

# --- Main App Execution Logic ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'theme' not in st.session_state: st.session_state.theme = "dark"

load_css()
if st.session_state.logged_in:
    show_main_app()
else:
    show_login_page()
