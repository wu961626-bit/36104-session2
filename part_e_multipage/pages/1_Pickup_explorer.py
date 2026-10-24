import altair as alt
import pandas as pd
import streamlit as st

st.title("Pickup explorer")
st.caption("An interactive page for comparing hourly patterns in the Uber September 2014 dataset.")

DATA_URL = "https://s3-us-west-2.amazonaws.com/streamlit-demo-data/uber-raw-data-sep14.csv.gz"


@st.cache_data(show_spinner="Loading pickup data…")
def load_data() -> pd.DataFrame:
    data = pd.read_csv(DATA_URL)
    data.columns = [column.lower().strip() for column in data.columns]
    data["date/time"] = pd.to_datetime(data["date/time"])
    return data


try:
    data = load_data()
except Exception as exc:
    st.error("The pickup dataset could not be loaded. Please refresh and try again.")
    st.exception(exc)
    st.stop()

selected_day = st.selectbox("Day of week", list(range(7)), format_func=lambda day: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day])
filtered = data[data["date/time"].dt.dayofweek == selected_day].copy()
counts = filtered.assign(hour=filtered["date/time"].dt.hour).groupby("hour").size().reset_index(name="pickups")

st.altair_chart(
    alt.Chart(counts).mark_line(point=True, color="#457b9d").encode(
        x=alt.X("hour:Q", title="Hour of day", scale=alt.Scale(domain=[0, 23])),
        y=alt.Y("pickups:Q", title="Pickups"),
        tooltip=["hour:Q", "pickups:Q"],
    ).properties(height=370),
    use_container_width=True,
)

st.subheader("Sample of filtered pickups")
st.dataframe(filtered.head(200), use_container_width=True, hide_index=True)
