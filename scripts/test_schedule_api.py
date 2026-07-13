"""
Test the schedule API endpoint
Usage: python test_schedule_api.py
"""

import requests
import json

print("=" * 60)
print("🧪 Testing Schedule API")
print("=" * 60)
print()

# Test the API endpoint
try:
    response = requests.get('http://localhost:5000/api/schedules',
                            # You might need actual session
                            cookies={'session': 'test'},
                            timeout=5)

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Received {len(data)} schedule(s)")
        print()

        if data:
            print("First schedule:")
            print(json.dumps(data[0], indent=2))
            print()

            # Check field names
            first = data[0]
            print("Field name check:")
            print(f"  Has 'subjCode': {'subjCode' in first}")
            print(f"  Has 'subjName': {'subjName' in first}")
            print(f"  Has 'subj_code': {'subj_code' in first}")
            print(f"  Has 'subj_name': {'subj_name' in first}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to http://localhost:5000")
    print("   Make sure app_supabase.py is running!")
except Exception as e:
    print(f"❌ Error: {str(e)}")
