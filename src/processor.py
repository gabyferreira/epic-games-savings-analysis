import pandas as pd
import logging
import os
from datetime import datetime
import re
from constants import INFLATION_MULTIPLIERS, SHARED_UNIVERSES, AUTO_PROMO_KEYWORDS

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

    df = calculate_hype_delta(df)
    df = tag_hype_candidates(df)
    
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
    # Standardize Publisher names
    df['publisher'] = df['publisher'].replace("Publisher Not Found", "Unknown Publisher")
    df['publisher'] = df['publisher'].fillna("Unknown Publisher").astype(str).str.strip().str.title()
    
    # Vectorized Date Conversion
    df['start_date'] = pd.to_datetime(df['start_date'], dayfirst=True, errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], dayfirst=True, errors='coerce')
    
    # Extract Year (Handles NaT by defaulting to 2026 for multipliers)
    df['year'] = df['start_date'].dt.year.fillna(2026).astype(int)
    
    # Vectorized Inflation Math
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
    df['real_value'] = df['price'] * df['year'].map(INFLATION_MULTIPLIERS).fillna(1.0)
    
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
    total_value = df.drop_duplicates(subset=['game'], keep='first')['price'].sum()
    avg_price = df['price'].mean()
    real_total = df.drop_duplicates(subset=['game'], keep='first')['real_value'].sum()
    inflation_impact = real_total - total_value
    
    # Most Expensive Title
    if not df.empty and total_value > 0:
        most_expensive = df.loc[df['price'].idxmax()]
        jewel_name, jewel_price = most_expensive['game'], most_expensive['price']
    else:
        jewel_name, jewel_price = "N/A", 0

    # Top Publishers
    top_publishers = df.groupby('publisher')['price'].sum().nlargest(3)
    publisher_stats = ", ".join([f"{name} (${val:,.2f})" for name, val in top_publishers.items()])

    if 'is_strategic_hype' in df.columns:
        strategic_count = df['is_strategic_hype'].sum()
        prestige_ratio = (strategic_count / total_games) * 100 if total_games > 0 else 0
        avg_lead = df['hype_delta_days'].mean() if 'hype_delta_days' in df.columns else 0
    else:
        prestige_ratio = 0
        avg_lead = 0

    # Seasonality, Quality, and Subscription Stats
    seasonality = analyze_seasonality(df)
    q_stats = get_quality_stats(df)
    sub_stats = calculate_subscription_value(df)
    
    # Hype Metrics
    strategic_count = df['is_strategic_hype'].sum()
    prestige_ratio = (strategic_count / total_games) * 100 if total_games > 0 else 0
    avg_lead_time = df['hype_delta_days'].mean()

    stats = (
        "| Metric | Statistics |\n"
        "| :--- | :--- |\n"
        f"| 💰 **Total Market Value** | **${total_value:,.2f}** |\n"
        f"| 📦 **Total Games Collected** | {total_games} |\n"
        f"| 👑 **MVP Publisher** | {df['publisher'].mode()[0] if not df.empty else 'N/A'} |\n"
        f"| 📈 **Inflation-Adjusted Value** | ${real_total:,.2f} |\n"
        f"| 🗓️ **Peak Saving Month** | {seasonality} |\n"
        f"| ⭐ **Average Score** | {q_stats['avg_rating']:.1f}/100 |\n"
        f"| 💳 **Subscription Equivalent** | **${sub_stats['monthly_val']:,.2f} / mo** |\n"
        f"| 🎯 **Prestige Ratio** | **{prestige_ratio:.1f}%** (Strategic Hype) |\n"
        f"| 🏎️ **Lead Time Avg** | {avg_lead_time:.0f} Days to Sequel |\n"
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
    pub_stats.columns = ['game_count', 'total_value', 'avg_unit_cost']

    # 3. NORMALIZE & SCORE: The 70/30 Logic
    max_total = pub_stats['total_value'].max()
    max_quality = pub_stats['avg_unit_cost'].max()

    # Apply the weights (0.7 and 0.3)
    pub_stats['generosity_score'] = (
        (pub_stats['total_value'] / max_total * value_score) + 
        (pub_stats['avg_unit_cost'] / max_quality * quality_score)
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
    Standardizes data types, removes unplottable rows, and 
    applies inflation multipliers for 'Real Value' analysis.
    """
    df_clean = df.copy()

    # 1. Force Numeric (Price)
    df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
    
    # 2. Force Numeric (Ratings) - Handles "Score Not Found"
    df_clean['aggregated_rating'] = pd.to_numeric(df_clean['aggregated_rating'], errors='coerce')
    

    # 4. Force Dates
    df_clean['start_date'] = pd.to_datetime(df_clean['start_date'], dayfirst=True, format='mixed', errors='coerce')
    
    # 5. Drop rows with missing critical data
    df_clean = df_clean.dropna(subset=['price', 'start_date'])

    # 6. Extract Year for Inflation Mapping
    df_clean['year'] = df_clean['start_date'].dt.year.astype(int)

    # 7. Apply Inflation Multipliers (Real Value 2026)
    df_clean['real_value'] = df_clean.apply(
        lambda row: row['price'] * INFLATION_MULTIPLIERS.get(row['year'], 1.0), 
        axis=1
    )

    df_clean = calculate_hype_delta(df_clean)
    df_clean = tag_hype_candidates(df_clean)
    


    # 8. Final Type Casting
    df_clean['price'] = df_clean['price'].astype(float)
    df_clean['real_value'] = df_clean['real_value'].astype(float)
    df_clean['aggregated_rating'] = df_clean['aggregated_rating'].astype(float)
    df_clean['month'] = df_clean['start_date'].dt.month_name()
    df_clean['year'] = df_clean['start_date'].dt.year
    
    return df_clean

def get_quality_stats(df):
    """
    Analyzes the aggregated_rating column to return average and top-tier metrics.
    Returns a dictionary of stats to be used in the README table.
    """
    # 1. Ensure numeric conversion (Coerce "Score Not Found" to NaN)
    # We work on a copy to avoid SettingWithCopy warnings
    temp_df = df.copy()
    temp_df['aggregated_rating'] = pd.to_numeric(temp_df['aggregated_rating'], errors='coerce')
    
    # 2. Filter for rows that actually have a numeric score
    df_ratings = temp_df.dropna(subset=['aggregated_rating'])

    # 3. Handle the 'Empty' case (e.g., first run or API failure)
    if df_ratings.empty:
        return {
            "avg_rating": 0.0,
            "max_rating": 0.0,
            "best_game_name": "N/A"
        }

    # 4. Calculate Metrics
    avg_rating = df_ratings['aggregated_rating'].mean()
    max_rating = df_ratings['aggregated_rating'].max()
    
    # 5. Find the name of the highest rated game
    # .idxmax() finds the index of the highest score
    best_game_row = df_ratings.loc[df_ratings['aggregated_rating'].idxmax()]
    best_game_name = best_game_row['game']

    return {
        "avg_rating": avg_rating,
        "max_rating": max_rating,
        "best_game_name": best_game_name
    }

def calculate_subscription_value(df):
    """
    Calculates the 'Monthly Subscription' value Epic provides.
    """
    df_clean = df.copy()
    df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce').fillna(0)
    df_clean['start_date'] = pd.to_datetime(df_clean['start_date'], dayfirst=True, errors='coerce')
    df_clean = df_clean.dropna(subset=['start_date'])

    # 1. Calculate the timespan in months
    start_date = df_clean['start_date'].min()
    end_date = df_clean['start_date'].max()
    
    # Total months = (Years * 12) + Months
    delta_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if delta_months == 0: delta_months = 1 # Avoid division by zero

    # 2. Calculate average monthly retail value
    total_nominal = df_clean['price'].sum()
    monthly_subscription_val = total_nominal / delta_months

    return {
        "monthly_val": monthly_subscription_val,
        "total_months": delta_months,
        "first_date": start_date.strftime('%B %Y')
    }

def calculate_hype_delta(df):
    """Calculates Lead Time between giveaway and franchise sequel."""
    # Ensure date objects
    start_dates = pd.to_datetime(df['start_date'], errors='coerce')
    
    # Robust Sequel Date Parsing (defending against Wikidata malformed strings)
    sequel_dates = pd.to_datetime(df['next_sequel_date'], errors='coerce')
    
    # Calculate Days Delta
    df['hype_delta_days'] = (sequel_dates - start_dates).dt.days
    
    return df

def tag_hype_candidates(df):
    """Tags 'Strategic Hype' based on the strict 0-90 day window."""
    df_clean = df.copy()
    
    if 'hype_delta_days' not in df_clean.columns:
        df_clean['hype_delta_days'] = pd.NA

    df_clean['hype_delta_days'] = pd.to_numeric(df_clean['hype_delta_days'], errors='coerce')
    
    # ✅ Sync with scraper: 0 to 90 days
    df_clean['is_strategic_hype'] = (df_clean['hype_delta_days'] >= 0) & (df_clean['hype_delta_days'] <= 90)
    
    # Fill NaN with False (Standardizes Scenario 3: No Sequel)
    df_clean['is_strategic_hype'] = df_clean['is_strategic_hype'].fillna(False)
    
    return df_clean

def identify_franchise(game_title, igdb_collection_name=None):
    """
    Determines if a game belongs to a franchise using a tiered approach.
    """
    # 1. Check Manual Overrides
    if game_title in SHARED_UNIVERSES:
        return SHARED_UNIVERSES[game_title]
    
    # 2. Check Keyword Matches
    for word in AUTO_PROMO_KEYWORDS:
        if word.lower() in game_title.lower():
            return word

    # 3. Fallback to API data
    return igdb_collection_name or "Standalone"

def get_hype_cycle_stats(df):
    """
    Compares Standard giveaways vs. Strategic Franchise Promotions.
    """
    df_clean = df.copy()
    df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce').fillna(0)
    
    # 1. Split the data
    promo_games = df_clean[df_clean['is_strategic_hype'] == True]
    standard_games = df_clean[df_clean['is_strategic_hype'] == False]
    
    # 2. Calculate Averages
    avg_promo_price = promo_games['price'].mean() if not promo_games.empty else 0
    avg_std_price = standard_games['price'].mean() if not standard_games.empty else 0
    
    return {
        "avg_promo_price": avg_promo_price,
        "avg_std_price": avg_std_price,
        "promo_count": len(promo_games)
    }