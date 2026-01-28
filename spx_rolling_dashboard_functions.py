"""
SPX 60-Day Rolling Tracker Functions for Dashboard Integration
Add these functions to app.py
"""

import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta

# ================== BUILD FUNCTION ==================
@st.cache_data(ttl=900, show_spinner=False)
def build_spx_60d_rolling(tf: str) -> pd.DataFrame:
    """
    Build SPX 60-day rolling returns with Z-scores and consecutive days tracking
    Returns dataframe with:
    - date
    - SPX price
    - rolling_60d_return (log return)
    - zscore_10y, zscore_5y, zscore_3y
    - consecutive_days (positive/negative streaks)
    - in_correction (boolean for >10% drawdown)
    """
    try:
        # Always fetch 15 years for proper Z-score calculations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=15 * 365 + 180)
        
        ticker = yf.Ticker("^GSPC")
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        df = df.reset_index()
        df['date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        df['Close'] = df['Close']
        df = df.sort_values('date').reset_index(drop=True)
        
        # 1. Calculate rolling 60-day log returns
        df['daily_log_return'] = np.log(df['Close'] / df['Close'].shift(1))
        df['rolling_60d_return'] = np.log(df['Close'] / df['Close'].shift(60))
        
        # 2. Calculate Z-scores for different lookback windows
        lookback_periods = {'10y': 10*252, '5y': 5*252, '3y': 3*252}
        
        for name, days in lookback_periods.items():
            df[f'mean_{name}'] = df['rolling_60d_return'].rolling(window=days, min_periods=days//2).mean()
            df[f'std_{name}'] = df['rolling_60d_return'].rolling(window=days, min_periods=days//2).std()
            df[f'zscore_{name}'] = (df['rolling_60d_return'] - df[f'mean_{name}']) / df[f'std_{name}']
        
        # 3. Calculate consecutive positive/negative days
        df['is_positive'] = (df['daily_log_return'] > 0).astype(int)
        df['is_positive'] = df['is_positive'].replace(0, -1)
        df['streak_id'] = (df['is_positive'] != df['is_positive'].shift()).cumsum()
        df['consecutive_days'] = df.groupby('streak_id').cumcount() + 1
        df['consecutive_days'] = df['consecutive_days'] * df['is_positive']
        
        # 4. Identify correction periods (>10% from ATH)
        df['ath'] = df['Close'].expanding().max()
        df['drawdown'] = (df['Close'] - df['ath']) / df['ath']
        df['in_correction'] = df['drawdown'] <= -0.10
        
        # 5. Filter to display timeframe
        if tf.upper() != "MAX":
            from datetime import date
            if tf.upper() == "5Y":
                cutoff = end_date - timedelta(days=5*365)
            elif tf.upper() == "3Y":
                cutoff = end_date - timedelta(days=3*365)
            elif tf.upper() == "1Y":
                cutoff = end_date - timedelta(days=365)
            elif tf.upper() == "6M":
                cutoff = end_date - timedelta(days=180)
            elif tf.upper() == "3M":
                cutoff = end_date - timedelta(days=90)
            elif tf.upper() == "1M":
                cutoff = end_date - timedelta(days=30)
            else:
                cutoff = end_date - timedelta(days=10*365)  # Default 10Y view
            
            df = df[df['date'] >= cutoff]
        
        return df[['date', 'Close', 'rolling_60d_return', 'zscore_10y', 'zscore_5y', 
                   'zscore_3y', 'consecutive_days', 'in_correction', 'drawdown']]
    
    except Exception as e:
        print(f"Error building SPX 60d rolling: {e}")
        return pd.DataFrame()


# ================== RENDER FUNCTION ==================
def render_spx_60d_rolling(tf: str, fullscreen: bool = False):
    """
    Render SPX 60-day rolling returns analysis with 4 subplots:
    - 10Y Z-score
    - 5Y Z-score  
    - 3Y Z-score
    - Consecutive days (area chart)
    """
    df = build_spx_60d_rolling(tf)
    
    if df.empty:
        st.caption("No SPX 60-day rolling data available")
        return
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        row_heights=[0.25, 0.25, 0.25, 0.25],
        vertical_spacing=0.08,
        subplot_titles=(
            "SPX 60-Day Rolling Returns: 10Y Z-Score",
            "SPX 60-Day Rolling Returns: 5Y Z-Score",
            "SPX 60-Day Rolling Returns: 3Y Z-Score",
            "Consecutive Positive/Negative Days"
        )
    )
    
    # Add grey shading for correction periods to all subplots
    for row in [1, 2, 3, 4]:
        # Find correction periods
        in_corr = df['in_correction'].values
        dates = df['date'].values
        
        i = 0
        while i < len(in_corr):
            if in_corr[i]:
                start_idx = i
                while i < len(in_corr) and in_corr[i]:
                    i += 1
                end_idx = i - 1
                
                fig.add_vrect(
                    x0=dates[start_idx], x1=dates[end_idx],
                    fillcolor="gray", opacity=0.2, layer="below", line_width=0,
                    row=row, col=1
                )
            i += 1
    
    # Plot 1: 10Y Z-score
    fig.add_trace(
        go.Scatter(x=df['date'], y=df['zscore_10y'], name='10Y Z-Score',
                   line=dict(color='#1f77b4', width=2), mode='lines'),
        row=1, col=1
    )
    fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.7, row=1, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="red", opacity=0.7, row=1, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.3, row=1, col=1)
    
    # Plot 2: 5Y Z-score
    fig.add_trace(
        go.Scatter(x=df['date'], y=df['zscore_5y'], name='5Y Z-Score',
                   line=dict(color='#ff7f0e', width=2), mode='lines'),
        row=2, col=1
    )
    fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.7, row=2, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="red", opacity=0.7, row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.3, row=2, col=1)
    
    # Plot 3: 3Y Z-score
    fig.add_trace(
        go.Scatter(x=df['date'], y=df['zscore_3y'], name='3Y Z-Score',
                   line=dict(color='#2ca02c', width=2), mode='lines'),
        row=3, col=1
    )
    fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.7, row=3, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="red", opacity=0.7, row=3, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.3, row=3, col=1)
    
    # Plot 4: Consecutive days (area chart)
    # Split positive and negative for different colors
    df_pos = df[df['consecutive_days'] >= 0].copy()
    df_neg = df[df['consecutive_days'] < 0].copy()
    
    fig.add_trace(
        go.Scatter(x=df_pos['date'], y=df_pos['consecutive_days'], 
                   fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.3)',
                   line=dict(color='green', width=0.5), name='Positive Days',
                   mode='lines'),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(x=df_neg['date'], y=df_neg['consecutive_days'], 
                   fill='tozeroy', fillcolor='rgba(255, 0, 0, 0.3)',
                   line=dict(color='red', width=0.5), name='Negative Days',
                   mode='lines'),
        row=4, col=1
    )
    fig.add_hline(y=0, line_color="black", line_width=1, row=4, col=1)
    
    # Update layout
    fig.update_layout(
        template="plotly_dark",
        height=1000 if fullscreen else 700,
        margin=dict(l=10, r=10, t=60, b=10),
        showlegend=False,
        paper_bgcolor="#11141b",
        plot_bgcolor="#11141b",
        hovermode="x unified"
    )
    
    # Update axes
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#22263a", title_text="Z-Score", row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor="#22263a", title_text="Z-Score", row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor="#22263a", title_text="Z-Score", row=3, col=1)
    fig.update_yaxes(showgrid=True, gridcolor="#22263a", title_text="Days", row=4, col=1)
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    
    # Add description
    latest = df.iloc[-1]
    st.caption(f"""
    **SPX 60-Day Rolling Returns Analysis:**  
    Latest 60d return: {latest['rolling_60d_return']*100:.2f}% | 
    10Y Z-score: {latest['zscore_10y']:.2f} | 
    5Y Z-score: {latest['zscore_5y']:.2f} | 
    3Y Z-score: {latest['zscore_3y']:.2f} | 
    Streak: {int(latest['consecutive_days'])} days | 
    Drawdown: {latest['drawdown']*100:.2f}%  
    
    Grey shading indicates correction periods (>10% from ATH). Red dashed lines mark +/-2 standard deviations.
    """)


