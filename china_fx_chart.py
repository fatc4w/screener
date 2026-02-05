"""
China FX Dashboard Chart
- USDCNY Central Parity Rate with 2% trading band
- USDCNY Spot Rate (from yfinance)
- FX Settlement (from SAFE China scraping)
"""

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
from datetime import datetime

# ============================================================
# 1. SCRAPE FX SETTLEMENT FROM SAFE CHINA
# ============================================================
def scrape_fx_settlement():
    """Scrape FX Settlement data from SAFE China"""
    print("📥 Scraping FX Settlement from SAFE China...")
    
    url = 'https://www.safe.gov.cn/en/2023/0215/2048.html'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    excel_url = None
    for link in soup.find_all('a'):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if 'Time-series' in text:
            excel_url = 'https://www.safe.gov.cn' + href
            break
    
    excel_response = requests.get(excel_url, headers=headers, timeout=30)
    excel_file = BytesIO(excel_response.content)
    df_raw = pd.read_excel(excel_file, sheet_name='in USD (Monthly)')
    
    # Clean - Row 2 has dates, Row 3+ is data
    headers_row = df_raw.iloc[2]
    new_columns = []
    for val in headers_row:
        if pd.isna(val):
            new_columns.append('Label')
        elif isinstance(val, pd.Timestamp):
            new_columns.append(val.strftime('%b %Y'))
        else:
            try:
                dt = pd.to_datetime(val)
                new_columns.append(dt.strftime('%b %Y'))
            except:
                new_columns.append(str(val))
    
    df = df_raw.iloc[3:].copy()
    df.columns = new_columns
    df = df.reset_index(drop=True)
    
    # Get month columns
    month_cols = [col for col in df.columns if any(m in str(col) for m in 
                  ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])]
    
    # Build arrays manually for rows 22 and 37
    row_22_vals = []
    row_37_vals = []
    valid_months = []
    
    for i, col in enumerate(df.columns):
        if col in month_cols:
            val_22 = df.iloc[22, i]
            val_37 = df.iloc[37, i]
            
            row_22_vals.append(float(val_22) if pd.notna(val_22) else np.nan)
            row_37_vals.append(float(val_37) if pd.notna(val_37) else np.nan)
            valid_months.append(col)
    
    row_22_vals = np.array(row_22_vals)
    row_37_vals = np.array(row_37_vals)
    
    # FX Settlement = Row 22 + Row 37 MoM change
    # Data is in 100 million USD, convert to billion USD (divide by 10)
    row_37_mom = np.diff(row_37_vals, prepend=np.nan)
    fx_settlement = (row_22_vals + row_37_mom) / 10
    
    # Parse dates
    dates = pd.to_datetime(valid_months, format='%b %Y')
    
    # Create dataframe
    fx_df = pd.DataFrame({
        'Date': dates,
        'FX_Settlement': fx_settlement
    })
    
    print(f"✅ FX Settlement: {len(fx_df)} months, {fx_df['Date'].min().strftime('%b %Y')} to {fx_df['Date'].max().strftime('%b %Y')}")
    return fx_df


# ============================================================
# 2. GET USDCNY SPOT FROM YFINANCE
# ============================================================
def get_usdcny_spot(start_date='2023-01-01'):
    """Get USDCNY spot rate from yfinance"""
    print("📥 Getting USDCNY spot from yfinance...")
    
    ticker = yf.Ticker("CNY=X")
    df = ticker.history(start=start_date)
    
    spot_df = pd.DataFrame({
        'Date': df.index.tz_localize(None),
        'USDCNY_Spot': df['Close'].values
    })
    
    print(f"✅ USDCNY Spot: {len(spot_df)} days, {spot_df['Date'].min().strftime('%Y-%m-%d')} to {spot_df['Date'].max().strftime('%Y-%m-%d')}")
    return spot_df


