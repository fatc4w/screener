"""
Test script to pull China Balance of Payments - Current Account data from CEIC API
using direct REST API calls and visualize it.

Series: CN.BOPCA.FL.USD-MN-Q (China BoP: Current Account)
ID: 368510437_SR96648087
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json

# API Key
CEIC_API_KEY = "REDACTED"

# Series details from the web interface
SERIES_ID = "368510437"
SERIES_REF = "SR96648087"
FULL_SERIES_ID = f"{SERIES_ID}_{SERIES_REF}"

# CEIC API Base URL
BASE_URL = "https://api.ceicdata.com/v2"

def fetch_series_data(series_id, access_token, start_date=None, end_date=None):
    """
    Fetch series data from CEIC API using direct REST calls
    
    Parameters:
    -----------
    series_id : str
        The CEIC series ID (e.g., "368510437_SR96648087")
    access_token : str
        The CEIC API access token
    start_date : str, optional
        Start date in YYYY-MM-DD format
    end_date : str, optional
        End date in YYYY-MM-DD format
    
    Returns:
    --------
    dict
        JSON response from the API
    """
    print(f"\n{'-' * 80}")
    print(f"FETCHING SERIES DATA")
    print(f"{'-' * 80}")
    print(f"Series ID: {series_id}")
    print(f"Date Range: {start_date} to {end_date}")
    print()
    
    # Build the request URL
    url = f"{BASE_URL}/series/{series_id}"
    
    # Set up parameters
    params = {
        "lang": "en"
    }
    
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    # Set up headers with authorization
    headers = {
        "Authorization": access_token
    }
    
    try:
        print(f"Making request to: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Data fetched successfully!")
            data = response.json()
            
            # Print structure
            if isinstance(data, dict):
                print(f"\nResponse keys: {list(data.keys())}")
            
            return data
        else:
            print(f"✗ Request failed with status code {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"✗ Error fetching data: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_ceic_data(data):
    """
    Parse CEIC API response into a pandas DataFrame
    
    Parameters:
    -----------
    data : dict
        JSON response from CEIC API
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with Date and Value columns
    """
    print(f"\n{'-' * 80}")
    print("PARSING DATA")
    print(f"{'-' * 80}\n")
    
    try:
        if not data:
            print("✗ No data to parse")
            return None
        
        # Print full data structure to understand format
        print("Data structure:")
        print(json.dumps(data, indent=2)[:2000])
        print()
        
        # Try to extract time series data
        # CEIC API typically returns data in different formats
        # Common formats: data['data'], data['series'], data['values']
        
        series_data = None
        metadata = None
        
        if 'data' in data:
            series_data = data['data']
            metadata = {k: v for k, v in data.items() if k != 'data'}
        elif 'series' in data:
            series_data = data['series']
        elif 'values' in data:
            series_data = data['values']
        elif 'observations' in data:
            series_data = data['observations']
        else:
            # Try to use the whole response
            series_data = data
        
        print(f"Series data type: {type(series_data)}")
        
        # Convert to DataFrame
        if isinstance(series_data, list):
            df = pd.DataFrame(series_data)
        elif isinstance(series_data, dict):
            # Might be date: value pairs
            df = pd.DataFrame(list(series_data.items()), columns=['Date', 'Value'])
        else:
            print(f"✗ Unexpected data format: {type(series_data)}")
            return None
        
        print(f"✓ Data converted to DataFrame")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {df.columns.tolist()}")
        print(f"\nFirst few rows:")
        print(df.head(10))
        print(f"\nLast few rows:")
        print(df.tail(10))
        
        # Standardize column names
        # Look for date and value columns
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or col.lower() in ['d', 'period', 'month', 'quarter', 'year']]
        value_cols = [col for col in df.columns if 'value' in col.lower() or col.lower() in ['v', 'val', 'amount', 'data']]
        
        if date_cols and value_cols:
            df = df.rename(columns={date_cols[0]: 'Date', value_cols[0]: 'Value'})
        elif 'Date' not in df.columns and len(df.columns) >= 2:
            # Assume first column is date, second is value
            df.columns = ['Date', 'Value'] + list(df.columns[2:])
        
        # Convert date to datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
        
        # Convert value to numeric
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        print(f"\n✓ Data processed successfully")
        print(f"  Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"  Observations: {len(df)}")
        
        # Print metadata if available
        if metadata:
            print(f"\nMetadata:")
            for key, value in metadata.items():
                if key not in ['data', 'series', 'values']:
                    print(f"  {key}: {value}")
        
        return df
        
    except Exception as e:
        print(f"✗ Error parsing data: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def visualize_bop_data(df, series_name="China BoP: Current Account (CA)"):
    """
    Create a visualization similar to the CEIC web interface
    """
    if df is None or df.empty:
        print("\n✗ No data to visualize")
        return
    
    print(f"\n{'-' * 80}")
    print("CREATING VISUALIZATION")
    print(f"{'-' * 80}\n")
    
    try:
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Plot the line
        ax.plot(df['Date'], df['Value'], linewidth=2.5, color='#6C63FF', marker='o', markersize=4)
        
        # Formatting
        ax.set_xlabel('Date', fontsize=13, fontweight='bold')
        ax.set_ylabel('USD mn', fontsize=13, fontweight='bold')
        ax.set_title(f'{series_name}\nQuarterly, USD million\nSource: State Administration of Foreign Exchange', 
                    fontsize=15, fontweight='bold', pad=20)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
        
        # Format y-axis with thousand separators
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        plt.xticks(rotation=45, ha='right')
        
        # Add horizontal line at y=0
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1.0, alpha=0.6)
        
        # Highlight latest data points
        latest_5 = df.tail(5)
        for _, row in latest_5.iterrows():
            ax.plot(row['Date'], row['Value'], 'o', markersize=10, 
                   color='#FF6B6B', markeredgecolor='darkred', markeredgewidth=1.5)
        
        # Add annotation for the latest value
        latest = df.iloc[-1]
        second_latest = df.iloc[-2] if len(df) > 1 else latest
        
        ax.annotate(f'{latest["Value"]:,.2f}\n{latest["Date"].strftime("%m/%Y")} (Latest)',
                   xy=(latest['Date'], latest['Value']),
                   xytext=(30, 30), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.7', fc='#FFD700', alpha=0.9, edgecolor='black', linewidth=1.5),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', linewidth=2),
                   fontsize=11, fontweight='bold')
        
        # Add annotation for second latest
        ax.annotate(f'{second_latest["Value"]:,.2f}\n{second_latest["Date"].strftime("%m/%Y")}',
                   xy=(second_latest['Date'], second_latest['Value']),
                   xytext=(-50, -40), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.8),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=-0.3', linewidth=1.5),
                   fontsize=10)
        
        plt.tight_layout()
        
        # Save the plot
        output_file = '/Users/ravelai/macro-dash-streamlit/china_bop_current_account.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✓ Plot saved to: {output_file}")
        
        # Show plot
        print("✓ Displaying plot...")
        plt.show()
        
        # Print summary statistics
        print(f"\n{'-' * 80}")
        print("DATA SUMMARY STATISTICS")
        print(f"{'-' * 80}")
        print(f"Series: {series_name}")
        print(f"Observations: {len(df)}")
        print(f"Date Range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"Latest Value: {latest['Value']:,.2f} USD mn ({latest['Date'].strftime('%Y-%m-%d')})")
        print(f"Previous Value: {second_latest['Value']:,.2f} USD mn ({second_latest['Date'].strftime('%Y-%m-%d')})")
        print(f"Change: {latest['Value'] - second_latest['Value']:,.2f} USD mn")
        print(f"Mean: {df['Value'].mean():,.2f} USD mn")
        print(f"Median: {df['Value'].median():,.2f} USD mn")
        print(f"Std Dev: {df['Value'].std():,.2f} USD mn")
        print(f"Max: {df['Value'].max():,.2f} USD mn ({df.loc[df['Value'].idxmax(), 'Date'].strftime('%Y-%m-%d')})")
        print(f"Min: {df['Value'].min():,.2f} USD mn ({df.loc[df['Value'].idxmin(), 'Date'].strftime('%Y-%m-%d')})")
        print(f"{'-' * 80}\n")
        
    except Exception as e:
        print(f"✗ Error creating visualization: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "CEIC API - CHINA BOP DATA TEST (REST API)" + " " * 22 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Fetch data using REST API
    data = fetch_series_data(
        series_id=FULL_SERIES_ID,
        access_token=CEIC_API_KEY,
        start_date="1998-01-01",
        end_date="2025-12-31"
    )
    
    if data:
        # Parse the data
        df = parse_ceic_data(data)
        
        if df is not None and not df.empty:
            # Visualize
            visualize_bop_data(df, series_name="China BoP: Current Account (CA)")
            
            # Export to CSV
            csv_file = '/Users/ravelai/macro-dash-streamlit/china_bop_data.csv'
            df.to_csv(csv_file, index=False)
            print(f"✓ Data exported to: {csv_file}\n")
        else:
            print("\n✗ Failed to parse data")
    else:
        print("\n✗ Failed to fetch data")
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()























