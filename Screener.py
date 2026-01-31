import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import scipy.stats as stats
import scipy.signal as signal
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, kpss, acf
from arch import arch_model
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
from typing import Optional

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Bullshet Screener")
st.markdown("""
    <style>
    .stMetric { background-color: #0E1117; border: 1px solid #303030; padding: 15px; border-radius: 5px; }
    .stAlert { background-color: #0E1117; border: 1px solid #303030; }
    .block-container { padding-top: 1rem; }
    hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    .explanation { font-size: 0.9em; color: #a0a0a0; background-color: #161b22; padding: 10px; border-radius: 5px; border-left: 3px solid #00AAFF; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CREDENTIALS ---
POLYGON_KEY = (
    st.secrets.get("POLYGON_KEY") or 
    os.getenv("POLYGON_KEY") or 
    os.getenv("POLYGON_API_KEY")
)

# --- HELPER FUNCTIONS ---

def briefing(title: str, md: str):
    """UI helper: collapsible briefing text next to a metric/test."""
    with st.expander(f"Briefing: {title}", expanded=False):
        st.markdown(md)

def forward_simple_returns_from_log(log_returns: pd.Series, horizon_days: int) -> pd.Series:
    """
    Compute forward simple returns over `horizon_days` using log returns.
    Returns a series aligned to the start date of the horizon.
    """
    lr = pd.Series(log_returns).dropna()
    if lr.empty or horizon_days < 1:
        return pd.Series(dtype=float)
    horizon_log = lr.shift(-1).rolling(horizon_days).sum().shift(-(horizon_days - 1))
    return np.expm1(horizon_log)

def forward_simple_returns_from_loglevel(log_level: pd.Series, horizon_days: int) -> pd.Series:
    """
    Compute forward simple returns for a log-level series (e.g., log spread).
    """
    s = pd.Series(log_level).dropna()
    if s.empty or horizon_days < 1:
        return pd.Series(dtype=float)
    horizon_log = s.shift(-horizon_days) - s
    return np.expm1(horizon_log)

def select_non_overlapping(event_idx: pd.DatetimeIndex, horizon_days: int) -> pd.DatetimeIndex:
    """Keep first event, then skip any events within the forward window."""
    if len(event_idx) == 0:
        return event_idx
    event_idx = event_idx.sort_values()
    selected = []
    last = None
    for dt in event_idx:
        if last is None or (dt - last).days >= horizon_days:
            selected.append(dt)
            last = dt
    return pd.DatetimeIndex(selected)

def select_non_overlapping_by_bars(index: pd.DatetimeIndex, event_idx: pd.DatetimeIndex, horizon_bars: int) -> pd.DatetimeIndex:
    """
    Keep the first event, then skip any events that occur within the next `horizon_bars`
    on the provided trading-day index (avoids weekend/holiday distortions).
    """
    if len(event_idx) == 0:
        return event_idx
    idx = pd.DatetimeIndex(index).sort_values()
    pos = {ts: i for i, ts in enumerate(idx)}
    events = [ts for ts in pd.DatetimeIndex(event_idx).sort_values() if ts in pos]
    selected = []
    last_i = None
    for ts in events:
        i = pos[ts]
        if last_i is None or (i - last_i) >= horizon_bars:
            selected.append(ts)
            last_i = i
    return pd.DatetimeIndex(selected)

def percentile_rank(series: pd.Series, value: float) -> float:
    """Percentile rank of `value` within `series` (0-100)."""
    s = pd.Series(series).dropna()
    if s.empty:
        return float("nan")
    return float(stats.percentileofscore(s, value))

def get_earnings_dates_yf(ticker: str) -> Optional[pd.DatetimeIndex]:
    """
    Best-effort earnings dates via yfinance. Returns None if unavailable.
    """
    try:
        t = yf.Ticker(ticker)
        df = t.get_earnings_dates(limit=32)
        if df is None or df.empty:
            return None
        dates = pd.to_datetime(df.index).normalize()
        return pd.DatetimeIndex(dates)
    except Exception:
        return None

def get_data(ticker, source, start_date, end_date):
    try:
        if source == "Polygon":
            if not POLYGON_KEY:
                raise RuntimeError("Missing Polygon API key. Set `POLYGON_KEY` in Streamlit Secrets (or env var POLYGON_KEY).")
            s_date = start_date.strftime("%Y-%m-%d")
            e_date = end_date.strftime("%Y-%m-%d")
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{s_date}/{e_date}"
            params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": POLYGON_KEY}
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get('status') != 'OK' or 'results' not in data:
                return None
                
            df = pd.DataFrame(data['results'])
            df['date'] = pd.to_datetime(df['t'], unit='ms')
            df.set_index('date', inplace=True)
            df.rename(columns={'c': 'Close'}, inplace=True)
            return df[['Close']]
            
        elif source == "YFinance":
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs('Close', axis=1, level=0)
                df.columns = ['Close']
            else:
                df = df[['Close']]
            return df
    except Exception:
        return None

def calculate_garch_vol(returns):
    am = arch_model(returns * 100, vol='Garch', p=1, o=0, q=1, dist='Normal')
    res = am.fit(disp='off')
    return (res.conditional_volatility / 100)

def calculate_cvar(returns, position_size=1000, confidence=0.95, horizon_days=1):
    """
    Historical CVaR (Expected Shortfall) using empirical tail mean.
    - `returns` is expected to be a series of 1-day log returns.
    - For multi-day CVaR, we compute the *actual* horizon return using a rolling window:
        horizon_logret = sum(log returns over horizon)
        horizon_simple = exp(horizon_logret) - 1
      then take the mean of returns in the (1-confidence) tail.
    """
    r = pd.Series(returns).dropna()
    if r.empty:
        return None

    if horizon_days <= 1:
        horizon_simple = np.expm1(r)
    else:
        horizon_log = r.rolling(horizon_days).sum().dropna()
        if horizon_log.empty:
            return None
        horizon_simple = np.expm1(horizon_log)

    var_cutoff = np.percentile(horizon_simple, (1 - confidence) * 100)
    tail = horizon_simple[horizon_simple <= var_cutoff]
    if len(tail) == 0:
        return None
    cvar_usd = abs(float(np.mean(tail))) * position_size
    return float(cvar_usd)

def calculate_var(returns, position_size=1000, confidence=0.95, horizon_days=1):
    """
    Historical VaR using empirical quantile of returns.
    - `returns` is expected to be a series of 1-day log returns.
    - For multi-day VaR, we compute the *actual* horizon return using a rolling window:
        horizon_logret = sum(log returns over horizon)
        horizon_simple = exp(horizon_logret) - 1
      then take the (1-confidence) quantile of horizon_simple.
    """
    r = pd.Series(returns).dropna()
    if r.empty:
        return None

    if horizon_days <= 1:
        horizon_simple = np.expm1(r)
    else:
        horizon_log = r.rolling(horizon_days).sum().dropna()
        if horizon_log.empty:
            return None
        horizon_simple = np.expm1(horizon_log)

    var_cutoff = np.percentile(horizon_simple, (1 - confidence) * 100)
    var_usd = abs(var_cutoff) * position_size
    return float(var_usd)

def calculate_ols_hedge_ratio(series_x, series_y):
    log_x = np.log(series_x)
    log_y = np.log(series_y)
    X = sm.add_constant(log_y)
    model = sm.OLS(log_x, X).fit()
    alpha = model.params.iloc[0]
    beta = model.params.iloc[1]
    spread = log_x - (alpha + beta * log_y)
    return spread, alpha, beta

def get_seasonality_composite(df, window_type="Month"):
    df = df.copy()
    df['Year'] = df.index.year
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    current_date = df.index[-1]
    
    season_data = {}
    # Use the last 10 *available* completed years from the data (avoid assuming full history exists).
    available_years = sorted(int(y) for y in df['Year'].dropna().unique())
    years = [y for y in available_years if y < current_date.year][-10:]
    valid_years = []
    
    for y in years:
        if window_type == "Month":
            mask = (df['Year'] == y) & (df['Month'] == current_date.month)
        else:
            mask = (df['Year'] == y) & (df['Quarter'] == current_date.quarter)
            
        period_df = df[mask].copy()
        if len(period_df) > 5:
            start_price = period_df['Close'].iloc[0]
            period_df['CumRet'] = (period_df['Close'] / start_price) - 1
            period_df['DayIndex'] = range(len(period_df))
            season_data[y] = period_df.set_index('DayIndex')['CumRet']
            valid_years.append(y)

    season_df = pd.DataFrame(season_data)
    if season_df.empty:
        return None, None, None, None, None, 0, 0

    # Use each year's last available cumulative return (month/quarter lengths vary).
    final_rets = season_df.apply(
        lambda s: s.dropna().iloc[-1] if s.dropna().size else np.nan,
        axis=0,
    ).dropna()
    n_years = int(final_rets.shape[0])
    win_rate = float((final_rets > 0).mean()) if n_years else None

    # Only trim best/worst outliers if we have enough history.
    if n_years >= 5:
        best_y = final_rets.idxmax()
        worst_y = final_rets.idxmin()
        filtered_years = [int(y) for y in final_rets.index if y not in (best_y, worst_y)]
    else:
        filtered_years = [int(y) for y in final_rets.index]

    filtered_df = season_df[filtered_years]
    counts = filtered_df.count(axis=1)

    avg_curve = filtered_df.mean(axis=1, skipna=True).where(counts >= 1)
    # Month/quarter lengths differ across years; once some years end, fewer observations remain.
    # Keep the band visible as long as we have at least 2 years (or 1 if only 1 exists).
    band_min_years = 2 if n_years >= 2 else 1
    p20 = filtered_df.quantile(0.20, axis=1).where(counts >= band_min_years)
    p80 = filtered_df.quantile(0.80, axis=1).where(counts >= band_min_years)
    
    if window_type == "Month":
        curr_mask = (df['Year'] == current_date.year) & (df['Month'] == current_date.month)
    else:
        curr_mask = (df['Year'] == current_date.year) & (df['Quarter'] == current_date.quarter)
    
    curr_df = df[curr_mask].copy()
    if not curr_df.empty:
        curr_df['CumRet'] = (curr_df['Close'] / curr_df['Close'].iloc[0]) - 1
        curr_df['DayIndex'] = range(len(curr_df))
        current_curve = curr_df.set_index('DayIndex')['CumRet']
    else:
        current_curve = pd.Series(dtype=float)
        
    return current_curve, avg_curve, p20, p80, win_rate, n_years, band_min_years

def calculate_drawdown(series):
    roll_max = series.cummax()
    # Avoid division by zero
    drawdown = np.where(roll_max != 0, (series / roll_max) - 1, 0)
    return pd.Series(drawdown, index=series.index)

# --- MAIN DASHBOARD ---
st.title("Bullshet Screener")

tab1, tab2 = st.tabs(["Single Stock (Valuation Screen)", "Spread (Relative Value Screen)"])

# ==========================================
# TAB 1: SINGLE STOCK SCREENER
# ==========================================
with tab1:
    c1, c2 = st.columns(2)
    with c1: t_poly = st.text_input("Ticker (Polygon)", placeholder="AAPL").upper()
    with c2: t_yf = st.text_input("Index (YFinance)", placeholder="^GSPC").upper()
    
    active = t_poly if t_poly else t_yf
    source = "Polygon" if t_poly else "YFinance"
    
    if active:
        end = datetime.now()
        start = end - timedelta(days=365*12) 
        df = get_data(active, source, start, end)
        
        if df is not None:
            # --- 1. Z-SCORES ---
            st.markdown("### 1. Cheapness & Vol Regime")
            briefing(
                "Z-Score + GARCH regime",
                r"""
**What is this?** A valuation + risk regime view. The blue line is a *standardized* (z-scored) detrended price signal; the orange line is a GARCH(1,1) conditional volatility estimate.

**How it works (high level):**
- **Z-score**: \(z_t = \\frac{x_t-\\mu_{t}}{\\sigma_{t}}\\) where \\(x_t\\) is a transformed/detrended price signal and \\(\\mu_t,\\sigma_t\\) are rolling mean/std (here ~6 months).
- **GARCH(1,1)**: models time-varying volatility \(\\sigma_t^2 = \\omega + \\alpha\\epsilon_{t-1}^2 + \\beta\\sigma_{t-1}^2\\).

**Interpretation:**
- Z below ~-2: *unusually low vs recent history*; above ~+2: *unusually high*.
- Rising GARCH: volatility regime is elevated → position sizing / risk may need to be smaller.

**When it can mislead:**
- Z-scores assume “recent history is relevant”; **structural breaks** (regime changes) can invalidate bands.
- Detrending/transform choices change the signal; treat it as a **screen**, not a forecast.
- GARCH is sensitive to return outliers; it estimates volatility, not direction.
                """,
            )
            
            # Logic
            df_sig = df[df.index >= end - timedelta(days=365*4)].copy()
            clean_p = df_sig['Close'][df_sig['Close'] > 0]
            transformed, lmbda = stats.boxcox(clean_p)
            detrended = signal.detrend(transformed)
            df_sig.loc[clean_p.index, 'BC_Detrended'] = detrended
            roll_win = 126 
            df_sig['Z'] = (df_sig['BC_Detrended'] - df_sig['BC_Detrended'].rolling(roll_win).mean()) / df_sig['BC_Detrended'].rolling(roll_win).std()
            df_sig['LogRet'] = np.log(df_sig['Close'] / df_sig['Close'].shift(1))
            df_sig.dropna(subset=['LogRet'], inplace=True)
            garch_vol = calculate_garch_vol(df_sig['LogRet'])
            df_sig['GARCH'] = garch_vol
            df_viz = df_sig[df_sig.index >= end - timedelta(days=365*2)]
            
            fig_risk = make_subplots(specs=[[{"secondary_y": True}]])
            fig_risk.add_trace(go.Scatter(x=df_viz.index, y=df_viz['Z'], name="Valuation Z-Score", line=dict(color='cyan', width=1.5)), secondary_y=False)
            fig_risk.add_trace(go.Scatter(x=df_viz.index, y=df_viz['GARCH'], name="Risk Regime (Vol)", line=dict(color='orange', width=1, dash='dot')), secondary_y=True)
            fig_risk.add_hrect(y0=2, y1=5, fillcolor="red", opacity=0.1, line_width=0, secondary_y=False)
            fig_risk.add_hrect(y0=-5, y1=-2, fillcolor="green", opacity=0.1, line_width=0, secondary_y=False)
            fig_risk.add_hline(y=0, line_color="white", line_width=0.5, line_dash="dot", secondary_y=False)
            fig_risk.update_layout(title=f"Trend-Adjusted Valuation (Z-Score) vs Volatility", template="plotly_dark", height=450)
            st.plotly_chart(fig_risk, use_container_width=True)

            # --- 2. PM SIGNAL (PRICE ACTION) ---
            st.markdown("#### PM Signal (Price Action)")
            briefing(
                "PM quick read (cheap/expensive + price action)",
                r"""
**What is this?** A simple, PM‑oriented read: are we cheap/rich, is price action stabilizing, and what happened *historically* after similar 7‑day setups.

**Definitions:**
- **Cheap**: Z-Score <= -1.5 (statistically low vs recent trend).
- **Rich**: Z-Score >= 1.5 (statistically high vs recent trend).
- **Stabilizing**: 7-day cumulative log return >= 0 (downward momentum has paused or reversed).
- **Weakening**: 7-day cumulative log return <= 0 (upward momentum has paused or reversed).
- **Still falling**: Z-Score is cheap, but 7-day return is still negative.
- **Still rising**: Z-Score is rich, but 7-day return is still positive.
- **Tight handle**: The 20-day price range (High - Low) divided by the 20-day average price. 
    - A **percentile rank** is then computed against its own history.
    - **Example**: A 5% "Tight handle" means the current 20-day trading range is narrower than 95% of all other 20-day periods in history. This indicates extreme volatility compression (a "handle" or "base").

**How we define “similar 7‑day stretches” (historical analogs):**
- We compute the **past‑7 trading day** cumulative log return: \(R_{7}(t)=\\sum_{i=0}^{6}\\ell_{t-i}\\).
- We match prior dates \(t\\) that satisfy **both**:\n
  1) \(|R_{7}(t) - R_{7}(\\text{today})| \\le 0.5\\times \\sigma(R_{7})\) (same 7D return regime), and\n
  2) \(|Z(t) - Z(\\text{today})| \\le 0.5\) (similar valuation regime).
