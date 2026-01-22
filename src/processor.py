import pandas as pd

def validate_and_clean_data(df):
    """The main entry point for data quality checks."""
    print("\n--- Starting Data Quality Checks ---")
    
    # Run Step 1
    df = check_for_null_titles(df)
    
    # Run Step 3 (Do this before prices to save API work)
    df = remove_duplicates(df)
    
    # Run Step 2
    df = validate_prices(df)
    
    print("--- Data Quality Checks Complete ---\n")
    return df

def check_for_null_titles(df):
    """Checks if any game titles are missing."""
    null_titles = df[df['game'].isnull() | (df['game'] == "")]
    if not null_titles.empty:
        print(f"❌ DATA QUALITY ERROR: {len(null_titles)} games are missing titles!")
        # We drop them because we can't search for prices without a name
        df = df.dropna(subset=['game'])
    else:
        print("✅ Success: All games have titles.")
    return df

def validate_prices(df):
    """Checks for suspicious 0.0 or missing prices."""
    # Convert to numeric first to be safe
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Identify zeros or NaNs
    invalid_prices = df[(df['price'] == 0) | (df['price'].isna())]
    
    if not invalid_prices.empty:
        print(f"⚠️  PRICE WARNING: {len(invalid_prices)} games have a price of $0.0 or None.")
        print(f"Sample missing: {invalid_prices['game'].head(3).tolist()}")
    else:
        print("✅ Success: All games have valid prices.")
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
        print(f"🧹 CLEANUP: Removed {initial_count - current_count} actual duplicate rows.")
    else:
        print("✅ Success: No duplicate giveaway instances found.")
    return df