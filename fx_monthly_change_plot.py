import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def create_fx_monthly_change_plot():
    # Read the CSV file
    df = pd.read_csv('/Users/ravelai/Downloads/FX_China_2020_2025_Complete.csv')
    
    # Extract the main FX settlement series (row index 1)
    fx_settlement_row = df.iloc[1]  # "I. Foreign exchange settlement"
    
    # Get the date columns (skip the first column which is "Item")
    date_columns = df.columns[1:]
    
    # Extract the values for FX settlement
    fx_values = fx_settlement_row[1:].values
    
    # Convert to numeric, handling any non-numeric values
    fx_values_numeric = []
    valid_dates = []
    
    for i, val in enumerate(fx_values):
        try:
            if pd.notna(val) and val != '':
                fx_values_numeric.append(float(val))
                valid_dates.append(date_columns[i])
        except (ValueError, TypeError):
            continue
    
    # Convert date strings to datetime objects
    parsed_dates = []
    for date_str in valid_dates:
        try:
            month_year = date_str.split('.')
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month = month_map[month_year[0]]
            year = int(month_year[1])
            parsed_dates.append(datetime(year, month, 1))
        except (ValueError, KeyError, IndexError):
            continue
    
    # Calculate monthly changes (month-over-month)
    monthly_changes = []
    change_dates = []
    
    for i in range(1, len(fx_values_numeric)):
        change = fx_values_numeric[i] - fx_values_numeric[i-1]
        monthly_changes.append(change)
        change_dates.append(parsed_dates[i])
    
    # Create subplots - original series and monthly changes
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    
    # Plot 1: Original FX Settlement Series
    ax1.plot(parsed_dates, fx_values_numeric, linewidth=2, marker='o', markersize=3, color='blue')
    ax1.set_title('China Foreign Exchange Settlement (Jan 2020 - Sep 2025)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('FX Settlement (Billion USD)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}B'))
    
    # Plot 2: Monthly Changes
    colors = ['red' if x < 0 else 'green' for x in monthly_changes]
    ax2.bar(change_dates, monthly_changes, color=colors, alpha=0.7, width=20)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax2.set_title('Monthly Change in FX Settlement (Month-over-Month)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Monthly Change (Billion USD)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:+.0f}B'))
    
    # Rotate x-axis labels for both plots
    for ax in [ax1, ax2]:
        ax.tick_params(axis='x', rotation=45)
    
    # Add statistics text box for monthly changes
    mean_change = np.mean(monthly_changes)
    std_change = np.std(monthly_changes)
    max_increase = np.max(monthly_changes)
    max_decrease = np.min(monthly_changes)
    
    stats_text = f'Monthly Change Stats:\nMean: {mean_change:+.1f}B\nStd Dev: {std_change:.1f}B\nMax Increase: {max_increase:+.1f}B\nMax Decrease: {max_decrease:+.1f}B'
    ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    # Tight layout
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('/Users/ravelai/macro-dash-streamlit/fx_monthly_change_chart.png', dpi=300, bbox_inches='tight')
    
    # Print statistics
    print(f"Monthly Change Analysis:")
    print(f"Mean monthly change: {mean_change:+.2f}B USD")
    print(f"Standard deviation: {std_change:.2f}B USD")
    print(f"Largest monthly increase: {max_increase:+.2f}B USD")
    print(f"Largest monthly decrease: {max_decrease:+.2f}B USD")
    print(f"Number of positive changes: {sum(1 for x in monthly_changes if x > 0)}")
    print(f"Number of negative changes: {sum(1 for x in monthly_changes if x < 0)}")
    print(f"Chart saved as: fx_monthly_change_chart.png")
    
    return fig

if __name__ == "__main__":
    create_fx_monthly_change_plot()
    print("Monthly change chart created and saved!")
