import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

DATA_FILE = 'time_log.csv'

def init_csv():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            'Name', 'Role', 'Action', 'Timestamp',
            'Total Hours Today', 'Total Hours This Week'
        ])
        df.to_csv(DATA_FILE, index=False)

def get_existing_names():
    if not os.path.exists(DATA_FILE):
        return []
    df = pd.read_csv(DATA_FILE)
    return sorted(df['Name'].dropna().unique().tolist())

def get_total_hours(df):
    total_seconds = 0
    clock_in_time = None
    for _, row in df.iterrows():
        if row['Action'] == 'Clock In':
            clock_in_time = row['Timestamp']
        elif row['Action'] == 'Clock Out' and clock_in_time:
            total_seconds += (row['Timestamp'] - clock_in_time).total_seconds()
            clock_in_time = None
    return round(total_seconds / 3600, 2)

def get_today_hours(df, name):
    today = datetime.now().date()
    logs = df[(df['Name'] == name) & (df['Timestamp'].dt.date == today)]
    logs = logs.sort_values('Timestamp')
    return get_total_hours(logs)

def get_week_hours(df, name):
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    logs = df[(df['Name'] == name) & (df['Timestamp'].dt.date >= monday.date())]
    logs = logs.sort_values('Timestamp')
    return get_total_hours(logs)

def log_time(name, role, action):
    df = pd.read_csv(DATA_FILE)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    now = datetime.now()
    new_entry = pd.DataFrame([[name, role, action, now, None, None]],
        columns=['Name', 'Role', 'Action', 'Timestamp', 'Total Hours Today', 'Total Hours This Week'])

    df = pd.concat([df, new_entry], ignore_index=True)

    today_hours = get_today_hours(df, name)
    week_hours = get_week_hours(df, name)

    df.at[df.index[-1], 'Total Hours Today'] = today_hours
    df.at[df.index[-1], 'Total Hours This Week'] = week_hours

    try:
        df.to_csv(DATA_FILE, index=False)
    except PermissionError:
        st.error("❌ Please close 'time_log.csv' in Excel before clocking in/out.")

def show_logs(name):
    df = pd.read_csv(DATA_FILE)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    user_logs = df[df['Name'] == name].sort_values('Timestamp', ascending=False)
    st.dataframe(user_logs.head(10))

def main():
    st.title("🕒 Froomira Time Tracker")

    existing_names = get_existing_names()
    selected_name = st.selectbox("Select your name", existing_names + ["Other"])

    if selected_name == "Other":
        name = st.text_input("Enter your name")
    else:
        name = selected_name

    role = st.selectbox("Select your role", ["Intern", "Store Worker", "Other"])

    if name:
        st.write(f"Hello, **{name}** 👋")

        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['Name', 'Role', 'Action', 'Timestamp'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp']) if not df.empty else None

        last_action = None
        if not df[df['Name'] == name].empty:
            last_action = df[df['Name'] == name].sort_values('Timestamp').iloc[-1]['Action']

        if st.button("🟢 Clock In"):
            if last_action == "Clock In":
                st.warning("⚠️ You already clocked in. Please clock out before clocking in again.")
            else:
                log_time(name, role, "Clock In")
                st.success("Clocked In successfully!")

        if st.button("🔴 Clock Out"):
            if last_action != "Clock In":
                st.warning("⚠️ You need to clock in before clocking out.")
            else:
                log_time(name, role, "Clock Out")
                st.success("Clocked Out successfully!")

        df = pd.read_csv(DATA_FILE)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])

        st.subheader("⏱️ Total Hours Worked Today")
        st.info(f"**{get_today_hours(df, name)} hours** worked today")

        st.subheader("📆 Total Hours Worked This Week")
        st.success(f"**{get_week_hours(df, name)} hours** worked this week")

        st.subheader("📋 Recent Entries")
        show_logs(name)

if __name__ == "__main__":
    init_csv()
    main()
