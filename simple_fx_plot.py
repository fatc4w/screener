import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def create_fx_plot():
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
    
    # Create the plot
    plt.figure(figsize=(14, 8))
    
    # Plot the line chart
    plt.plot(parsed_dates, fx_values_numeric, linewidth=2, marker='o', markersize=3, color='blue')
    
    # Customize the plot
    plt.title('China Foreign Exchange Settlement (Jan 2020 - Sep 2025)', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('FX Settlement (Billion USD)', fontsize=12)
    
    # Add grid
    plt.grid(True, alpha=0.3)
    
    # Rotate x-axis labels
    plt.xticks(rotation=45)
    
    # Format y-axis
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}B'))
    
    # Tight layout
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('/Users/ravelai/macro-dash-streamlit/fx_line_chart.png', dpi=300, bbox_inches='tight')
    
    # Show basic stats
    print(f"FX Settlement Data:")
    print(f"Mean: {np.mean(fx_values_numeric):.1f}B USD")
    print(f"Max: {np.max(fx_values_numeric):.1f}B USD")
    print(f"Min: {np.min(fx_values_numeric):.1f}B USD")
    print(f"Chart saved as: fx_line_chart.png")
    
    return plt

if __name__ == "__main__":
    create_fx_plot()
    print("Chart created and saved!")
