import requests
import json

# API key
access_token = "rO5GTyEu730ByoEDLKqeeexWUwusLd7CV6fBsZ8eOgrNg7yGfwl7c7eaYvaN8uk1lQCqeeZsfA3bnEtbIKZg0t6w24u104rs67RHr0sj0ngXSEoA7Bq5TscsTTb8s7ZN"

print("=" * 60)
print("Testing CEIC API with requests library")
print("=" * 60)

# Test 1: Authorization header
print("\nTest 1: Using Authorization header...")
url = "https://api.ceicdata.com/v2/series/369703417_SR136012947"
params = {"lang": "en"}
headers = {"Authorization": access_token}

try:
    response = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        print("\n✓ SUCCESS with Authorization header!")
        data = response.json()
        print(f"\nData keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
    else:
        print(f"\n✗ Failed with status {response.status_code}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__} - {str(e)}")

# Test 2: Token query parameter
print("\n" + "-" * 60)
print("\nTest 2: Using token query parameter...")
params_with_token = {"lang": "en", "token": access_token}

try:
    response = requests.get(url, params=params_with_token, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        print("\n✓ SUCCESS with token query parameter!")
        data = response.json()
        print(f"\nData keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
    else:
        print(f"\n✗ Failed with status {response.status_code}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__} - {str(e)}")

print("\n" + "=" * 60)

# Summary
print("\nSUMMARY:")
print("If both tests show 403, the API key doesn't have access to this series.")
print("If tests show 401, the API key is invalid.")
print("If tests show 200, the API key is working correctly!")
print("=" * 60)