- We then compute the **forward** 7 trading‑day simple return from \(t\\):\n
  \(F_{7}(t)=e^{\\sum_{j=1}^{7}\\ell_{t+j}} - 1\\) (i.e., next 7 trading days, not including today).\n
- We use **non‑overlapping** matches in **trading days** (once a match triggers, we skip the next 7 trading days before allowing another match), to avoid double-counting the same move.

**Interpretation:**
- **Signal bias**:
    - *Buy bias*: cheap (Z < -1.5) and price is stabilizing (7D return >= 0).
    - *Sell bias*: rich (Z > 1.5) and price is weakening (7D return <= 0).
    - *Watch*: extreme valuation but price action is still trending against the mean-reversion thesis.
- **Avg fwd 7D return**: the mean simple return over the next 7 days across all non-overlapping historical matches.
- **Hit rate**: the percentage of those historical matches that ended with a positive return.

**When it can mislead:**
- Event risk (earnings, macro shocks) can dominate short‑horizon returns.
- Conditioning on short windows can be noisy; always check sample size.
- "Tight handle" can precede a breakout in *either* direction; it indicates compressed volatility, not necessarily a bottom.
                """,
            )

            # Use longer history for analog matching (same data used to compute Z/returns), if available.
            hist_df = df_sig.copy()
            r7 = hist_df['LogRet'].rolling(7).sum()
            curr_r7 = r7.iloc[-1]
            r7_std = r7.std()
            r7_tol = 0.5 * r7_std if pd.notna(r7_std) else 0.0

            z_series = hist_df['Z']
            curr_z = z_series.iloc[-1]
            z_tol = 0.5

            event_mask = (r7 - curr_r7).abs() <= r7_tol
            event_mask &= (z_series - curr_z).abs() <= z_tol
            event_idx = r7.index[event_mask].intersection(r7.dropna().index)

            fwd7 = forward_simple_returns_from_log(hist_df['LogRet'], 7)
            event_idx = event_idx[event_idx <= fwd7.dropna().index.max()] if not fwd7.dropna().empty else pd.DatetimeIndex([])
            event_idx = select_non_overlapping_by_bars(hist_df.index, event_idx, horizon_bars=7)

            if len(event_idx) > 0:
                avg_fwd7 = fwd7.loc[event_idx].mean()
                hit_rate = (fwd7.loc[event_idx] > 0).mean()
            else:
                avg_fwd7 = np.nan
                hit_rate = np.nan

            # Tight handle proxy: 20D range as % of price
            range20 = (df_viz['Close'].rolling(20).max() - df_viz['Close'].rolling(20).min()) / df_viz['Close'].rolling(20).mean()
            curr_range20 = range20.iloc[-1]
            range_pct = percentile_rank(range20.dropna(), curr_range20)

            # Earnings flag share (best-effort)
            earnings_dates = get_earnings_dates_yf(active) if active else None
            earnings_flag_pct = None
            if earnings_dates is not None and len(event_idx) > 0:
                flags = []
                for dt in event_idx:
                    end_dt = dt + pd.Timedelta(days=7)
                    flags.append(((earnings_dates >= dt.normalize()) & (earnings_dates <= end_dt.normalize())).any())
                earnings_flag_pct = float(np.mean(flags)) if flags else None

            bias = "Neutral"
            if curr_z <= -1.5 and curr_r7 >= 0:
                bias = "Buy bias (cheap + stabilizing)"
            elif curr_z <= -1.5 and curr_r7 < 0:
                bias = "Watch (cheap, but still falling)"
            elif curr_z >= 1.5 and curr_r7 <= 0:
                bias = "Sell/short bias (rich + weakening)"
            elif curr_z >= 1.5 and curr_r7 > 0:
                bias = "Watch (rich, but still rising)"

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Signal bias", bias)
            s2.metric("Tight handle (20D range pctile)", f"{range_pct:.0f}%" if pd.notna(range_pct) else "N/A")
            s3.metric("Avg fwd 7D return (similar setups)", f"{avg_fwd7*100:.2f}%" if pd.notna(avg_fwd7) else "N/A")
            s4.metric("Hit rate (fwd 7D > 0)", f"{hit_rate*100:.0f}%" if pd.notna(hit_rate) else "N/A")

            if earnings_flag_pct is not None:
                st.caption(f"Earnings-window share in matched history: {earnings_flag_pct*100:.0f}% (flagged, not excluded).")
            else:
                st.caption("Earnings-window share: unavailable (no earnings calendar).")
            
            # --- 2. VaR ---
            st.markdown("#### Value at Risk (VaR)")
            briefing(
                "VaR (historical / empirical)",
                r"""
