import streamlit as st
from google.oauth2.service_account import Credentials
import gspread

st.set_page_config(layout="wide")
st.title("Google Sheets Connection Debugger")

st.info("This is a diagnostic app. It will run a series of tests to find the exact point of failure.")

# --- Test 1: Check Streamlit Secrets ---
st.header("Test 1: Verifying Streamlit Secrets")
creds_dict = None
try:
    creds_dict = st.secrets["gcp_service_account"]
    st.success("✅ Test 1 Passed: Successfully found the `gcp_service_account` section in your secrets.")
    
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing_keys = [key for key in required_keys if key not in creds_dict]
    
    if not missing_keys:
        st.success("✅ All required keys (`project_id`, `private_key`, etc.) are present in the secret.")
    else:
        st.error(f"❌ TEST 1 FAILED: The following keys are MISSING from your `gcp_service_account` secret: `{', '.join(missing_keys)}`. Please correct your secrets.")
        st.stop()

except Exception as e:
    st.error(f"❌ TEST 1 FAILED: Could not read `st.secrets['gcp_service_account']`. The TOML format in your secrets might be incorrect. Error: {e}")
    st.stop()


# --- Test 2: Creating Credentials from Secrets ---
st.header("Test 2: Creating Credentials from Secrets")
creds = None
try:
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    st.success("✅ Test 2 Passed: Successfully created a credential object from your secrets.")
except Exception as e:
    st.error(f"❌ TEST 2 FAILED: The credential information itself is malformed. The `private_key` might be copied incorrectly into your secrets. Error: {e}")
    st.stop()


# --- Test 3: Authorizing with Google ---
st.header("Test 3: Authorizing with Google Servers")
gc = None
try:
    gc = gspread.authorize(creds)
    st.success("✅ Test 3 Passed: Successfully authorized with Google and received an access token.")
except Exception as e:
    st.error(f"❌ TEST 3 FAILED: Could not authorize with Google. This can be a temporary network issue or a problem with the service account itself (e.g., it might be disabled in Google Cloud). Error: {e}")
    st.stop()


# --- Test 4: Listing Accessible Spreadsheets ---
st.header("Test 4: Listing All Spreadsheets the Service Account Can See")
try:
    accessible_sheets = gc.list_spreadsheets()
    st.success(f"✅ Test 4 Passed: Successfully queried Google Drive. The service account can see {len(accessible_sheets)} spreadsheet(s).")
    if accessible_sheets:
        st.write("Here are the sheets it can see:")
        for sheet in accessible_sheets:
            st.write(f"- `{sheet.title}` (ID: `{sheet.id}`)")
    else:
        st.warning("⚠️ The service account connected to Google but does not have access to ANY spreadsheets. This confirms the 'Share' settings on your Google Sheet are the problem. Please share your sheet with the service account email.")
        st.stop()
except Exception as e:
    st.error(f"❌ TEST 4 FAILED: Could not list spreadsheets. This points to a high-level permission issue. Is the 'Google Drive API' enabled in your project? Error: {e}")
    st.stop()


# --- Test 5: Opening Your Specific Sheet by ID ---
st.header("Test 5: Attempting to Open Your Specific Sheet")
SPREADSHEET_ID = "1snHjynQb3ecyXMgbP4d7WrhAtPoJpzNNC7moZTEW6FM"
st.info(f"Trying to open sheet with ID: `{SPREADSHEET_ID}`")
try:
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    st.balloons()
    st.success("🎉 SUCCESS! The application can successfully open your spreadsheet. The connection issue is resolved.")
    st.info("You can now replace the content of this debug app with the last complete application code I provided.")
except Exception as e:
    st.error(f"❌ TEST 5 FAILED: Could not open the specific sheet. This is the final point of failure. It means all previous steps worked, but the service account does NOT have 'Editor' access to THIS specific sheet ID. Please double-check the sharing settings one last time.")
    st.code(f"Error details: {e}")
