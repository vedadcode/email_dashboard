import streamlit as st
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import gspread

# --- Page Configuration ---
st.set_page_config(
    page_title="Company Email Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- Custom CSS (No Changes) ---
def load_css():
    # ... (The same CSS code from the previous version goes here) ...
    # It's long, so I'm omitting it here for brevity.
    # Just make sure your CSS function is still in the script.
    css_to_inject = """
    :root { /* Default: Dark Theme */
        --primary-accent-color: #00CFE8;
        /* ... all your other CSS rules ... */
    }
    /* ... etc ... */
    """
    st.markdown(f'<style>{css_to_inject}</style>', unsafe_allow_html=True)


# --- NEW: Google Sheets Connection ---
# The scope of permissions we need
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Get credentials from Streamlit Secrets
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
gc = gspread.authorize(creds)

# Open the Google Sheet (use the exact name of your sheet)
SPREADSHEET_NAME = "Email Dashboard Data" 
try:
    spreadsheet = gc.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.sheet1
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Spreadsheet '{SPREADSHEET_NAME}' not found. Please check the name and sharing settings.")
    st.stop()
    
ALL_COLUMNS = [
    "companyName", "emailAccount", "password", "accountHolder", "remarks",
    "subscriptionPlatform", "purchaseDate", "expiryDate", "mailType", "status"
]

# --- REWRITTEN: Data Functions ---
def load_data():
    """Loads data from the Google Sheet."""
    df = get_as_dataframe(worksheet, evaluate_formulas=False)
    # Ensure all columns exist, even if sheet is empty
    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = None
    # Ensure proper data types, especially for dates
    df['purchaseDate'] = pd.to_datetime(df['purchaseDate'], errors='coerce').dt.strftime('%Y-%m-%d')
    df['expiryDate'] = pd.to_datetime(df['expiryDate'], errors='coerce').dt.strftime('%Y-%m-%d')
    return df[ALL_COLUMNS].fillna('')


def save_data(df):
    """Saves the entire DataFrame back to the Google Sheet."""
    # Convert date columns to string to avoid timezone issues with gspread
    df['purchaseDate'] = df['purchaseDate'].astype(str)
    df['expiryDate'] = df['expiryDate'].astype(str)
    set_with_dataframe(worksheet, df)


# (The rest of your app code remains largely the same, but I'll include it for completeness)
# App Constants, Login Page, Main App Page...
# The code below is the same as the previous version.

# --- App Constants ---
COMPANY_OPTIONS = ["", "Rewardoo Private Limited", "Eseries Sports Private Limited", "Heksa Skills Private Limited", "Softscience Tech Private Limited"]
PLATFORM_OPTIONS = ["", "Hostinger", "GoDaddy", "Google Console (Workspace)", "Zoho Mail", "Microsoft 365 (Exchange)"]
MAIL_TYPE_OPTIONS = ["", "Gmail Regular", "Gmail Paid (Workspace)", "Hostinger Webmail", "GoDaddy Webmail", "Zoho Standard", "Microsoft Exchange"]
STATUS_OPTIONS = ["Active", "Inactive", "On Hold"]
COLUMN_CONFIG = {
    "companyName": st.column_config.SelectboxColumn("Company", options=COMPANY_OPTIONS[1:], required=True),
    "emailAccount": st.column_config.TextColumn("Email", required=True),
    "accountHolder": st.column_config.TextColumn("Account Holder", required=True),
    "subscriptionPlatform": st.column_config.SelectboxColumn("Platform", options=PLATFORM_OPTIONS[1:], required=True),
    "purchaseDate": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD", required=True),
    "expiryDate": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD", required=True),
    "mailType": st.column_config.SelectboxColumn("Mail Type", options=MAIL_TYPE_OPTIONS[1:], required=True),
    "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, default="Active", required=True),
    "remarks": st.column_config.TextColumn("Remarks"),
}

def show_login_page():
    st.title("Company Email Dashboard")
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        with st.form("login_form"):
            st.header("Please Login to Continue")
            username = st.text_input("Username", placeholder="Admin")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if username == st.secrets["app_credentials"]["username"] and password == st.secrets["app_credentials"]["password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect username or password")

def show_main_app():
    with st.sidebar:
        st.success(f"Logged in as **{st.secrets['app_credentials']['username']}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    st.title("Company Email Dashboard")
    if 'email_data' not in st.session_state:
        st.session_state.email_data = load_data()
    with st.expander("➕ Add New Email Entry", expanded=False):
        with st.form("new_entry_form", clear_on_submit=True):
            # ... (The form code is exactly the same as before)
            cols = st.columns((1, 1, 1))
            companyName = cols[0].selectbox("Company Name*", options=COMPANY_OPTIONS[1:])
            emailAccount = cols[1].text_input("Email Account*")
            password = cols[2].text_input("Password*", type="password")
            cols = st.columns((1, 1, 1))
            accountHolder = cols[0].text_input("Account Holder*")
            subscriptionPlatform = cols[1].selectbox("Subscription Platform*", options=PLATFORM_OPTIONS[1:])
            mailType = cols[2].selectbox("Mail Type*", options=MAIL_TYPE_OPTIONS[1:])
            cols = st.columns((1, 1, 1))
            purchaseDate = cols[0].date_input("Purchase Date*", value=None, format="YYYY-MM-DD")
            expiryDate = cols[1].date_input("Expiry Date*", value=None, format="YYYY-MM-DD")
            status = cols[2].selectbox("Status", options=STATUS_OPTIONS)
            remarks = st.text_area("Remarks")
            submitted = st.form_submit_button("Add New Entry")
            if submitted:
                if not all([companyName, emailAccount, password, accountHolder, subscriptionPlatform, mailType, purchaseDate, expiryDate]):
                    st.error("Please fill in all required (*) fields.")
                else:
                    new_entry_df = pd.DataFrame([{
                        "companyName": companyName, "emailAccount": emailAccount, "password": password,
                        "accountHolder": accountHolder, "remarks": remarks, "subscriptionPlatform": subscriptionPlatform,
                        "purchaseDate": str(purchaseDate), "expiryDate": str(expiryDate),
                        "mailType": mailType, "status": status
                    }])
                    st.session_state.email_data = pd.concat([st.session_state.email_data, new_entry_df], ignore_index=True)
                    save_data(st.session_state.email_data)
                    st.success("✅ Entry added successfully!")
                    st.rerun()

    st.header("Filter & Export Data")
    # ... (Filter/Export code is the same)
    st.header("Email Account Entries")
    # ... (Data Editor code is the same)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
load_css() # Make sure to call the CSS function
if st.session_state.logged_in:
    show_main_app()
else:
    show_login_page()