**What is this?** Value-at-Risk estimates a loss threshold over a horizon such that losses exceed it only \\((1-\\alpha)\\) of the time (here \\(\\alpha=95\\%\\)).

**How it works here:** *Historical (non-parametric) VaR* using the empirical distribution:
- Convert 1‑day log returns to simple returns: \(r = e^{\\ell}-1\\)
- **1D VaR**: \(\\text{VaR}_{1d} = |Q_{5\\%}(r_{1d})|\\times\\text{position}\)
- **10D / 1M VaR**: compute rolling \(h\)-day returns (sum log returns → convert to simple), then take the 5% quantile.

**Interpretation:** “Based on the recent return history, a loss worse than this should occur ~5% of the time over that horizon.”

**When it can mislead:**
- Depends heavily on the chosen history window; **rare events** may be absent.
- If volatility is changing quickly, historical VaR can lag.
- VaR says nothing about how bad losses are **beyond** the threshold (that’s what CVaR addresses).
                """,
            )

            var_1d = calculate_var(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=1)
            var_10d = calculate_var(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=10)
            var_1m = calculate_var(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=21)
            v1, v2, v3 = st.columns(3)
            v1.metric("1-Day VaR (95%)", f"${var_1d:.2f}" if var_1d is not None else "N/A")
            v2.metric("10-Day VaR (95%)", f"${var_10d:.2f}" if var_10d is not None else "N/A")
            v3.metric("1-Month VaR (95%)", f"${var_1m:.2f}" if var_1m is not None else "N/A")

            # --- 3. CVaR ---
            st.markdown("#### Conditional Value at Risk (CVaR)")
            briefing(
                "CVaR / Expected Shortfall (historical)",
                r"""
