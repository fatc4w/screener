"""
NVDA EARNINGS TONIGHT - Options Analysis
Run this: python nvda_earnings_analysis.py
"""

import os
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Config
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
TICKER = "NVDA"

print(f"\n{'='*80}")
print(f"🎯 {TICKER} EARNINGS TONIGHT - REAL-TIME ANALYSIS")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")

# ========== DATA PULL ==========
def get_price(ticker):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    r = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=10)
    if r.ok:
        data = r.json()
        if data.get("results"):
            return data["results"][0]["c"]
    return None

def get_chain(ticker):
    url = f"https://api.polygon.io/v3/snapshot/options/{ticker}"
    r = requests.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=30)
    if r.ok:
        data = r.json()
        if data.get("status") == "OK":
            return data.get("results", [])
    return []

print("📊 Fetching live data...")
spot = get_price(TICKER)
print(f"✓ {TICKER} Spot: ${spot:.2f}")

raw_chain = get_chain(TICKER)
print(f"✓ Options chain: {len(raw_chain):,} contracts")

# DEBUG: Print first contract to see structure
if raw_chain:
    print("\n🔍 DEBUG - First contract structure:")
    import json
    print(json.dumps(raw_chain[0], indent=2))
    print()

# Parse - Polygon structure inspection
records = []
for opt in raw_chain:
    d = opt.get("details", {})
    g = opt.get("greeks", {})
    day = opt.get("day", {})
    q = opt.get("last_quote", {})
    
    # Handle different possible field names
    iv_val = g.get("implied_volatility") or g.get("iv")
    oi_val = day.get("open_interest") or opt.get("open_interest", 0)
    vol_val = day.get("volume") or opt.get("volume", 0)
    
    # Price fallback chain
    last_price = (
        day.get("close") or 
        day.get("last_price") or 
        q.get("last_price") or
        q.get("p") or
        opt.get("price")
    )
    
    bid_price = q.get("bid") or q.get("b")
    ask_price = q.get("ask") or q.get("a")
    
    records.append({
        'exp': pd.to_datetime(d.get("expiration_date")),
        'strike': d.get("strike_price"),
        'type': d.get("contract_type"),
        'delta': g.get("delta"),
        'gamma': g.get("gamma"),
        'theta': g.get("theta"),
        'vega': g.get("vega"),
        'iv': iv_val,
        'volume': vol_val,
        'oi': oi_val,
        'last': last_price,
        'bid': bid_price,
        'ask': ask_price,
    })

df = pd.DataFrame(records)
df['dte'] = (df['exp'] - pd.Timestamp.now()).dt.days

# Safe mid price calculation
df['mid'] = df.apply(lambda row: (row['bid'] + row['ask']) / 2 if pd.notna(row['bid']) and pd.notna(row['ask']) else row['last'], axis=1)

# Convert numeric columns, handling None/NaN
numeric_cols = ['strike', 'delta', 'gamma', 'theta', 'vega', 'iv', 'volume', 'oi', 'last', 'bid', 'ask', 'mid']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

df = df[df['dte'] >= 0].copy()

# Data quality check
print("🔍 DATA QUALITY CHECK:")
print(f"  Total contracts: {len(df):,}")
print(f"  IV populated: {df['iv'].notna().sum():,} ({df['iv'].notna().sum()/len(df)*100:.1f}%)")
print(f"  OI populated: {(df['oi'] > 0).sum():,} ({(df['oi'] > 0).sum()/len(df)*100:.1f}%)")
print(f"  Volume populated: {(df['volume'] > 0).sum():,} ({(df['volume'] > 0).sum()/len(df)*100:.1f}%)")
print(f"  Prices populated: {df['last'].notna().sum():,} ({df['last'].notna().sum()/len(df)*100:.1f}%)")

if df['iv'].notna().sum() == 0:
    print("\n⚠️ WARNING: No IV data found! Check API response structure above.")
if (df['oi'] > 0).sum() == 0:
    print("\n⚠️ WARNING: No OI data found! Check API response structure above.")

next_exp = df['exp'].min()
df_next = df[df['exp'] == next_exp].copy()
dte = df_next['dte'].iloc[0]

