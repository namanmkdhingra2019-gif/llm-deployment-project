import requests
import json

# Configuration
ENDPOINT = "https://hyperthermal-lelia-headlong.ngrok-free.dev/api-endpoint"
SECRET = "mynameisnaman"

# Test payload
payload = {
    "secret": SECRET,
    "email": "naman@test.com",
    "task": "calculator-v3",
    "round": 1,
    "nonce": "test-nonce-12345",
    "brief": "Create a simple calculator app with buttons for numbers 0-9 and operations +, -, *, / and = to show result",
    "checks": [
        "Calculator has number buttons 0-9",
        "Has operation buttons +, -, *, /",
        "Has equals button to calculate",
        "Shows result in display"
    ],
    "evaluation_url": "https://httpbin.org/post"
}

print("="*70)
print("🧪 COMPLETE WORKFLOW TEST")
print("="*70)
print(f"📡 Endpoint: {ENDPOINT}")
print(f"🎯 Task: {payload['task']}")
print()
print("⏳ Sending request...")
print()

try:
    response = requests.post(ENDPOINT, json=payload, timeout=30)
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"📦 Response: {response.json()}")
        print()
        print("="*70)
        print("✅ ✅ ✅ SUCCESS! REQUEST ACCEPTED! ✅ ✅ ✅")
        print("="*70)
        print()
        print("📝 Next Steps:")
        print("  1. Check your main.py terminal for processing logs")
        print("  2. Process will take 1-2 minutes to complete")
        print(f"  3. Look for repository: tds-{payload['task']}-r{payload['round']}")
        print("  4. GitHub Pages URL will be shown in logs")
        print("  5. Wait 2 minutes, then visit the live site")
        print("="*70)
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ Request timed out after 30 seconds")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