**What is this?** CVaR (Expected Shortfall) is the *average loss* conditional on being in the worst \\((1-\\alpha)\\) tail of outcomes.

**How it works here:** compute the same horizon return series used for VaR, then:
- Find the VaR cutoff \(q = Q_{5\\%}(r)\\)
- Compute \(\\text{CVaR} = |\\mathbb{E}[r\\mid r\\le q]|\\times\\text{position}\\)

**Interpretation:** “If we are already in the worst 5% of outcomes, the average loss is about this much.”

**When it can mislead:**
- Still depends on the historical sample; if crises aren’t in the window, CVaR understates tail risk.
- For very small samples, tail estimates are noisy (especially for 10D/1M horizons).
                """,
            )
            
            cvar_1d = calculate_cvar(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=1)
            cvar_10d = calculate_cvar(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=10)
            cvar_1m = calculate_cvar(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=21)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("1-Day CVaR (95%)", f"${cvar_1d:.2f}" if cvar_1d is not None else "N/A")
            m2.metric("10-Day CVaR (95%)", f"${cvar_10d:.2f}" if cvar_10d is not None else "N/A")
            m3.metric("1-Month CVaR (95%)", f"${cvar_1m:.2f}" if cvar_1m is not None else "N/A")
            m4.metric("Current Vol (Ann)", f"{df_viz['GARCH'].iloc[-1] * np.sqrt(252) * 100:.2f}%")

            # --- 3. SEASONALITY ---
            st.markdown("### 2. Seasonality Composite")
            briefing(
                "Seasonality composite (path + band + win rate)",
                r"""
