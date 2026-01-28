# NVDA Options Analysis Notebook

## 🎯 Overview

Comprehensive pre-earnings options analysis for hedge fund managers. This notebook pulls real-time options data from Polygon.io and provides institutional-grade analytics.

## 📊 What's Included

### 1. **Gamma Exposure (GEX) Profile**
   - Shows dealer positioning and market structure
   - Identifies zero-gamma strike (volatility regime boundary)
   - GREEN bars = stabilizing, RED bars = volatility amplifying

### 2. **Implied Volatility Analysis**
   - IV smile across multiple expirations
   - Put/Call skew (25-delta risk reversal)
   - Term structure analysis

### 3. **Open Interest & Volume**
   - Distribution by strike (calls vs puts)
   - Put/Call ratios (OI and Volume)
   - Top strikes by positioning

### 4. **Max Pain & Expected Move**
   - Max pain calculation (theoretical pin level)
   - ATM straddle-based expected move
   - Upper/Lower breakeven targets

### 5. **Unusual Options Activity**
   - Top volume contracts
   - Vol/OI ratio detection (new positions)
   - Smart money flow identification

### 6. **Executive Summary**
   - All key metrics in one dashboard
   - Trade setup considerations
   - Risk/reward assessment

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install pandas numpy plotly requests scipy jupyter
```

### 2. Set API Key

Export your Polygon.io API key:
```bash
export POLYGON_API_KEY="your_api_key_here"
```

Or set it in the notebook directly (cell 2).

### 3. Run the Notebook

```bash
jupyter notebook nvda_options_analysis.ipynb
```

Then run all cells sequentially.

## 🔑 Key Metrics Explained

### Gamma Exposure (GEX)
- **Positive GEX**: Dealers are long gamma → sell on rallies, buy on dips (stabilizing)
- **Negative GEX**: Dealers are short gamma → buy on rallies, sell on dips (amplifying)
- **Zero Gamma Strike**: Dividing line between regimes

### Put/Call Ratio
- **> 1.0**: More puts (bearish/hedging activity)
- **< 1.0**: More calls (bullish positioning)
- **> 1.5**: Extreme fear/hedging

### Expected Move
- Calculated from ATM straddle price
- Represents 1 standard deviation move
- ~68% probability the stock stays within the range

### Max Pain
- Strike where most option value expires worthless
- Theoretically where dealers want to pin the stock
- Not a prediction, but a magnet

### Vol/OI Ratio
- **> 2.0**: New positions being opened (unusual activity)
- **< 0.5**: Position closing/rolling
- Watch for large trades with high vol/OI

## 📈 How to Use for Earnings

### Pre-Earnings Analysis (1-2 days before)

1. **Check GEX Profile**
   - If spot > zero gamma → expect range compression
   - If spot < zero gamma → expect volatility expansion
   
2. **Review Expected Move**
   - Compare to historical earnings moves
   - Is IV elevated or cheap relative to history?

3. **Identify Key Strikes**
   - Large OI concentrations = support/resistance
   - Max pain = potential pin level

4. **Scan Unusual Activity**
   - Large call sweeps = bullish positioning
   - Large put sweeps = hedging/bearish
   - Straddle buying = expecting big move

### Trade Setups

**If IV is ELEVATED (expensive options):**
- ✅ Sell premium (iron condors, credit spreads)
- ✅ Ratio spreads
- ❌ Avoid buying straddles/strangles

**If IV is CHEAP (relative to expected move):**
- ✅ Buy straddles/strangles
- ✅ Directional long options
- ❌ Avoid naked selling

**High Put/Call Ratio (> 1.5):**
- Suggests fear/hedging
- Contrarian bullish signal (too much downside protection)
- Watch for put seller squeeze

**Low Put/Call Ratio (< 0.7):**
- Suggests complacency
- Potential for downside surprise
- Consider protective puts

## 🎓 Advanced Analysis

### Gamma Squeeze Mechanics
- When dealers are short gamma (negative GEX)
- Stock rallies → dealers forced to buy
- Creates feedback loop → explosive moves

### Zero Gamma Strike
- Above: Dealers provide liquidity (stabilizing)
- Below: Dealers add to momentum (destabilizing)
- Critical level to monitor intraday

### Vol Skew Interpretation
- **Positive skew** (puts > calls): Fear premium, downside protection expensive
- **Negative skew** (calls > puts): FOMO premium, upside participation expensive
- **Flat skew**: Balanced, no directional bias

## 📊 Customization

Want to analyze a different ticker? Just change cell 2:

```python
TICKER = "TSLA"  # or any other ticker
```

Want different DTE range for GEX? Modify cell 8:

```python
gex_by_strike, df_gex = calculate_gamma_exposure(df_options, current_price, dte_filter=7)  # 7 DTE instead of 30
```

## ⚠️ Important Notes

- **Data Quality**: Requires Polygon.io options subscription
- **Refresh**: Data is snapshot at time of execution
- **Greeks**: Provided by Polygon, may differ from your broker
- **Max Pain**: Theoretical construct, not a guarantee
- **Risk Management**: Always use stops and position sizing

## 🔗 Resources

- [Polygon.io API Docs](https://polygon.io/docs/options/getting-started)
- [Spotgamma (GEX methodology)](https://spotgamma.com/)
- [CBOE Options Hub](https://www.cboe.com/insights/)

## 📝 Notes

This notebook is for educational and analysis purposes. Past performance doesn't guarantee future results. Options trading involves significant risk.

---

Built with ❤️ for serious traders

