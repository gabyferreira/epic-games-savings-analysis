import pandas as pd
import logging
import os
from datetime import datetime
import re

# --- Setup Logging ---
if not os.path.exists('logs'):
    os.makedirs('logs')

log_filename = f"logs/{datetime.now().strftime('%Y-%m-%d')}_report.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_and_clean_data(df):
    """The main entry point for data quality checks. Order matters here!"""
    logger.info("\n--- Starting Data Quality Checks ---")
    
    # 1. Drop ghost columns immediately (Unnamed: 0, etc.)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 2. Basic Quality Gatekeepers
    df = check_for_null_titles(df)
    df = remove_duplicates(df)
    
    # 3. Data Formatting & Inflation (Crucial: Calculates year/real_value)
    df = clean_metadata_and_inflation(df)
    
    # 4. Final Type Enforcement
    df = enforce_schema(df)
    
    logger.info("--- Data Quality Checks Complete ---\n")
    return df

def check_for_null_titles(df):
    """Drops games without names; warns about missing publishers."""
    null_titles = df[df['game'].isna() | (df['game'].str.strip() == "")]
    if not null_titles.empty:
        logger.warning(f"❌ DATA QUALITY ERROR: {len(null_titles)} games missing titles! Dropping.")
        df = df.dropna(subset=['game'])
    return df

def remove_duplicates(df):
    """Ensures giveaway instances (Game + Start Date) are unique."""
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game', 'start_date'], keep='first')
    current_count = len(df)
    if current_count < initial_count:
        logger.warning(f"🧹 CLEANUP: Removed {initial_count - current_count} duplicates.")
    return df

def clean_metadata_and_inflation(df):
    """Cleans seller strings and calculates inflation-adjusted values."""
    # 1. Clean Publisher names
    df['publisher'] = df['publisher'].replace("Publisher Not Found", "Unknown Publisher")
    df['publisher'] = df['publisher'].fillna("Unknown Publisher").astype(str).str.strip().str.title()
    
    # 2. Fix Dates (European format DD/MM/YYYY)
    df['start_date'] = pd.to_datetime(df['start_date'], dayfirst=True, errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], dayfirst=True, errors='coerce')
    
    # 3. Build/Repair the Year column
    df['year'] = df['start_date'].dt.year.fillna(0).astype(int)
    
    # 4. Inflation Math
    multipliers = {
        2018: 1.32, 2019: 1.29, 2020: 1.27, 2021: 1.22,
        2022: 1.12, 2023: 1.08, 2024: 1.04, 2025: 1.01, 2026: 1.00
    }
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
    df['real_value'] = df.apply(
        lambda row: row['price'] * multipliers.get(row['year'], 1.0), axis=1
    )
    return df

def enforce_schema(df):
    """Ensures IDs are present and data types are locked for CSV safety."""
    # Handle ID creation if missing
    if 'id' not in df.columns:
        logger.info("Adding missing ID column.")
        df['id'] = range(1, len(df) + 1)
    
    # Force column types to prevent 'disappearing data' on next load
    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    df['price'] = df['price'].astype(float)
    df['real_value'] = df['real_value'].astype(float)
    
    # Logic check for dates
    invalid_dates = df[df['start_date'] > df['end_date']]
    if not invalid_dates.empty:
        logger.warning(f"❌ LOGIC ERROR: {len(invalid_dates)} games end before they start!")
        
    return df

def generate_summary_stats(df, generosity_df):
    """Builds the Markdown dashboard table."""
    total_games = len(df)
    total_value = df['price'].sum()
    avg_price = df['price'].mean()
    real_total = df['real_value'].sum()
    inflation_impact = real_total - total_value
    
    if not df.empty and total_value > 0:
        most_expensive = df.loc[df['price'].idxmax()]
        jewel_name = most_expensive['game']
        jewel_price = most_expensive['price']
    else:
        jewel_name, jewel_price = "N/A", 0

    top_publishers = df.groupby('publisher')['price'].sum().nlargest(3)
    publisher_stats = ", ".join([f"{name} (${val:,.2f})" for name, val in top_publishers.items()])

    if not df.empty:
        counts = df['publisher'].value_counts()
        mvp_name = counts.idxmax()
        mvp_count = counts.max()
        mvp_display = f"{mvp_name} ({mvp_count} games)"
    else:
        mvp_display = "N/A"

    seasonality_insight = analyze_seasonality(df)

    gen_stats = calculate_generosity_index(df)
    top_gen = gen_stats.head(3)

    gen_display = ", ".join([
        f"{name} (Score: {row['generosity_score']:.1f})" 
        for name, row in top_gen.iterrows()
        ])

    stats = (
        "| Metric | Statistics |\n"
        "| :--- | :--- |\n"
        f"| 💰 **Total Market Value** | **${total_value:,.2f}** |\n"
        f"| 📦 **Total Games Collected** | {total_games} |\n"
        f"| 📉 **Average Game Price** | ${avg_price:,.2f} |\n"
        f"| 🏆 **Most Valuable Game** | {jewel_name} (${jewel_price:,.2f}) |\n"
        f"| 🏢 **Top 3 Contributors** | {publisher_stats} |\n"
        f"| 👑 **MVP Publisher** | {mvp_display} |\n"
        f"| 📈 **Inflation-Adjusted Value** | ${real_total:,.2f} |\n"
        f"| 💸 **Purchasing Power Gained** | ${inflation_impact:,.2f} |\n"
        f"| 🗓️ **Peak Saving Month** | {seasonality_insight} |\n"
        f"| 🏆 **Generosity Leaderboard** | {gen_display} |\n"
    )
    return stats

