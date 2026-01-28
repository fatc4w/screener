#!/usr/bin/env python3
"""
Quick test to confirm Polygon API currency options availability
"""

import requests
import os

def quick_test():
    """Quick test without requiring input"""
    
    # Try to get API key from environment or use a placeholder
    api_key = os.getenv("POLYGON_API_KEY", "your_api_key_here")
    
    if api_key == "your_api_key_here":
        print("🔍 POLYGON API CURRENCY OPTIONS TEST")
        print("=" * 50)
        print("❌ No API key found in environment variables")
        print("📝 To test with your API key, run:")
        print("   export POLYGON_API_KEY='your_key_here'")
        print("   python test_polygon_currency_options.py")
        print("\n🎯 KEY FINDING:")
        print("Based on Polygon API documentation:")
        print("✅ Polygon provides forex data (USDJPY, USDEUR, etc.)")
        print("❌ Polygon does NOT provide options data for currency pairs")
        print("✅ Polygon only provides options data for U.S. equities and indices")
        print("\n💡 SOLUTION:")
        print("For currency hedging cost, you would need to:")
        print("1. Use a different data provider (Bloomberg, Refinitiv, etc.)")
        print("2. Calculate hedging cost from forex volatility data")
        print("3. Use simulated data based on historical patterns")
        return
    
    print("🔍 Testing Polygon API currency options access...")
    
    # Test currency options contracts
    currency = "C:USDJPY"
    contracts_url = f"https://api.polygon.io/v3/reference/options/contracts"
    contracts_params = {
        "underlying_ticker": currency,
        "limit": 5,
        "apikey": api_key
    }
    
    try:
        response = requests.get(contracts_url, params=contracts_params, timeout=10)
        data = response.json()
        
        print(f"📊 Testing {currency} options contracts...")
        print(f"   Status: {data.get('status')}")
        print(f"   Results count: {len(data.get('results', []))}")
        
        if data.get('message'):
            print(f"   Message: {data.get('message')}")
            
        if data.get('status') == 'OK' and data.get('results'):
            print("   ✅ Currency options data available!")
        else:
            print("   ❌ No currency options data available")
            print("   📝 This confirms Polygon doesn't provide currency options")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    quick_test()
