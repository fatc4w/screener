"""
China FX Dashboard - Streamlit App
CNY/USD and FX Settlement Chart
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime
import os

st.set_page_config(page_title="China FX Dashboard", page_icon="🇨🇳", layout="wide")

# ============================================================
# DATA FUNCTIONS
# ============================================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def scrape_fx_settlement():
    """Scrape FX Settlement data from SAFE China"""
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
    
    # Build arrays for rows 22 and 37
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
    
    # FX Settlement = Row 22 + Row 37 MoM change (convert to billions)
    row_37_mom = np.diff(row_37_vals, prepend=np.nan)
    fx_settlement = (row_22_vals + row_37_mom) / 10
    
    dates = pd.to_datetime(valid_months, format='%b %Y')
    
    return pd.DataFrame({'Date': dates, 'FX_Settlement': fx_settlement})


@st.cache_data(ttl=3600)
def get_usdcny_spot(start_date='2023-01-01'):
    """Get USDCNY spot rate from yfinance"""
    ticker = yf.Ticker("CNY=X")
    df = ticker.history(start=start_date)
    return pd.DataFrame({
        'Date': df.index.tz_localize(None),
        'USDCNY_Spot': df['Close'].values
    })


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_parity_rate():
    """Load PBOC central parity rate from local file"""
    # Try relative path first (for Streamlit Cloud), then absolute (for local)
    filepath = 'data/parity_rate_monthly.xlsx'
    if not os.path.exists(filepath):
        filepath = '/Users/ravelai/Downloads/Monthly_Average_Central_Parity_Historical_Data (1).xlsx'
    
    df = pd.read_excel(filepath)
    
    # Filter out footer rows
    df = df[df['Date'].notna() & ~df['Date'].astype(str).str.contains('Data source|www\\.', na=False)]
    
    parity_df = pd.DataFrame({
        'Date': pd.to_datetime(df['Date'], format='%b %Y', errors='coerce'),
        'Parity_Rate': pd.to_numeric(df['USD/CNY'], errors='coerce')
    })
    
    parity_df = parity_df.dropna(subset=['Date'])
    parity_df = parity_df.sort_values('Date').reset_index(drop=True)
    parity_df['Band_Upper'] = parity_df['Parity_Rate'] * 1.02
    parity_df['Band_Lower'] = parity_df['Parity_Rate'] * 0.98
    
    return parity_df


# ============================================================
# CHART FUNCTION
# ============================================================

def create_chart(fx_df, spot_df, parity_df, start_date='2023-01-01'):
    """Create the CNY/USD and Settlement chart using Plotly"""
    start = pd.to_datetime(start_date)
    fx_filtered = fx_df[fx_df['Date'] >= start].copy()
    spot_filtered = spot_df[spot_df['Date'] >= start].copy()
    parity_filtered = parity_df[parity_df['Date'] >= start].copy()
    
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 2% trading band (shaded area)
    fig.add_trace(
        go.Scatter(
            x=parity_filtered['Date'], y=parity_filtered['Band_Upper'],
            fill=None, mode='lines', line=dict(color='rgba(255,0,0,0.5)', width=0.5),
            name='2% band upper', showlegend=False
        ), secondary_y=False
    )
    fig.add_trace(
        go.Scatter(
            x=parity_filtered['Date'], y=parity_filtered['Band_Lower'],
            fill='tonexty', mode='lines', line=dict(color='rgba(255,0,0,0.5)', width=0.5),
            fillcolor='rgba(255,200,200,0.3)', name='2% trading band'
        ), secondary_y=False
    )
    
    # PBOC central parity rate
    fig.add_trace(
        go.Scatter(
            x=parity_filtered['Date'], y=parity_filtered['Parity_Rate'],
            mode='lines', line=dict(color='#666666', width=2.5),
            name='PBOC central parity rate'
        ), secondary_y=False
    )
    
    # CNY Spot Rate
    fig.add_trace(
        go.Scatter(
            x=spot_filtered['Date'], y=spot_filtered['USDCNY_Spot'],
            mode='lines', line=dict(color='#0066CC', width=2),
            name='CNY Spot Rate'
        ), secondary_y=False
    )
    
    # FX Settlement (step chart on right axis)
    fig.add_trace(
        go.Scatter(
            x=fx_filtered['Date'], y=fx_filtered['FX_Settlement'],
            mode='lines', line=dict(color='#000000', width=3, shape='hv'),
            name='Settlement (rhs)'
        ), secondary_y=True
    )
    
    # Update layout with white background
    fig.update_layout(
        title=dict(
            text='<b>CNY/USD (lhs) and Settlement in USD Billion (rhs)</b>',
            font=dict(size=20, color='#CC0000'),
            x=0.5
        ),
        height=600,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black')
    )
    
    # Update y-axes (invert left axis for FX convention)
    fig.update_yaxes(
        title_text="CNY/USD", 
        autorange="reversed", 
        secondary_y=False,
        gridcolor='#E5E5E5',
        showgrid=True
    )
    fig.update_yaxes(
        title_text="USD Billion", 
        secondary_y=True,
        gridcolor='#E5E5E5',
        showgrid=True
    )
    
    # Add zero line on right axis
    fig.add_hline(y=0, line_dash="dash", line_color="#999999", line_width=1.5, secondary_y=True)
    
    return fig


# ============================================================
# MAIN APP
# ============================================================

st.title("🇨🇳 China FX Dashboard")
st.markdown("**CNY/USD Exchange Rate and FX Settlement Data**")

# Load data with status
with st.spinner("Loading FX Settlement from SAFE China..."):
    fx_df = scrape_fx_settlement()

with st.spinner("Loading USDCNY Spot from Yahoo Finance..."):
    spot_df = get_usdcny_spot(start_date='2023-01-01')

with st.spinner("Loading PBOC Central Parity Rate..."):
    parity_df = load_parity_rate()

# Time frame selector
st.markdown("### Select Time Frame")
col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

with col1:
    if st.button("3Y", use_container_width=True):
        start_date = pd.to_datetime('today') - pd.DateOffset(years=3)
        st.session_state['start_date'] = start_date
        
with col2:
    if st.button("10Y", use_container_width=True):
        start_date = pd.to_datetime('today') - pd.DateOffset(years=10)
        st.session_state['start_date'] = start_date
        
with col3:
    if st.button("ALL", use_container_width=True):
        start_date = pd.to_datetime('2010-01-01')
        st.session_state['start_date'] = start_date

# Initialize session state
if 'start_date' not in st.session_state:
    st.session_state['start_date'] = pd.to_datetime('2023-01-01')

start_date = st.session_state['start_date']

with col4:
    st.info(f"📅 Showing data from: **{start_date.strftime('%b %Y')}** to present")

# Create and display chart
fig = create_chart(fx_df, spot_df, parity_df, start_date=str(start_date))
st.plotly_chart(fig, use_container_width=True)

# Data info
st.markdown("---")
st.markdown("### Data Sources")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("FX Settlement", f"{len(fx_df)} months", f"{fx_df['Date'].min().strftime('%b %Y')} - {fx_df['Date'].max().strftime('%b %Y')}")
with col2:
    st.metric("CNY Spot Rate", f"{len(spot_df)} days", f"{spot_df['Date'].min().strftime('%Y-%m-%d')} - {spot_df['Date'].max().strftime('%Y-%m-%d')}")
with col3:
    st.metric("Parity Rate", f"{len(parity_df)} months", f"{parity_df['Date'].min().strftime('%b %Y')} - {parity_df['Date'].max().strftime('%b %Y')}")

st.markdown("""
**Sources:**
- FX Settlement: [SAFE China](https://www.safe.gov.cn/en/2023/0215/2048.html)
- CNY Spot Rate: Yahoo Finance (CNY=X)
- PBOC Central Parity Rate: China Foreign Exchange Trade System (CFETS)

**Formula:** FX Settlement = Row 22 + Row 37 MoM change (in USD Billion)
""")
