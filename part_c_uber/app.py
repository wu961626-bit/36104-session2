import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Uber pickups explorer", page_icon="🚕", layout="wide")
st.title("Uber pickups in New York City")
st.caption("Interactive exploration of September 2014 Uber pickups, following the Streamlit tutorial pattern.")

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

st.sidebar.header("Filters")
hour = st.sidebar.slider("Hour of day", 0, 23, 17)
show_map = st.sidebar.checkbox("Show pickup map", value=True)

hourly = data[data["date/time"].dt.hour == hour]
left, right = st.columns((1, 1))
with left:
    st.subheader(f"Pickups at {hour:02d}:00")
    st.metric("Pickups", f"{len(hourly):,}")
    st.dataframe(hourly.head(100), use_container_width=True, hide_index=True)
with right:
    st.subheader("Pickups by hour")
    counts = data.assign(hour=data["date/time"].dt.hour).groupby("hour").size().reset_index(name="pickups")
    st.altair_chart(
        alt.Chart(counts).mark_bar(color="#f4a261").encode(
            x=alt.X("hour:O", title="Hour"),
            y=alt.Y("pickups:Q", title="Pickups"),
            tooltip=["hour:O", "pickups:Q"],
        ).properties(height=320),
        use_container_width=True,
    )

if show_map:
    st.subheader(f"Map of pickups at {hour:02d}:00")
    st.map(hourly.rename(columns={"lat": "latitude", "lon": "longitude"})[["latitude", "longitude"]])