print(f"\n📅 Next Expiration: {next_exp.date()} ({dte} DTE)")
print(f"📊 Total OI: {df['oi'].sum():,.0f} | Volume: {df['volume'].sum():,.0f}\n")

# ========== CHART 1: EXPECTED MOVE ==========
print("="*80)
print("🎲 CHART 1: EXPECTED MOVE")
print("="*80)

df_next['strike_diff'] = abs(df_next['strike'] - spot)
atm_strike = df_next.loc[df_next['strike_diff'].idxmin(), 'strike']

atm_call = df_next[(df_next['strike'] == atm_strike) & (df_next['type'] == 'call')]
atm_put = df_next[(df_next['strike'] == atm_strike) & (df_next['type'] == 'put')]

if not atm_call.empty and not atm_put.empty:
    call_price = atm_call.iloc[0]['mid'] if pd.notna(atm_call.iloc[0]['mid']) else atm_call.iloc[0]['last']
    put_price = atm_put.iloc[0]['mid'] if pd.notna(atm_put.iloc[0]['mid']) else atm_put.iloc[0]['last']
    
    if pd.notna(call_price) and pd.notna(put_price) and call_price > 0 and put_price > 0:
        straddle = call_price + put_price
        move_pct = (straddle / spot) * 100
        move_dollar = straddle
        
        upper = spot + move_dollar
        lower = spot - move_dollar
        
        print(f"\n  ATM Straddle (${atm_strike:.0f}): ${straddle:.2f}")
        print(f"  Expected Move: ±{move_pct:.1f}% (±${move_dollar:.2f})")
        print(f"  Upper Target: ${upper:.2f} (+{((upper/spot-1)*100):.1f}%)")
        print(f"  Lower Target: ${lower:.2f} ({((lower/spot-1)*100):.1f}%)")
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[spot], y=[1],
            mode='markers+text',
            marker=dict(size=25, color='white', symbol='diamond'),
            text=[f'SPOT<br>${spot:.2f}'],
            textposition='top center',
            textfont=dict(size=16, color='white'),
            name='Current Price'
        ))
        
        fig.add_trace(go.Scatter(
            x=[lower, upper],
            y=[0.5, 0.5],
            mode='lines+markers+text',
            line=dict(color='cyan', width=10),
            marker=dict(size=20, color='cyan'),
            text=[f'${lower:.2f}<br>-{move_pct:.1f}%', f'${upper:.2f}<br>+{move_pct:.1f}%'],
            textposition='bottom center',
            textfont=dict(size=14, color='cyan'),
            name='Expected Range'
        ))
        
        fig.update_layout(
            title=dict(
                text=f"<b>{TICKER} Expected Move for {next_exp.strftime('%b %d')}</b><br>"
                     f"<sub>Market pricing ±{move_pct:.1f}% move (${straddle:.2f} straddle)</sub>",
                x=0.5,
                font=dict(size=22)
            ),
            xaxis=dict(
                title='Price Level',
                range=[lower - move_dollar*0.5, upper + move_dollar*0.5],
                showgrid=True,
                gridcolor='#333',
                tickformat='$,.0f'
            ),
            yaxis=dict(visible=False),
            height=350,
            template='plotly_dark',
            showlegend=False
        )
        
        fig.write_html("nvda_1_expected_move.html")
        print(f"\n  ✓ Chart saved: nvda_1_expected_move.html")
        fig.show()

# ========== CHART 2: GAMMA WALLS ==========
print("\n" + "="*80)
print("⚡ CHART 2: GAMMA EXPOSURE (WALLS)")
print("="*80)

df_gex = df[df['dte'] <= 7].copy()
# Filter out NaN values for calculation
df_gex = df_gex[df_gex['gamma'].notna() & df_gex['oi'].notna()].copy()
df_gex['gex'] = df_gex['gamma'] * df_gex['oi'] * 100 * spot**2 * 0.01
df_gex.loc[df_gex['type'] == 'put', 'gex'] *= -1

gex_by_strike = df_gex.groupby('strike')['gex'].sum().reset_index()
gex_by_strike = gex_by_strike.sort_values('strike')

