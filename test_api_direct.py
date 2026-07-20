"""
Direct API Test - bypasses Flask session to test database query directly
"""

import sys
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Supabase credentials not found")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 60)
print("🧪 Testing Research API Direct Query")
print("=" * 60)
print()

# Test 1: Get all research directly from Supabase
print("Test 1: Direct Supabase query")
print("-" * 60)
try:
    response = supabase.table('research').select('*').execute()
    if response.data:
        print(f"✅ Found {len(response.data)} research records")
        for i, r in enumerate(response.data, 1):
            print(f"\n  Research {i}:")
            print(f"    ID: {r.get('id')}")
            print(f"    Title: {r.get('title')}")
            print(f"    Type: {r.get('research_type')}")
            print(f"    Member: {r.get('member_name')}")
            print(f"    UID: {r.get('uid')}")
            print(f"    Created: {r.get('created_at')}")
    else:
        print("⚠️  No research found")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("-" * 60)

# Test 2: Check users table for admin
print("\nTest 2: Check admin users")
print("-" * 60)
try:
    response = supabase.table('users').select(
        '*').eq('role', 'admin').execute()
    if response.data:
        print(f"✅ Found {len(response.data)} admin users")
        for user in response.data:
            print(f"  - Email: {user.get('email')}, UID: {user.get('uid')}")
    else:
        print("⚠️  No admin users found")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
