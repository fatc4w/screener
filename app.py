import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import date, timedelta
import io
import yfinance as yf

# ---------- Constants ----------
TF = ["1M", "3M", "YTD", "1Y", "5Y", "MAX"]
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
COUNTRIES = {
    "US": {
        "name": "United States",
        "fred_series": {
            "gdp": "GDP",
            "inflation": "CPIAUCSL",
            "unemployment": "UNRATE",
            "retail": "RSAFS",
            "industrial": "INDPRO",
            "housing": "HOUST"
        }
    },
    "EU": {
        "name": "European Union",
        "fred_series": {
            "gdp": "CLVMNACSCAB1GQEU272020",
            "inflation": "CP0000EZ19M086NEST",
            "unemployment": "LRHUTTTTEZM156S",
            "retail": "SLRTTO01EZM661S",
            "industrial": "PROINDEZM052N",
            "housing": "EUHC1"
        }
    },
    "UK": {
        "name": "United Kingdom",
        "fred_series": {
            "gdp": "UKNGDP",
            "inflation": "GBRCPIALLMINMEI",
            "unemployment": "LMUNRRTTGBM156S",
            "retail": "GBRRTTTLM",
            "industrial": "GBRPROINDMISMEI",
            "housing": "QGBR628BIS"
        }
    },
    "CN": {
        "name": "China",
        "fred_series": {
            "gdp": "MKTGDPCNA646NWDB",
            "inflation": "CHNCPIALLMINMEI",
            "unemployment": "LMUNRRTTCNM156S",
            "retail": "CHNRTTTLM",
            "industrial": "CHNPROINDMISMEI",
            "housing": "QCNN628BIS"
        }
    },
    "JP": {
        "name": "Japan",
        "fred_series": {
            "gdp": "MKTGDPJPA646NWDB",
            "inflation": "JPNCPIALLMINMEI",
            "unemployment": "LMUNRRTTJPM156S",
            "retail": "JPNRTTTLM",
            "industrial": "JPNPROINDMISMEI",
            "housing": "QJPN628BIS"
        }
    }
}