if not gex_by_strike.empty:
    zero_gex = gex_by_strike.loc[gex_by_strike['gex'].abs().idxmin(), 'strike']
    max_call_wall = gex_by_strike.loc[gex_by_strike['gex'].idxmax()]
    max_put_wall = gex_by_strike.loc[gex_by_strike['gex'].idxmin()]
else:
    # Fallback if no gamma data
    zero_gex = spot
    max_call_wall = {'strike': spot, 'gex': 0}
    max_put_wall = {'strike': spot, 'gex': 0}

print(f"\n  Zero Gamma Strike: ${zero_gex:.2f}")
print(f"  Largest Call Wall: ${max_call_wall['strike']:.2f} ({max_call_wall['gex']/1e9:.2f}B GEX)")
print(f"  Largest Put Wall: ${max_put_wall['strike']:.2f} ({max_put_wall['gex']/1e9:.2f}B GEX)")
if not gex_by_strike.empty:
    print(f"  Net GEX: {gex_by_strike['gex'].sum()/1e9:.2f}B")
else:
    print(f"  Net GEX: N/A (no data)")

if spot > zero_gex:
    print(f"\n  ✅ ABOVE zero gamma → Dealers stabilizing (sell rallies)")
else:
    print(f"\n  ⚠️ BELOW zero gamma → Dealers amplifying (buy rallies)")

fig = go.Figure()

if not gex_by_strike.empty:
    colors = ['green' if x > 0 else 'red' for x in gex_by_strike['gex']]
    
    fig.add_trace(go.Bar(
        x=gex_by_strike['strike'],
        y=gex_by_strike['gex'] / 1e9,
        marker_color=colors,
        marker_line_width=0,
        hovertemplate='<b>$%{x:.0f}</b><br>GEX: %{y:.2f}B<extra></extra>'
    ))
else:
    fig.add_annotation(text="No gamma data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

fig.add_vline(x=spot, line_dash="dash", line_color="white", line_width=3,
              annotation_text=f"Spot ${spot:.2f}", annotation_position="top")

fig.add_vline(x=zero_gex, line_dash="dot", line_color="yellow", line_width=3,
              annotation_text=f"Zero Gamma ${zero_gex:.2f}", annotation_position="bottom")

fig.update_layout(
    title=dict(
        text=f"<b>{TICKER} Gamma Exposure Profile (7 DTE)</b><br>"
             f"<sub>GREEN = Call wall (resistance) | RED = Put wall (support)</sub>",
        x=0.5,
        font=dict(size=20)
    ),
    xaxis_title='Strike Price',
    yaxis_title='Gamma Exposure ($B)',
    height=550,
    template='plotly_dark',
    hovermode='x',
    showlegend=False
)

fig.write_html("nvda_2_gamma_walls.html")
print(f"  ✓ Chart saved: nvda_2_gamma_walls.html")
fig.show()

# ========== CHART 3: OPEN INTEREST ==========
print("\n" + "="*80)
print("📊 CHART 3: OPEN INTEREST DISTRIBUTION")
print("="*80)

calls = df_next[df_next['type'] == 'call'].sort_values('strike')
puts = df_next[df_next['type'] == 'put'].sort_values('strike')

put_oi = puts['oi'].sum()
call_oi = calls['oi'].sum()
pc_ratio = put_oi / call_oi if call_oi > 0 else 0

put_vol = puts['volume'].sum()
call_vol = calls['volume'].sum()
pc_vol_ratio = put_vol / call_vol if call_vol > 0 else 0

print(f"\n  Put OI: {put_oi:,.0f}")
print(f"  Call OI: {call_oi:,.0f}")
print(f"  P/C Ratio (OI): {pc_ratio:.2f}")
print(f"  P/C Ratio (Vol): {pc_vol_ratio:.2f}")

if pc_ratio > 1.2:
    print(f"\n  📉 BEARISH - Heavy put positioning")
elif pc_ratio < 0.8:
    print(f"\n  📈 BULLISH - Heavy call positioning")
else:
    print(f"\n  ⚖️ BALANCED positioning")

fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=['Open Interest by Strike', 'Volume by Strike'],
    vertical_spacing=0.15,
    row_heights=[0.5, 0.5]
)

fig.add_trace(go.Bar(
    x=calls['strike'], y=calls['oi'],
    name='Calls OI', marker_color='green', opacity=0.7
), row=1, col=1)