**What is this?** A historical seasonality overlay for the current month/quarter. It shows:
- **Typical path**: average cumulative return across prior years for that calendar window.
- **Range band (20–80%)**: percentile band across years at each “day within month/quarter”.
- **Win rate**: fraction of years where the full month/quarter return was positive.

**How it works (high level):**
- For each prior year, compute cumulative return from the first trading day of the month/quarter.
- Align by “day index” (0,1,2,...) and aggregate across years.

**Interpretation:**
- Band width = dispersion (uncertainty) of historical paths.
- Win rate reflects how often that calendar window ended positive historically.

**When it can mislead:**
- Data coverage limits reduce “years used” and can make bands unstable.
- Seasonality is not causality; regime changes, macro shocks, and event timing can dominate.
- Month length differs by year → later days may have fewer observations (band can taper).
                """,
            )
            
            
            s_mode = st.radio("Window", ["Current Month", "Current Quarter"], horizontal=True)
            w_type = "Month" if "Month" in s_mode else "Quarter"
            curr, avg, p20, p80, win_rate, n_years, band_min_years = get_seasonality_composite(df, w_type)
            
            if avg is not None:
                m1, m2, m3 = st.columns(3)
                m1.metric("10Y Win Rate (period up)", f"{(win_rate * 100):.0f}%" if win_rate is not None else "N/A")
                m2.metric("Years used", str(n_years))
                m3.metric("Band min years/day", str(band_min_years))

                fig_s = go.Figure()
                x_axis = avg.index

                band_mask = p20.notna() & p80.notna()
                x_band = x_axis[band_mask]
                if len(x_band) >= 2:
                    p20_band = p20[band_mask]
                    p80_band = p80[band_mask]
                    x_fill = list(x_band) + list(x_band[::-1])
                    y_fill = list(p80_band) + list(p20_band[::-1])
                    fig_s.add_trace(go.Scatter(
                        x=x_fill,
                        y=y_fill,
                        fill='toself',
                        fillcolor='rgba(0, 100, 255, 0.15)',
                        line=dict(color='rgba(255,255,255,0)'),
                        name='Normal Range (20-80%)'
                    ))

                fig_s.add_trace(go.Scatter(x=x_axis, y=avg, mode='lines', name='Typical Path (10Y Avg)', line=dict(color='#FFD700', dash='dash', width=2)))
                fig_s.add_trace(go.Scatter(x=curr.index, y=curr, mode='lines', name='Current Price Action', line=dict(color='white', width=3)))
                fig_s.update_layout(title=f"Seasonality: {s_mode} Projection", xaxis_title="Trading Days", yaxis_title="Cumulative Return", template="plotly_dark", height=500)
                st.plotly_chart(fig_s, use_container_width=True)

# ==========================================
# TAB 2: SPREAD SCREENER
# ==========================================
with tab2:
    st.markdown("### Relative Value Screener")
    briefing(
        "Pair / spread model (log-OLS hedge)",
        r"""
