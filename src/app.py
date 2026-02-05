import streamlit as st
import pandas as pd
from processor import validate_and_clean_data

st.set_page_config(page_title="Epic Savings Tracker", layout="wide")

# 1. Load Data
@st.cache_data
def load_data():
    df = pd.read_csv("data/epic_games_data_edited_active8.csv")
    return validate_and_clean_data(df)

df = load_data()

st.title("🎮 Epic Games Store: Personal Savings Calculator")

# 2. Interactive Sidebar
st.sidebar.header("Your Epic History")
user_date = st.sidebar.date_input("When did you create your account?", 
                                 value=pd.to_datetime("2020-01-01"))

# 3. Filter & Calculate
user_df = df[df['start_date'] >= pd.to_datetime(user_date)]
total_saved = user_df['price'].sum()
game_count = len(user_df)

# 4. Display Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Savings", f"${total_saved:,.2f}")
col2.metric("Games Missed", f"{len(df) - game_count}")
col3.metric("Average Game Quality", f"{user_df['aggregated_rating'].mean():.1f}/100")

# 5. Display the Plot
st.write("### Your Potential Library Growth")
st.area_chart(user_df.set_index('start_date')['price'].cumsum())