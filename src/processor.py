import pandas as pd
import logging
import os
from datetime import datetime
import re

# 1. Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# 2. Setup the log filename with today's date
log_filename = f"logs/{datetime.now().strftime('%Y-%m-%d')}_report.log"

# 3. Configure the logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
    logging.FileHandler(log_filename, encoding='utf-8'), # ADD encoding='utf-8' HERE
    logging.StreamHandler()
]
)

logger = logging.getLogger(__name__)

def validate_and_clean_data(df):
    """The main entry point for data quality checks."""
    logger.info("\n--- Starting Data Quality Checks ---")
    
    # Check for rows without titles
    df = check_for_null_titles(df)
    
    # Remove potential duplicates (Do this before prices to save API work)
    df = remove_duplicates(df)
    
    # Every row should have a price
    df = validate_prices(df)

    # Schema enforcement (The final check)
    df = enforce_schema(df)
    
    logger.info("--- Data Quality Checks Complete ---\n")
    return df

def check_for_null_titles(df):
    """Checks if any game titles are missing."""
    null_titles = df[df['game'].isnull() | (df['game'] == "")]
    if not null_titles.empty:
        logger.warning(f"❌ DATA QUALITY ERROR: {len(null_titles)} games are missing titles!")
        # We drop them because we can't search for prices without a name
        df = df.dropna(subset=['game'])
    else:
        logger.info("✅ Success: All games have titles.")
    return df

def validate_prices(df):
    """Checks for suspicious 0.0 or missing prices."""
    # Convert to numeric first to be safe
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Identify zeros or NaNs
    invalid_prices = df[(df['price'] == 0) | (df['price'].isna())]
    
    if not invalid_prices.empty:
        logger.warning(f"⚠️  PRICE WARNING: {len(invalid_prices)} games have a price of $0.0 or None.")
        logger.warning(f"Sample missing: {invalid_prices['game'].head(3).tolist()}")
    else:
        logger.info("✅ Success: All games have valid prices.")
    return df

def remove_duplicates(df):
    """
    Ensures each unique giveaway instance appears once.
    Allows the same game name on different dates.
    """
    initial_count = len(df)
    
    # NEW LOGIC: Use a list of columns for the subset.
    # A row is only a duplicate if BOTH 'game' AND 'start_date' match.
    df = df.drop_duplicates(subset=['game', 'start_date'], keep='first')
    
    current_count = len(df)
    if current_count < initial_count:
        logger.warning(f"🧹 CLEANUP: Removed {initial_count - current_count} duplicate rows.")
    else:
        logger.info("✅ Success: No duplicate giveaway instances found.")
    return df

def enforce_schema(df):
    """Ensures dates are logical and types are correct."""
    # 1. Logic Check: End date must be after start date
    # Convert to datetime objects for math
    start = pd.to_datetime(df['start_date'], dayfirst=True, errors='coerce')
    end = pd.to_datetime(df['end_date'], dayfirst=True, errors='coerce')
    
    invalid_dates = df[start > end]
    if not invalid_dates.empty:
        logger.warning(f"❌ LOGIC ERROR: {len(invalid_dates)} games end before they start!")
        
    # 2. Type Casting
    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    return df

def generate_summary_stats(df):
    """Calculates high-level metrics for the logs."""
    total_games = len(df)
    total_value = df['price'].sum()
    avg_price = df['price'].mean()
    
    # Identify the 'Crown Jewel' (Most expensive game)
    if not df.empty:
        most_expensive = df.loc[df['price'].idxmax()]
        jewel_name = most_expensive['game']
        jewel_price = most_expensive['price']
    else:
        jewel_name, jewel_price = "N/A", 0

    stats = (
        f"\n--- 📊 PORTFOLIO SUMMARY ---"
        f"\nTotal Games Collected: {total_games}"
        f"\nTotal Market Value: ${total_value:,.2f}"
        f"\nAverage Game Price: ${avg_price:,.2f}"
        f"\nMost Valuable Game: {jewel_name} (${jewel_price})"
        f"\n----------------------------"
    )
    return stats

def update_readme(stats_text):
    """Overwrites the stats section in README.md with live data."""
    readme_path = "README.md"
    
    if not os.path.exists(readme_path):
        logger.warning("README.md not found. Skipping update.")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the markers
    start_marker = '<a name="stats_start"></a>'
    end_marker = '<a name="stats_end"></a>'
    
    # This regex pattern finds everything between the markers
    pattern = f"{start_marker}.*?{end_marker}"
    new_section = f"{start_marker}\n{stats_text}\n{end_marker}"
    
    # Replace the old section with the new section (re.DOTALL handles newlines)
    updated_content = re.sub(pattern, new_section, content, flags=re.DOTALL)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
    
    logger.info("✅ README.md updated with live stats.")