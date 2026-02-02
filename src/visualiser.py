import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import datetime
import matplotlib.dates as mdates
from processor import preprocess_for_plotting
from datetime import datetime

plt.rcParams['font.family'] = 'sans-serif'

STEAM_SALES = [
    ("2018-12-20", "2019-01-03"), ("2019-06-25", "2019-07-09"),
    ("2019-12-19", "2020-01-02"), ("2020-06-25", "2020-07-09"),
    ("2020-12-22", "2021-01-05"), ("2021-06-24", "2021-07-08"),
    ("2021-12-22", "2022-01-05"), ("2022-06-23", "2022-07-07"),
    ("2022-12-22", "2023-01-05"), ("2023-06-29", "2023-07-13"),
    ("2023-12-21", "2024-01-04"), ("2024-06-27", "2024-07-11"),
    ("2024-12-19", "2025-01-02"), ("2025-06-26", "2025-07-10"),
    ("2025-12-18", "2026-01-02"), ("2026-06-25", "2026-07-09"),
    ("2026-12-17", "2027-01-04")
]


def add_timestamp(fig):
    """Adds a standard 'Last Updated' timestamp to the bottom right of any figure."""
    timestamp = datetime.now().strftime("%d %b %Y, %H:%M")
    fig.text(0.99, 0.01, f"Updated: {timestamp} (2026)", 
             ha='right', va='bottom', fontsize=8, color='gray', fontstyle='italic')

def generate_savings_chart(df, output_path='assets/savings_chart.png'):
    """
    Creates a cumulative savings line chart with Epic branding and timestamp.
    """
    # 1. Self-Healing Logic: Handle both DataFrames and file paths
    if isinstance(df, str):
        df = pd.read_csv(df, encoding='utf-8-sig')

    # 2. Data Preparation
    df_plot = df.copy()
    df_plot['start_date'] = pd.to_datetime(df_plot['start_date'], dayfirst=True, errors='coerce')
    df_plot = df_plot.dropna(subset=['start_date']).sort_values('start_date')
    
    # Calculate Cumulative Savings
    df_plot['cumulative_value'] = df_plot['price'].cumsum()

    # 3. Setup Figure (Professional Object-Oriented Style)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 4. Plotting (Epic Blue Gradient)
    ax.plot(df_plot['start_date'], df_plot['cumulative_value'], 
            color='#0078f2', linewidth=3, label='Total Value')
    
    # Fill the area under the curve for a modern "Dashboard" look
    ax.fill_between(df_plot['start_date'], df_plot['cumulative_value'], 
                    color='#0078f2', alpha=0.2)

    # 5. Styling
    ax.set_title('Total Collection Value Over Time', fontsize=16, color='white', pad=25)
    ax.set_ylabel('Cumulative Value ($)', fontsize=12, color='white')
    ax.set_xlabel('Date Added', fontsize=12, color='white')
    
    # Clean up the grid to be subtle
    ax.grid(axis='both', linestyle='--', alpha=0.2)
    
    # Format the Y-axis with dollar signs (e.g., $2,000)
    import matplotlib.ticker as mtick
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))

    # 6. Add Consistent Timestamp
    add_timestamp(fig) # Works now because 'fig' is defined

    # 7. Save logic
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📈 Savings line chart saved to {output_path}")
def generate_monthly_bar_chart(df, output_path='assets/monthly_trends.png'):
    """
    Creates a bar chart of savings per month with consistent styling and timestamp.
    """
    # 1. Prepare Data
    # Filter out any NaT (Not a Time) rows to prevent grouping errors
    df_clean = df.dropna(subset=['start_date']).copy()
    df_clean['month_name'] = df_clean['start_date'].dt.month_name()
    
    monthly_stats = df_clean.groupby('month_name')['price'].sum().reindex([
        'January', 'February', 'March', 'April', 'May', 'June', 
        'July', 'August', 'September', 'October', 'November', 'December'
    ]).fillna(0) # Fill months with no giveaways with 0 instead of NaN

    # 2. Setup Figure (The "Professional" way)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6)) # Defines 'fig' so add_timestamp can see it
    
    # 3. Plotting
    # Using the consistent #0078f2 (Epic Blue) or #f39c12 (your choice!)
    bars = ax.bar(monthly_stats.index, monthly_stats.values, color='#0078f2', edgecolor='white')
    
    # 4. Styling
    ax.set_title('Total Savings Provided by Month', fontsize=16, color='white', pad=20)
    ax.set_ylabel('Total Value ($)', fontsize=12, color='white')
    plt.xticks(rotation=45, color='white')
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # 5. Add consistent elements
    add_timestamp(fig) 
    
    # 6. Save logic
    plt.tight_layout()
    if not os.path.exists('assets'): os.makedirs('assets')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"📈 Monthly trends chart saved to {output_path}")

