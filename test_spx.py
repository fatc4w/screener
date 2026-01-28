#!/usr/bin/env python3
"""
Test SPX data fetching and display
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date, timedelta

def test_spx_data():
    """Test SPX data fetching"""
    print("🔍 Testing SPX data fetching...")
    
    # Test yfinance SPX data
    try:
        ticker = yf.Ticker("^GSPC")
        df = ticker.history(period="1mo")
        
        if not df.empty:
            df = df.reset_index()
            df["date"] = pd.to_datetime(df["Date"])
            df["value"] = df["Close"]
            df["log_return"] = np.log(df["value"] / df["value"].shift(1))
            
            print(f"✅ SPX data fetched successfully")
            print(f"   Shape: {df.shape}")
            print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"   Latest close: {df['value'].iloc[-1]:.2f}")
            print(f"   Latest return: {df['log_return'].iloc[-1]*100:.2f}%")
            
            return True
        else:
            print("❌ No SPX data returned")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching SPX data: {str(e)}")
        return False

def test_polygon_spx_options():
    """Test Polygon SPX options data"""
    print("\n🔍 Testing Polygon SPX options data...")
    
    # You can test this with your API key
    api_key = "your_api_key_here"  # Replace with actual key
    
    if api_key == "your_api_key_here":
        print("📝 To test Polygon SPX options, replace 'your_api_key_here' with your actual API key")
        print("   SPX options should be available since Polygon supports U.S. equities/indices")
        return
    
    try:
        # Test SPX options contracts
        contracts_url = "https://api.polygon.io/v3/reference/options/contracts"
        contracts_params = {
            "underlying_ticker": "SPX",
            "limit": 5,
            "apikey": api_key
        }
        
        import requests
        response = requests.get(contracts_url, params=contracts_params, timeout=10)
        data = response.json()
        
        print(f"   Status: {data.get('status')}")
        print(f"   Results count: {len(data.get('results', []))}")
        
        if data.get('status') == 'OK' and data.get('results'):
            print("   ✅ SPX options data available!")
            sample = data['results'][0]
            print(f"   📋 Sample: {sample.get('ticker', 'N/A')} - {sample.get('expiration_date', 'N/A')}")
        else:
            print("   ❌ No SPX options data available")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🎯 SPX DATA TEST")
    print("=" * 40)
    
    spx_success = test_spx_data()
    test_polygon_spx_options()
    
    print("\n" + "=" * 40)
    if spx_success:
        print("✅ SPX data fetching is working")
        print("📝 If SPX charts aren't showing in the app:")
        print("   1. Make sure you're on the 'US' tab")
        print("   2. Check if there are any error messages")
        print("   3. Verify the app is running the latest code")
    else:
        print("❌ SPX data fetching has issues")
        print("📝 Check your internet connection and yfinance installation")
