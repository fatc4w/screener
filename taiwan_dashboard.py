# Taiwan FX Correlation Dashboard (Streamlit)
# -------------------------------------------------------------
# Quick start:
#   1) pip install streamlit requests plotly pandas numpy
#   2) streamlit run taiwan_dashboard.py
#   3) Put keys in .streamlit/secrets.toml or paste in sidebar:
#        POLYGON_API_KEY="..."
# -------------------------------------------------------------

import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import re

# -------------------- Page config --------------------
st.set_page_config(page_title="Taiwan FX Dashboard", layout="wide", initial_sidebar_state="collapsed")

# -------------------- Live Auto-Refresh --------------------
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_refresh >= 300:  # 5 minute refresh
    st.session_state.last_refresh = current_time
    st.rerun()

# -------------------- Styling ------------------------
DARK_BG = "#0e1117"
DARK_CARD = "#11141b"

st.markdown(
    f"""
    <style>
        .stApp {{ background: {DARK_BG}; }}
        .block-container {{ padding-top: 1rem; padding-bottom: 2rem; }}
        h1, h2, h3, h4, h5, h6, p, span, label {{ color: #e5e7eb !important; }}
        
        .chart-card {{ 
            background: {DARK_CARD}; 
            border-radius: 16px; 
            padding: 16px; 
            border: 1px solid #20243a;
            margin-bottom: 20px;
        }}
        
        .chart-title {{ 
            font-weight: 600;
            font-size: 18px;
            color: #f3f4f6;
            margin-bottom: 12px;
        }}
        
        .timeframe-container {{
            margin-bottom: 16px;
        }}
        
        .stButton > button {{
            background: #1f2937;
            color: #e5e7eb;
            border: 1px solid #374151;
            border-radius: 8px;
            white-space: nowrap;
            width: 100%;
        }}
        
        .stButton > button:hover {{ 
            border-color: #4b5563; 
        }}

        .hint {{ color:#9ca3af; font-size:12px; }}
        
        .stat-box {{
            background: {DARK_CARD};
            border-radius: 8px;
            padding: 12px 16px;
            border: 1px solid #374151;
            margin-bottom: 12px;
        }}
        
        .stat-label {{
            color: #9ca3af;
            font-size: 12px;
            margin-bottom: 4px;
        }}
        
        .stat-value {{
            color: #f3f4f6;
            font-size: 20px;
            font-weight: 600;
        }}
        
        .national-stats-container {{
            background: {DARK_CARD};
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #374151;
            margin-bottom: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .national-stats-container:hover {{
            border-color: #4b5563;
            background: #1a1d29;
            transform: translateY(-2px);
        }}
        
        .national-stats-title {{
            font-size: 22px;
            font-weight: 600;
            color: #f3f4f6;
            margin-bottom: 8px;
        }}
        
        .national-stats-description {{
            color: #9ca3af;
            font-size: 14px;
            margin-top: 8px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 style='margin:0 0 12px 0;'>Taiwan food is the best</h1>", unsafe_allow_html=True)

# Force cache clear on every page load to ensure fresh data
if 'cache_cleared' not in st.session_state:
    st.cache_data.clear()
    st.session_state['cache_cleared'] = True

# -------------------- Keys ---------------------------
try:
    DEFAULT_POLY = os.getenv("POLYGON_API_KEY") or st.secrets.get("POLYGON_API_KEY", "")
except Exception:
    DEFAULT_POLY = os.getenv("POLYGON_API_KEY", "")

# Hardcoded key as fallback (from notebook)
HARDCODED_KEY = "REDACTED"

with st.sidebar:
    st.subheader("API Keys")
    poly_key = st.text_input("Polygon.io API Key", type="password", value=DEFAULT_POLY or HARDCODED_KEY)
    fred_key = st.text_input("FRED API Key", type="password", value="REDACTED")
    st.caption("Keys are kept in memory only for this session.")

# -------------------- Utilities ----------------------
TF_LABELS = ["1m", "3m", "6m", "YTD", "1y", "2y", "5y", "10y", "MAX"]
POLY_FOREX_EARLIEST = date(2009, 9, 25)
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
TAIPEI_TZ = timezone(timedelta(hours=8))

def adjust_to_previous_weekday(target_date: date) -> date:
    """Return the latest weekday on or before target_date."""
    while target_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        target_date -= timedelta(days=1)
    return target_date

def get_market_reference_date() -> date:
    """
    Determine the date we expect data for (Taipei timezone, weekends handled).
    Returns today's date if it's a weekday in Taipei timezone, otherwise the previous weekday.
    """
    now_local = datetime.now(TAIPEI_TZ)
    today_local = now_local.date()
    return adjust_to_previous_weekday(today_local)

def ticker_to_currency_pair(ticker: str) -> Tuple[str, str]:
    """
    Convert Polygon FX ticker (e.g., C:USDTWD) to (base, quote) tuple for last quote endpoint.
    """
    symbol = ticker.split(":")[-1] if ":" in ticker else ticker
    if len(symbol) < 6:
        raise ValueError(f"Unrecognized FX ticker format: {ticker}")
    base = symbol[:3]
    quote = symbol[3:]
    return base, quote

def fetch_latest_fx_quote(ticker: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest intraday FX quote (bid/ask) for a currency pair.
    Returns dict with price and date (in Taipei timezone) if available.
    """
    try:
        base, quote = ticker_to_currency_pair(ticker)
    except ValueError:
        return None
    
    url = f"https://api.polygon.io/v1/last_quote/currencies/{base}/{quote}"
    params = {"apiKey": api_key}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if not response.ok:
            return None
        data = response.json()
        last_quote = data.get("last")
        if not last_quote:
            return None
        
        bid = last_quote.get("bid")
        ask = last_quote.get("ask")
        price = None
        if bid is not None and ask is not None:
            price = (bid + ask) / 2
        else:
            price = bid or ask
        if price is None:
            return None
        
        timestamp = last_quote.get("timestamp")
        if not timestamp:
            return None
        ts_local = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).astimezone(TAIPEI_TZ)
        return {"price": float(price), "datetime": ts_local, "date": ts_local.date()}
    except Exception:
        return None

def maybe_update_with_intraday(df: pd.DataFrame, ticker: str, api_key: str) -> pd.DataFrame:
    """
    Ensure the FX DataFrame includes the latest market date.
    If daily aggregates are missing today's data, supplement with latest intraday quote.
    """
    if df.empty or "close" not in df.columns:
        return df
    
    try:
        latest_date = df["date"].max().date()
    except Exception:
        return df
    
    market_date = get_market_reference_date()
    if latest_date >= market_date:
        return df
    
    latest_quote = fetch_latest_fx_quote(ticker, api_key)
    if not latest_quote:
        return df
    
    quote_date = latest_quote.get("date")
    price = latest_quote.get("price")
    if not quote_date or price is None or quote_date < market_date:
        return df
    
    quote_ts = pd.Timestamp(quote_date)
    df_dates = df["date"].dt.date
    
    if quote_ts.date() in df_dates.values:
        # Update existing row for today
        idx = df[df_dates == quote_ts.date()].index[-1]
        df.loc[idx, "close"] = price
    else:
        new_row = pd.DataFrame([{"date": quote_ts, "close": price}])
        df = pd.concat([df[["date", "close"]], new_row], ignore_index=True)
    
    df = df.sort_values("date").reset_index(drop=True)
    df["returns"] = df["close"].pct_change()
    return df

def today_utc_date() -> date:
    return datetime.now(timezone.utc).date()

def tf_to_daterange(tf: str) -> Tuple[date, date]:
    end = today_utc_date()
    t = tf.upper()
    if t == "1M": return end - timedelta(days=31), end
    if t == "3M": return end - timedelta(days=93), end
    if t == "6M": return end - timedelta(days=186), end
    if t == "YTD": return date(end.year, 1, 1), end
    if t == "1Y": return end - timedelta(days=365), end
    if t == "2Y": return end - timedelta(days=365*2), end
    if t == "5Y": return end - timedelta(days=365*5), end
    if t == "10Y": return end - timedelta(days=365*10), end
    if t == "MAX": return date(1900, 1, 1), end  # Very early date to get all data
    return end - timedelta(days=365), end

# -------------------- Currency Config ----------------
CURRENCY_PAIRS = {
    'TWD': 'C:USDTWD',
    'CNH': 'C:USDCNH', 
    'THB': 'C:USDTHB',
    'AUD': 'C:USDAUD',
    'SGD': 'C:USDSGD',
    'KRW': 'C:USDKRW',
    'JPY': 'C:USDJPY'
}

FX_COLOR_MAP = {
    'CNH': '#1f77b4',  # Blue
    'THB': '#ff7f0e',  # Orange
    'AUD': '#2ca02c',  # Green
    'SGD': '#d62728',  # Red
    'KRW': '#9467bd',  # Purple
    'JPY': '#8c564b'   # Brown
}

CORRELATION_WINDOW = 21  # ~1 month of trading days

