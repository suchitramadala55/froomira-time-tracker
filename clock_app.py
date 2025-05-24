import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Connect to Google Sheets ---
@st.cache_resource
def get_gsheet_connection():
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Froomira Time Log").sheet1
    return sheet

# --- Load & Process Log Data ---
def load_log_df(sheet, show_debug=False):
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()

    if not df.empty:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    if show_debug:
        st.write("🔍 DEBUG - Columns in Sheet:", df.columns.tolist())

    return df

# --- Calculate total hours for today ---
def get_today_hours(df, name):
    today = datetime.now().date()
    logs = df[(df["Name"] == name) & (df["Timestamp"].dt.date == today)]
    return calculate_total_hours(logs)

# --- Calculate total hours for the week ---
def get_week_hours(df, name):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    logs = df[(df["Name"] == name) & (df["Timestamp"].dt.date >= start_of_week.date())]
    return calculate_total_hours(logs)

# --- Core logic to calculate time diffs ---
def calculate_total_hours(logs):
    total_seconds = 0
    clock_in_time = None
    for _, row in logs.iterrows():
        if row["Action"].strip() == "Clock In":
            clock_in_time = row["Timestamp"]
        elif row["Action"].strip() == "Clock Out" and clock_in_time:
            total_seconds += (row["Timestamp"] - clock_in_time).total_seconds()
            clock_in_time = None
    return round(total_seconds / 3600, 2)

# --- Log time and update Google Sheets ---
def log_time_to_sheet(name, role, action):
    sheet = get_gsheet_connection()
    df = load_log_df(sheet)

    now = datetime.now()
    today_hours = get_today_hours(df, name)
    week_hours = get_week_hours(df, name)

    row = [name, role, action, now.strftime("%Y-%m-%d %H:%M:%S"), today_hours, week_hours]
    sheet.append_row(row)

# --- Streamlit UI ---
st.set_page_config(page_title="Froomira Time Tracker", layout="centered")
st.title("🕒 Froomira Time Tracker")

# Developer checkbox only defined once
show_debug = st.sidebar.checkbox("🔍 Developer Mode")

name = st.selectbox("Select your name", ["Suchi", "Dharshine", "Other"])
if name == "Other":
    name = st.text_input("Enter your name")

role = st.selectbox("Select your role", ["Intern", "Store Worker", "Other"])

if name:
    st.write(f"Hello, **{name}** 👋")

    # Load data once
    sheet = get_gsheet_connection()
    df_logs = load_log_df(sheet, show_debug)
    user_logs = df_logs[df_logs["Name"] == name].sort_values("Timestamp", ascending=False)

    # Show last Clock In/Out
    last_in = user_logs[user_logs["Action"].str.strip() == "Clock In"]["Timestamp"].max()
    last_out = user_logs[user_logs["Action"].str.strip() == "Clock Out"]["Timestamp"].max()

    if pd.notna(last_in):
        st.info(f"🟢 Last Clock In: `{last_in.strftime('%Y-%m-%d %H:%M:%S')}`")
    if pd.notna(last_out):
        st.warning(f"🔴 Last Clock Out: `{last_out.strftime('%Y-%m-%d %H:%M:%S')}`")

    # Clock In / Out buttons
    if st.button("✅ Clock In"):
        log_time_to_sheet(name, role, "Clock In")
        st.success("✅ Clock In recorded!")

    if st.button("🔴 Clock Out"):
        log_time_to_sheet(name, role, "Clock Out")
        st.success("🔴 Clock Out recorded!")

    # Refresh logs and show totals
    df_logs = load_log_df(sheet, show_debug)
    today_total = get_today_hours(df_logs, name)
    week_total = get_week_hours(df_logs, name)

    st.markdown(f"### 📅 Total Hours Today: `{today_total}`")
    st.markdown(f"### 📈 Total Hours This Week: `{week_total}`")

    # --- Full log history table ---
    with st.expander("📜 Show Full Log History"):
        st.dataframe(
            user_logs[["Timestamp", "Action", "Role"]].sort_values("Timestamp", ascending=False).reset_index(drop=True),
            use_container_width=True
        )

# Footer
st.markdown("---")
st.caption("🧠 Built by Suchi | Powered by Streamlit + Google Sheets")
