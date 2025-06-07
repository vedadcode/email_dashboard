import streamlit as st
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import gspread
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import altair as alt
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Company Email Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- All UI/CSS Styling (No Changes) ---
def load_css():
    # The full CSS from the previous step goes here.
    # It is omitted for brevity but is unchanged.
    st.markdown("""<style>... a lot of css ...</style>""", unsafe_allow_html=True) # Placeholder

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
        if col not in df.columns: df[col] = ""
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
def calculate_metrics(df):
    if df.empty: return 0, 0, 0
    total_accounts = len(df)
    active_accounts = len(df[df['status'].str.lower() == 'active'])
    today = datetime.now()
    thirty_days_from_now = today + timedelta(days=30)
    exp_dates = pd.to_datetime(df['expiryDate'], errors='coerce')
    expiring_soon = df[(exp_dates.notna()) & (exp_dates >= today) & (exp_dates <= thirty_days_from_now)].shape[0]
    return total_accounts, active_accounts, expiring_soon
def get_status_chart(df):
    if df.empty or df['status'].nunique() == 0:
        return alt.Chart(pd.DataFrame({'status': ['No Data'], 'count': [1]})).mark_arc().encode(color=alt.value('#444')).properties(title="No status data available")
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    chart = alt.Chart(status_counts).mark_arc(innerRadius=60, outerRadius=100).encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(field="status", type="nominal", scale=alt.Scale(domain=['Active', 'Inactive', 'On Hold'], range=['#23D5AB', '#F93154', '#FFC107']), legend=None),
        tooltip=['status', 'count']
    ).properties(width=300, height=300)
    return chart

def show_login_page():
    # ... Login page code (unchanged) ...
    pass

def show_main_app():
    # ... Sidebar and Title code (unchanged) ...
    # ... Theme application logic (unchanged) ...
    
    if 'email_data' not in st.session_state:
        st.session_state.email_data = load_data()

    # ... Metrics Panel (unchanged) ...

    with st.expander("Add a Single Entry", icon="➕"):
        # ... The single entry form (unchanged) ...
        pass
    
    # --- NEW: Bulk Import Feature ---
    with st.expander("Bulk Import from CSV File", icon="📁"):
        # 1. Provide a template for download
        st.info("Download the template, fill it out, and upload it here. The 'emailAccount' column must be unique for each entry.")
        template_df = pd.DataFrame(columns=ALL_COLUMNS)
        csv_template = template_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV Template", csv_template, "import_template.csv", "text/csv", use_container_width=True)

        # 2. The file uploader
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        
        if uploaded_file is not None:
            try:
                # Read the uploaded data
                new_data_df = pd.read_csv(uploaded_file)
                
                # 3. Validate the columns
                if not all(col in new_data_df.columns for col in ALL_COLUMNS):
                    st.error(f"The uploaded CSV is missing required columns. Please ensure it has all of the following columns: {', '.join(ALL_COLUMNS)}")
                else:
                    # 4. Process and merge the data
                    new_data_df = new_data_df[ALL_COLUMNS].astype(str).fillna("")
                    
                    # Combine with existing data
                    combined_df = pd.concat([st.session_state.email_data, new_data_df], ignore_index=True)
                    
                    # Remove duplicates based on email, keeping the last (newest) entry
                    combined_df.drop_duplicates(subset=['emailAccount'], keep='last', inplace=True)
                    
                    # 5. Save back to the database and update the app state
                    save_data(combined_df)
                    st.session_state.email_data = combined_df
                    st.success(f"✅ Successfully imported and merged data! {len(new_data_df)} rows were processed.")
                    st.rerun()

            except Exception as e:
                st.error(f"An error occurred while processing the file: {e}")

    # ... Data Records, Chart, and Export sections (unchanged) ...
    pass

# --- Main App Execution Logic (unchanged) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'theme' not in st.session_state: st.session_state.theme = "dark"
load_css()
if st.session_state.logged_in:
    show_main_app()
else:
    show_login_page()
