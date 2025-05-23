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
def load_log_df(sheet):
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
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
        if row["Action"] == "Clock In":
            clock_in_time = row["Timestamp"]
        elif row["Action"] == "Clock Out" and clock_in_time:
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

    if action == "Clock Out":
        today_hours = round(today_hours + 0, 2)
        week_hours = round(week_hours + 0, 2)

    row = [name, role, action, now.strftime("%Y-%m-%d %H:%M:%S"), today_hours, week_hours]
    sheet.append_row(row)

# --- UI ---
st.title("🕒 Froomira Time Tracker")

name = st.selectbox("Select your name", ["Suchi", "Dharshine", "Other"])
if name == "Other":
    name = st.text_input("Enter your name")

role = st.selectbox("Select your role", ["Intern", "Store Worker", "Other"])

if name:
    st.write(f"Hello, **{name}** 👋")

    if st.button("✅ Clock In"):
        log_time_to_sheet(name, role, "Clock In")
        st.success("✅ Clock In recorded!")

    if st.button("🔴 Clock Out"):
        log_time_to_sheet(name, role, "Clock Out")
        st.success("🔴 Clock Out recorded!")

    # Show live totals
    sheet = get_gsheet_connection()
    df = load_log_df(sheet)

    today_total = get_today_hours(df, name)
    week_total = get_week_hours(df, name)

    st.markdown(f"### 📅 Total Hours Today: `{today_total}`")
    st.markdown(f"### 📈 Total Hours This Week: `{week_total}`")
