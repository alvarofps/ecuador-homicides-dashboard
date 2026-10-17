import streamlit as st

st.set_page_config(page_title="Ecuador Homicidios", layout="wide")

pages = st.navigation([
    st.Page("app_monthly.py", title="Mes a mes / Monthly", icon=":material/bar_chart:"),
    st.Page("app_rates.py", title="Tasas / Rates", icon=":material/trending_up:"),
    st.Page("app_sex_age.py", title="Sexo y edad / Sex & Age", icon=":material/group:"),
])
pages.run()