# ---------- Utils ----------
@st.cache_data(ttl=1800)
def fetch_fred(series_id: str, start: str, end: str) -> pd.DataFrame:
    """Fetch data directly from FRED API using key from secrets.toml."""
    try:
        # Get API key from secrets.toml
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key:
            st.error("FRED_API_KEY not found in secrets.toml")
            return pd.DataFrame()
        
        params = {
            "api_key": api_key,
            "series_id": series_id,
            "observation_start": start,
            "observation_end": end,
            "file_type": "json"
        }
        
        r = requests.get(FRED_API_URL, params=params, timeout=30)
        r.raise_for_status()
        
        data = r.json()
        observations = data.get("observations", [])
        
        if not observations:
            return pd.DataFrame()
        
        df = pd.DataFrame(observations)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])
        df["log_return"] = np.log(df["value"] / df["value"].shift(1))
        return df[["date", "value", "log_return"]]
        
    except Exception as e:
        st.error(f"Error fetching {series_id}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_spx_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch SPX data from yfinance."""
    try:
        ticker = yf.Ticker("^GSPC")
        df = ticker.history(start=start_date, end=end_date)
        
        if not df.empty:
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["Date"])
            df["value"] = df["Close"]
            df["log_return"] = np.log(df["value"] / df["value"].shift(1))
            return df[["date", "value", "log_return"]]
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching SPX data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_polygon_options_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch options data from Polygon API."""
    try:
        # Get API key from secrets
        api_key = st.secrets.get("POLYGON_API_KEY")
        if not api_key:
            st.error("Polygon API key not found in secrets")
            return pd.DataFrame()
        
        # Fetch options data for the ticker
        url = f"https://api.polygon.io/v3/reference/options/contracts"
        params = {
            "underlying_ticker": ticker,
            "expiration_date.gte": start_date,
            "expiration_date.lte": end_date,
            "limit": 1000,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") == "OK" and data.get("results"):
            df = pd.DataFrame(data["results"])
            return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching Polygon options data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_fred_spread(series_id_1: str, series_id_2: str, start: str, end: str) -> pd.DataFrame:
    """Fetch two FRED series and calculate the spread (series_1 - series_2)."""
    try:
        df1 = fetch_fred(series_id_1, start, end)
        df2 = fetch_fred(series_id_2, start, end)
        
        if df1.empty or df2.empty:
            return pd.DataFrame()
        
        # Merge on date
        merged = pd.merge(df1, df2, on="date", suffixes=("_1", "_2"))
        
        # Calculate spread
        merged["value"] = merged["value_1"] - merged["value_2"]
        merged["log_return"] = np.log(merged["value"] / merged["value"].shift(1))
        
        return merged[["date", "value", "log_return"]]
        
    except Exception as e:
        st.error(f"Error calculating spread: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_polygon_options_iv(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch real implied volatility data from Polygon API."""
    try:
        # Get API key from secrets
        api_key = st.secrets.get("POLYGON_API_KEY")
        if not api_key:
            st.error("Polygon API key not found in secrets")
            return pd.DataFrame()
        
        # Get current SPX price for ATM calculation
        spx_url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        spx_params = {"apikey": api_key}
        
        spx_response = requests.get(spx_url, params=spx_params, timeout=30)
        if spx_response.status_code == 200:
            spx_data = spx_response.json()
            current_price = spx_data.get("ticker", {}).get("day", {}).get("c", 5000)  # Default to 5000 if not available
        else:
            current_price = 5000  # Fallback
        
        # Get options contracts for the ticker
        contracts_url = f"https://api.polygon.io/v3/reference/options/contracts"
        contracts_params = {
            "underlying_ticker": ticker,
            "limit": 1000,
            "apikey": api_key
        }
        
        contracts_response = requests.get(contracts_url, params=contracts_params, timeout=30)
        contracts_response.raise_for_status()
        
        contracts_data = contracts_response.json()
        
        if contracts_data.get("status") == "OK" and contracts_data.get("results"):
            contracts = contracts_data["results"]
            
            # Find 3M expiration contracts (approximately 90 days out)
            from datetime import datetime, timedelta
            current_date = datetime.now()
            target_expiry = current_date + timedelta(days=90)
            
            # Find contracts closest to 3M expiration
            best_contracts = []
            min_diff = float('inf')
            
            for contract in contracts:
                exp_date_str = contract.get("expiration_date")
                if not exp_date_str:
                    continue
                
                try:
                    exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d")
                    days_diff = abs((exp_date - current_date).days - 90)
                    
                    if days_diff < min_diff:
                        min_diff = days_diff
                        best_contracts = [contract]
                    elif days_diff == min_diff:
                        best_contracts.append(contract)
                except ValueError:
                    continue
            
            if not best_contracts:
                st.warning(f"No options contracts found for {ticker}")
                return pd.DataFrame()
            
            # Get options chain snapshot for the best expiration
            best_expiry = best_contracts[0]["expiration_date"]
            
            # For now, return a single data point with current hedging cost
            # In a full implementation, you would fetch historical data
            snapshot_url = f"https://api.polygon.io/v3/snapshot/options/{ticker}"
            snapshot_params = {"apikey": api_key}
            
            snapshot_response = requests.get(snapshot_url, params=snapshot_params, timeout=30)
            snapshot_response.raise_for_status()
            
            snapshot_data = snapshot_response.json()
            
            if snapshot_data.get("status") == "OK" and snapshot_data.get("results"):
                options_data = snapshot_data["results"]
                
                # Process options data to find ATM and 25d put options
                atm_iv = None
                put_25d_iv = None
                
                for option in options_data:
                    option_details = option.get("details", {})
                    option_greeks = option.get("greeks", {})
                    
                    # Get expiration date
                    exp_date = option_details.get("expiration_date")
                    if not exp_date or exp_date != best_expiry:
                        continue
                    
                    # Get option type and strike
                    option_type = option_details.get("contract_type")
                    strike = option_details.get("strike_price")
                    iv = option_greeks.get("implied_volatility")
                    delta = option_greeks.get("delta")
                    
                    if not all([option_type, strike, iv]):
                        continue
                    
                    # Find ATM option (closest to current spot price)
                    if option_type == "call" and abs(strike - current_price) < 100:
                        if atm_iv is None or abs(strike - current_price) < abs(atm_iv - current_price):
                            atm_iv = iv
                    
                    # Find 25 delta put (approximate)
                    if option_type == "put" and delta and 0.2 <= abs(delta) <= 0.3:
                        if put_25d_iv is None or abs(abs(delta) - 0.25) < abs(abs(put_25d_iv) - 0.25):
                            put_25d_iv = iv
                
                if atm_iv and put_25d_iv:
                    # Calculate hedging cost (25d Put IV - ATM IV)
                    hedging_cost = put_25d_iv - atm_iv
                    
                    df = pd.DataFrame({
                        "date": [current_date],
                        "value": [hedging_cost],
                        "log_return": [0.0]
                    })
                    
                    return df
        
        st.warning(f"No options data found for {ticker}")
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error fetching Polygon options IV data: {str(e)}")
        return pd.DataFrame()