# -------------------- Data Fetchers ------------------
def fetch_fred_series(
    series_id: str,
    api_key: str,
    observation_start: Optional[date] = None,
    observation_end: Optional[date] = None,
) -> pd.DataFrame:
    """
    Fetch data from FRED API
    
    Parameters:
    -----------
    series_id : str
        FRED series ID (e.g., 'TRESEGTWM194N')
    api_key : str
        FRED API key
    observation_start : Optional[date]
        Start date for observations (if None, gets all available data)
    observation_end : Optional[date]
        End date for observations (if None, gets all available data)
    
    Returns:
    --------
    pd.DataFrame with columns: date, value
    """
    if not api_key:
        return pd.DataFrame()
    
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json"
    }
    
    if observation_start is not None:
        params["observation_start"] = observation_start.isoformat()
    if observation_end is not None:
        params["observation_end"] = observation_end.isoformat()
    
    try:
        response = requests.get(FRED_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        observations = data.get("observations", [])
        if not observations:
            return pd.DataFrame()
        
        df = pd.DataFrame(observations)
        # Filter out "." values (FRED uses "." for missing data)
        df = df[df["value"] != "."].copy()
        
        # Convert date column
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        
        # Convert value to numeric
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        
        # Remove NaN values
        df = df.dropna(subset=["value"])
        
        # Rename value column to series_id for clarity
        df = df.rename(columns={"value": series_id})
        
        return df[["date", series_id]].sort_values("date")
    
    except Exception as e:
        st.warning(f"Error fetching FRED series {series_id}: {e}")
        return pd.DataFrame()

def fetch_fx_data_polygon(ticker: str, start_date: str, end_date: str, api_key: str, _force_refresh: int = 0) -> pd.DataFrame:
    """
    Fetch FX data from Polygon.io aggregates endpoint
    
    Parameters:
    -----------
    _force_refresh : int
        Internal parameter to force cache refresh (use timestamp)
    """
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "apikey": api_key
    }
    
    all_data = []
    next_url = None
    
    try:
        while True:
            if next_url:
                response = requests.get(next_url, params={"apikey": api_key}, timeout=30)
            else:
                response = requests.get(url, params=params, timeout=30)
            
            if not response.ok:
                break
                
            data = response.json()
            
            if data.get("status") == "OK":
                results = data.get("results", [])
                if not results:
                    break
                all_data.extend(results)
                next_url = data.get("next_url")
                if not next_url:
                    break
            else:
                break
                
    except Exception as e:
        st.warning(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()
    
    if not all_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data)
    # Convert timestamp to datetime, then normalize to date-only (no time component)
    df['date'] = pd.to_datetime(df['t'], unit='ms').dt.normalize()
    df = df.rename(columns={'c': 'close'})
    df = df[['date', 'close']].sort_values('date').reset_index(drop=True)
    df['returns'] = df['close'].pct_change()
    
    return df

def fetch_all_fx_data(api_key: str, years_back: int = 10, _force_refresh: int = 0) -> Dict[str, pd.DataFrame]:
    """Fetch FX data for all currency pairs
    
    Parameters:
    -----------
    _force_refresh : int
        Internal parameter to force cache refresh (use timestamp)
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years_back*365)).strftime("%Y-%m-%d")
    
    fx_data = {}
    
    for currency, ticker in CURRENCY_PAIRS.items():
        df = fetch_fx_data_polygon(ticker, start_date, end_date, api_key, _force_refresh=_force_refresh)
        if not df.empty:
            df = maybe_update_with_intraday(df, ticker, api_key)
            fx_data[currency] = df
    
    return fx_data

def fetch_twd_seasonality_data(api_key: str, _force_refresh: int = 0) -> pd.DataFrame:
    """Fetch USDTWD data from 2016 to present for seasonality analysis
    
    Args:
        api_key: Polygon API key
        _force_refresh: Internal parameter to force cache refresh (use timestamp)
    """
    start_date = "2016-01-01"
    # Request data up to tomorrow (UTC) to ensure we get the latest possible aggregates
    today_utc = datetime.now(timezone.utc).date()
    end_date = (today_utc + timedelta(days=1)).strftime("%Y-%m-%d")
    market_reference_date = get_market_reference_date()
    
    twd_ticker = 'C:USDTWD'
    twd_df = fetch_fx_data_polygon(twd_ticker, start_date, end_date, api_key, _force_refresh=_force_refresh)
    
    if not twd_df.empty:
        # Ensure we have the most recent market date by supplementing with intraday quotes if needed
        twd_df = maybe_update_with_intraday(twd_df, twd_ticker, api_key)
        # Ensure dates are normalized (no time component)
        twd_df['date'] = pd.to_datetime(twd_df['date']).dt.normalize()
        # Filter out any future dates beyond the market reference date
        twd_df = twd_df[twd_df['date'].dt.date <= market_reference_date].copy()
        # Sort by date to ensure proper ordering and recompute returns
        twd_df = twd_df.sort_values('date').reset_index(drop=True)
        twd_df['returns'] = twd_df['close'].pct_change()
        # Add year, month, day columns for analysis
        twd_df['year'] = twd_df['date'].dt.year
        twd_df['month'] = twd_df['date'].dt.month
        twd_df['day'] = twd_df['date'].dt.day
        twd_df['day_of_year'] = twd_df['date'].dt.dayofyear
    
    return twd_df

def build_correlation_data(api_key: str, _force_refresh: int = 0) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Build correlation DataFrame and metadata
    Returns: (aligned_returns_df, correlation_df, metadata)
    
    Parameters:
    -----------
    _force_refresh : int
        Internal parameter to force cache refresh (use timestamp)
    """
    fx_data = fetch_all_fx_data(api_key, years_back=10, _force_refresh=_force_refresh)
    
    if 'TWD' not in fx_data or len(fx_data) < 2:
        return pd.DataFrame(), pd.DataFrame(), {}
    
    # Align all FX data to common dates
    twd_df = fx_data['TWD'][['date', 'returns']].copy()
    twd_df = twd_df.rename(columns={'returns': 'TWD'})
    
    for currency in ['CNH', 'THB', 'AUD', 'SGD', 'KRW', 'JPY']:
        if currency in fx_data:
            curr_df = fx_data[currency][['date', 'returns']].copy()
            curr_df = curr_df.rename(columns={'returns': currency})
            twd_df = twd_df.merge(curr_df, on='date', how='inner')
    
    twd_df = twd_df.dropna()
    
    if len(twd_df) < CORRELATION_WINDOW:
        return pd.DataFrame(), pd.DataFrame(), {}
    
    # Calculate rolling correlations
    corr_df = pd.DataFrame({'date': twd_df['date'].values})
    
    for currency in ['CNH', 'THB', 'AUD', 'SGD', 'KRW', 'JPY']:
        if currency in twd_df.columns:
            rolling_corr = []
            for i in range(len(twd_df)):
                if i < CORRELATION_WINDOW - 1:
                    rolling_corr.append(np.nan)
                else:
                    window_data = twd_df[['TWD', currency]].iloc[i-CORRELATION_WINDOW+1:i+1]
                    if window_data['TWD'].notna().sum() >= CORRELATION_WINDOW * 0.8 and \
                       window_data[currency].notna().sum() >= CORRELATION_WINDOW * 0.8:
                        corr_val = window_data['TWD'].corr(window_data[currency])
                        rolling_corr.append(corr_val)
                    else:
                        rolling_corr.append(np.nan)
            corr_df[currency] = rolling_corr
    
    corr_df = corr_df.dropna()
    
    # Build metadata
    sample_start = corr_df['date'].min()
    sample_end = corr_df['date'].max()
    sample_years = (sample_end - sample_start).days / 365.25
    
    metadata = {
        'sample_start': sample_start,
        'sample_end': sample_end,
        'sample_years': sample_years,
        'sample_label': f"{sample_start.year}–{sample_end.year}",
        'total_obs': len(corr_df)
    }
    
    return twd_df, corr_df, metadata

# -------------------- Plot helpers -------------------
PLOTLY_TEMPLATE = "plotly_dark"

def seg_control(options: List[str], key: str, default: str = "1y") -> str:
    try:
        result = st.segmented_control(
            "Timeframe", options=options, default=default, key=key, label_visibility="collapsed"
        )
        # Return default if result is None (can happen on first render)
        return result if result is not None else default
    except Exception:
        result = st.radio(
            "Timeframe", options=options, index=options.index(default) if default in options else 0, 
            horizontal=True, key=key, label_visibility="collapsed"
        )
        return result if result is not None else default

def chart_card(chart_id: str, title: str, renderer, *, default_tf: str = "1y", has_timeframe: bool = True):
    """Chart card component - full width"""
    with st.container():
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f"<div class='chart-title'>{title}</div>", unsafe_allow_html=True)
        
        if has_timeframe:
            st.markdown('<div class="timeframe-container">', unsafe_allow_html=True)
            tf = seg_control(TF_LABELS, key=f"tf_{chart_id}", default=default_tf)
            st.markdown('</div>', unsafe_allow_html=True)
            renderer(tf)
        else:
            renderer()
        
        st.markdown("</div>", unsafe_allow_html=True)

def chart_card_no_tf(chart_id: str, title: str, renderer):
    """Chart card without timeframe controls"""
    chart_card(chart_id, title, renderer, has_timeframe=False)

# -------------------- Renderers ----------------------

