import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import datetime
import matplotlib.dates as mdates
from processor import preprocess_for_plotting, tag_hype_candidates, get_hype_cycle_stats
from datetime import datetime
from constants import STEAM_SALES
import numpy as np
import logging

logger = logging.getLogger(__name__)



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


    
    df_plot = df_plot.drop_duplicates(subset=['game'], keep='first')
    
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
    A side-by-side comparison of Nominal vs. Real value per year using centralized preprocessing.
    """
    # 1. Standardize and Clean using your existing helper
    df_plot = preprocess_for_plotting(df)
    
    # 2. Group by year
    # Since preprocess_for_plotting already created 'year', 'price', and 'real_value'
    yearly_data = df_plot.groupby('year')[['price', 'real_value']].sum()

    # 3. Setup Figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 4. Plotting Side-by-Side Bars
    x = yearly_data.index
    width = 0.35 
    
    # Using the Epic Games Blue (#0078f2) for Real Value looks very professional
    ax.bar(x - width/2, yearly_data['price'], width, label='Nominal Value (Sticker Price)', color='#444444', alpha=0.8)
    ax.bar(x + width/2, yearly_data['real_value'], width, label='Real Value (2026 Dollars)', color='#0078f2')

    # Ensure every year is labeled on the X-axis
    ax.set_xticks(x)
    ax.set_xticklabels(x.astype(int))
    
    # 5. Styling & Formatting
    ax.set_title('The Inflation Story: Nominal vs. Real Purchasing Power', fontsize=16, color='white', pad=25)
    ax.set_ylabel('Total Value ($)', fontsize=12, color='white')
    
    # Currency formatting ($1,000)
    import matplotlib.ticker as mtick
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
    
    ax.legend(frameon=False, loc='upper left')
    ax.grid(axis='y', linestyle='--', alpha=0.2)
    
    # 6. Global Branding & Save
    add_timestamp(fig)
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

def generate_inflation_comparison_chart(df, output_path='assets/inflation_comparison.png'):
    df_plot = preprocess_for_plotting(df).sort_values('start_date')
    
    # Calculate Cumulative Totals
    df_plot['cumulative_nominal'] = df_plot['price'].cumsum()
    df_plot['cumulative_real'] = df_plot['real_value'].cumsum()

    plt.figure(figsize=(12, 6))
    
    # Plot both lines
    plt.fill_between(df_plot['start_date'], df_plot['cumulative_real'], color="skyblue", alpha=0.3, label='Inflation Gap (Purchasing Power)')
    plt.plot(df_plot['start_date'], df_plot['cumulative_real'], label='Real Value (2026 $)', color='#1f77b4', linewidth=2)
    plt.plot(df_plot['start_date'], df_plot['cumulative_nominal'], label='Nominal Value (Retail at Time)', color='#ff7f0e', linestyle='--')

    plt.title("The 'Real' Value of the Epic Collection (Inflation Adjusted)", fontsize=14, pad=20)
    plt.ylabel("Total Collection Value ($)")
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()

def generate_quality_pulse_chart(df, output_path='assets/quality_pulse.png'):
    # Preprocess first
    df_plot = preprocess_for_plotting(df)
    
    # 1. Filter out the "Score Not Found" rows (which are now NaN)
    # If we don't do this, np.polyfit will return 'nan' for the trend line
    df_plot = df_plot.dropna(subset=['aggregated_rating'])

    if df_plot.empty:
        print("⚠️ No ratings found to plot.")
        return

    # 2. Prep data for the trend line
    x_dates = mdates.date2num(df_plot['start_date'])
    y_scores = df_plot['aggregated_rating']

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))

    # 3. Scatter Plot
    ax.scatter(df_plot['start_date'], y_scores, color='#0078f2', alpha=0.5, edgecolors='white', linewidth=0.5)

    # 4. Calculate Trend Line
    z = np.polyfit(x_dates, y_scores, 1)
    p = np.poly1d(z)
    ax.plot(df_plot['start_date'], p(x_dates), "r--", label="Quality Trend")

    # 5. Styling
    ax.set_title("The Quality Pulse: Content Strategy Over Time", fontsize=15, color='white')
    ax.set_ylabel("Critic Score (IGDB / Metacritic)")
    ax.set_ylim(0, 105) # Give a little room at the top
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    add_timestamp(fig)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def generate_hype_cycle_chart(df, output_path='assets/hype_cycle_comparison.png'):
    stats = get_hype_cycle_stats(df)
    
    labels = ['Standard Giveaway', 'Strategic Franchise Promo']
    values = [stats['avg_std_price'], stats['avg_promo_price']]
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(labels, values, color=['#444444', '#0078f2'], alpha=0.8)
    
    # Styling
    ax.set_title("The Hype Cycle: Strategic Value of Franchise Promotions", fontsize=14, pad=20)
    ax.set_ylabel("Average Retail Price ($)")
    ax.yaxis.set_major_formatter('${x:,.0f}')
    
    # Add labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'${height:.2f}', ha='center', va='bottom', color='white', fontweight='bold')

    add_timestamp(fig)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def generate_hype_heatmap(df, output_path='assets/hype_heatmap.png'):
    df_plot = tag_hype_candidates(df)
    
# Check if we have enough data to pivot
    if df_plot['is_strategic_hype'].sum() == 0:
        logger.warning("No hype candidates found—creating a 'Zero State' heatmap.")
        # Create a tiny 1x1 dataframe with 0 to prevent NumPy crash
        heatmap_data = pd.DataFrame([[0]], index=[2026], columns=['January'])
    else:
        # Normal heatmap logic...
        pass

    # 1. Filter for Strategic games
    strategic_only = df_plot[df_plot['is_strategic_hype'] == True].copy()
    # --- THE FIX: Handle empty data ---
    if strategic_only.empty:
        logger.warning("⚠️ No 'Prime Hype' candidates found. Skipping heatmap generation.")
        # Optional: Create a "blank" placeholder image so the README doesn't have a broken link
        return 

    # 2. Prepare the data
    strategic_only['month'] = strategic_only['start_date'].dt.month_name()
    strategic_only['year'] = strategic_only['start_date'].dt.year
    
    # Create the Matrix
    heatmap_data = strategic_only.groupby(['year', 'month']).size().unstack(fill_value=0)
    
    # Reorder months to be chronological
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    heatmap_data = heatmap_data.reindex(columns=month_order)

    # 3. Plotting
    plt.style.use('dark_background')
    plt.figure(figsize=(14, 7))
    sns.heatmap(heatmap_data, annot=True, cmap='Blues', cbar_kws={'label': 'Strategic Giveaways'})
    
    plt.title("The Hype Heatmap: Identifying Strategic Marketing Windows", fontsize=16, pad=20)
    plt.xlabel("Month")
    plt.ylabel("Year")
    
    add_timestamp(plt.gcf())
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def plot_quality_vs_price(df):
    plt.figure(figsize=(10, 6))
    
    # 1. Clean the data (Filter out games without scores)
    plot_df = df.dropna(subset=['aggregated_rating', 'price'])
    plot_df = plot_df[plot_df['price'] > 0] # Ignore $0 placeholders

    # 2. Create the Scatter
    sns.regplot(data=plot_df, x='aggregated_rating', y='price', 
                scatter_kws={'alpha':0.5, 'color':'#7289da'}, 
                line_kws={'color':'#ff4655'})

    plt.title("Epic Games Strategy: Quality vs. Retail Price")
    plt.xlabel("IGDB Aggregated Rating (0-100)")
    plt.ylabel("Retail Price at Time of Giveaway ($)")
    
    # 3. Save it
    plt.savefig('assets/quality_vs_price.png', bbox_inches='tight', dpi=300)
    plt.close()

def generate_price_distribution_chart(df, output_path='assets/price_distribution.png'):
    """
    Visualizes the retail value of giveaways over time using a scatter plot
    with a regression line to show value trends.
    """
    # 1. Self-Healing & Data Preparation
    if isinstance(df, str):
        df = pd.read_csv(df, encoding='utf-8-sig')

    df_plot = df.copy()
    df_plot['start_date'] = pd.to_datetime(df_plot['start_date'], dayfirst=True, errors='coerce')
    df_plot = df_plot.dropna(subset=['start_date'])
    
    # Extract year for the X-axis and ensure price is a float
    df_plot['year'] = df_plot['start_date'].dt.year
    df_plot['price'] = pd.to_numeric(df_plot['price'], errors='coerce').fillna(0)

    # 2. Setup Figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7))

    # 3. Plotting (Scatter with Regression)
    # Using #0078f2 (Epic Blue) for points and #ff4655 (Epic Red) for the trend line
    sns.regplot(
        data=df_plot, x='year', y='price',
        scatter_kws={'alpha': 0.4, 'color': '#0078f2', 's': 60},
        line_kws={'color': '#ff4655', 'linewidth': 3, 'label': 'Value Trend'},
        x_jitter=0.2, ax=ax
    )

    # 4. Styling & Labels
    ax.set_title('Retail Price vs. Year Made Free', fontsize=16, color='white', pad=25)
    ax.set_ylabel('Original Retail Price ($)', fontsize=12, color='white')
    ax.set_xlabel('Year', fontsize=12, color='white')
    
    # Ensure the X-axis only shows whole years
    ax.set_xticks(sorted(df_plot['year'].unique().astype(int)))
    
    # Format Y-axis to $
    import matplotlib.ticker as mtick
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))

    # 5. Global Branding
    add_timestamp(fig)

    # 6. Save
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📈 Price distribution chart saved to {output_path}")