**What is this?** A basic relative value (pairs) model using an OLS hedge ratio on log prices.

**How it works (high level):**
- Regress \(\\log X_t\\) on \(\\log Y_t\\): \(\\log X_t = \\alpha + \\beta \\log Y_t + \\epsilon_t\\)
- The **spread** shown is the residual: \(\\epsilon_t = \\log X_t - (\\alpha + \\beta\\log Y_t)\\)
- If the relationship is stable and mean-reverting, the residual can be interpreted as “rich/cheap” vs the pair relationship.

**Interpretation:**
- \\(\\beta\\) is the hedge ratio (approx. how much Y to short per 1 unit of X, in log terms).
- A stationary residual supports mean-reversion framing; a non-stationary residual suggests drift/trend.

**When it can mislead:**
- OLS assumes a stable linear relationship; **structural breaks** and regime changes can break it.
- Logs are invalid if prices hit 0; corporate actions / bad prints can distort.
- A stationary residual does not guarantee tradability (costs, borrow, liquidity, jumps).
        """,
    )
    c1, c2 = st.columns(2)
    with c1: tx = st.text_input("Long Asset", placeholder="GOOGL").upper()
    with c2: ty = st.text_input("Short Asset", placeholder="SPY").upper()
    
    if tx and ty:
        end = datetime.now()
        start = end - timedelta(days=365*7)
        dfx = get_data(tx, "Polygon", start, end)
        dfy = get_data(ty, "Polygon", start, end)
        
        if dfx is not None and dfy is not None:
            pair = pd.concat([dfx['Close'], dfy['Close']], axis=1, keys=['X', 'Y']).dropna()
            spread, alpha, beta = calculate_ols_hedge_ratio(pair['X'], pair['Y'])
            viz_start = end - timedelta(days=365*2)
            spread_2y = spread[spread.index >= viz_start]
            st.info(f"**Hedge Ratio:** 1.0 {tx} vs {beta:.3f} {ty}")

            # --- PM SIGNAL (SPREAD EXTREMITY) ---
            st.markdown("#### PM Signal (Spread Extremity)")
            briefing(
                "Spread extremity + forward 3M outcome",
                r"""
**What is this?** A simple PM‑style read: how extreme the spread is vs history, whether it’s widening or tightening, and what happened **next 3 months** in similar past episodes.

**How it works (high level):**
- **Extremity**: compare today’s spread to history (percentile rank).
- **Velocity**: sign of recent spread change (widening vs tightening) over a 5-day window.
- **Historical analogs**: find past dates where the spread was at least as extreme as today and had the same velocity sign (widening vs tightening).
- **Non-overlapping**: to avoid double-counting, once a signal triggers, we skip the next 3 months (63 trading days) before looking for the next match.

**Interpretation:**
- **Extreme + widening**: the spread is stretched but still moving away from the mean. Mean reversion may be premature; "don't catch a falling knife."
- **Extreme + tightening**: the spread is stretched but has started turning back toward the mean. This often represents a better risk-reward entry for a reversion trade.
- **Avg fwd 3M spread return**: the average simple return of the spread (Long X / Short Y) over the next 63 trading days across all historical matches.