fig.add_trace(go.Bar(
    x=puts['strike'], y=-puts['oi'],
    name='Puts OI', marker_color='red', opacity=0.7
), row=1, col=1)

fig.add_trace(go.Bar(
    x=calls['strike'], y=calls['volume'],
    name='Calls Vol', marker_color='lightgreen', opacity=0.7
), row=2, col=1)

fig.add_trace(go.Bar(
    x=puts['strike'], y=-puts['volume'],
    name='Puts Vol', marker_color='lightcoral', opacity=0.7
), row=2, col=1)

for row in [1, 2]:
    fig.add_vline(x=spot, line_dash="dash", line_color="white", row=row, col=1)

fig.update_xaxes(title_text='Strike', row=2, col=1)
fig.update_yaxes(title_text='Contracts', row=1, col=1)
fig.update_yaxes(title_text='Contracts', row=2, col=1)

fig.update_layout(
    title=dict(
        text=f"<b>{TICKER} OI & Volume Distribution</b><br>"
             f"<sub>P/C Ratio: {pc_ratio:.2f} (OI) | {pc_vol_ratio:.2f} (Vol)</sub>",
        x=0.5,
        font=dict(size=20)
    ),
    height=750,
    template='plotly_dark',
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
)

fig.write_html("nvda_3_oi_distribution.html")
print(f"  ✓ Chart saved: nvda_3_oi_distribution.html")
fig.show()

# ========== CHART 4: IV SURFACE ==========
print("\n" + "="*80)
print("📈 CHART 4: IMPLIED VOLATILITY SURFACE")
print("="*80)

exps = sorted(df['exp'].unique())[:5]

fig = go.Figure()

for exp in exps:
    df_exp = df[df['exp'] == exp].copy()
    dte_exp = df_exp['dte'].iloc[0]
    
    c = df_exp[(df_exp['type'] == 'call') & df_exp['iv'].notna()].sort_values('strike')
    if not c.empty:
        fig.add_trace(go.Scatter(
            x=c['strike'], y=c['iv'] * 100,
            mode='lines+markers',
            name=f"{dte_exp}D Calls",
            line=dict(width=2),
            marker=dict(size=4)
        ))
    
    p = df_exp[(df_exp['type'] == 'put') & df_exp['iv'].notna()].sort_values('strike')
    if not p.empty:
        fig.add_trace(go.Scatter(
            x=p['strike'], y=p['iv'] * 100,
            mode='lines+markers',
            name=f"{dte_exp}D Puts",
            line=dict(width=2, dash='dash'),
            marker=dict(size=4)
        ))

fig.add_vline(x=spot, line_dash="dot", line_color="white",
              annotation_text=f"ATM ${spot:.2f}")

fig.update_layout(
    title=dict(
        text=f"<b>{TICKER} Implied Volatility Surface</b><br>"
             f"<sub>Solid = Calls | Dashed = Puts</sub>",
        x=0.5,
        font=dict(size=20)
    ),
    xaxis_title='Strike Price',
    yaxis_title='Implied Volatility (%)',
    height=550,
    template='plotly_dark',
    hovermode='x unified',
    legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01, font=dict(size=10))
)

fig.write_html("nvda_4_iv_surface.html")
print(f"  ✓ Chart saved: nvda_4_iv_surface.html")
fig.show()

atm_calls = df_next[(df_next['type'] == 'call') & (abs(df_next['strike'] - spot) < 10) & df_next['iv'].notna()]
atm_puts = df_next[(df_next['type'] == 'put') & (abs(df_next['strike'] - spot) < 10) & df_next['iv'].notna()]

atm_iv = None
if not atm_calls.empty and not atm_puts.empty:
    call_iv_mean = atm_calls['iv'].mean()
    put_iv_mean = atm_puts['iv'].mean()
    if pd.notna(call_iv_mean) and pd.notna(put_iv_mean):
        atm_iv = (call_iv_mean + put_iv_mean) / 2 * 100
        print(f"\n  ATM IV: {atm_iv:.1f}%")
        
        if atm_iv > 60:
            print(f"  ⚠️ IV ELEVATED - Options expensive, consider selling")
        elif atm_iv < 40:
            print(f"  ✅ IV LOW - Options cheap, consider buying")
        else:
            print(f"  ⚖️ IV NORMAL - Fair value")
    else:
        print(f"\n  ⚠️ Could not calculate ATM IV - missing data")
