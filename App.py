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

# --- Custom CSS ---
def load_css():
    css_to_inject = """
    :root { /* Default: Dark Theme */
        --primary-accent-color: #00CFE8;
        --primary-accent-hover-color: #00A9BF;
        --secondary-accent-color: #FFC107;
        --secondary-accent-hover-color: #E0A800;
        --danger-color: #F93154;
        --danger-hover-color: #D12745;
        --success-color: #4CAF50;
        --info-color: #17A2B8;
        --bg-color: #1A1D24;
        --card-bg-color: #252A34;
        --border-color: #3A3F4B;
        --input-bg-color: var(--card-bg-color);
        --input-focus-border: var(--primary-accent-color);
        --text-color-primary: #EAEAEA;
        --text-color-secondary: #A0AEC0;
        --text-color-headings: #FFFFFF;
        --border-radius: 12px;
        --shadow-distance: 6px;
        --shadow-blur: 12px;
        --highlight-shadow-color: rgba(255, 255, 255, 0.05);
        --dark-shadow-color: rgba(0, 0, 0, 0.3);
        --inset-highlight-shadow-color: rgba(255, 255, 255, 0.03);
        --inset-dark-shadow-color: rgba(0, 0, 0, 0.4);
    }
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color-primary);
    }
    h1 {
        color: var(--primary-accent-color) !important;
        text-shadow: 1px 1px 2px var(--dark-shadow-color), -1px -1px 2px var(--highlight-shadow-color);
        text-align: center;
        padding-bottom: 20px;
    }
    h2, h3 {
         color: var(--text-color-headings);
         text-shadow: 0.5px 0.5px 1px var(--dark-shadow-color);
    }
    .stExpander, div[data-testid="stDataFrame"], .stButton, div[data-testid="stForm"], div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div[data-has-equals-button="true"] {
        background: var(--card-bg-color) !important;
        padding: 25px !important;
        border-radius: var(--border-radius) !important;
        box-shadow: var(--shadow-distance) var(--shadow-distance) var(--shadow-blur) var(--dark-shadow-color),
                    calc(-1 * var(--shadow-distance)) calc(-1 * var(--shadow-distance)) var(--shadow-blur) var(--highlight-shadow-color) !important;
        border: none !important;
        margin-bottom: 25px;
    }
    .stExpander header {
        font-size: 1.3em;
        color: var(--text-color-headings) !important;
        font-weight: 600;
        padding: 0 !important;
    }
    .stTextInput > div > div > input, .stDateInput > div > div > input, .stSelectbox > div > div {
        background-color: var(--input-bg-color) !important;
        color: var(--text-color-primary) !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: inset 3px 3px 5px var(--inset-dark-shadow-color),
                    inset -3px -3px 5px var(--inset-highlight-shadow-color) !important;
    }
    .stTextInput > label, .stDateInput > label, .stSelectbox > label {
        color: var(--text-color-secondary) !important;
        font-weight: 500;
    }
     .stButton > button, .stDownloadButton > button {
        padding: 10px 20px; border: none; border-radius: var(--border-radius); font-weight: 600;
        transition: box-shadow 0.15s ease-out, transform 0.15s ease-out;
        background-color: var(--primary-accent-color); color: #121212;
         box-shadow: var(--shadow-distance) var(--shadow-distance) var(--shadow-blur) var(--dark-shadow-color),
                    calc(-1 * var(--shadow-distance)) calc(-1 * var(--shadow-distance)) var(--blur-shadow-color);
    }
    .stButton > button:active, .stDownloadButton > button:active {
        box-shadow: inset 3px 3px 5px var(--inset-dark-shadow-color),
                    inset -3px -3px 5px var(--inset-highlight-shadow-color);
        transform: translateY(2px);
    }
    div[data-testid="stDataFrame"] { padding: 0 !important; }
    div[data-testid="stDataFrame"] > div { border-radius: var(--border-radius) !important; overflow: hidden; }
    .stDataFrame .data-grid { background-color: var(--card-bg-color); }
    .stDataFrame .data-grid-header { background-color: transparent; color: var(--primary-accent-color); font-weight: 600; }
    .stDataFrame .data-grid-cell { color: var(--text-color-secondary); border-bottom: 1px solid var(--border-color); }
    .stDownloadButton > button { background-color: var(--info-color) !important; color: white !important; }
    div[data-testid="stForm"] .stButton > button {
        background-color: var(--primary-accent-color); color: #121212;
    }
    """
    st.markdown(f'<style>{css_to_inject}</style>', unsafe_allow_html=True)


# --- Google Sheets Connection ---
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
    
ALL_COLUMNS = [
    "companyName", "emailAccount", "password", "accountHolder", "remarks",
    "subscriptionPlatform", "purchaseDate", "expiryDate", "mailType", "status"
]

# --- REWRITTEN & IMPROVED: Data Functions ---
def load_data():
    """Loads and cleans data from the Google Sheet."""
    df = get_as_dataframe(worksheet, evaluate_formulas=False, header=1)
    # Drop rows that are completely empty
    df.dropna(how='all', inplace=True)
    # Ensure all defined columns exist
    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = "" # Initialize empty columns
    # Ensure the dataframe only has the columns we want in the right order
    df = df[ALL_COLUMNS]
    # Convert all columns to string type to avoid errors, then fill empty values
    df = df.astype(str).fillna("")
    # Replace common "empty" values just in case
    df.replace(['nan', 'None', '<NA>'], '', inplace=True)
    return df

