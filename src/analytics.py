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