else:
    print(f"\n  ⚠️ Could not calculate ATM IV - no ATM contracts found")

# ========== CHART 5: FLOW ==========
print("\n" + "="*80)
print("🔥 CHART 5: TODAY'S FLOW")
print("="*80)

top_vol = df.nlargest(15, 'volume')[['exp', 'dte', 'strike', 'type', 'volume', 'oi', 'last']].copy()
top_vol['vol_oi'] = top_vol['volume'] / top_vol['oi'].replace(0, 1)

print(f"\n  Top 15 Volume Contracts:\n")
print(top_vol.to_string(index=False))

unusual = df[
    (df['volume'] > df['volume'].quantile(0.95)) &
    (df['oi'] > 100)
].copy()
unusual['vol_oi'] = unusual['volume'] / unusual['oi'].replace(0, 1)
unusual = unusual[unusual['vol_oi'] > 1.5]

if not unusual.empty:
    print(f"\n  ⚠️ UNUSUAL ACTIVITY ({len(unusual)} contracts with Vol/OI > 1.5):")
    print(unusual.nlargest(10, 'volume')[['exp', 'strike', 'type', 'volume', 'oi', 'vol_oi']].to_string(index=False))

c_vol = calls.sort_values('volume', ascending=False).head(15)
p_vol = puts.sort_values('volume', ascending=False).head(15)

fig = go.Figure()

fig.add_trace(go.Bar(
    y=[f"${s:.0f}C" for s in c_vol['strike']],
    x=c_vol['volume'],
    orientation='h',
    name='Call Volume',
    marker_color='green',
    text=c_vol['volume'].apply(lambda x: f'{x:,.0f}'),
    textposition='outside'
))

fig.add_trace(go.Bar(
    y=[f"${s:.0f}P" for s in p_vol['strike']],
    x=p_vol['volume'],
    orientation='h',
    name='Put Volume',
    marker_color='red',
    text=p_vol['volume'].apply(lambda x: f'{x:,.0f}'),
    textposition='outside'
))

fig.update_layout(
    title=dict(
        text=f"<b>Top 15 Most Traded Strikes ({next_exp.strftime('%b %d')})</b>",
        x=0.5,
        font=dict(size=20)
    ),
    xaxis_title='Volume (contracts)',
    yaxis_title='',
    height=650,
    template='plotly_dark',
    showlegend=True,
    barmode='group'
)

fig.write_html("nvda_5_flow.html")
print(f"\n  ✓ Chart saved: nvda_5_flow.html")
fig.show()

# ========== CHART 6: MAX PAIN ==========
print("\n" + "="*80)
print("🎯 CHART 6: MAX PAIN")
print("="*80)

strikes = sorted(df_next['strike'].unique())
pain = []

for k in strikes:
    calls_itm = df_next[(df_next['type'] == 'call') & (df_next['strike'] < k)]
    puts_itm = df_next[(df_next['type'] == 'put') & (df_next['strike'] > k)]
    
    call_val = sum((k - row['strike']) * row['oi'] for _, row in calls_itm.iterrows())
    put_val = sum((row['strike'] - k) * row['oi'] for _, row in puts_itm.iterrows())
    
    pain.append({'strike': k, 'pain': call_val + put_val})

df_pain = pd.DataFrame(pain)
max_pain = df_pain.loc[df_pain['pain'].idxmin(), 'strike']

print(f"\n  Max Pain: ${max_pain:.2f}")
print(f"  Current: ${spot:.2f}")
print(f"  Distance: {((spot - max_pain) / spot * 100):.1f}%")

# Only compare to move_dollar if it was calculated
if 'move_dollar' in locals() and move_dollar:
    if abs(spot - max_pain) < move_dollar * 0.5:
        print(f"\n  ⚠️ CLOSE TO MAX PAIN - Pin risk")
    elif spot > max_pain:
        print(f"\n  📉 Above max pain - Gravity pulling down")
    else:
        print(f"\n  📈 Below max pain - Gravity pulling up")