**When it can mislead:**
- **Structural breaks**: if the fundamental relationship between the two assets has changed, historical analogs are irrelevant.
- **Sample size**: if the spread is at an all-time extreme, there may be few or no historical matches.
- **Velocity lag**: a 5-day window might lag very fast turns or be noisy in high-volatility regimes.
                """,
            )

            spread_all = spread.dropna()
            curr_spread = spread_all.iloc[-1] if not spread_all.empty else np.nan
            vel_window = 5
            spread_vel = spread_all.diff(vel_window)
            curr_vel = spread_vel.iloc[-1] if not spread_vel.empty else np.nan
            vel_sign = "Widening" if pd.notna(curr_vel) and curr_vel > 0 else "Tightening"

            spread_pct = percentile_rank(spread_all, curr_spread)
            if pd.notna(spread_pct) and spread_pct >= 50:
                extreme_mask = spread_all >= curr_spread
            else:
                extreme_mask = spread_all <= curr_spread

            vel_mask = spread_vel > 0 if (pd.notna(curr_vel) and curr_vel > 0) else (spread_vel <= 0)
            event_idx = spread_all.index[extreme_mask & vel_mask]

            fwd63 = forward_simple_returns_from_loglevel(spread_all, 63)
            event_idx = event_idx[event_idx <= fwd63.dropna().index.max()] if not fwd63.dropna().empty else pd.DatetimeIndex([])
            event_idx = select_non_overlapping_by_bars(spread_all.index, event_idx, horizon_bars=63)

            if len(event_idx) > 0:
                avg_fwd63 = fwd63.loc[event_idx].mean()
                hit63 = (fwd63.loc[event_idx] > 0).mean()
                last_hit = event_idx.max()
                last_hit_days = (spread_all.index[-1] - last_hit).days if last_hit is not None else None
            else:
                avg_fwd63 = np.nan
                hit63 = np.nan
                last_hit_days = None

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Spread percentile rank", f"{spread_pct:.0f}%" if pd.notna(spread_pct) else "N/A")
            p2.metric("Velocity (5D)", vel_sign)
            p3.metric("Avg fwd 3M spread return", f"{avg_fwd63*100:.2f}%" if pd.notna(avg_fwd63) else "N/A")
            p4.metric("Hit rate (fwd 3M > 0)", f"{hit63*100:.0f}%" if pd.notna(hit63) else "N/A")

            if last_hit_days is not None:
                st.caption(f"Last similar extreme/velocity setup: {last_hit_days} days ago.")
            else:
                st.caption("No historical matches for current extremity/velocity.")
            
            # --- 1. MAIN CHART ---
            briefing(
                "Spread + drawdown",
                r"""
**What is this?** The top panel is the (log) spread residual; the bottom is drawdown computed on an implied “spread price” \(e^{\\epsilon_t}\\).

**How it works (high level):**
- Spread residual \(\\epsilon_t\\) is plotted directly (log units).
- For drawdown, we convert to a positive price-like series \(S_t = e^{\\epsilon_t}\\) and compute drawdown:
  \(DD_t = \\frac{S_t}{\\max_{u\\le t} S_u} - 1\\).

**Interpretation:**
- Drawdown near 0 means the spread is near its historical peak (momentum strong).
- Large negative drawdown means the spread has fallen materially from peak (risk / pain).

**When it can mislead:**
- If the spread is non-stationary, drawdown can remain deep for long periods.
- Drawdown is path-dependent and ignores speed-of-recovery; combine with stationarity + correlation health.
                """,
            )
            
            spread_price = np.exp(spread_2y)
            dd_2y = calculate_drawdown(spread_price)
            fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], subplot_titles=("Spread Performance (Log-OLS)", "Drawdown Risk"))
            fig_main.add_trace(go.Scatter(x=spread_2y.index, y=spread_2y, name="Spread", line=dict(color='cyan')), row=1, col=1)
            fig_main.add_trace(go.Scatter(x=dd_2y.index, y=dd_2y, name="Drawdown", fill='tozeroy', line=dict(color='red')), row=2, col=1)
            fig_main.update_layout(template="plotly_dark", height=600)
            st.plotly_chart(fig_main, use_container_width=True)
            
            # --- 2. STATS ---
            st.markdown("#### 2. Stationarity Tests (Stability Check)")
            briefing(
                "ADF + KPSS stationarity tests",
                r"""
**What are these?** Two complementary tests for whether the spread residual behaves like a mean-reverting process.

**How they work (high level):**
- **ADF (Augmented Dickey-Fuller)** tests the null: **unit root** (non-stationary). Low p-value → reject unit root → evidence of stationarity.
- **KPSS** tests the null: **stationary** (around a constant here). Low p-value → reject stationarity → evidence of non-stationarity.

**Interpretation (rule of thumb):**
- ADF p < 0.05 **and** KPSS p > 0.05 → most consistent with stationarity.
- ADF p > 0.05 **and** KPSS p < 0.05 → most consistent with non-stationarity.
- If both “reject” or both “don’t reject”, results are ambiguous (window too short, regime change, nonlinearities).

**When they can mislead:**
- Sensitive to sample window length; short samples reduce power.
- Structural breaks, changing vol, and non-linear mean reversion can confuse both tests.
- Stationary does not imply profitable; execution costs/jumps still matter.
                """,
            )
            
            clean_s = spread_2y.dropna()
            adf_res = adfuller(clean_s)
            kpss_res = kpss(clean_s, regression='c', nlags="auto")
            
            tc1, tc2 = st.columns(2)
            with tc1:
                st.markdown(f"**ADF p-value:** `{adf_res[1]:.4f}`")
                if adf_res[1] < 0.05: st.success("Stationary (Stable)")
                else: st.error("Non-Stationary (Trending)")
            with tc2:
                st.markdown(f"**KPSS p-value:** `{kpss_res[1]:.4f}`")
                if kpss_res[1] < 0.05: st.error("Non-Stationary")
                else: st.success("Stationary")
            
            # --- 3. DISTRIBUTION ---
            st.markdown("#### 3. Distribution & Tail Risk")
            briefing(
                "Distribution diagnostics (Histogram, Q-Q, Jarque–Bera)",
                r"""
