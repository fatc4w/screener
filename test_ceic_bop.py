"""
Test script to pull China Balance of Payments - Current Account data from CEIC API
and visualize it similar to the web interface.

Series: CN.BOPCA.FL.USD-MN-Q (China BoP: Current Account)
ID: 368510437_SR96648087
"""

import ceic_api_client
from ceic_api_client import pyceic
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import ssl
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable SSL verification (needed for proxy/self-signed certs)
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'
ssl._create_default_https_context = ssl._create_unverified_context

# API Key
CEIC_API_KEY = "REDACTED"

# Series details from the web interface
SERIES_ID = "368510437"
SERIES_REF = "SR96648087"
FULL_SERIES_ID = f"{SERIES_ID}_{SERIES_REF}"

def test_ceic_connection():
    """Test basic CEIC API connection"""
    print("=" * 80)
    print("TESTING CEIC API CONNECTION")
    print("=" * 80)
    
    try:
        # Initialize the CEIC client
        ceic_client = pyceic.Ceic(CEIC_API_KEY)
        print("✓ CEIC client initialized successfully")
        return ceic_client
    except Exception as e:
        print(f"✗ Error initializing CEIC client: {e}")
        return None

def fetch_bop_data(ceic_client, series_id, start_date="1998-01-01", end_date="2025-12-31"):
    """
    Fetch China Balance of Payments - Current Account data
    
    Parameters:
    -----------
    ceic_client : pyceic.Ceic
        The initialized CEIC client
    series_id : str
        The CEIC series ID
    start_date : str
        Start date in YYYY-MM-DD format
    end_date : str
        End date in YYYY-MM-DD format
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with Date index and Value column
    """
    print(f"\n{'-' * 80}")
    print(f"FETCHING DATA FOR SERIES: {series_id}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"{'-' * 80}\n")
    
    try:
        # Fetch series data
        data = ceic_client.series(
            series_id=series_id,
            start_date=start_date,
            end_date=end_date,
            lang='en'
        )
        
        print(f"✓ Data fetched successfully")
        print(f"  Type: {type(data)}")
        
        # Convert to DataFrame
        if hasattr(data, 'to_dataframe'):
            df = data.to_dataframe()
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            # Try to extract data manually
            print(f"  Data attributes: {dir(data)}")
            if hasattr(data, 'data'):
                df = pd.DataFrame(data.data)
            else:
                print(f"  Raw data: {data}")
                return None
        
        print(f"✓ Data converted to DataFrame")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {df.columns.tolist()}")
        print(f"\nFirst few rows:")
        print(df.head())
        print(f"\nLast few rows:")
        print(df.tail())
        print(f"\nData info:")
        print(df.info())
        
        return df
        
    except Exception as e:
        print(f"✗ Error fetching data: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
        return None

def visualize_bop_data(df, series_name="China BoP: Current Account (CA)"):
    """
    Create a visualization similar to the CEIC web interface
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with date index and value column
    series_name : str
        Name of the series for the plot title
    """
    if df is None or df.empty:
        print("✗ No data to visualize")
        return
    
    print(f"\n{'-' * 80}")
    print("CREATING VISUALIZATION")
    print(f"{'-' * 80}\n")
    
    try:
        # Create figure with larger size
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Determine date and value columns
        if 'Date' in df.columns:
            date_col = 'Date'
        elif df.index.name in ['Date', 'date', 'TIME_PERIOD']:
            df = df.reset_index()
            date_col = df.columns[0]
        else:
            date_col = df.columns[0]
        
        # Find value column
        value_cols = [col for col in df.columns if col not in [date_col, 'STATUS']]
        if value_cols:
            value_col = value_cols[0]
        else:
            value_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        
        # Ensure date is datetime
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Sort by date
        df = df.sort_values(date_col)
        
        # Plot the line
        ax.plot(df[date_col], df[value_col], linewidth=2, color='#6C63FF', marker='o', markersize=3)
        
        # Formatting
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('USD mn', fontsize=12, fontweight='bold')
        ax.set_title(f'{series_name}\nQuarterly, USD million', fontsize=14, fontweight='bold', pad=20)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Format y-axis with thousand separators
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        plt.xticks(rotation=45, ha='right')
        
        # Add horizontal line at y=0
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
        
        # Highlight latest data points
        latest_5 = df.tail(5)
        for _, row in latest_5.iterrows():
            ax.plot(row[date_col], row[value_col], 'o', markersize=8, color='#FF6B6B')
        
        # Add annotation for the latest value
        latest = df.iloc[-1]
        ax.annotate(f'{latest[value_col]:,.2f}\n{latest[date_col].strftime("%m/%Y")}',
                   xy=(latest[date_col], latest[value_col]),
                   xytext=(20, 20), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        plt.tight_layout()
        
        # Save the plot
        output_file = '/Users/ravelai/macro-dash-streamlit/china_bop_current_account.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Plot saved to: {output_file}")
        
        # Show the plot
        plt.show()
        
        # Print summary statistics
        print(f"\n{'-' * 80}")
        print("DATA SUMMARY STATISTICS")
        print(f"{'-' * 80}")
        print(f"Series: {series_name}")
        print(f"Observations: {len(df)}")
        print(f"Date Range: {df[date_col].min()} to {df[date_col].max()}")
        print(f"Latest Value: {latest[value_col]:,.2f} USD mn ({latest[date_col].strftime('%Y-%m-%d')})")
        print(f"Mean: {df[value_col].mean():,.2f} USD mn")
        print(f"Median: {df[value_col].median():,.2f} USD mn")
        print(f"Max: {df[value_col].max():,.2f} USD mn ({df.loc[df[value_col].idxmax(), date_col].strftime('%Y-%m-%d')})")
        print(f"Min: {df[value_col].min():,.2f} USD mn ({df.loc[df[value_col].idxmin(), date_col].strftime('%Y-%m-%d')})")
        print(f"{'-' * 80}\n")
        
    except Exception as e:
        print(f"✗ Error creating visualization: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "CEIC API - CHINA BOP DATA TEST" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Test 1: Initialize CEIC client
    ceic_client = test_ceic_connection()
    if not ceic_client:
        print("\n✗ Failed to initialize CEIC client. Exiting.")
        return
    
    # Test 2: Fetch data
    df = fetch_bop_data(ceic_client, FULL_SERIES_ID, start_date="1998-01-01", end_date="2025-12-31")
    
    if df is not None and not df.empty:
        # Test 3: Visualize data
        visualize_bop_data(df, series_name="China BoP: Current Account (CA)")
        
        # Export to CSV
        csv_file = '/Users/ravelai/macro-dash-streamlit/china_bop_data.csv'
        df.to_csv(csv_file, index=False)
        print(f"✓ Data exported to: {csv_file}\n")
    else:
        print("\n✗ No data available to visualize")
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