def generate_generosity_chart(generosity_df):
    """
    Draws the Top 10 bar chart using the pre-calculated generosity data.
    """
    if generosity_df.empty:
        print("⚠️ No data available to generate Generosity Chart.")
        return

    # 2. DELETE the pd.read_csv line. We already have the data!

    # 3. Use the data passed from the processor
    # We take the top 10 and sort ascending for the horizontal bar layout
    top_10 = generosity_df.head(10).sort_values('generosity_score', ascending=True)

    plt.style.use('dark_background') 
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Draw the bars
    bars = ax.barh(top_10.index, top_10['generosity_score'], color='#0078f2', edgecolor='white')

    # Styling (Same as before)
    ax.set_title('Top 10 Most Generous Publishers (70/30 Index)', fontsize=14, color='white')
    ax.set_xlabel('Generosity Score (out of 100)', fontsize=12, color='white')
    ax.grid(axis='x', linestyle='--', alpha=0.3)

    # Add score labels to the end of bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}', va='center', color='white', fontweight='bold')
        

    add_timestamp(fig)
    plt.tight_layout()
    
    # Save
    if not os.path.exists('assets'): os.makedirs('assets')
    plt.savefig("assets/generosity_leaderboard.png", dpi=300)
    plt.close()


def generate_velocity_chart(df, output_path='assets/giveaway_velocity.png'):
    """
    Visualizes the annual budget Epic has spent on giveaways (2018-2026).
    Shows if the 'momentum' is increasing or decreasing.
    """
    # 1. Self-Healing & Data Prep
    if isinstance(df, str):
        df = pd.read_csv(df, encoding='utf-8-sig')
    
    df_plot = df.copy()
    df_plot['start_date'] = pd.to_datetime(df_plot['start_date'], dayfirst=True, errors='coerce')
    df_plot['year'] = df_plot['start_date'].dt.year
    
    # Group by year and sum the prices
    velocity = df_plot.groupby('year')['price'].sum().reset_index()
    
    # 2. Setup Figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 3. Plotting (Step Chart looks great for 'Budgets')
    # Using a step plot shows the 'budget level' for each year clearly
    ax.step(velocity['year'], velocity['price'], where='mid', 
            color='#0078f2', linewidth=4, marker='o', markersize=10)
    
    # 4. Styling
    ax.set_title('Epic Games Giveaway Velocity (Annual Budget Trend)', fontsize=16, color='white', pad=25)
    ax.set_ylabel('Total Annual Value ($)', fontsize=12, color='white')
    ax.set_xlabel('Year', fontsize=12, color='white')
    
    # Format Y-axis to $ (e.g., $1,500)
    import matplotlib.ticker as mtick
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    
    # Add Value Labels on each point
    for i, row in velocity.iterrows():
        ax.text(row['year'], row['price'] + 50, f"${row['price']:,.0f}", 
                ha='center', va='bottom', color='white', fontweight='bold')

    # 5. Consistency
    add_timestamp(fig)
    
    # 6. Save
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📈 Velocity chart saved to {output_path}")


def generate_inflation_comparison_chart(df, output_path='assets/inflation_impact.png'):
    """
    A side-by-side comparison of Nominal vs. Real value per year.
    """
    if isinstance(df, str):
        df = pd.read_csv(df, encoding='utf-8-sig')

    # 1. Prepare Data
    df_plot = df.copy()
    df_plot['start_date'] = pd.to_datetime(df_plot['start_date'], dayfirst=True, errors='coerce')
    df_plot['year'] = df_plot['start_date'].dt.year
    
    # Group by year for both price and real_value
    yearly_data = df_plot.groupby('year')[['price', 'real_value']].sum()

    # 2. Setup Figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 3. Plotting Side-by-Side Bars
    x = yearly_data.index
    width = 0.35  # Width of the bars
    
    ax.bar(x - width/2, yearly_data['price'], width, label='Nominal Value (Sticker Price)', color='gray', alpha=0.7)
    ax.bar(x + width/2, yearly_data['real_value'], width, label='Real Value (2026 Dollars)', color='#0078f2')

    ax.set_xticks(x) # Forces a tick for every year in the index
    ax.set_xticklabels(x.astype(int))
    
    # 4. Styling
    ax.set_title('The Inflation Story: Nominal vs. Real Purchasing Power', fontsize=16, color='white', pad=25)
    ax.set_ylabel('Total Value ($)', fontsize=12, color='white')
    
    import matplotlib.ticker as mtick
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    ax.legend()
    
    # 5. Consistency
    add_timestamp(fig)
    
    # 6. Save
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📈 Inflation comparison chart saved to {output_path}")


