#!/usr/bin/env python3
"""
SPX Rolling 60-Day Returns Analysis
- Calculates rolling 60-day log returns
- Computes Z-scores for 10y, 5y, and 3y lookback windows
- Tracks consecutive positive/negative days
- Identifies correction periods (>10% from ATH)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

def fetch_spx_data(years_back=15):
    """Fetch SPX daily data from yfinance"""
    print(f"📊 Fetching SPX data for the past {years_back} years...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365 + 180)  # Add buffer for rolling calcs
    
    ticker = yf.Ticker("^GSPC")
    df = ticker.history(start=start_date, end=end_date)
    
    if df.empty:
        raise ValueError("No data fetched from yfinance")
    
    df = df.reset_index()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    print(f"✅ Fetched {len(df)} days of data")
    print(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"   Latest close: ${df['Close'].iloc[-1]:.2f}")
    
    return df

def calculate_rolling_returns(df, window=60):
    """Calculate rolling log returns"""
    print(f"\n📈 Calculating {window}-day rolling log returns...")
    
    # Daily log returns
    df['daily_log_return'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # 60-day cumulative log return: log(price_today / price_60_days_ago)
    df['rolling_60d_return'] = np.log(df['Close'] / df['Close'].shift(window))
    
    print(f"✅ Calculated rolling returns")
    
    return df

def calculate_z_scores(df, lookback_periods={'10y': 10*252, '5y': 5*252, '3y': 3*252}):
    """Calculate Z-scores for different lookback windows"""
    print(f"\n📊 Calculating Z-scores for lookback periods...")
    
    for name, days in lookback_periods.items():
        # Rolling mean and std of the 60-day returns
        df[f'mean_{name}'] = df['rolling_60d_return'].rolling(window=days, min_periods=days//2).mean()
        df[f'std_{name}'] = df['rolling_60d_return'].rolling(window=days, min_periods=days//2).std()
        
        # Z-score: (current_value - mean) / std
        df[f'zscore_{name}'] = (df['rolling_60d_return'] - df[f'mean_{name}']) / df[f'std_{name}']
        
        print(f"   {name}: {days} trading days")
    
    print(f"✅ Z-scores calculated")
    
    return df

def calculate_consecutive_days(df):
    """Calculate consecutive positive/negative days"""
    print(f"\n📅 Calculating consecutive positive/negative days...")
    
    # Determine if each day is positive or negative
    df['is_positive'] = (df['daily_log_return'] > 0).astype(int)
    df['is_positive'] = df['is_positive'].replace(0, -1)  # -1 for negative days
    
    # Calculate consecutive streaks
    df['streak_id'] = (df['is_positive'] != df['is_positive'].shift()).cumsum()
    df['consecutive_days'] = df.groupby('streak_id').cumcount() + 1
    df['consecutive_days'] = df['consecutive_days'] * df['is_positive']
    
    print(f"✅ Consecutive days calculated")
    print(f"   Max positive streak: {df['consecutive_days'].max()} days")
    print(f"   Max negative streak: {df['consecutive_days'].min()} days")
    
    return df

def identify_corrections(df, threshold=0.10):
    """Identify periods where SPX is >10% below ATH"""
    print(f"\n🔻 Identifying correction periods (>{threshold*100:.0f}% from ATH)...")
    
    # Calculate running all-time high
    df['ath'] = df['Close'].expanding().max()
    
    # Calculate drawdown from ATH
    df['drawdown'] = (df['Close'] - df['ath']) / df['ath']
    
    # Mark correction periods
    df['in_correction'] = df['drawdown'] <= -threshold
    
    # Count correction periods
    correction_periods = (df['in_correction'] != df['in_correction'].shift()).cumsum()
    num_corrections = df[df['in_correction']].groupby(correction_periods)['in_correction'].count().shape[0]
    
    current_drawdown = df['drawdown'].iloc[-1]
    print(f"✅ Correction periods identified")
    print(f"   Number of correction periods: {num_corrections}")
    print(f"   Current drawdown from ATH: {current_drawdown*100:.2f}%")
    print(f"   Currently in correction: {'Yes' if df['in_correction'].iloc[-1] else 'No'}")
    
    return df

def create_visualizations(df):
    """Create comprehensive visualizations"""
    print(f"\n📊 Creating visualizations...")
    
    # Filter to only show last 10 years for cleaner visualization
    cutoff_date = df['Date'].max() - timedelta(days=10*365)
    df_plot = df[df['Date'] >= cutoff_date].copy()
    
    # Create figure with 4 subplots
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 1, height_ratios=[1, 1, 1, 0.8], hspace=0.3)
    
    # Plot 1: 10Y Z-score
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df_plot['Date'], df_plot['zscore_10y'], 
             label='10Y Z-Score', color='#1f77b4', linewidth=1.5)
    ax1.axhline(y=2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='+2 SD')
    ax1.axhline(y=-2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='-2 SD')
    ax1.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    ax1.set_ylabel('Z-Score (10Y)', fontsize=10, fontweight='bold')
    ax1.set_title('SPX Rolling 60-Day Returns: Z-Score Analysis (10Y Lookback)', 
                  fontsize=12, fontweight='bold', pad=10)
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    shade_corrections(ax1, df_plot)
    
    # Plot 2: 5Y Z-score
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(df_plot['Date'], df_plot['zscore_5y'], 
             label='5Y Z-Score', color='#ff7f0e', linewidth=1.5)
    ax2.axhline(y=2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='+2 SD')
    ax2.axhline(y=-2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='-2 SD')
    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    ax2.set_ylabel('Z-Score (5Y)', fontsize=10, fontweight='bold')
    ax2.set_title('SPX Rolling 60-Day Returns: Z-Score Analysis (5Y Lookback)', 
                  fontsize=12, fontweight='bold', pad=10)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)
    shade_corrections(ax2, df_plot)
    
    # Plot 3: 3Y Z-score
    ax3 = fig.add_subplot(gs[2])
    ax3.plot(df_plot['Date'], df_plot['zscore_3y'], 
             label='3Y Z-Score', color='#2ca02c', linewidth=1.5)
    ax3.axhline(y=2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='+2 SD')
    ax3.axhline(y=-2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='-2 SD')
    ax3.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    ax3.set_ylabel('Z-Score (3Y)', fontsize=10, fontweight='bold')
    ax3.set_title('SPX Rolling 60-Day Returns: Z-Score Analysis (3Y Lookback)', 
                  fontsize=12, fontweight='bold', pad=10)
    ax3.legend(loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)
    shade_corrections(ax3, df_plot)
    
    # Plot 4: Consecutive Days Bar Chart
    ax4 = fig.add_subplot(gs[3])
    
    # Create colors: green for positive, red for negative
    colors = ['green' if x > 0 else 'red' for x in df_plot['consecutive_days']]
    
    ax4.bar(df_plot['Date'], df_plot['consecutive_days'], 
            color=colors, alpha=0.7, width=1)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_ylabel('Consecutive Days', fontsize=10, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=10, fontweight='bold')
    ax4.set_title('Consecutive Positive/Negative Return Days', 
                  fontsize=12, fontweight='bold', pad=10)
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Format x-axis for all plots
    for ax in [ax1, ax2, ax3, ax4]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.tick_params(axis='both', which='major', labelsize=9)
    
    plt.tight_layout()
    
    # Save figure
    filename = 'spx_rolling_analysis.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"✅ Chart saved as '{filename}'")
    
    plt.show()
    
    return fig

def shade_corrections(ax, df):
    """Add grey shading for correction periods"""
    # Find continuous correction periods
    in_correction = df['in_correction'].values
    dates = df['Date'].values
    
    start_idx = None
    for i in range(len(in_correction)):
        if in_correction[i] and start_idx is None:
            start_idx = i
        elif not in_correction[i] and start_idx is not None:
            # End of correction period
            ax.axvspan(dates[start_idx], dates[i-1], 
                      alpha=0.2, color='gray', linewidth=0)
            start_idx = None
    
    # Handle case where correction extends to end of data
    if start_idx is not None:
        ax.axvspan(dates[start_idx], dates[-1], 
                  alpha=0.2, color='gray', linewidth=0)

def print_summary_statistics(df):
    """Print summary statistics"""
    print(f"\n" + "="*60)
    print("📊 SUMMARY STATISTICS")
    print("="*60)
    
    # Latest values
    latest = df.iloc[-1]
    print(f"\n📅 Latest Data (as of {latest['Date'].date()}):")
    print(f"   SPX Close: ${latest['Close']:.2f}")
    print(f"   60-Day Log Return: {latest['rolling_60d_return']*100:.2f}%")
    print(f"   10Y Z-Score: {latest['zscore_10y']:.2f}")
    print(f"   5Y Z-Score: {latest['zscore_5y']:.2f}")
    print(f"   3Y Z-Score: {latest['zscore_3y']:.2f}")
    print(f"   Consecutive Days: {int(latest['consecutive_days'])}")
    print(f"   Drawdown from ATH: {latest['drawdown']*100:.2f}%")
    
    # Historical extremes
    print(f"\n📈 Historical Extremes (60-Day Returns):")
    max_return = df['rolling_60d_return'].max()
    max_date = df.loc[df['rolling_60d_return'].idxmax(), 'Date'].date()
    print(f"   Max Return: {max_return*100:.2f}% on {max_date}")
    
    min_return = df['rolling_60d_return'].min()
    min_date = df.loc[df['rolling_60d_return'].idxmin(), 'Date'].date()
    print(f"   Min Return: {min_return*100:.2f}% on {min_date}")
    
    # Z-score extremes
    print(f"\n📊 Z-Score Extremes:")
    for period in ['10y', '5y', '3y']:
        col = f'zscore_{period}'
        max_z = df[col].max()
        max_z_date = df.loc[df[col].idxmax(), 'Date'].date()
        min_z = df[col].min()
        min_z_date = df.loc[df[col].idxmin(), 'Date'].date()
        print(f"   {period.upper()}: Max {max_z:.2f} ({max_z_date}), Min {min_z:.2f} ({min_z_date})")
    
    # Correction statistics
    total_days = len(df)
    correction_days = df['in_correction'].sum()
    pct_in_correction = (correction_days / total_days) * 100
    print(f"\n🔻 Correction Statistics:")
    print(f"   Days in correction: {correction_days} ({pct_in_correction:.1f}% of total)")
    print(f"   Max drawdown: {df['drawdown'].min()*100:.2f}%")
    
    print(f"\n" + "="*60)

def main():
    """Main execution function"""
    print("="*60)
    print("🚀 SPX ROLLING 60-DAY RETURNS ANALYSIS")
    print("="*60)
    
    try:
        # Fetch data
        df = fetch_spx_data(years_back=15)
        
        # Calculate metrics
        df = calculate_rolling_returns(df, window=60)
        df = calculate_z_scores(df)
        df = calculate_consecutive_days(df)
        df = identify_corrections(df, threshold=0.10)
        
        # Print summary
        print_summary_statistics(df)
        
        # Create visualizations
        create_visualizations(df)
        
        # Optionally save data to CSV
        output_file = 'spx_rolling_analysis_data.csv'
        df.to_csv(output_file, index=False)
        print(f"\n💾 Data saved to '{output_file}'")
        
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