def update_readme(stats_text):
    """Injects the table into README.md using specific markers."""
    readme_path = "README.md"
    if not os.path.exists(readme_path): return

    with open(readme_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    start_marker = '<a name="stats_start"></a>'
    end_marker = '<a name="stats_end"></a>'
    
    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    new_section = f"{start_marker}\n{stats_text}\n{end_marker}"
    
    if start_marker not in content or end_marker not in content:
        logger.error("❌ Stats markers not found in README.md!")
        return

    updated_content = re.sub(pattern, new_section, content, flags=re.DOTALL)

    with open(readme_path, "w", encoding="utf-8-sig") as f:
        f.write(updated_content)
    logger.info("✅ README.md updated.")

def analyze_seasonality(df):
    """Calculates which month historically provides the most value."""
    # Ensure date is correct
    df['start_date'] = pd.to_datetime(df['start_date'], dayfirst=True)
    
    # Group by month and sum the price
    monthly_trends = df.groupby(df['start_date'].dt.strftime('%B'))['price'].sum()
    
    # Sort by value to find the 'Saving King'
    top_month = monthly_trends.idxmax()
    top_value = monthly_trends.max()
    
    return f"🎄 **Seasonality Peak:** {top_month} is historically the best month, offering ${top_value:,.2f} in savings."

def calculate_generosity_index(df):
    """
    Ranks publishers by a 'Generosity Score'.
    Single Source of Truth for both README stats and Visualiser charts.
    """
    # 1. CLEANUP: Filter out 'Unknown' and ensure we use the 'seller' column
    # We also check if the dataframe is empty to prevent crashes
    value_score = 70
    quality_score = 30
    df_filtered = df[df['publisher'] != "Unknown Publisher"].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    # 2. AGGREGATE: Group by Seller
    # We use 'price' for both total and mean to keep the index consistent
    pub_stats = df_filtered.groupby('publisher').agg({
        'game': 'count',
        'price': ['sum', 'mean']
    })
    
    # Flatten the multi-index columns created by .agg
    pub_stats.columns = ['game_count', 'total_value', 'avg_quality']

    # 3. NORMALIZE & SCORE: The 70/30 Logic
    max_total = pub_stats['total_value'].max()
    max_quality = pub_stats['avg_quality'].max()

    # Apply the weights (0.7 and 0.3)
    pub_stats['generosity_score'] = (
        (pub_stats['total_value'] / max_total * value_score) + 
        (pub_stats['avg_quality'] / max_quality * quality_score)
    )

    # 4. RETURN: Sorted by the new index
    return pub_stats.sort_values(by='generosity_score', ascending=False)


def calculate_inflation_story(df):
    """
    Calculates the gap between 'Nominal' (Face Value) and 'Real' (2026 Purchasing Power).
    """
    # Sum up the two columns we created in clean_metadata_and_inflation
    nominal_total = df['price'].sum()
    real_total = df['real_value'].sum()
    
    # Calculate the 'Bonus' value created by inflation
    inflation_bonus = real_total - nominal_total
    
    # Calculate the percentage increase
    pct_increase = (inflation_bonus / nominal_total) * 100 if nominal_total > 0 else 0
    
    return {
        "nominal": nominal_total,
        "real": real_total,
        "bonus": inflation_bonus,
        "percentage": pct_increase
    }


def preprocess_for_plotting(df):
    """
    Agresively standardizes data types and removes unplottable rows.
    """
    df_clean = df.copy()

    # 1. Force Numeric
    # 'coerce' turns trash strings into NaN, then we drop them
    df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
    
    # 2. Force Dates
    df_clean['start_date'] = pd.to_datetime(df_clean['start_date'], dayfirst=True, format='mixed', errors='coerce')
    
    # 3. THE CRITICAL STEP: Drop rows that failed conversion
    # Matplotlib warns when it sees NaN or Strings where numbers should be.
    df_clean = df_clean.dropna(subset=['price', 'start_date'])

    # 4. Final cast to ensure they aren't "Objects"
    df_clean['price'] = df_clean['price'].astype(float)
    
    return df_clean