else:
    if spot > max_pain:
        print(f"\n  📉 Above max pain - Gravity pulling down")
    else:
        print(f"\n  📈 Below max pain - Gravity pulling up")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_pain['strike'],
    y=df_pain['pain'] / 1e6,
    mode='lines',
    fill='tozeroy',
    line=dict(color='orange', width=2),
    fillcolor='rgba(255,165,0,0.3)'
))

fig.add_vline(x=max_pain, line_dash="dash", line_color="red", line_width=3,
              annotation_text=f"Max Pain ${max_pain:.2f}", annotation_position="top")

fig.add_vline(x=spot, line_dash="dot", line_color="white", line_width=2,
              annotation_text=f"Spot ${spot:.2f}", annotation_position="bottom")

fig.update_layout(
    title=dict(
        text=f"<b>{TICKER} Max Pain Analysis</b><br>"
             f"<sub>Strike where most options expire worthless</sub>",
        x=0.5,
        font=dict(size=20)
    ),
    xaxis_title='Strike Price',
    yaxis_title='Total Option Value at Expiry ($M)',
    height=500,
    template='plotly_dark'
)

fig.write_html("nvda_6_max_pain.html")
print(f"  ✓ Chart saved: nvda_6_max_pain.html")
fig.show()

# ========== EXECUTIVE SUMMARY ==========
print("\n" + "="*80)
print("📋 EXECUTIVE SUMMARY")
print("="*80)

print(f"\n💰 CURRENT: ${spot:.2f}\n")

if 'move_pct' in locals() and 'move_dollar' in locals() and 'lower' in locals() and 'upper' in locals():
    print(f"🎲 EXPECTED MOVE ({next_exp.strftime('%b %d')})")
    print(f"  ±{move_pct:.1f}% (±${move_dollar:.2f})")
    print(f"  Range: ${lower:.2f} - ${upper:.2f}\n")
else:
    print(f"🎲 EXPECTED MOVE ({next_exp.strftime('%b %d')})")
    print(f"  ⚠️ Could not calculate - missing price data\n")

print(f"⚡ GAMMA")
print(f"  Zero: ${zero_gex:.2f}")
print(f"  Call wall: ${max_call_wall['strike']:.2f}")
print(f"  Put wall: ${max_put_wall['strike']:.2f}")
if spot > zero_gex:
    print(f"  Status: ✅ Stabilizing")
else:
    print(f"  Status: ⚠️ Volatile")

print(f"\n📊 POSITIONING")
print(f"  P/C: {pc_ratio:.2f}")
if pc_ratio > 1.2:
    print(f"  Sentiment: 📉 Bearish")
elif pc_ratio < 0.8:
    print(f"  Sentiment: 📈 Bullish")
else:
    print(f"  Sentiment: ⚖️ Neutral")

print(f"\n🎯 KEY LEVELS")
print(f"  Max pain: ${max_pain:.2f}")
if atm_iv:
    print(f"  ATM IV: {atm_iv:.1f}%")
else:
    print(f"  ATM IV: ⚠️ Not available")

print(f"\n💡 TRADE IDEAS:")
if atm_iv and atm_iv > 60 and pc_ratio > 1.2:
    if 'lower' in locals() and 'upper' in locals():
        print(f"  • SELL put spreads (high IV + fear)")
        print(f"  • Iron condors ${lower:.0f}-${upper:.0f}")
    else:
        print(f"  • SELL put spreads (high IV + fear)")
elif atm_iv and atm_iv < 40:
    print(f"  • BUY straddles (cheap vol)")
else:
    print(f"  • Wait for direction")
    if 'max_put_wall' in locals() and 'max_call_wall' in locals():
        print(f"  • Watch ${max_put_wall['strike']:.0f} support / ${max_call_wall['strike']:.0f} resistance")

print(f"\n⚠️ POST-EARNINGS:")
print(f"  • IV crush: 50-70% drop typical")
print(f"  • Monitor ${zero_gex:.0f} (regime change)")
print(f"  • Pin risk toward ${max_pain:.0f}")

print("\n" + "="*80)
print("\n✅ ALL CHARTS SAVED AS HTML FILES")
print("   Open them in your browser to see the interactive charts")
print("="*80 + "\n")

