import streamlit as st

st.title("About this app")
st.markdown(
    """
    **Purpose.** This multipage app demonstrates Streamlit's `pages/` convention.

    **Data.** The Pickup explorer page reads the public September 2014 Uber pickup dataset used in Streamlit's official tutorial.

    **Interaction.** Select a weekday to compare its hourly pickup pattern, then inspect a sample of the underlying records.
    """
)