def render_twd_rolling_correlations(tf: str):
    """Render TWD Rolling 1-Month Correlations with Asian Currencies"""
    # Use current minute timestamp to force cache refresh every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    _, corr_df, metadata = build_correlation_data(poly_key, _force_refresh=cache_buster)
    
    if corr_df.empty:
        st.warning("No correlation data available. Check API key and data availability.")
        return
    
    # Ensure tf is valid
    if tf is None or tf not in TF_LABELS:
        tf = "5y"  # Default fallback
    
    # Filter by timeframe
    start, end = tf_to_daterange(tf)
    df_filtered = corr_df[
        (corr_df['date'].dt.date >= start) & 
        (corr_df['date'].dt.date <= end)
    ].copy()
    
    if df_filtered.empty:
        st.warning(f"No data available for the selected timeframe ({tf}).")
        return
    
    # Create figure
    fig = go.Figure()
    
    for currency in ['CNH', 'THB', 'AUD', 'SGD', 'KRW', 'JPY']:
        if currency in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered['date'],
                y=df_filtered[currency],
                name=currency,
                line=dict(width=2, color=FX_COLOR_MAP[currency]),
                opacity=0.85,
                hovertemplate=f'<b>{currency}</b><br>' +
                             'Date: %{x|%Y-%m-%d}<br>' +
                             'Correlation: %{y:.3f}<extra></extra>'
            ))
    
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        xaxis_title='Date',
        yaxis_title='Rolling 1-Month Correlation',
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a'),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#22263a',
            range=[-1, 1],
            zeroline=True,
            zerolinecolor='white',
            zerolinewidth=1
        ),
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    
    # Show summary stats for filtered period
    st.markdown(f"<div class='hint'>Data range: {df_filtered['date'].min().date()} to {df_filtered['date'].max().date()} | {len(df_filtered):,} observations</div>", unsafe_allow_html=True)

