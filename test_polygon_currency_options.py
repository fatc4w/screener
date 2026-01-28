#!/usr/bin/env python3
"""
Test script to check Polygon API access to currency options data
"""

import requests
import json
from datetime import datetime, timedelta

def test_polygon_currency_options():
    """Test Polygon API access to currency options data"""
    
    # You'll need to add your Polygon API key here
    api_key = input("Enter your Polygon API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return
    
    print("🔍 Testing Polygon API access to currency options data...")
    print("=" * 60)
    
    # Test currencies
    currencies = ["C:USDJPY", "C:USDEUR", "C:USDCNH", "C:USDAUD"]
    
    for currency in currencies:
        print(f"\n📊 Testing {currency}...")
        
        # 1. Test if we can get basic currency data
        print(f"  1. Testing basic currency data...")
        currency_url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{currency}"
        currency_params = {"apikey": api_key}
        
        try:
            response = requests.get(currency_url, params=currency_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK":
                    ticker_data = data.get("ticker", {})
                    current_price = ticker_data.get("day", {}).get("c", "N/A")
                    print(f"     ✅ Currency data found - Current price: {current_price}")
                else:
                    print(f"     ❌ API returned status: {data.get('status')}")
            else:
                print(f"     ❌ HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
        
        # 2. Test if we can get options contracts
        print(f"  2. Testing options contracts...")
        contracts_url = f"https://api.polygon.io/v3/reference/options/contracts"
        contracts_params = {
            "underlying_ticker": currency,
            "limit": 10,
            "apikey": api_key
        }
        
        try:
            response = requests.get(contracts_url, params=contracts_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK":
                    results = data.get("results", [])
                    print(f"     ✅ Found {len(results)} options contracts")
                    
                    if results:
                        # Show sample contract
                        sample = results[0]
                        print(f"     📋 Sample contract:")
                        print(f"        - Ticker: {sample.get('ticker', 'N/A')}")
                        print(f"        - Expiration: {sample.get('expiration_date', 'N/A')}")
                        print(f"        - Strike: {sample.get('strike_price', 'N/A')}")
                        print(f"        - Type: {sample.get('contract_type', 'N/A')}")
                else:
                    print(f"     ❌ API returned status: {data.get('status')}")
                    if data.get('message'):
                        print(f"     📝 Message: {data.get('message')}")
            else:
                print(f"     ❌ HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
        
        # 3. Test if we can get options chain snapshot
        print(f"  3. Testing options chain snapshot...")
        snapshot_url = f"https://api.polygon.io/v3/snapshot/options/{currency}"
        snapshot_params = {"apikey": api_key}
        
        try:
            response = requests.get(snapshot_url, params=snapshot_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK":
                    results = data.get("results", [])
                    print(f"     ✅ Found {len(results)} options in snapshot")
                    
                    if results:
                        # Show sample option with Greeks
                        sample = results[0]
                        print(f"     📋 Sample option with Greeks:")
                        print(f"        - Ticker: {sample.get('ticker', 'N/A')}")
                        greeks = sample.get('greeks', {})
                        print(f"        - IV: {greeks.get('implied_volatility', 'N/A')}")
                        print(f"        - Delta: {greeks.get('delta', 'N/A')}")
                        print(f"        - Gamma: {greeks.get('gamma', 'N/A')}")
                else:
                    print(f"     ❌ API returned status: {data.get('status')}")
                    if data.get('message'):
                        print(f"     📝 Message: {data.get('message')}")
            else:
                print(f"     ❌ HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
        
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("🎯 SUMMARY:")
    print("If you see 'Found X options contracts' and 'Found X options in snapshot',")
    print("then you have access to currency options data.")
    print("\nIf you see 'No options contracts found' or HTTP errors,")
    print("then you may need to:")
    print("1. Upgrade your Polygon subscription")
    print("2. Check if currency options are available in your plan")
    print("3. Verify your API key has the right permissions")

if __name__ == "__main__":
    test_polygon_currency_options()
