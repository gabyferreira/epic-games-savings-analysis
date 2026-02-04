import pandas as pd

def apply_inflation_adjustment(df):
    """Adjusts historical prices to 2026 dollars."""
    # Approximate CPI multipliers to bring past years to 2026 value
    # (Source: Historical CPI trends)
    multipliers = {
        2018: 1.32, 2019: 1.29, 2020: 1.27, 2021: 1.22,
        2022: 1.12, 2023: 1.08, 2024: 1.04, 2025: 1.01, 2026: 1.00
    }
    
    # Extract year from the start_date
    df['year'] = pd.to_datetime(df['start_date'], dayfirst=True).dt.year
    
    # Calculate Adjusted Price: Price * Multiplier
    df['real_value'] = df.apply(
        lambda row: row['price'] * multipliers.get(row['year'], 1.0), axis=1
    )
    
    return df

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