def render_twd_correlation_heatmap():
    """Render TWD Correlation Heatmap (10-year lookback, yearly averages)"""
    # Use current minute timestamp to force cache refresh every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    _, corr_df, metadata = build_correlation_data(poly_key, _force_refresh=cache_buster)
    
    if corr_df.empty:
        st.warning("No correlation data available.")
        return
    
    currencies = ['CNH', 'THB', 'AUD', 'SGD', 'KRW', 'JPY']
    corr_yearly = corr_df.copy()
    corr_yearly['year'] = pd.to_datetime(corr_yearly['date']).dt.year
    yearly_avg = corr_yearly.groupby('year')[currencies].mean()
    
    if yearly_avg.empty:
        st.warning("Not enough data for yearly heatmap.")
        return
    
    # Get last 10 years
    last_year = yearly_avg.index.max()
    start_year = max(yearly_avg.index.min(), last_year - 9)
    yearly_avg = yearly_avg.loc[start_year:last_year]
    
    fig = go.Figure(data=go.Heatmap(
        z=yearly_avg.values.T,
        x=yearly_avg.index.astype(str),
        y=yearly_avg.columns,
        colorscale='RdBu',
        zmid=0,
        zmin=-1,
        zmax=1,
        text=yearly_avg.values.T,
        texttemplate='%{text:.2f}',
        textfont={"size": 11},
        colorbar=dict(
            title=dict(text="Correlation", side="right"),
            tickmode="linear",
            tick0=-1,
            dtick=0.5
        ),
        hovertemplate='<b>%{y} vs TWD</b><br>' +
                      'Year: %{x}<br>' +
                      'Avg Correlation: %{z:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        xaxis_title='Year',
        yaxis_title='Currency',
        height=400,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    
    st.markdown(f"<div class='hint'>10-year lookback: {start_year}–{last_year} | Yearly average correlations vs TWD</div>", unsafe_allow_html=True)

def render_twd_correlation_regime():
    """Render Share of Time in Each Correlation Regime (10-year lookback)"""
    # Use current minute timestamp to force cache refresh every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    _, corr_df, metadata = build_correlation_data(poly_key, _force_refresh=cache_buster)
    
    if corr_df.empty:
        st.warning("No correlation data available.")
        return
    
    currencies = ['CNH', 'THB', 'AUD', 'SGD', 'KRW', 'JPY']
    regime_bins = [-1.01, -0.3, 0.3, 0.6, 1.01]
    regime_labels = ['Inverse (<-0.3)', 'Low/Neutral (-0.3 to 0.3)', 'Moderate (0.3 to 0.6)', 'High Sync (>0.6)']
    regime_colors = ['#d62728', '#7f7f7f', '#1f77b4', '#2ca02c']
    
    regime_df = pd.DataFrame(index=regime_labels)
    
    for currency in currencies:
        if currency in corr_df.columns:
            cats = pd.cut(corr_df[currency], bins=regime_bins, labels=regime_labels)
            shares = cats.value_counts(normalize=True).reindex(regime_labels, fill_value=0)
            regime_df[currency] = shares.values
    
    fig = go.Figure()
    for idx, regime in enumerate(regime_labels):
        fig.add_trace(go.Bar(
            x=regime_df.columns,
            y=regime_df.loc[regime],
            name=regime,
            marker_color=regime_colors[idx],
            opacity=0.9
        ))
    
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        barmode='stack',
        height=450,
        yaxis=dict(
            title='Time Share',
            tickformat='.0%',
            range=[0, 1],
            showgrid=True,
            gridcolor='#22263a'
        ),
        xaxis_title='Currency',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    
    st.markdown(f"<div class='hint'>10-year lookback | Regime definitions: Inverse (<-0.3), Low/Neutral (-0.3 to 0.3), Moderate (0.3 to 0.6), High Sync (>0.6)</div>", unsafe_allow_html=True)

def render_correlation_summary():
    """Render correlation summary statistics"""
    # Use current minute timestamp to force cache refresh every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    _, corr_df, metadata = build_correlation_data(poly_key, _force_refresh=cache_buster)
    
    if corr_df.empty or not metadata:
        st.warning("No correlation data available.")
        return
    
    currencies = ['CNH', 'THB', 'AUD', 'SGD', 'KRW', 'JPY']
    
    # Create summary table
    summary_data = []
    for currency in currencies:
        if currency in corr_df.columns:
            series = corr_df[currency]
            summary_data.append({
                'Currency': currency,
                'Mean': f"{series.mean():.3f}",
                'Std': f"{series.std():.3f}",
                'Min': f"{series.min():.3f}",
                'Max': f"{series.max():.3f}",
                'Latest': f"{series.iloc[-1]:.3f}",
                'Current vs Avg': f"{(series.iloc[-1] - series.mean()):+.3f}"
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Currency': st.column_config.TextColumn('Currency', width='small'),
            'Mean': st.column_config.TextColumn('Mean', width='small'),
            'Std': st.column_config.TextColumn('Std Dev', width='small'),
            'Min': st.column_config.TextColumn('Min', width='small'),
            'Max': st.column_config.TextColumn('Max', width='small'),
            'Latest': st.column_config.TextColumn('Latest', width='small'),
            'Current vs Avg': st.column_config.TextColumn('Δ from Avg', width='small'),
        }
    )
    
    st.markdown(f"<div class='hint'>Sample period: {metadata.get('sample_label', 'N/A')} | {metadata.get('total_obs', 0):,} observations | Rolling window: {CORRELATION_WINDOW} trading days</div>", unsafe_allow_html=True)

# -------------------- Seasonality Helpers ----------------

def get_two_month_window(current_date):
    """Determine which 2-month window the current date falls into"""
    month = current_date.month
    windows = {
        (1, 2): (1, 2, "Jan-Feb"),
        (3, 4): (3, 4, "Mar-Apr"),
        (5, 6): (5, 6, "May-Jun"),
        (7, 8): (7, 8, "Jul-Aug"),
        (9, 10): (9, 10, "Sep-Oct"),
        (11, 12): (11, 12, "Nov-Dec")
    }
    for (start_m, end_m), (s, e, name) in windows.items():
        if month in [start_m, end_m]:
            return s, e, name
    return 1, 2, "Jan-Feb"

def get_one_month_window(current_date):
    """Get the current month"""
    month = current_date.month
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    return month, month_names[month]

def build_window_seasonality(df, months_list):
    """Build seasonality data for specified months"""
    window_data = df[df['month'].isin(months_list)].copy()
    if window_data.empty:
        return pd.DataFrame()
    
    yearly_paths = []
    for year in window_data['year'].unique():
        year_data = window_data[window_data['year'] == year].copy().sort_values('date')
        if len(year_data) < 2:
            continue
        
        year_data['days_from_start'] = (year_data['date'] - year_data['date'].min()).dt.days
        first_close = year_data['close'].iloc[0]
        year_data['pct_change'] = ((year_data['close'] - first_close) / first_close) * 100
        year_data['year_label'] = year
        yearly_paths.append(year_data[['days_from_start', 'pct_change', 'year_label']])
    
    if not yearly_paths:
        return pd.DataFrame()
    return pd.concat(yearly_paths, ignore_index=True)

def build_monthly_heatmap_data(df):
    """Build monthly performance heatmap data"""
    monthly_returns = []
    for year in df['year'].unique():
        year_data = df[df['year'] == year].copy()
        for month in range(1, 13):
            month_data = year_data[year_data['month'] == month].copy()
            if len(month_data) >= 2:
                first_close = month_data['close'].iloc[0]
                last_close = month_data['close'].iloc[-1]
                pct_change = ((last_close - first_close) / first_close) * 100
                monthly_returns.append({'year': year, 'month': month, 'return': pct_change})
    
    if not monthly_returns:
        return pd.DataFrame()
    monthly_df = pd.DataFrame(monthly_returns)
    heatmap_df = monthly_df.pivot(index='year', columns='month', values='return')
    return heatmap_df

# -------------------- Taiwan DGBAS Data Functions ----------------

PRICE_INDEX_LINK_PATTERNS = {
    "Export Price Indices": ["export price indices"],
    "Import Price Indices": ["import price indices"],
    "Construction Cost Indices": ["construction cost indices"],
    "Producer Price Indices": ["producer price indices"],
    "Services Producer Price Indices": ["services producer price indices"],
}


@st.cache_data(ttl=86400)
def fetch_taiwan_price_index_links() -> Dict[str, Optional[str]]:
    """Scrape the DGBAS price index page to build download URLs."""
    from bs4 import BeautifulSoup

    url = "https://eng.stat.gov.tw//cp.aspx?n=2327"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    found_links = {name: None for name in PRICE_INDEX_LINK_PATTERNS}

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        context_parts = []
        if link.parent:
            context_parts.append(link.parent.get_text(separator=" "))
        prev_sibling, next_sibling = link.previous_sibling, link.next_sibling
        if prev_sibling and hasattr(prev_sibling, "get_text"):
            context_parts.append(prev_sibling.get_text())
        if next_sibling and hasattr(next_sibling, "get_text"):
            context_parts.append(next_sibling.get_text())
        context_text = " ".join(context_parts + [text]).lower()

        if not ("excel" in context_text or href.lower().endswith((".xls", ".xlsx"))):
            continue

        for idx_name, patterns in PRICE_INDEX_LINK_PATTERNS.items():
            if found_links[idx_name]:
                continue
            for pattern in patterns:
                if pattern in context_text:
                    found_links[idx_name] = href
                    break

    for name, href in found_links.items():
        if href:
            if href.startswith("/"):
                found_links[name] = "https://eng.stat.gov.tw" + href
            elif href.startswith("http"):
                found_links[name] = href
            else:
                found_links[name] = "https://eng.stat.gov.tw/" + href

    return found_links


def load_taiwan_price_index_excel(excel_url: str) -> pd.DataFrame:
    """Download Excel and return DataFrame regardless of .xls/.xlsx engine differences."""
    response = requests.get(excel_url, timeout=60, verify=False)
    response.raise_for_status()

    if excel_url.lower().endswith(".xls"):
        try:
            return pd.read_excel(io.BytesIO(response.content))
        except Exception:
            try:
                import pyexcel_xls
            except ImportError as err:
                raise ImportError("Install pyexcel-xls to read .xls files: pip install pyexcel-xls") from err
            xls_data = pyexcel_xls.get_data(io.BytesIO(response.content))
            if not xls_data:
                raise ValueError("pyexcel-xls returned no sheet data.")
            first_sheet = next(iter(xls_data.values()))
            if not first_sheet:
                raise ValueError("First sheet in .xls is empty.")
            return pd.DataFrame(first_sheet)
    else:
        return pd.read_excel(io.BytesIO(response.content), engine="openpyxl")


@st.cache_data(ttl=3600)
def fetch_taiwan_price_indices() -> Dict[str, pd.DataFrame]:
    """Fetch and clean all price indices we care about."""
    links = fetch_taiwan_price_index_links()
    results = {}
    for name, url in links.items():
        if not url:
            continue
        try:
            raw_df = load_taiwan_price_index_excel(url)
            cleaned = clean_taiwan_dgbas_data(raw_df, header_row_idx=None, min_year=2000)
            if not cleaned.empty:
                results[name] = cleaned
        except Exception:
            continue
    return results

PRICE_INDEX_SERIES_ORDER = [
    ("Export Price Indices", "Export Price Index YoY"),
    ("Import Price Indices", "Import Price Index YoY"),
    ("Construction Cost Indices", "Construction Cost Index YoY"),
    ("Producer Price Indices", "Producer Price Index YoY"),
    ("Services Producer Price Indices", "Services Producer Price Index YoY"),
]

PRICE_INDEX_COLOR_MAP = [
    "#1f77b4",  # Export - blue
    "#ff7f0e",  # Import - orange
    "#2ca02c",  # Construction - green
    "#d62728",  # Producer - red
    "#9467bd",  # Services - purple
]


@st.cache_data(ttl=86400)
def fetch_taiwan_gdp_quarterly(_force_refresh: int = 0) -> pd.DataFrame:
    """Download the quarterly GDP by kind of activity (current price, 1981~)."""
    from bs4 import BeautifulSoup
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    page_url = "https://eng.stat.gov.tw//cp.aspx?n=2334"
    response = requests.get(page_url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    workbook_href = None
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "生產帳_季_對外發布版" in href:
            workbook_href = href
            break

    if not workbook_href:
        st.warning("Could not find the quarterly GDP workbook link on the DGBAS page.")
        return pd.DataFrame()

    if workbook_href.startswith("/"):
        workbook_href = "https://eng.stat.gov.tw" + workbook_href
    elif not workbook_href.startswith("http"):
        workbook_href = "https://eng.stat.gov.tw/" + workbook_href

    params = {"_": _force_refresh} if _force_refresh else None
    download_response = requests.get(workbook_href, timeout=60, verify=False, params=params)
    download_response.raise_for_status()

    raw = pd.read_excel(io.BytesIO(download_response.content), sheet_name="current price1981~", header=None)
    raw = raw.dropna(how="all")
    if len(raw) < 5:
        return pd.DataFrame()

    header_row = raw.iloc[3]
    quarter_pattern = re.compile(r"^\d{4}Q[1-4]$")
    quarter_cols = [idx for idx, val in enumerate(header_row) if isinstance(val, str) and quarter_pattern.match(val.strip())]
    if not quarter_cols:
        st.warning("Could not identify quarterly column labels in the GDP workbook.")
        return pd.DataFrame()

    quarter_labels = [str(header_row[idx]).strip() for idx in quarter_cols]
    selected_cols = [0] + quarter_cols

    df = raw.iloc[4:, selected_cols].copy()
    df.columns = ["Activity"] + quarter_labels
    df["Activity"] = df["Activity"].astype(str).str.strip()
    df = df[df["Activity"].ne("")]
    df = df.set_index("Activity")
    df = df.apply(pd.to_numeric, errors="coerce")

    periods = pd.PeriodIndex(quarter_labels, freq="Q")
    df.columns = periods.to_timestamp(how="end")
    return df


def build_growth_area_figure(df: pd.DataFrame, title: str, stackgroup: str, legend_y: float = -0.15) -> go.Figure:
    fig = go.Figure()
    for idx, (name, row) in enumerate(df.iterrows()):
        y_values = row.fillna(0).values
        fig.add_trace(go.Scatter(
            x=df.columns,
            y=y_values,
            name=name,
            mode="lines",
            stackgroup=stackgroup,
            line=dict(width=1.5),
            hovertemplate=(
                f"<b>{name}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Value: %{y:,.0f}<extra></extra>"
            )
        ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=f"<b>{title}</b>", x=0.5, xanchor="center"),
        xaxis_title="Quarter",
        yaxis_title="NT$ Millions",
        hovermode="x unified",
        height=520,
        legend=dict(orientation="h", yanchor="top", y=legend_y, xanchor="center", x=0.5),
        xaxis=dict(showgrid=True, gridcolor="#22263a", tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor="#22263a", zeroline=True, zerolinewidth=1, zerolinecolor="#444"),
        margin=dict(l=10, r=10, t=70, b=60),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )
    return fig


GROWTH_TF_LABELS = ["1y", "5y", "10y", "MAX"]


def filter_growth_df_by_tf(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf == "MAX":
        return df.copy()
    start, end = tf_to_daterange(tf)
    mask = (df.columns.date >= start) & (df.columns.date <= end)
    filtered = df.loc[:, mask]
    return filtered


def render_growth_stack_chart(title: str, row_indices: List[int], stackgroup: str, tf_key: str):
    df = fetch_taiwan_gdp_quarterly()
    if df.empty:
        st.warning("GDP quarterly data is unavailable right now.")
        return

    trimmed = df.index.to_series().str.strip()
    selected = df.iloc[row_indices].copy()
    selected.index = trimmed.iloc[row_indices].tolist()

    tf = seg_control(GROWTH_TF_LABELS, key=tf_key, default="5y")
    filtered = filter_growth_df_by_tf(selected, tf)
    if filtered.empty:
        st.warning("No quarterly data for the chosen timeframe.")
        return

    fig = build_growth_area_figure(filtered, title, stackgroup)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    latest = filtered.iloc[:, -1].dropna()
    if not latest.empty:
        summary = " | ".join(f"{name}: {value:,.0f}" for name, value in latest.items())
        st.markdown(
            f"<div class='hint'>Latest quarter {filtered.columns[-1].date()}: {summary} | Source: DGBAS</div>",
            unsafe_allow_html=True,
        )


def render_gdp_component_stack():
    df = fetch_taiwan_gdp_quarterly()
    if df.empty:
        st.warning("GDP quarterly data is unavailable right now.")
        return

    trimmed = df.index.to_series().str.strip()
    try:
        stop_idx = trimmed.tolist().index("Statistical Discrepancy")
    except ValueError:
        stop_idx = len(df) - 1

    render_growth_stack_chart(
        "GDP components by Sector",
        list(range(stop_idx + 1)),
        "growth-components",
        tf_key="growth_components_tf",
    )


def render_gdp_sector_stack():
    df = fetch_taiwan_gdp_quarterly()
    if df.empty:
        st.warning("GDP quarterly data is unavailable right now.")
        return

    trimmed = df.index.to_series().str.strip().tolist()
    targets = ["Agriculture", "Industry", "Services"]
    rows = [idx for idx, name in enumerate(trimmed) if name in targets]
    if not rows:
        st.warning("Could not locate Agriculture / Industry / Services rows.")
        return

    render_growth_stack_chart(
        "Agriculture / Industry / Services ",
        rows,
        "growth-sectors",
        tf_key="growth_sectors_tf",
    )


def render_inflation_price_series(tf: str):
    data_map = fetch_taiwan_price_indices()
    if not data_map:
        st.warning("No Taiwan price indices data available right now.")
        return

    start, end = tf_to_daterange(tf)
    fig = go.Figure()
    summary_notes = []

    for (key, label), color in zip(PRICE_INDEX_SERIES_ORDER, PRICE_INDEX_COLOR_MAP):
        df = data_map.get(key)
        if df is None or df.empty:
            continue

        filtered = df[
            (df["Date"].dt.date >= start) &
            (df["Date"].dt.date <= end)
        ].copy()

        if filtered.empty:
            continue

        fig.add_trace(go.Scatter(
            x=filtered["Date"],
            y=filtered["YoY_PctChange"],
            name=label,
            line=dict(width=2.5, color=color),
            mode="lines",
            hovertemplate=(
                f"<b>{label}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "YoY % Change: %{y:.2f}%<extra></extra>"
            )
        ))

        latest_value = filtered["YoY_PctChange"].iloc[-1]
        latest_date = filtered["Date"].dt.date.iloc[-1]
        summary_notes.append(f"{label}: {latest_value:+.2f}% ({latest_date})")

    if not fig.data:
        st.warning(f"No price index data available for timeframe {tf}.")
        return

    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1, opacity=0.6)
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        xaxis_title="Date",
        yaxis_title="YoY % Change",
        hovermode="x unified",
        height=520,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor="#22263a"),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="#22263a", zeroline=False),
        margin=dict(l=10, r=10, t=80, b=10),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    if summary_notes:
        st.markdown(
            "<div class='hint'>" + " | ".join(summary_notes) + " | Source: Taiwan DGBAS</div>",
            unsafe_allow_html=True
        )


def clean_taiwan_dgbas_data(raw_df, header_row_idx=None, min_year=2000):
    """
    Universal cleaning function for Taiwan DGBAS Excel files.
    Returns DataFrame with columns: Date, Year, Month, Value, YoY_PctChange
    """
    df = raw_df.copy()
    
    # Remove rows where all values are NaN
    df = df.dropna(how='all')
    
    # Auto-detect header row if not specified
    if header_row_idx is None:
        month_patterns = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for row_idx in range(min(10, len(df))):
            row_values = df.iloc[row_idx].values
            month_count = 0
            for val in row_values:
                if pd.isna(val):
                    continue
                val_str = str(val).lower().strip()
                for pattern in month_patterns:
                    if pattern in val_str:
                        month_count += 1
                        break
            if month_count >= 6:
                header_row_idx = row_idx
                break
        
        if header_row_idx is None:
            for row_idx in range(min(10, len(df))):
                row_text = ' '.join([str(v).lower() for v in df.iloc[row_idx].values if pd.notna(v)])
                if 'year' in row_text or 'month' in row_text:
                    header_row_idx = row_idx
                    break
        
        if header_row_idx is None:
            header_row_idx = 4
    
    if header_row_idx >= len(df):
        raise ValueError(f"Header row index {header_row_idx} is out of range")
    
    header_row = df.iloc[header_row_idx].values
    month_patterns = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    month_col_indices = []
    month_names = []
    
    for col_idx, val in enumerate(header_row):
        if pd.isna(val):
            continue
        val_str = str(val).lower().strip()
        for i, pattern in enumerate(month_patterns):
            if pattern in val_str:
                month_col_indices.append(col_idx)
                month_names.append(i + 1)
                break
    
    if len(month_col_indices) < 10:
        for col_idx, val in enumerate(header_row):
            if pd.isna(val):
                continue
            try:
                month_num = int(float(val))
                if 1 <= month_num <= 12 and col_idx not in month_col_indices:
                    month_col_indices.append(col_idx)
                    month_names.append(month_num)
            except (ValueError, TypeError):
                continue
    
    if len(month_col_indices) < 10 and header_row_idx > 0:
        prev_row = df.iloc[header_row_idx - 1].values
        for col_idx, val in enumerate(prev_row):
            if pd.isna(val):
                continue
            val_str = str(val).lower().strip()
            for i, pattern in enumerate(month_patterns):
                if pattern in val_str and col_idx not in month_col_indices:
                    month_col_indices.append(col_idx)
                    month_names.append(i + 1)
                    break
    
    sorted_pairs = sorted(zip(month_col_indices, month_names))
    month_col_indices = [p[0] for p in sorted_pairs]
    month_names = [p[1] for p in sorted_pairs]
    
    if len(month_col_indices) == 0:
        raise ValueError("Could not identify month columns")
    
    year_col_idx = None
    for col_idx in range(min(month_col_indices)):
        col_val = str(df.iloc[header_row_idx, col_idx]).lower()
        if 'year' in col_val or col_idx == 0:
            year_col_idx = col_idx
            break
    
    if year_col_idx is None:
        year_col_idx = 0
    
    data_start_row = None
    for idx in range(header_row_idx + 1, len(df)):
        year_val = df.iloc[idx, year_col_idx]
        if pd.isna(year_val):
            continue
        try:
            year_int = int(float(year_val))
            if year_int >= min_year:
                data_start_row = idx
                break
        except (ValueError, TypeError):
            continue
    
    if data_start_row is None:
        raise ValueError(f"Could not find data starting from year {min_year}")
    
    data_rows = df.iloc[data_start_row:].copy()
    years = pd.to_numeric(data_rows.iloc[:, year_col_idx], errors='coerce')
    
    time_series_rows = []
    for row_idx in range(len(data_rows)):
        year = years.iloc[row_idx]
        if pd.isna(year):
            continue
        
        year_int = int(year)
        if year_int < min_year:
            continue
        
        for month_idx, month_num in enumerate(month_names):
            col_idx = month_col_indices[month_idx]
            value = data_rows.iloc[row_idx, col_idx]
            
            if pd.isna(value):
                continue
            
            try:
                value_float = float(value)
            except (ValueError, TypeError):
                continue
            
            date_val = pd.Timestamp(year=int(year_int), month=int(month_num), day=1)
            time_series_rows.append({
                'Date': date_val,
                'Year': year_int,
                'Month': month_num,
                'Value': value_float
            })
    
    result_df = pd.DataFrame(time_series_rows)
    if len(result_df) == 0:
        raise ValueError("No valid data found")
    
    result_df = result_df.sort_values('Date').reset_index(drop=True)
    
    # Calculate YoY % change
    result_df['YoY_PctChange'] = np.nan
    for month in range(1, 13):
        month_mask = result_df['Month'] == month
        month_data = result_df[month_mask].copy().sort_values('Year')
        
        if len(month_data) < 2:
            continue
        
        current_values = month_data['Value'].values
        prev_year_values = month_data['Value'].shift(1).values
        
        valid_mask = ~pd.isna(prev_year_values) & (prev_year_values != 0)
        yoy_changes = np.where(
            valid_mask,
            ((current_values - prev_year_values) / prev_year_values) * 100,
            np.nan
        )
        
        result_df.loc[month_mask, 'YoY_PctChange'] = yoy_changes
    
    return result_df

def fetch_taiwan_export_price_indices(_force_refresh: int = 0) -> pd.DataFrame:
    """
    Fetch Taiwan Export Price Indices from DGBAS website
    Returns cleaned DataFrame with YoY % change
    """
    try:
        from bs4 import BeautifulSoup
        import urllib3
        import io
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        url = "https://eng.stat.gov.tw//cp.aspx?n=2327"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        excel_link = None
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if 'EXCEL' in text.upper() or href.endswith('.xls') or href.endswith('.xlsx'):
                context_text = ''
                if link.parent:
                    context_text += link.parent.get_text() + ' '
                prev_sibling = link.previous_sibling
                if prev_sibling and hasattr(prev_sibling, 'get_text'):
                    context_text += prev_sibling.get_text() + ' '
                next_sibling = link.next_sibling
                if next_sibling and hasattr(next_sibling, 'get_text'):
                    context_text += next_sibling.get_text() + ' '
                
                if 'Export' in context_text and 'Price' in context_text and 'Indices' in context_text:
                    excel_link = href
                    break
        
        if not excel_link:
            return pd.DataFrame()
        
        if excel_link.startswith('/'):
            excel_url = "https://eng.stat.gov.tw" + excel_link
        elif excel_link.startswith('http'):
            excel_url = excel_link
        else:
            excel_url = "https://eng.stat.gov.tw/" + excel_link
        
        excel_response = requests.get(excel_url, timeout=60, verify=False)
        excel_response.raise_for_status()
        
        # Important: avoid any hard dependency on xlrd in this app environment.
        # For .xls we mirror the notebook behaviour but build the DataFrame
        # directly from pyexcel_xls to sidestep pandas/xlrd version issues.
        if excel_url.endswith('.xls'):
            try:
                # First try pandas' default engine – if the environment happens
                # to have a working stack, this will just work.
                df = pd.read_excel(io.BytesIO(excel_response.content))
            except Exception:
                try:
                    # Fallback: use pyexcel_xls to parse the binary and then
                    # convert the first sheet into a DataFrame.
                    import pyexcel_xls
                    from collections import OrderedDict  # noqa: F401
                    
                    xls_data = pyexcel_xls.get_data(io.BytesIO(excel_response.content))
                    if not xls_data:
                        raise ValueError("pyexcel_xls returned no sheets")
                    
                    # Take the first sheet
                    first_sheet_name = next(iter(xls_data.keys()))
                    rows = xls_data[first_sheet_name]
                    if not rows:
                        raise ValueError("First sheet in .xls file is empty")
                    
                    df = pd.DataFrame(rows)
                except Exception as e:
                    raise ValueError(
                        "Could not read Excel file. Please install pyexcel-xls in your "
                        "virtual environment: pip install pyexcel-xls. "
                        f"Underlying error: {e}"
                    )
        else:
            # .xlsx – use openpyxl
            df = pd.read_excel(io.BytesIO(excel_response.content), engine='openpyxl')
        
        if df is None or df.empty:
            raise ValueError("Failed to load Excel data")
        
        cleaned_df = clean_taiwan_dgbas_data(df, header_row_idx=None, min_year=2000)
        return cleaned_df
    
    except Exception as e:
        st.warning(f"Error fetching Taiwan Export Price Indices: {e}")
        return pd.DataFrame()

# -------------------- Placeholder Renderers ----------------

def render_placeholder(chart_name: str):
    """Placeholder renderer for charts"""
    st.info(f"📊 Chart placeholder for {chart_name} - Coming soon")

# -------------------- FRED Chart Renderers ----------------

def render_fred_chart(series_id: str, title: str, yaxis_title: str, tf: str):
    """Generic FRED chart renderer with timeframe support"""
    # Get date range based on timeframe
    start, end = tf_to_daterange(tf)
    
    # For MAX, use None to get all available data
    if tf.upper() == "MAX":
        df = fetch_fred_series(series_id, fred_key, observation_start=None)
    else:
        df = fetch_fred_series(series_id, fred_key, observation_start=start)
    
    if df.empty:
        st.warning(f"No data available for {title}.")
        return
    
    # Filter by selected timeframe (except MAX which already has all data)
    if tf.upper() != "MAX":
        df = df[(df['date'].dt.date >= start) & (df['date'].dt.date <= end)]
    
    if df.empty:
        st.warning(f"No data available for {title} in the selected timeframe.")
        return
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df[series_id],
        name=series_id,
        line=dict(width=2, color='#1f77b4'),
        mode='lines',
        hovertemplate=f'<b>{title}</b><br>' +
                     'Date: %{x|%Y-%m-%d}<br>' +
                     'Value: %{y:.2f}<extra></extra>'
    ))
    
    # Show latest value
    if not df.empty:
        latest_value = df[series_id].iloc[-1]
        st.markdown(f"<h2 style='margin:0 0 16px 0; font-size:24px;'>{latest_value:,.2f}</h2>", unsafe_allow_html=True)
    
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=f'<b>{title}</b>', x=0.5, xanchor='center'),
        xaxis_title='Date',
        yaxis_title=yaxis_title,
        height=500,
        hovermode='x unified',
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a'),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    
    # Show data range info
    st.markdown(f"<div class='hint'>Data range: {df['date'].min().date()} to {df['date'].max().date()} | {len(df):,} observations | Source: FRED</div>", unsafe_allow_html=True)