def analyze_hedging_cost_calculation():
    """Analyze the hedging cost calculation and provide insights."""
    st.subheader("Hedging Cost Analysis")
    
    st.markdown("""
    ### Hedging Cost Calculation Methodology:
    
    1. **Formula**: **25d Put IV - ATM IV**
       - Shows how much more expensive puts are compared to ATM options
       - Positive values indicate put skew (normal market condition)
       - Negative values would indicate call skew (rare, usually during extreme market stress)
    
    2. **Expected Values**: 
       - Put skew typically ranges from 0.5 to 3.0 volatility points
       - During market stress, put skew can spike to 5+ volatility points
       - Values should generally be positive due to the natural put skew
    
    3. **Data Source**: Real-time Polygon API options data
       - Uses 3M expiration options
       - Finds ATM call options (closest to current spot price)
       - Finds 25 delta put options
       - Calculates the difference in implied volatility
    
    4. **Implementation Details**:
       - Uses Polygon's options chain snapshot endpoint
       - Filters for approximately 90-day expiration
       - Handles missing data gracefully
       - Updates in real-time during market hours
    """)
    
    st.markdown("""
    ### Troubleshooting:
    
    - **No Data**: Check if Polygon API key is configured and has options data access
    - **Negative Values**: Verify that put IV is being subtracted from ATM IV (not vice versa)
    - **Missing Options**: Ensure the ticker has active options contracts
    - **API Errors**: Check Polygon API status and rate limits
    """)

def preset_range(preset: str):
    today = date.today()
    # Handle None or invalid preset - default to 1Y
    if preset is None:
        preset = "1Y"
    preset = preset.upper()
    
    if preset == "MAX":
        start = date(1999, 1, 1)
    elif preset == "5Y":
        start = today - timedelta(days=365 * 5)
    elif preset == "1Y":
        start = today - timedelta(days=365)
    elif preset == "YTD":
        start = date(today.year, 1, 1)
    elif preset == "3M":
        start = today - timedelta(days=90)
    else:  # "1M" or fallback
        start = today - timedelta(days=30)
    return start.isoformat(), today.isoformat()

def segmented(key: str, default="1Y"):
    """Create a segmented time frame control."""
    result = st.segmented_control(
        "Time frame",
        options=TF,
        key=key,
        label_visibility="collapsed",
        default=default,
    )
    # Return default if None (first load)
    return result if result is not None else default

# ---------- Tiles ----------
def fred_tile(tile_id: str, series_id: str, label: str, big=False):
    """Display a FRED data tile."""
    # Header row with title and time frame control
    header_l, header_r = st.columns([2, 2])
    with header_l:
        st.subheader(f"{label}")
        st.caption(f"[Source: FRED](https://fred.stlouisfed.org/series/{series_id})")
    with header_r:
        tf = segmented(f"tf_{tile_id}_{series_id}")  # Make key unique by including series_id
    
    start, end = preset_range(tf)
    df = fetch_fred(series_id, start, end)
    
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            name=label,
            line=dict(color="#1f77b4"),
            hovertemplate="%{x|%Y-%m-%d}<br>" + label + ": %{y:.2f}<extra></extra>"
        ))
        
        fig.update_layout(
            height=540 if big else 300,
            margin=dict(l=8, r=8, t=8, b=8),
            showlegend=False,
            hovermode="x",
            xaxis_title=None,
            yaxis_title=None,
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"fred_{tile_id}_{series_id}")
        
        # Show latest value
        latest = df.iloc[-1]
        st.metric(
            label="Latest",
            value=f"{latest["value"]:.2f}",
            delta=f"{latest["log_return"]*100:.1f}%",
            delta_color="normal"
        )
    else:
        st.info(f"No data available for {series_id}")

