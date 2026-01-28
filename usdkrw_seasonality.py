import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_polygon_fx_data(api_key, from_currency='USD', to_currency='KRW', years=15):
    """
    Fetch FX data from Polygon API for the past N years
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    # Format dates for API
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Polygon API endpoint for forex aggregates (daily bars)
    ticker = f'C:{from_currency}{to_currency}'
    url = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_str}/{end_str}'
    
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 50000,
        'apiKey': api_key
    }
    
    print(f"Fetching {ticker} data from {start_str} to {end_str}...")
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    data = response.json()
    
    if 'results' not in data or not data['results']:
        raise Exception(f"No data returned from API: {data}")
    
    # Convert to DataFrame
    df = pd.DataFrame(data['results'])
    
    # Convert timestamp to datetime
    df['date'] = pd.to_datetime(df['t'], unit='ms')
    
    # Use close price
    df = df[['date', 'c']].rename(columns={'c': 'close'})
    df = df.set_index('date').sort_index()
    
    print(f"Fetched {len(df)} data points from {df.index[0]} to {df.index[-1]}")
    
    return df

def calculate_q1_seasonality(df):
    """
    Calculate Q1 (Jan-Mar) seasonality statistics
    """
    # Filter for Q1 months only (January, February, March)
    df_q1 = df[df.index.month.isin([1, 2, 3])].copy()
    
    # Add year and day-of-year columns
    df_q1['year'] = df_q1.index.year
    df_q1['month'] = df_q1.index.month
    df_q1['day'] = df_q1.index.day
    
    # Create a "Q1 day" column (day 1 = Jan 1, day 31 = Jan 31, day 32 = Feb 1, etc.)
    df_q1['q1_day'] = df_q1.index.dayofyear
    
    # Calculate daily returns
    df_q1['return'] = df_q1['close'].pct_change() * 100  # in percentage
    
    # For each year, calculate cumulative returns from Jan 1
    yearly_cumulative = {}
    
    for year in df_q1['year'].unique():
        year_data = df_q1[df_q1['year'] == year].copy()
        if len(year_data) == 0:
            continue
            
        # Get the first close price of the year (or closest to Jan 1)
        first_close = year_data.iloc[0]['close']
        
        # Calculate cumulative return from start of year
        year_data['cumulative_return'] = ((year_data['close'] - first_close) / first_close) * 100
        
        yearly_cumulative[year] = year_data[['q1_day', 'cumulative_return']]
    
    # Combine all years and calculate statistics for each Q1 day
    all_years_data = []
    for year, data in yearly_cumulative.items():
        for _, row in data.iterrows():
            all_years_data.append({
                'year': year,
                'q1_day': row['q1_day'],
                'cumulative_return': row['cumulative_return']
            })
    
    df_combined = pd.DataFrame(all_years_data)
    
    # Calculate statistics for each Q1 day
    stats_by_day = []
    
    for day in sorted(df_combined['q1_day'].unique()):
        day_data = df_combined[df_combined['q1_day'] == day]['cumulative_return']
        
        if len(day_data) < 3:  # Need at least 3 years of data
            continue
        
        # Calculate percentiles
        p10 = np.percentile(day_data, 10)
        p25 = np.percentile(day_data, 25)
        p75 = np.percentile(day_data, 75)
        p90 = np.percentile(day_data, 90)
        
        # Calculate average of 10-90th percentile values
        trimmed_data = day_data[(day_data >= p10) & (day_data <= p90)]
        avg_trimmed = trimmed_data.mean()
        
        stats_by_day.append({
            'q1_day': day,
            'avg_10_90': avg_trimmed,
            'p25': p25,
            'p75': p75,
            'p10': p10,
            'p90': p90,
            'median': np.median(day_data),
            'count': len(day_data)
        })
    
    df_stats = pd.DataFrame(stats_by_day)
    
    return df_stats, df_combined

def plot_seasonality(df_stats, df_combined):
    """
    Plot the Q1 seasonality analysis
    """
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Convert q1_day to date labels (using a reference year, e.g., 2024)
    def q1_day_to_label(day):
        ref_date = datetime(2024, 1, 1) + timedelta(days=int(day) - 1)
        return ref_date.strftime('%b %d')
    
    df_stats['date_label'] = df_stats['q1_day'].apply(q1_day_to_label)
    
    # Plot the 25-75 percentile range as a shaded area
    ax.fill_between(df_stats['q1_day'], df_stats['p25'], df_stats['p75'], 
                     alpha=0.3, color='lightblue', label='25th-75th Percentile Range')
    
    # Plot the average line (10-90th percentile trimmed mean)
    ax.plot(df_stats['q1_day'], df_stats['avg_10_90'], 
            linewidth=2.5, color='darkblue', label='Average (10-90th Percentile)', marker='o', markersize=2)
    
    # Plot individual years as thin lines for reference
    for year in df_combined['year'].unique():
        year_data = df_combined[df_combined['year'] == year].sort_values('q1_day')
        ax.plot(year_data['q1_day'], year_data['cumulative_return'], 
                linewidth=0.5, alpha=0.3, color='gray')
    
    # Add a horizontal line at 0
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    
    # Customize the plot
    ax.set_title('USDKRW Q1 Seasonality Analysis (15-Year Historical Pattern)', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date (Q1: January - March)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Cumulative Return from Jan 1 (%)', fontsize=12, fontweight='bold')
    
    # Set x-axis labels to show dates
    # Show labels every 7 days
    tick_positions = df_stats['q1_day'].values[::7]
    tick_labels = df_stats['date_label'].values[::7]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend
    ax.legend(loc='best', fontsize=10, framealpha=0.9)
    
    # Format y-axis to show percentage
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
    
    plt.tight_layout()
    
    # Save the plot
    output_file = '/Users/ravelai/macro-dash-streamlit/usdkrw_q1_seasonality.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nChart saved as: {output_file}")
    
    # Print summary statistics
    print("\n=== Q1 Seasonality Summary ===")
    print(f"End of Q1 (around Mar 31):")
    last_day_stats = df_stats.iloc[-1]
    print(f"  Average Return: {last_day_stats['avg_10_90']:.2f}%")
    print(f"  25th Percentile: {last_day_stats['p25']:.2f}%")
    print(f"  75th Percentile: {last_day_stats['p75']:.2f}%")
    print(f"  Median: {last_day_stats['median']:.2f}%")
    
    return fig

def main():
    # Get API key from environment
    api_key = os.getenv('POLYGON_API_KEY')
    
    if not api_key:
        raise Exception("POLYGON_API_KEY not found in .env file")
    
    # Fetch data
    df = fetch_polygon_fx_data(api_key, from_currency='USD', to_currency='KRW', years=15)
    
    # Calculate seasonality
    df_stats, df_combined = calculate_q1_seasonality(df)
    
    # Plot
    plot_seasonality(df_stats, df_combined)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