# -------------------- Seasonality Renderers ----------------

def render_two_month_seasonality():
    """Render 2-month window seasonality chart"""
    # Use current minute as cache buster to ensure fresh data every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    twd_df = fetch_twd_seasonality_data(poly_key, _force_refresh=cache_buster)
    if twd_df.empty:
        st.warning("No USDTWD data available for seasonality analysis.")
        return
    
    # Use Taipei timezone for consistent date handling
    current_date = datetime.now(TAIPEI_TZ)
    start_m, end_m, window_name = get_two_month_window(current_date)
    
    # Show data freshness info
    latest_date_in_data = twd_df['date'].max().date()
    market_reference_date = get_market_reference_date()
    days_behind = (market_reference_date - latest_date_in_data).days
    
    if days_behind > 0:
        st.warning(
            f"⚠️ Data is {days_behind} day(s) behind. "
            f"Latest available: {latest_date_in_data} | Market date: {market_reference_date}"
        )
    else:
        st.success(f"✅ Data includes the latest market date ({latest_date_in_data}).")
    
    # Filter to current year's data to check what we have
    current_year_data = twd_df[(twd_df['year'] == current_date.year) & (twd_df['month'].isin([start_m, end_m]))].copy()
    if not current_year_data.empty:
        latest_current_year_date = current_year_data['date'].max().date()
        st.caption(f"Current year ({current_date.year}) data in {window_name}: {current_year_data['date'].min().date()} to {latest_current_year_date}")
    
    seasonality_data = build_window_seasonality(twd_df, [start_m, end_m])
    
    if seasonality_data.empty:
        st.warning(f"No data available for {window_name} window.")
        return
    
    # Calculate statistics
    all_days = sorted(seasonality_data['days_from_start'].unique())
    stats_by_day = []
    for day in all_days:
        day_data = seasonality_data[seasonality_data['days_from_start'] == day]['pct_change']
        if len(day_data) > 0:
            stats_by_day.append({
                'day': day, 'mean': day_data.mean(), 'median': day_data.median(),
                'p10': day_data.quantile(0.10), 'p25': day_data.quantile(0.25),
                'p75': day_data.quantile(0.75), 'p90': day_data.quantile(0.90)
            })
    stats_df = pd.DataFrame(stats_by_day)
    
    # Create figure
    fig = go.Figure()
    
    # Percentile ranges
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p90'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p10'], mode='lines', line=dict(width=0), fillcolor='rgba(173, 216, 230, 0.3)', fill='tonexty', name='10th-90th Percentile'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p75'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p25'], mode='lines', line=dict(width=0), fillcolor='rgba(100, 149, 237, 0.4)', fill='tonexty', name='25th-75th Percentile'))
    
    # Median and mean
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['median'], mode='lines', line=dict(color='#1f77b4', width=2.5), name='Median'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['mean'], mode='lines', line=dict(color='#333333', width=2, dash='dash'), name='Mean'))
    
    # Past 2 years (orange)
    for year in [current_date.year - 2, current_date.year - 1]:
        year_data = seasonality_data[seasonality_data['year_label'] == year].sort_values('days_from_start')
        if not year_data.empty:
            fig.add_trace(go.Scatter(x=year_data['days_from_start'], y=year_data['pct_change'], mode='lines', line=dict(color='#ff7f0e', width=2), name=f'{year}'))
    
    # Current year (red, thicker)
    current_year_data = seasonality_data[seasonality_data['year_label'] == current_date.year].sort_values('days_from_start')
    if not current_year_data.empty:
        fig.add_trace(go.Scatter(x=current_year_data['days_from_start'], y=current_year_data['pct_change'], mode='lines', line=dict(color='#d62728', width=3.5), name=f'{current_date.year} (Ongoing)'))
    
    avg_return = stats_df['mean'].iloc[-1] if len(stats_df) > 0 else 0
    median_return = stats_df['median'].iloc[-1] if len(stats_df) > 0 else 0
    
    fig.update_layout(
        title=dict(text=f'<b>USDTWD Seasonality: {window_name} (2016-{current_date.year})</b><br><sub>Avg Return: {avg_return:+.2f}% | Median Return: {median_return:+.2f}%</sub>', x=0.5, xanchor='center'),
        xaxis_title=f'Days from {window_name.split("-")[0]} 1', yaxis_title='% Change from Start',
        template=PLOTLY_TEMPLATE, height=500, hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a', zeroline=True, zerolinecolor='white', zerolinewidth=1),
        margin=dict(l=10, r=10, t=60, b=10), paper_bgcolor=DARK_CARD, plot_bgcolor=DARK_CARD
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    st.markdown(f"<div class='hint'>Current window: {window_name} | Data: 2016-present | Red line shows {current_date.year} progress. Current year</div>", unsafe_allow_html=True)

def render_one_month_seasonality():
    """Render 1-month window seasonality chart"""
    # Use current minute as cache buster to ensure fresh data every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    twd_df = fetch_twd_seasonality_data(poly_key, _force_refresh=cache_buster)
    if twd_df.empty:
        st.warning("No USDTWD data available for seasonality analysis.")
        return
    
    # Use Taipei timezone for consistent date handling
    current_date = datetime.now(TAIPEI_TZ)
    month, month_name = get_one_month_window(current_date)
    
    # Show data freshness info
    latest_date_in_data = twd_df['date'].max().date()
    market_reference_date = get_market_reference_date()
    days_behind = (market_reference_date - latest_date_in_data).days
    
    if days_behind > 0:
        st.warning(
            f"⚠️ Data is {days_behind} day(s) behind. "
            f"Latest available: {latest_date_in_data} | Market date: {market_reference_date}"
        )
    else:
        st.success(f"✅ Data includes the latest market date ({latest_date_in_data}).")
    
    # Filter to current year's data to check what we have
    current_year_data = twd_df[(twd_df['year'] == current_date.year) & (twd_df['month'] == month)].copy()
    if not current_year_data.empty:
        latest_current_year_date = current_year_data['date'].max().date()
        st.caption(f"Current year ({current_date.year}) data in {month_name}: {current_year_data['date'].min().date()} to {latest_current_year_date}")
    
    seasonality_data = build_window_seasonality(twd_df, [month])
    
    if seasonality_data.empty:
        st.warning(f"No data available for {month_name}.")
        return
    
    # Calculate statistics
    all_days = sorted(seasonality_data['days_from_start'].unique())
    stats_by_day = []
    for day in all_days:
        day_data = seasonality_data[seasonality_data['days_from_start'] == day]['pct_change']
        if len(day_data) > 0:
            stats_by_day.append({
                'day': day, 'mean': day_data.mean(), 'median': day_data.median(),
                'p10': day_data.quantile(0.10), 'p25': day_data.quantile(0.25),
                'p75': day_data.quantile(0.75), 'p90': day_data.quantile(0.90)
            })
    stats_df = pd.DataFrame(stats_by_day)
    
    # Create figure
    fig = go.Figure()
    
    # Percentile ranges
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p90'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p10'], mode='lines', line=dict(width=0), fillcolor='rgba(173, 216, 230, 0.3)', fill='tonexty', name='10th-90th Percentile'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p75'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['p25'], mode='lines', line=dict(width=0), fillcolor='rgba(100, 149, 237, 0.4)', fill='tonexty', name='25th-75th Percentile'))
    
    # Median and mean
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['median'], mode='lines', line=dict(color='#1f77b4', width=2.5), name='Median'))
    fig.add_trace(go.Scatter(x=stats_df['day'], y=stats_df['mean'], mode='lines', line=dict(color='#333333', width=2, dash='dash'), name='Mean'))
    
    # Past 2 years (orange)
    for year in [current_date.year - 2, current_date.year - 1]:
        year_data = seasonality_data[seasonality_data['year_label'] == year].sort_values('days_from_start')
        if not year_data.empty:
            fig.add_trace(go.Scatter(x=year_data['days_from_start'], y=year_data['pct_change'], mode='lines', line=dict(color='#ff7f0e', width=2), name=f'{year}'))
    
    # Current year (red, thicker)
    current_year_data = seasonality_data[seasonality_data['year_label'] == current_date.year].sort_values('days_from_start')
    if not current_year_data.empty:
        fig.add_trace(go.Scatter(x=current_year_data['days_from_start'], y=current_year_data['pct_change'], mode='lines', line=dict(color='#d62728', width=3.5), name=f'{current_date.year} (Ongoing)'))
    
    avg_return = stats_df['mean'].iloc[-1] if len(stats_df) > 0 else 0
    median_return = stats_df['median'].iloc[-1] if len(stats_df) > 0 else 0
    
    fig.update_layout(
        title=dict(text=f'<b>USDTWD Seasonality: {month_name} (2016-{current_date.year})</b><br><sub>Avg Return: {avg_return:+.2f}% | Median Return: {median_return:+.2f}%</sub>', x=0.5, xanchor='center'),
        xaxis_title=f'Days from {month_name} 1', yaxis_title='% Change from Start',
        template=PLOTLY_TEMPLATE, height=500, hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='#22263a', zeroline=True, zerolinecolor='white', zerolinewidth=1),
        margin=dict(l=10, r=10, t=60, b=10), paper_bgcolor=DARK_CARD, plot_bgcolor=DARK_CARD
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    st.markdown(f"<div class='hint'>Current month: {month_name} | Data: 2016-present | Red line shows {current_date.year} progress</div>", unsafe_allow_html=True)