# ================== Z-SCORE CALCULATOR (for other charts) ==================
def calculate_5y_zscore(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Add 5-year Z-score column to any dataframe
    Args:
        df: DataFrame with 'date' and value column
        value_col: Name of the column to calculate Z-score for
    Returns:
        DataFrame with additional 'zscore_5y' column
    """
    if df.empty or value_col not in df.columns:
        return df
    
    df = df.sort_values('date').copy()
    
    # 5-year window = approximately 1260 trading days
    window = 1260
    
    df[f'{value_col}_mean_5y'] = df[value_col].rolling(window=window, min_periods=window//2).mean()
    df[f'{value_col}_std_5y'] = df[value_col].rolling(window=window, min_periods=window//2).std()
    df['zscore_5y'] = (df[value_col] - df[f'{value_col}_mean_5y']) / df[f'{value_col}_std_5y']
    
    return df


# ================== USAGE INSTRUCTIONS ==================
"""
INTEGRATION STEPS:

1. Add these functions to app.py (after the existing build_ functions)

2. Update CHARTS registry to include:
   "us_spx_60d_rolling": ("SPX 60-Day Rolling Tracker", render_spx_60d_rolling),

3. Replace line 2520 in app.py:
   OLD: chart_card("us_zscore", "SPX & Nasdaq 10-Year Z-Scores", render_zscore_spx_nasdaq, default_tf="5y")
   NEW: chart_card("us_spx_60d_rolling", "SPX 60-Day Rolling Tracker", render_spx_60d_rolling, default_tf="5y")

4. For Z-Score toggles on 2s10s, 2s5s10s, VVIX-VIX:
   - Modify their render functions to accept a 'show_zscore' parameter
   - Add a st.toggle() widget in the header
   - If toggled, apply calculate_5y_zscore() to the data before plotting
   
5. Test with: streamlit run app.py
"""