# ============================================================
# 3. LOAD CENTRAL PARITY RATE (MONTHLY)
# ============================================================
def load_parity_rate(filepath='/Users/ravelai/Downloads/Monthly_Average_Central_Parity_Historical_Data (1).xlsx'):
    """Load PBOC central parity rate from Excel (monthly data)"""
    print("📥 Loading Central Parity Rate...")
    
    df = pd.read_excel(filepath)
    
    # Filter out footer rows (Data source, etc.)
    df = df[df['Date'].notna() & ~df['Date'].astype(str).str.contains('Data source|www\\.', na=False)]
    
    # Parse date (format: 'Mon YYYY') and extract USD/CNY
    parity_df = pd.DataFrame({
        'Date': pd.to_datetime(df['Date'], format='%b %Y', errors='coerce'),
        'Parity_Rate': pd.to_numeric(df['USD/CNY'], errors='coerce')
    })
    
    # Drop NaN dates
    parity_df = parity_df.dropna(subset=['Date'])
    parity_df = parity_df.sort_values('Date').reset_index(drop=True)
    
    # Calculate 2% trading band
    parity_df['Band_Upper'] = parity_df['Parity_Rate'] * 1.02
    parity_df['Band_Lower'] = parity_df['Parity_Rate'] * 0.98
    
    print(f"✅ Parity Rate: {len(parity_df)} months, {parity_df['Date'].min().strftime('%b %Y')} to {parity_df['Date'].max().strftime('%b %Y')}")
    return parity_df


# ============================================================
# 4. CREATE THE CHART
# ============================================================
def create_chart(fx_df, spot_df, parity_df, start_date='2023-01-01'):
    """Create the CNY/USD and Settlement chart"""
    print("📊 Creating chart...")
    
    # Filter to start_date
    start = pd.to_datetime(start_date)
    fx_filtered = fx_df[fx_df['Date'] >= start].copy()
    spot_filtered = spot_df[spot_df['Date'] >= start].copy()
    parity_filtered = parity_df[parity_df['Date'] >= start].copy()
    
    # Create figure with dual y-axis
    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax2 = ax1.twinx()
    
    # Plot 2% trading band (shaded area) - if we have parity data
    if len(parity_filtered) > 0:
        ax1.fill_between(parity_filtered['Date'], 
                         parity_filtered['Band_Upper'], 
                         parity_filtered['Band_Lower'],
                         color='red', alpha=0.15, label='2% trading band')
        
        # Plot PBOC central parity rate
        ax1.plot(parity_filtered['Date'], parity_filtered['Parity_Rate'], 
                 color='gray', linewidth=1.5, label='PBOC central parity rate')
    
    # Plot CNY Spot Rate
    ax1.plot(spot_filtered['Date'], spot_filtered['USDCNY_Spot'], 
             color='blue', linewidth=1, alpha=0.8, label='CNY Spot Rate')
    
    # Plot FX Settlement as step chart on right axis
    ax2.step(fx_filtered['Date'], fx_filtered['FX_Settlement'], 
             where='mid', color='black', linewidth=2, label='Settlement (rhs)')
    
    # Formatting - Left axis (FX rates) - INVERTED
    ax1.set_ylabel('CNY/USD', fontsize=12, color='black')
    ax1.invert_yaxis()  # Invert so stronger CNY is up
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.set_xlabel('', fontsize=12)
    
    # Formatting - Right axis (Settlement)
    ax2.set_ylabel('USD Billion', fontsize=12, color='black')
    ax2.tick_params(axis='y', labelcolor='black')
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    
    # Title
    ax1.set_title('CNY/USD (lhs) and Settlement in USD Billion (rhs)', 
                  fontsize=16, fontweight='bold', color='red', pad=20)
    
    # Grid
    ax1.grid(True, alpha=0.3, linestyle='-')
    
    # Format x-axis
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
    plt.xticks(rotation=45, ha='right')
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower left', fontsize=10)
    
    plt.tight_layout()
    plt.show()
    print("✅ Chart displayed!")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("="*60)
    print("CHINA FX DASHBOARD")
    print("="*60)
    
    # Load all data
    fx_df = scrape_fx_settlement()
    spot_df = get_usdcny_spot(start_date='2023-01-01')
    parity_df = load_parity_rate()
    
    # Save parity data to workspace for future use
    parity_df.to_csv('data/parity_rate.csv', index=False)
    print("✅ Parity rate saved to data/parity_rate.csv")
    
    # Create chart
    create_chart(fx_df, spot_df, parity_df, start_date='2023-01-01')
    
    print("\n" + "="*60)
    print("DONE!")
    print("="*60)
