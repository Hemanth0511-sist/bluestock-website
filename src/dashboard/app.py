import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Main title
st.title("📊 Nifty 100 Analytics")

st.write("Welcome to the N100 Financial Intelligence Platform.")

st.markdown("---")

st.subheader("Dashboard")

st.info("Use the sidebar to select a dashboard screen.")