def generate_market_timing_chart(df, output_path='assets/steam_shadow_analysis.png'):
    """
    Overlays Epic giveaway values against Steam seasonal sales.
    Two-level X-axis: Years (Bold) and Quarterly Months.
    """
    if isinstance(df, str):
        df = pd.read_csv(df, encoding='utf-8-sig')

    # 1. Prepare Data
    df_plot = df.copy()
    df_plot['start_date'] = pd.to_datetime(df_plot['start_date'], dayfirst=True, errors='coerce')
    df_plot = df_plot.dropna(subset=['start_date'])
    
    # Weekly resample for 'pulse' effect
    weekly_val = df_plot.set_index('start_date').resample('W')['price'].sum().reset_index()

    # 2. Setup Figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(16, 8)) # Slightly wider for better label spacing
    
    # 3. Plot Epic's Giveaway Pulse
    ax.plot(weekly_val['start_date'], weekly_val['price'], 
            color='#0078f2', linewidth=2, label='Epic Weekly Giveaway Value', alpha=0.9, zorder=3)
    
    # --- 🕒 FIXED DATE FORMATTING ---
    # Major Ticks: Years (2024, 2025...)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    # Minor Ticks: Months (every 3 months: Jan, Apr, Jul, Oct)
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%b'))
    
    # PUSH labels to different levels so they don't overlap
    # Major (Year) is bold and lower
    ax.tick_params(axis='x', which='major', pad=25, labelsize=12, colors='white')
    ax.tick_params(axis='x', which='minor', pad=5, labelsize=9, colors='gray')
    
    for label in ax.get_xticklabels(which='major'):
        label.set_fontweight('bold')
    # ---------------------------------

    # 4. Shade the Steam Sales
    first_label = True
    for start, end in STEAM_SALES:
        ax.axvspan(pd.to_datetime(start), pd.to_datetime(end), 
                   color='gray', alpha=0.25, label='Steam Seasonal Sale' if first_label else "", zorder=1)
        first_label = False

    # 5. Styling
    ax.set_title('Market Timing: Epic Giveaways vs. Steam Seasonal Sales', fontsize=18, pad=35)
    ax.set_ylabel('Weekly Retail Value ($)', fontsize=12)
    
    # Create a cleaner legend
    ax.legend(loc='upper left', frameon=True, facecolor='#111111', edgecolor='white', fontsize=10)
    
    # Grid Logic: Solid lines for Years, dotted for Quarters
    ax.grid(which='major', axis='x', linestyle='-', alpha=0.3)
    ax.grid(which='minor', axis='x', linestyle=':', alpha=0.1)
    ax.grid(axis='y', linestyle='--', alpha=0.2)

    # Format Y-axis to $
    import matplotlib.ticker as mtick
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    
    # 6. Consistency
    add_timestamp(fig)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"📈 Market timing chart saved to {output_path}")


def generate_maturity_histogram(df, output_path='assets/maturity_gap_dist.png'):
    """
    Visualizes how many years publishers wait before a game goes free.
    """
    if isinstance(df, str):
        df = pd.read_csv(df, encoding='utf-8-sig')

    # 1. Calculate the Gap (Years)
    df_plot = df.copy()
    df_plot['start_date'] = pd.to_datetime(
    df_plot['start_date'], 
    dayfirst=True, 
    format='mixed', 
    errors='coerce'
)
    df_plot['release_date'] = pd.to_datetime(
    df_plot['original_release_date'], 
    format='mixed', 
    errors='coerce'
)
    
    # Drop rows without release dates
    df_plot = df_plot.dropna(subset=['release_date', 'start_date'])
    
    # Calculate gap in years
    df_plot['maturity_gap_years'] = (df_plot['start_date'] - df_plot['release_date']).dt.days / 365.25

    # 2. Setup Figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 3. Plot Histogram
    # We use 1-year bins to see the distribution clearly
    n, bins, patches = ax.hist(df_plot['maturity_gap_years'], bins=range(0, 16), 
                               color='#0078f2', edgecolor='white', alpha=0.7)

    # 4. Styling
    ax.set_title('The Maturity Gap: How "Old" are Epic Freebies?', fontsize=16, pad=20)
    ax.set_xlabel('Years from Original Release to Giveaway', fontsize=12)
    ax.set_ylabel('Number of Games', fontsize=12)
    
    # Force X-axis to show every year
    ax.set_xticks(range(0, 16))
    
    # Add a vertical line for the Average
    avg_gap = df_plot['maturity_gap_years'].mean()
    ax.axvline(avg_gap, color='#f39c12', linestyle='--', linewidth=2, label=f'Average: {avg_gap:.1f} Yrs')
    ax.legend()

    # 5. Consistency
    add_timestamp(fig)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()