def render_monthly_heatmap():
    """Render monthly seasonality heatmap"""
    # Use current minute as cache buster to ensure fresh data every minute
    cache_buster = int(datetime.now().timestamp() // 60)
    twd_df = fetch_twd_seasonality_data(poly_key, _force_refresh=cache_buster)
    if twd_df.empty:
        st.warning("No USDTWD data available for heatmap.")
        return
    
    heatmap_df = build_monthly_heatmap_data(twd_df)
    if heatmap_df.empty:
        st.warning("No data available for heatmap.")
        return
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_df.values, x=month_names, y=heatmap_df.index.astype(str),
        colorscale='RdYlGn', zmid=0, text=heatmap_df.values,
        texttemplate='%{text:.2f}%', textfont={"size": 10},
        colorbar=dict(title=dict(text="Return (%)", side="right"), ticksuffix="%"),
        hovertemplate='<b>%{y} %{x}</b><br>Return: %{z:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text='<b>USDTWD Monthly % Performance Heatmap (2016-Present)</b><br><sub>Monthly % Returns</sub>', x=0.5, xanchor='center'),
        xaxis_title='Month', yaxis_title='Year', template=PLOTLY_TEMPLATE, height=500,
        yaxis=dict(autorange='reversed'), margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor=DARK_CARD, plot_bgcolor=DARK_CARD
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    
    # Show average monthly returns
    avg_monthly = heatmap_df.mean(axis=0)
    avg_text = " | ".join([f"{month_names[i]}: {avg_monthly.iloc[i]:+.2f}%" for i in range(12)])
    st.markdown(f"<div class='hint'>Average monthly returns: {avg_text}</div>", unsafe_allow_html=True)

# -------------------- Last 7 Days Price Action Analysis --------------------

def calculate_price_action_share(series_id: str, api_key: str, start_year: int = 2000, end_year: int = 2025) -> pd.DataFrame:
    """
    Calculate S (price-action share) metric for a FRED series
    Returns DataFrame with median S% by month
    """
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    
    df = fetch_fred_series(series_id, api_key, observation_start=start_date, observation_end=end_date)
    
    if df.empty:
        return pd.DataFrame()
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    # Calculate daily log returns using diff method: log_ret = np.log(price).diff()
    df['log_price'] = np.log(df[series_id])
    df['log_return'] = df['log_price'].diff()
    
    # Drop the first NaN
    df = df.dropna(subset=['log_return']).reset_index(drop=True)
    
    # Add year, month columns
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    
    # Calculate monthly metrics
    monthly_metrics = []
    
    for year in sorted(df['year'].unique()):
        year_data = df[df['year'] == year].copy()
        
        for month in range(1, 13):
            month_data = year_data[year_data['month'] == month].copy()
            
            if len(month_data) < 7:  # Need at least 7 days
                continue
            
            # Sort by date
            month_data = month_data.sort_values('date').reset_index(drop=True)
            
            # Get last 7 trading days
            last_7_days = month_data.tail(7).copy()
            
            # Calculate absolute log returns
            month_data['abs_log_return'] = month_data['log_return'].abs()
            last_7_days['abs_log_return'] = last_7_days['log_return'].abs()
            
            # Calculate Price-Action Share (S)
            A_L = last_7_days['abs_log_return'].sum()
            A_M = month_data['abs_log_return'].sum()
            
            if A_M < 1e-10:
                S = np.nan
            else:
                S = A_L / A_M  # Price-action share (0 to 1)
            
            monthly_metrics.append({
                'year': year,
                'month': month,
                'S': S
            })
    
    metrics_df = pd.DataFrame(monthly_metrics)
    
    if metrics_df.empty:
        return pd.DataFrame()
    
    # Calculate median by month (NaNs are ignored by default in median)
    monthly_median = metrics_df.groupby('month')['S'].median().reset_index()
    monthly_median.columns = ['month', 'median_S']
    monthly_median['median_S_pct'] = monthly_median['median_S'] * 100
    
    return monthly_median

def render_last_7_days_price_action():
    """Render grouped bar chart showing S metric for USDTWD, USDJPY, USDKRW"""
    # Calculate metrics for all three currencies
    currencies = [
        ("DEXTAUS", "USDTWD"),
        ("DEXJPUS", "USDJPY"),
        ("DEXKOUS", "USDKRW")
    ]
    
    all_data = {}
    
    for series_id, currency_name in currencies:
        monthly_median = calculate_price_action_share(series_id, fred_key, 2000, 2025)
        if not monthly_median.empty:
            all_data[currency_name] = monthly_median
    
    if not all_data:
        st.warning("No data available for last 7 days price action analysis.")
        return
    
    # Combine all currencies into one DataFrame
    combined_df = pd.DataFrame({'month': range(1, 13)})
    
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    combined_df['month_name'] = combined_df['month'].map(month_names)
    
    for currency_name, monthly_median in all_data.items():
        merged = combined_df.merge(monthly_median[['month', 'median_S_pct']], on='month', how='left')
        combined_df[currency_name] = merged['median_S_pct']
    
    # Create grouped bar chart
    fig = go.Figure()
    
    # Color map for currencies
    currency_colors = {
        'USDTWD': '#1f77b4',  # Blue
        'USDJPY': '#ff7f0e',  # Orange
        'USDKRW': '#2ca02c'   # Green
    }
    
    # Add bars for each currency
    for currency_name in all_data.keys():
        fig.add_trace(go.Bar(
            name=currency_name,
            x=combined_df['month_name'],
            y=combined_df[currency_name],
            marker_color=currency_colors.get(currency_name, '#7f7f7f'),
            opacity=0.85,
            hovertemplate=f'<b>{currency_name}</b><br>' +
                         'Month: %{x}<br>' +
                         'Median S: %{y:.2f}%<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(
            text='<b>What proportion of month price action is attributable to the last 7 days (S)</b><br>' +
                 '<sub>Median % of monthly movement occurring in last 7 trading days (2000-2025)</sub>',
            x=0.5,
            xanchor='center',
            font=dict(size=18)
        ),
        xaxis=dict(
            title='Month',
            showgrid=False
        ),
        yaxis=dict(
            title='S (%)',
            range=[0, 100],
            showgrid=True,
            gridcolor='#22263a'
        ),
        barmode='group',
        height=500,
        margin=dict(l=60, r=40, t=80, b=40),
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        paper_bgcolor=DARK_CARD,
        plot_bgcolor=DARK_CARD,
    )
    
    # Add annotation
    n_years = 26  # 2000-2025
    fig.add_annotation(
        text=f"Based on {n_years} years of data (2000-2025) | " +
             "S = (Sum of |log returns| in last 7 days) / (Sum of |log returns| for full month)",
        xref="paper", yref="paper",
        x=0.5, y=-0.12,
        showarrow=False,
        font=dict(size=10, color='gray')
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
    st.markdown(f"<div class='hint'>Data source: FRED API | Currencies: USDTWD (DEXTAUS), USDJPY (DEXJPUS), USDKRW (DEXKOUS)</div>", unsafe_allow_html=True)

# -------------------- Theme Router --------------------
def clear_theme_query_params():
    """Clear theme query parameter"""
    try:
        qp = st.query_params
        if "theme" in qp:
            del qp["theme"]
    except Exception:
        pass

def national_stats_theme_router():
    """Handle theme navigation for National Statistics tab - returns True if a theme is active"""
    try:
        qp = st.query_params
        theme = qp.get("theme")
    except Exception:
        return False
    
    if not theme:
        return False
    
    # Only handle themes when we're on Tab 2
    try:
        qp = st.query_params
        active_tab = qp.get("tab", "Tab 1")
    except Exception:
        active_tab = "Tab 1"
    
    if active_tab != "Tab 2":
        return False
    
    # Valid themes
    valid_themes = ["growth", "inflation", "bop", "central_bank"]
    if theme not in valid_themes:
        return False
    
    # Back button
    if st.button("← Back to National Statistics", key="back_to_national_stats", use_container_width=True):
        clear_theme_query_params()
        st.rerun()
    
    return True

# -------------------- Tab Router --------------------
try:
    qp = st.query_params
    active_tab = qp.get("tab", "Tab 1")
except Exception:
    active_tab = "Tab 1"

# Global refresh button at the top
col_refresh_top, col_time = st.columns([1, 3])
with col_refresh_top:
    if st.button("🔄 Refresh All Data", key="refresh_top", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_time:
    st.caption(f"Data as of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Click refresh to get latest data")

# Tab buttons
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("TWD", key="tab_1", use_container_width=True, 
                 type="primary" if active_tab == "Tab 1" else "secondary"):
        st.query_params["tab"] = "Tab 1"
        st.rerun()
with col2:
    if st.button("National Stats", key="tab_2", use_container_width=True,
                 type="primary" if active_tab == "Tab 2" else "secondary"):
        st.query_params["tab"] = "Tab 2"
        st.rerun()
with col3:
    if st.button("Later on", key="tab_3", use_container_width=True,
                 type="primary" if active_tab == "Tab 3" else "secondary"):
        st.query_params["tab"] = "Tab 3"
        st.rerun()

st.markdown("<hr style='margin: 20px 0; border: 1px solid #333;'>", unsafe_allow_html=True)

# -------------------- Tab Content --------------------

if active_tab == "Tab 1":
    st.session_state["active_tab"] = "Tab 1"
    
    # TWD Rolling Correlations - with timeframe controls
    chart_card(
        "twd_rolling_corr",
        "TWD Rolling 1-Month Correlations with Asian Currencies",
        render_twd_rolling_correlations,
        default_tf="5y",
        has_timeframe=True
    )
    
    # Correlation Heatmap - no timeframe (10-year lookback)
    chart_card_no_tf(
        "twd_heatmap",
        "TWD Correlation Heatmap, other Asian Currencies",
        render_twd_correlation_heatmap
    )
    
    # Regime chart - no timeframe (10-year lookback)
    chart_card_no_tf(
        "twd_regime",
        "Share of Time in Each Correlation Regime (10-Year Lookback)",
        render_twd_correlation_regime
    )
    
    # Seasonality Charts
    st.markdown("<hr style='margin: 30px 0; border: 1px solid #333;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin:0 0 20px 0; font-size:24px;'>USDTWD Performance Analysis</h2>", unsafe_allow_html=True)
    
    # 2-Month Window Seasonality
    chart_card_no_tf(
        "twd_2m_seasonality",
        "USDTWD 2-Month Window. Should adjust to the current 2 month window",
        render_two_month_seasonality
    )
    
    # 1-Month Window Seasonality
    chart_card_no_tf(
        "twd_1m_seasonality",
        "USDTWD Curent Month",
        render_one_month_seasonality
    )
    
    # Monthly Heatmap
    chart_card_no_tf(
        "twd_monthly_heatmap",
        "USDTWD Monthly Performance Heatmap. Note lower values mean stronger TWD performance",
        render_monthly_heatmap
    )
    
    # Last 7 Days Price Action Analysis
    st.markdown("<hr style='margin: 30px 0; border: 1px solid #333;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='margin:0 0 20px 0; font-size:24px;'>Last 7 Days Price Action </h2>", unsafe_allow_html=True)
    
    chart_card_no_tf(
        "last_7_days_price_action",
        "USDTWD, USDJPY, USDKRW",
        render_last_7_days_price_action
    )

elif active_tab == "Tab 2":
    st.session_state["active_tab"] = "Tab 2"
    
    # Check if we're in a theme view
    if national_stats_theme_router():
        try:
            qp = st.query_params
            theme = qp.get("theme")
        except Exception:
            theme = None
        
        if theme == "growth":
            st.markdown("<h2 style='margin:0 0 20px 0; font-size:28px;'>Growth Indicators</h2>", unsafe_allow_html=True)
            chart_card_no_tf("gdp_components_stack", "Narrow GDP by Acitivity (quarterly update)", render_gdp_component_stack)
            chart_card_no_tf("gdp_sectors_stack", "Broad version of GDP by activity", render_gdp_sector_stack)
        
        elif theme == "inflation":
            st.markdown("<h2 style='margin:0 0 20px 0; font-size:28px;'>Inflation Indicators</h2>", unsafe_allow_html=True)
            
            tf_labels_no_max = ["1m", "3m", "6m", "YTD", "1y", "2y", "5y", "10y"]
            with st.container():
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown("<div class='chart-title'>Inflation pillars YoY growth</div>", unsafe_allow_html=True)
                st.markdown('<div class="timeframe-container">', unsafe_allow_html=True)
                tf = seg_control(tf_labels_no_max, key="tf_export_price_yoy", default="5y")
                st.markdown('</div>', unsafe_allow_html=True)
                render_inflation_price_series(tf)
                st.markdown("</div>", unsafe_allow_html=True)
        
        elif theme == "bop":
            st.markdown("<h2 style='margin:0 0 20px 0; font-size:28px;'>Balance of Payments Analysis</h2>", unsafe_allow_html=True)
        
        elif theme == "central_bank":
            st.markdown("<h2 style='margin:0 0 20px 0; font-size:28px;'>Central Bank Balance Sheet</h2>", unsafe_allow_html=True)
            
            # Total Reserves excluding Gold
            def render_total_reserves(tf: str):
                render_fred_chart(
                    "TRESEGTWM194N",
                    "Total Reserves excluding Gold (go change to as % of CB BS later)",
                    "Total Reserves (USD Millions)",
                    tf
                )
            
            chart_card("cb_reserves", "Total Reserves excluding Gold", render_total_reserves, default_tf="10y", has_timeframe=True)
    
    else:
        # Main National Statistics view - show containers
        st.markdown("<h2 style='margin:0 0 30px 0; font-size:24px; text-align:center;'>National Statistics Categories</h2>", unsafe_allow_html=True)
        
        # Container 1: Growth
        st.markdown("""
        <div class="national-stats-container">
            <div class="national-stats-title">Economic Growth</div>
            <div class="national-stats-description">GDP growth, industrial production, employment, and other growth indicators</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Growth Indicators", key="view_growth", use_container_width=True):
            try:
                st.query_params["theme"] = "growth"
                st.rerun()
            except Exception:
                st.experimental_set_query_params(theme="growth")
                st.experimental_rerun()
        
        # Container 2: Inflation
        st.markdown("""
        <div class="national-stats-container">
            <div class="national-stats-title">Inflation</div>
            <div class="national-stats-description">CPI, core CPI, PPI, and other inflation metrics</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Inflation Indicators", key="view_inflation", use_container_width=True):
            try:
                st.query_params["theme"] = "inflation"
                st.rerun()
            except Exception:
                st.experimental_set_query_params(theme="inflation")
                st.experimental_rerun()
        
        # Container 3: BoP Analysis
        st.markdown("""
        <div class="national-stats-container">
            <div class="national-stats-title">BoP Analysis</div>
            <div class="national-stats-description">Current account, trade balance, capital flows, and balance of payments indicators</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View BoP Analysis", key="view_bop", use_container_width=True):
            try:
                st.query_params["theme"] = "bop"
                st.rerun()
            except Exception:
                st.experimental_set_query_params(theme="bop")
                st.experimental_rerun()
        
        # Container 4: Central Bank Balance Sheet
        st.markdown("""
        <div class="national-stats-container">
            <div class="national-stats-title">Central Bank Balance Sheet</div>
            <div class="national-stats-description">Total reserves, foreign exchange reserves, and central bank balance sheet indicators</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Central Bank Balance Sheet", key="view_central_bank", use_container_width=True):
            try:
                st.query_params["theme"] = "central_bank"
                st.rerun()
            except Exception:
                st.experimental_set_query_params(theme="central_bank")
                st.experimental_rerun()

elif active_tab == "Tab 3":
    st.session_state["active_tab"] = "Tab 3"
    
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">Coming Soon</div>
        <p style="color: #9ca3af;">Additional charts and analytics will be added here.</p>
        <br>
        <p style="color: #9ca3af;">Potential additions:</p>
        <ul style="color: #9ca3af;">
            <li>TWD vs individual currency pair deep dives</li>
            <li>Volatility analysis</li>
            <li>Carry trade indicators</li>
            <li>Macro event overlays</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# -------------------- Footer -------------------------
st.markdown("""

""", unsafe_allow_html=True)

