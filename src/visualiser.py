import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_savings_chart(file_path, output_path='assets/savings_chart.png'):
    # Load data
    df = pd.read_csv(file_path, encoding='latin1')
    
    # Ensure date is a datetime object and sort
    df['start_date'] = pd.to_datetime(df['start_date'], dayfirst=True, errors='coerce')
    # Drop any rows where the date couldn't be parsed (safety check)
    df = df.dropna(subset=['start_date'])
    
    # Sort by date so the line moves forward in time
    df = df.sort_values('start_date')
    
    # Calculate Cumulative Savings
    df['cumulative_value'] = df['price'].cumsum()
    
    # Create the Plot
    plt.figure(figsize=(10, 5))
    sns.set_style("darkgrid")
    plt.plot(df['start_date'], df['cumulative_value'], color='#0078D4', linewidth=3)
    plt.fill_between(df['start_date'], df['cumulative_value'], color='#0078D4', alpha=0.1)
    
    plt.title('Epic Games Collection: Cumulative Market Value', fontsize=14, pad=20)
    plt.ylabel('Total Value ($)', fontsize=12)
    plt.xlabel('Date Added', fontsize=12)
    
    # Ensure assets folder exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save chart
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()