**What is this?** A quick check of whether spread changes look approximately normal or exhibit fat tails / skew.

**How it works (high level):**
- **Histogram** shows the empirical distribution of the spread values.
- **Q–Q plot** compares empirical quantiles to normal-theory quantiles: deviations in tails indicate fat tails / skew.
- **Jarque–Bera** tests normality using skewness and kurtosis (null: normal). Low p-value → reject normality.

**Interpretation:**
- If tails bend away from the line in the Q–Q plot, extreme moves are more likely than a normal model suggests.
- Low JB p-value means “non-normal”—not necessarily “untradeable”, but tail risk is real.

**When it can mislead:**
- The spread level itself is not returns; consider also analyzing spread *changes*.
- Outliers / bad prints can dominate these diagnostics.
- Many financial series are non-normal; this is a warning flag, not a model selection theorem.
                """,
            )
            
            d1, d2, d3 = st.columns(3)
            with d1:
                fig_hist = px.histogram(clean_s, nbins=50, title="Spread Dist", marginal="box")
                fig_hist.update_layout(showlegend=False, template="plotly_dark", height=300)
                st.plotly_chart(fig_hist, use_container_width=True)
            with d2:
                sorted_s = np.sort(clean_s)
                theo = stats.norm.ppf(np.linspace(0.01, 0.99, len(sorted_s)))
                theo_scaled = theo * np.std(sorted_s) + np.mean(sorted_s)
                fig_qq = go.Figure()
                fig_qq.add_trace(go.Scatter(x=theo_scaled, y=sorted_s, mode='markers', name='Data'))
                fig_qq.add_trace(go.Scatter(x=[min(theo_scaled), max(theo_scaled)], y=[min(theo_scaled), max(theo_scaled)], mode='lines', line=dict(color='red')))
                fig_qq.update_layout(title="Q-Q Plot (Tail Check)", template="plotly_dark", height=300)
                st.plotly_chart(fig_qq, use_container_width=True)
            with d3:
                jb_stat, jb_p = stats.jarque_bera(clean_s)
                st.markdown("**Jarque-Bera Test**")
                st.metric("p-value", f"{jb_p:.4e}")
            
            # --- 4. ACF ---
            st.markdown("#### 4. Autocorrelation (Memory)")
            briefing(
                "ACF (autocorrelation function)",
                r"""
**What is this?** The autocorrelation function measures how correlated the series is with its own lagged values.

**How it works (high level):**
- ACF at lag \(k\): correlation between \(x_t\) and \(x_{t-k}\).
- The red dashed lines are an approximate 95% confidence band for zero correlation (rule-of-thumb).

**Interpretation:**
- Fast decay to ~0 suggests little memory (more “shock-driven”).
- Persistent positive/negative autocorrelation suggests momentum/mean-reversion dynamics.

**When it can mislead:**
- Non-stationarity inflates autocorrelation.
- Confidence bands are approximate; heteroskedasticity and regime changes distort them.
                """,
            )
            
            acf_vals = acf(clean_s, nlags=40)
            fig_acf = go.Figure()
            fig_acf.add_trace(go.Bar(x=list(range(len(acf_vals))), y=acf_vals))
            ci = 1.96/np.sqrt(len(clean_s))
            fig_acf.add_hline(y=ci, line_dash="dash", line_color="red")
            fig_acf.add_hline(y=-ci, line_dash="dash", line_color="red")
            fig_acf.update_layout(title="ACF (40 Lags)", template="plotly_dark", height=300)
            st.plotly_chart(fig_acf, use_container_width=True)
            
            # --- 5. ROLLING CORRELATION ---
            st.markdown("#### 5. Relationship Health (Correlation)")
            briefing(
                "Rolling correlation (returns)",
                r"""
**What is this?** Rolling correlation of **log returns** between the two legs over a ~6-month window.

**How it works (high level):**
- Compute log returns for each asset.
- Over a rolling window (e.g., 126 trading days), compute correlation.

**Interpretation:**
- High positive correlation suggests the hedge relationship is intact.
- Falling correlation suggests relationship breakdown → hedged pair can behave like two independent risks.

**When it can mislead:**
- Correlation is not stability of \\(\\beta\\); you can have high corr but changing hedge ratio.
- Correlation can flip during stress regimes; a stable relationship in calm markets can break in crises.
                """,
            )
            
            roll_win = 126
            pair['X_ret'] = np.log(pair['X']).diff()
            pair['Y_ret'] = np.log(pair['Y']).diff()
            pair['Roll_Corr'] = pair['X_ret'].rolling(roll_win).corr(pair['Y_ret'])
            df_roll_viz = pair[pair.index >= viz_start]
            fig_rc = px.line(df_roll_viz, y='Roll_Corr', title="Rolling 6-Month Correlation")
            fig_rc.add_hline(y=0, line_dash="dot", line_color="white")
            fig_rc.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_rc, use_container_width=True)