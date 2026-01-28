import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Set style for better-looking plots
plt.style.use('default')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

def plot_fx_settlement_data():
    # Read the CSV file
    df = pd.read_csv('/Users/ravelai/Downloads/FX_China_2020_2025_Complete.csv')
    
    # Extract the main FX settlement series (row index 1, which is "I. Foreign exchange settlement")
    fx_settlement_row = df.iloc[1]  # Row 2 in the file (0-indexed)
    
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
    # The format appears to be like "Jan.2020", "Feb.2020", etc.
    parsed_dates = []
    for date_str in valid_dates:
        try:
            # Parse dates like "Jan.2020"
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
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # Plot the main time series
    ax.plot(parsed_dates, fx_values_numeric, linewidth=2.5, marker='o', markersize=4, 
            color='#2E86AB', alpha=0.8, label='FX Settlement')
    
    # Customize the plot
    ax.set_title('China Foreign Exchange Settlement Time Series\n(January 2020 - December 2025)', 
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('FX Settlement (Billion USD)', fontsize=12, fontweight='bold')
    
    # Format y-axis to show values in a readable format
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.1f}'))
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Add some statistics as text
    mean_val = np.mean(fx_values_numeric)
    max_val = np.max(fx_values_numeric)
    min_val = np.min(fx_values_numeric)
    
    stats_text = f'Mean: {mean_val:.1f}B\nMax: {max_val:.1f}B\nMin: {min_val:.1f}B'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Highlight recent trend (last 12 months of actual data)
    recent_data_cutoff = datetime(2024, 1, 1)
    recent_indices = [i for i, date in enumerate(parsed_dates) if date >= recent_data_cutoff]
    
    if recent_indices:
        recent_dates = [parsed_dates[i] for i in recent_indices]
        recent_values = [fx_values_numeric[i] for i in recent_indices]
        ax.plot(recent_dates, recent_values, linewidth=3, color='#F18F01', alpha=0.7, 
                label='Recent Trend (2024+)')
    
    # Add legend
    ax.legend(loc='upper right', framealpha=0.9)
    
    # Tight layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('/Users/ravelai/macro-dash-streamlit/fx_china_settlement_plot.png', 
                dpi=300, bbox_inches='tight')
    
    # Don't show the plot interactively, just save it
    print("Plot saved to fx_china_settlement_plot.png")
    
    # Print some basic statistics
    print(f"\nFX Settlement Data Summary:")
    print(f"Period: {valid_dates[0]} to {valid_dates[-1]}")
    print(f"Number of observations: {len(fx_values_numeric)}")
    print(f"Mean: {mean_val:.2f} billion USD")
    print(f"Standard deviation: {np.std(fx_values_numeric):.2f} billion USD")
    print(f"Maximum: {max_val:.2f} billion USD")
    print(f"Minimum: {min_val:.2f} billion USD")
    
    return fig, ax

if __name__ == "__main__":
    plot_fx_settlement_data()
