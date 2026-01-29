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

def calculate_cvar(returns, position_size=1000, confidence=0.95):
    var_cutoff = np.percentile(returns, (1 - confidence) * 100)
    cvar_series = returns[returns <= var_cutoff]
    cvar_1d_pct = cvar_series.mean()
    cvar_1d_usd = abs(cvar_1d_pct) * position_size
    cvar_10d_usd = cvar_1d_usd * np.sqrt(10)
    return cvar_1d_usd, cvar_10d_usd

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
            st.markdown("""
            <div class='explanation'>
            <b>This cock is a valuation screener combining "Cheapness" (Z-Score) and "Risk" (using GARCH).</b><br>
            <b>So this shit does a Box Cox Transformation (normaliser, but doesn't necessarily mean it becomes normalised after, its just more normal). Then a linear detrending to just consider trend-agnostic, is this shit cheap or rich. So considers trend.</b><br>
            <b>2 Sigma moves, this is on a 6m lookback</b>
            <ul>
                <li><b>Z-Score < -2 (Green Zone):</b> Statistically "Cheap." Potential "Buy the Dip" zone.</li>
                <li><b>Z-Score > +2 (Red Zone):</b> Statistically "Rich." Potential "Take Profit" zone.</li>
                <li><b>GARCH (Orange):</b> If high, risk is elevated. Cheap + High Vol = "Falling Knife, fuck off." Cheap + Low Vol = "Stable Entry."</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
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
            
            # --- 2. VaR ---
            st.markdown("#### Value at Risk (VaR)")
            st.markdown("""
            <div class='explanation'>
            <b>Historical VaR:</b> the loss threshold that should only be breached (1−confidence) of the time, based on the empirical return distribution.<br>
            <b>10-Day VaR here uses an actual 10-day rolling return window</b> (not √t scaling). Assumes USD 1k position.
            </div>
            """, unsafe_allow_html=True)

            var_1d = calculate_var(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=1)
            var_10d = calculate_var(df_viz['LogRet'], position_size=1000, confidence=0.95, horizon_days=10)
            v1, v2 = st.columns(2)
            v1.metric("1-Day VaR (95%)", f"${var_1d:.2f}" if var_1d is not None else "N/A")
            v2.metric("10-Day VaR (95%)", f"${var_10d:.2f}" if var_10d is not None else "N/A")

            # --- 3. CVaR ---
            st.markdown("#### Conditional Value at Risk (CVaR)")
            st.markdown("""
            <div class='explanation'>
            <b>The 5% tail occurance you lose this amount. Assumes USD 1k position</b><br>
            </div>
            """, unsafe_allow_html=True)
            
            cvar_1d, cvar_10d = calculate_cvar(df_viz['LogRet'], position_size=1000)
            m1, m2, m3 = st.columns(3)
            m1.metric("1-Day CVaR (95%)", f"${cvar_1d:.2f}")
            m2.metric("10-Day CVaR (95%)", f"${cvar_10d:.2f}")
            m3.metric("Current Vol (Ann)", f"{df_viz['GARCH'].iloc[-1] * np.sqrt(252) * 100:.2f}%")

            # --- 3. SEASONALITY ---
            st.markdown("### 2. Seasonality Composite")
            
            
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
            
            # --- 1. MAIN CHART ---
            st.markdown("""
            <div class='explanation'>
            <b>What is this?</b> Visualizes the performance of the pair trade (Long X / Short Y) and its risk.<br>
            <b>Screening Logic:</b>
            <ul>
                <li><b>Top Chart:</b> The "Price" of the spread. If rising, X is beating Y.</li>
                <li><b>Bottom Chart (Drawdown):</b> The "Pain." Shows how far the spread has fallen from its peak. If Drawdown is near 0%, momentum is strong. If Drawdown is deep, it's a "Falling Knife."</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            spread_price = np.exp(spread_2y)
            dd_2y = calculate_drawdown(spread_price)
            fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], subplot_titles=("Spread Performance (Log-OLS)", "Drawdown Risk"))
            fig_main.add_trace(go.Scatter(x=spread_2y.index, y=spread_2y, name="Spread", line=dict(color='cyan')), row=1, col=1)
            fig_main.add_trace(go.Scatter(x=dd_2y.index, y=dd_2y, name="Drawdown", fill='tozeroy', line=dict(color='red')), row=2, col=1)
            fig_main.update_layout(template="plotly_dark", height=600)
            st.plotly_chart(fig_main, use_container_width=True)
            
            # --- 2. STATS ---
            st.markdown("#### 2. Stationarity Tests (Stability Check)")
            st.markdown("""
            <div class='explanation'>
            <b>Why check this?</b> To verify if "Cheap" actually means "Cheap."<br>
            <b>Logic:</b>
            <ul>
                <li><b>Stationary (Green):</b> The spread has a stable mean. If it goes up, it usually comes down. Bounds are reliable.</li>
                <li><b>Non-Stationary (Red):</b> The spread is trending/drifting. "Cheap" can get "Cheaper." Bounds are unreliable.</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
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
            st.markdown("""
            <div class='explanation'>
            <b>What is this?</b> Checks if the spread behaves "normally" or if it has extreme moves (Fat Tails).<br>
            <b>Screening Logic:</b>
            <ul>
                <li><b>Histogram:</b> Should look like a Bell Curve.</li>
                <li><b>Q-Q Plot:</b> If dots deviate from the Red Line at the edges, beware of "Black Swan" moves in this pair.</li>
                <li><b>Jarque-Bera:</b> A low p-value means "Warning: High Crash Risk" (Non-Normal).</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
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
            st.markdown("""
            <div class='explanation'>
            <b>What is this?</b> Checks if today's price is influenced by yesterday's price.<br>
            <b>Screening Logic:</b>
            <ul>
                <li><b>Fast Drop-off:</b> Good. The spread reacts to news quickly and forgets history.</li>
                <li><b>Slow Decay (Bars stay high):</b> Bad. The spread has "momentum" and drifts. Harder to pick tops/bottoms.</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
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
            st.markdown("""
            <div class='explanation'>
            <b>What is this?</b> Checks if the two assets are still moving together.<br>
            <b>Screening Logic:</b>
            <ul>
                <li><b>Correlation > 0.8:</b> Strong relationship. The hedge is working.</li>
                <li><b>Correlation dropping to 0:</b> Breakdown! The spread is no longer a "pair." It's just two random stocks. <b>Stop trading.</b></li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            roll_win = 126
            pair['X_ret'] = np.log(pair['X']).diff()
            pair['Y_ret'] = np.log(pair['Y']).diff()
            pair['Roll_Corr'] = pair['X_ret'].rolling(roll_win).corr(pair['Y_ret'])
            df_roll_viz = pair[pair.index >= viz_start]
            fig_rc = px.line(df_roll_viz, y='Roll_Corr', title="Rolling 6-Month Correlation")
            fig_rc.add_hline(y=0, line_dash="dot", line_color="white")
            fig_rc.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_rc, use_container_width=True)