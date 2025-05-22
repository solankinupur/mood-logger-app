import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime,timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
from streamlit_plotly_events import plotly_events


# Setup Google Sheet connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Mood Logger").sheet1

st.set_page_config(page_title="Vibe Check", page_icon=":bar_chart:")

st.markdown("### Log a New Mood Entry")

# Ticket input form
with st.form("ticket_form"):
    ticket_no = f"#T{datetime.now().strftime('%y%m%d%H%M%S')}"
    st.text_input("Ticket Number", value=ticket_no, disabled=True)

    user_note = st.text_input("Describe the issue")
    user_mood = st.selectbox("Select Mood", ["😊 Happy", "😠 Frustrated", "😕 Confused", "🎉 Joyful"])

    submit = st.form_submit_button("Submit")

    if submit:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, ticket_no, user_mood, user_note])
        st.success("Ticket logged successfully!")

# Load Sheet Data
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.subheader("Select Date Range")
date_mode = st.radio("", ["Today", "Custom Range"], horizontal=True, label_visibility="collapsed")

# Make sure Timestamp is in datetime format
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# Calculate min/max dates from your data
min_date = df["Timestamp"].min().date()
max_date = df["Timestamp"].max().date()

start_date = end_date = datetime.now().date()

# Date input: range or single day
if date_mode == "Custom Range":
    date_range = st.date_input(
        "Choose date or range",
        value=(start_date, end_date),
        min_value=min_date,
        max_value=max_date
    )


# Confirm user has entered both start and end dates
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.stop()

# Filter your data based on the selected range
df_filtered = df[(df["Timestamp"].dt.date >= start_date) & (df["Timestamp"].dt.date <= end_date)]

## DISPLAY CHARTS
# Mood bar chart
st.subheader("What's the Vibe ??")

if not df_filtered.empty:
    mood_counts = df_filtered["Mood"].value_counts().reset_index()
    mood_counts.columns = ["Mood", "Count"]
    fig = px.bar(mood_counts, x="Mood", y="Count", title=f"",
                 color="Mood", text="Count")
    fig.update_layout( yaxis=dict(showgrid=False),
                       xaxis=dict(showgrid=False), plot_bgcolor='rgba(0,0,0,0)', )

    #Capture click event on bar

    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        key="mood_chart"
    )

    if event and event.selection and event.selection.points:
        try:
            clicked_point = event.selection.points[0]
            clicked_mood = clicked_point['x']

            mood_df = df_filtered[df_filtered["Mood"] == clicked_mood]
            st.subheader(f"All Tickets for {clicked_mood}")

            if not mood_df.empty:
                st.dataframe(mood_df,use_container_width=True,hide_index=True, height=300) #Display tickets for selected bar

            else:
                st.warning("No data found for the selected combination.")

        except Exception as e:
            st.error(f"Error processing click event: {e}")
    else:
        st.info("Click on any bar in the chart above to see detailed data")


# Stacked Bar Chart
st.subheader("Daily Mood Distribution")

# Filter data for last 7 days
last_7_days = datetime.now().date() - timedelta(days=6)
df["Date"] = pd.to_datetime(df["Timestamp"]).dt.date
df_7d = df[df["Date"] >= last_7_days]

mood_counts = df_7d.groupby(["Date", "Mood"]).size().reset_index(name="Count")

if not mood_counts.empty:
    fig2 = px.bar(mood_counts, x="Date", y="Count", color="Mood", text="Count", title="Mood Distribution over last 7 Days", barmode="stack")
    fig2.update_layout(xaxis_title="Date", yaxis_title="Tickets", plot_bgcolor='rgba(0,0,0,0)')

    event2 = st.plotly_chart(
        fig2,
        use_container_width=True,
        on_select="rerun",
        key="date_chart"
    )

    if event2 and event2.selection and event2.selection.points:
        try:
            clicked_point2 = event2.selection.points[0]
            clicked_date2 = clicked_point2['x']
            clicked_color = clicked_point2['legendgroup']
            clicked_date = (datetime.strptime(clicked_date2, "%Y-%m-%d")).date()

            date_df = df_7d[(df_7d["Mood"] == clicked_color) & (df_7d["Date"] == clicked_date)]
            st.subheader(f"Detailed Data for {clicked_color} on {clicked_date}")

            if not date_df.empty:
                st.metric("Total Entries", len(date_df))
                st.dataframe(date_df[['Date','Ticket Number','Mood','Description']], use_container_width=True, hide_index=True,height=300)

            else:
                st.warning("No data found for the selected combination.")

        except Exception as e:
            st.error(f"Error processing click event: {e}")
    else:
        st.info("Click on any bar in the chart above to see detailed data")