def spx_tile(tile_id: str, label: str, big=False):
    """Display SPX data tile."""
    # Header row with title and time frame control
    header_l, header_r = st.columns([2, 2])
    with header_l:
        st.subheader(f"{label}")
        st.caption("[Source: Yahoo Finance]")
    with header_r:
        tf = segmented(f"tf_{tile_id}_spx")
    
    start, end = preset_range(tf)
    df = fetch_spx_data(start, end)
    
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            name=label,
            line=dict(color="#1f77b4"),
            hovertemplate="%{x|%Y-%m-%d}<br>" + label + ": %{y:.2f}<extra></extra>"
        ))
        
        fig.update_layout(
            height=540 if big else 300,
            margin=dict(l=8, r=8, t=8, b=8),
            showlegend=False,
            hovermode="x",
            xaxis_title=None,
            yaxis_title=None,
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"spx_{tile_id}")
        
        # Show latest value
        latest = df.iloc[-1]
        st.metric(
            label="Latest",
            value=f"{latest["value"]:.2f}",
            delta=f"{latest["log_return"]*100:.1f}%",
            delta_color="normal"
        )
    else:
        st.info(f"No SPX data available")

def hedging_cost_tile(tile_id: str, ticker: str, label: str, big=False):
    """Display hedging cost tile."""
    # Header row with title and time frame control
    header_l, header_r = st.columns([2, 2])
    with header_l:
        st.subheader(f"{label}")
        st.caption("[Source: Polygon API]")
    with header_r:
        tf = segmented(f"tf_{tile_id}_hedging")
    
    start, end = preset_range(tf)
    df = fetch_polygon_options_iv(ticker, start, end)
    
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            name=label,
            line=dict(color="#ff7f0e"),
            hovertemplate="%{x|%Y-%m-%d}<br>" + label + ": %{y:.2f} vol<extra></extra>"
        ))
        
        fig.update_layout(
            height=540 if big else 300,
            margin=dict(l=8, r=8, t=8, b=8),
            showlegend=False,
            hovermode="x",
            xaxis_title=None,
            yaxis_title=None,
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"hedging_{tile_id}")
        
        # Show latest value
        latest = df.iloc[-1]
        st.metric(
            label="Latest",
            value=f"{latest["value"]:.1f} vol",
            delta=f"{latest["log_return"]*100:.1f}%",
            delta_color="normal"
        )
        
        # Add description
        st.caption(f"{label}: 25d Put IV - ATM IV (3M options). Volatility points. Positive values indicate put skew (puts more expensive than ATM).")
    else:
        st.info(f"No hedging cost data available for {ticker}. Check Polygon API key and options data availability.")