def save_data(df):
    """Saves the entire DataFrame back to the Google Sheet."""
    # Convert to string before saving to avoid type/timezone errors
    df_to_save = df.astype(str)
    set_with_dataframe(worksheet, df_to_save)


# --- App Constants ---
COMPANY_OPTIONS = ["", "Rewardoo Private Limited", "Eseries Sports Private Limited", "Heksa Skills Private Limited", "Softscience Tech Private Limited"]
PLATFORM_OPTIONS = ["", "Hostinger", "GoDaddy", "Google Console (Workspace)", "Zoho Mail", "Microsoft 365 (Exchange)"]
MAIL_TYPE_OPTIONS = ["", "Gmail Regular", "Gmail Paid (Workspace)", "Hostinger Webmail", "GoDaddy Webmail", "Zoho Standard", "Microsoft Exchange"]
STATUS_OPTIONS = ["Active", "Inactive", "On Hold"]
COLUMN_CONFIG = { "companyName": st.column_config.SelectboxColumn("Company", options=COMPANY_OPTIONS[1:], required=True), "emailAccount": st.column_config.TextColumn("Email", required=True), "accountHolder": st.column_config.TextColumn("Account Holder", required=True), "subscriptionPlatform": st.column_config.SelectboxColumn("Platform", options=PLATFORM_OPTIONS[1:], required=True), "purchaseDate": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD", required=True), "expiryDate": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD", required=True), "mailType": st.column_config.SelectboxColumn("Mail Type", options=MAIL_TYPE_OPTIONS[1:], required=True), "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, default="Active", required=True), "remarks": st.column_config.TextColumn("Remarks"),}

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
                    new_entry_df = pd.DataFrame([{ "companyName": companyName, "emailAccount": emailAccount, "password": password, "accountHolder": accountHolder, "remarks": remarks, "subscriptionPlatform": subscriptionPlatform, "purchaseDate": str(purchaseDate), "expiryDate": str(expiryDate), "mailType": mailType, "status": status }])
                    st.session_state.email_data = pd.concat([st.session_state.email_data, new_entry_df], ignore_index=True)
                    save_data(st.session_state.email_data)
                    st.success("✅ Entry added successfully!")
                    st.rerun()

    st.header("Filter & Export Data")
    with st.container():
        filter_cols = st.columns((2, 1))
        # Check if email_data is not empty before accessing columns
        if not st.session_state.email_data.empty:
            unique_companies = ["Show All Companies"] + st.session_state.email_data["companyName"].dropna().unique().tolist()
        else:
            unique_companies = ["Show All Companies"]
        selected_company = filter_cols[0].selectbox("Filter by Company", options=unique_companies)
        if selected_company != "Show All Companies":
            display_df = st.session_state.email_data[st.session_state.email_data["companyName"] == selected_company].copy()
        else:
            display_df = st.session_state.email_data.copy()
        @st.cache_data
        def to_csv(df_to_export):
            return df_to_export.drop(columns=['password'], errors='ignore').to_csv(index=False).encode('utf-8')
        csv_data = to_csv(display_df)
        filter_cols[1].markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        filter_cols[1].download_button(label="📥 Export to CSV", data=csv_data, file_name='company_email_data.csv', mime='text/csv')

    st.header("Email Account Entries")
    if display_df.empty:
        st.warning("No data found for the selected filter.")
    else:
        # Convert columns to appropriate types before showing in editor
        # This helps the editor's specialized columns (like date) to work correctly
        df_for_editor = display_df.copy()
        df_for_editor['purchaseDate'] = pd.to_datetime(df_for_editor['purchaseDate'], errors='coerce')
        df_for_editor['expiryDate'] = pd.to_datetime(df_for_editor['expiryDate'], errors='coerce')

        edited_df = st.data_editor(df_for_editor.drop(columns=['password'], errors='ignore'), column_config=COLUMN_CONFIG, num_rows="dynamic", use_container_width=True, key="data_editor")
        
        # Compare original with the edited version to detect changes
        if not df_for_editor.drop(columns=['password'], errors='ignore').equals(edited_df):
            # Create a full version of the edited dataframe to merge back
            edited_df_full = edited_df.copy()
            edited_df_full['password'] = df_for_editor['password'] # Keep original passwords
            
            # Find the original indices from the session state that match the displayed data
            original_indices = st.session_state.email_data[st.session_state.email_data.index.isin(df_for_editor.index)].index
            
            # Drop the old versions of the edited rows from the main data
            st.session_state.email_data.drop(original_indices, inplace=True)
            
            # Add the updated rows back
            st.session_state.email_data = pd.concat([st.session_state.email_data, edited_df_full]).reset_index(drop=True)
            
            save_data(st.session_state.email_data)
            st.success("💾 Changes saved!")
            st.rerun()

# --- Main App Execution Logic ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
load_css()
if st.session_state.logged_in:
    show_main_app()
else:
    show_login_page()