def money_market_spreads_tile(tile_id: str, label: str, big=False):
    """Display money market spreads tile with SOFR-EFFR and SOFR-ON RRP."""
    # Header row with title and time frame control
    header_l, header_r = st.columns([2, 2])
    with header_l:
        st.subheader(f"{label}")
        st.caption("[Source: FRED]")
    with header_r:
        tf = segmented(f"tf_{tile_id}_spreads")
    
    start, end = preset_range(tf)
    
    # Fetch spreads
    sofr_effr = fetch_fred_spread("SOFR", "EFFR", start, end)
    sofr_onrrp = fetch_fred_spread("SOFR", "RRPONTSYD", start, end)
    
    fig = go.Figure()
    
    # Add SOFR-EFFR spread
    if not sofr_effr.empty:
        fig.add_trace(go.Scatter(
            x=sofr_effr["date"],
            y=sofr_effr["value"],
            name="SOFR - EFFR",
            line=dict(color="#1f77b4"),
            hovertemplate="%{x|%Y-%m-%d}<br>SOFR - EFFR: %{y:.2f} bps<extra></extra>"
        ))
    
    # Add SOFR-ON RRP spread
    if not sofr_onrrp.empty:
        fig.add_trace(go.Scatter(
            x=sofr_onrrp["date"],
            y=sofr_onrrp["value"],
            name="SOFR - ON RRP",
            line=dict(color="#ff7f0e"),
            hovertemplate="%{x|%Y-%m-%d}<br>SOFR - ON RRP: %{y:.2f} bps<extra></extra>"
        ))
    
    fig.update_layout(
        height=540 if big else 300,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x",
        xaxis_title=None,
        yaxis_title="Basis Points",
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"spreads_{tile_id}")
    
    # Show latest values for both spreads
    col1, col2 = st.columns(2)
    
    with col1:
        if not sofr_effr.empty:
            latest = sofr_effr.iloc[-1]
            st.metric(
                label="SOFR - EFFR",
                value=f"{latest['value']:.2f} bps",
                delta=f"{latest['log_return']*100:.1f}%",
                delta_color="normal"
            )
        else:
            st.info("No SOFR-EFFR data available")
    
    with col2:
        if not sofr_onrrp.empty:
            latest = sofr_onrrp.iloc[-1]
            st.metric(
                label="SOFR - ON RRP",
                value=f"{latest['value']:.2f} bps",
                delta=f"{latest['log_return']*100:.1f}%",
                delta_color="normal"
            )
        else:
            st.info("No SOFR-ON RRP data available")

# ---------- Views ----------
def country_grid(country_code: str):
    """Display economic indicators for a country."""
    country = COUNTRIES[country_code]
    series = country["fred_series"]
    
    # Add SPX charts for US only
    if country_code == "US":
        st.subheader("General Charts")
        
        # Create column layout for SPX charts
        col1, col2 = st.columns(2)
        
        # SPX Index and SPX Hedge Cost
        with col1:
            spx_tile(
                f"{country_code}_spx",
                "SPX Index",
                big=True
            )
        with col2:
            hedging_cost_tile(
                f"{country_code}_spx_hedging",
                "SPX",
                "SPX Hedge Cost",
                big=True
            )
        
        # Money Market Spreads (full width)
        money_market_spreads_tile(
            f"{country_code}_mm_spreads",
            "US Money Market Spreads",
            big=True
        )
        
        # Add analysis button
        if st.button("Analyze Hedging Cost Calculation", key="hedging_analysis"):
            analyze_hedging_cost_calculation()
        
        st.divider()
        st.subheader("Economic Themes")
    
    # Create column layout
    col1, col2 = st.columns(2)
    
    # GDP and Inflation
    with col1:
        fred_tile(
            f"{country_code}_gdp",
            series["gdp"],
            f"{country["name"]} GDP",
            big=True
        )
    with col2:
        fred_tile(
            f"{country_code}_cpi",
            series["inflation"],
            f"{country["name"]} CPI",
            big=True
        )
    
    # Unemployment and Retail
    with col1:
        fred_tile(
            f"{country_code}_unemployment",
            series["unemployment"],
            f"{country["name"]} Unemployment Rate"
        )
    with col2:
        fred_tile(
            f"{country_code}_retail",
            series["retail"],
            f"{country["name"]} Retail Sales"
        )
    
    # Industrial Production and Housing
    with col1:
        fred_tile(
            f"{country_code}_industrial",
            series["industrial"],
            f"{country["name"]} Industrial Production"
        )
    with col2:
        fred_tile(
            f"{country_code}_housing",
            series["housing"],
            f"{country["name"]} Housing Starts"
        )

def handle_country_nav(country_code: str):
    """Handle navigation and display for a country."""
    country = COUNTRIES[country_code]
    st.header(f"{country['name']} Economic Indicators")
    country_grid(country_code)

# ---------- Config ----------
# Page config
st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📈",
    layout="wide"
)

# ---------- Main App ----------
# Main app config
st.title("Macro Dashboard")

# Navigation - country selector
country_options = list(COUNTRIES.keys())
selected_country = st.segmented_control(
    "Country",
    options=country_options,
    key="country",
    label_visibility="hidden",
    default="US",
)

# Handle None case (first load before user selects)
if selected_country is None:
    selected_country = "US"

# Display selected country
handle_country_nav(selected_country)
