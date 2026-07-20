"""
Check all users in the database
"""

import sys
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 60)
print("👥 Checking All Users")
print("=" * 60)
print()

try:
    response = supabase.table('users').select('*').execute()
    if response.data:
        print(f"✅ Found {len(response.data)} users:\n")
        for i, user in enumerate(response.data, 1):
            print(f"User {i}:")
            print(f"  UID: {user.get('uid')}")
            print(f"  Email: {user.get('email')}")
            print(f"  Role: {user.get('role', 'NOT SET')}")
            print(f"  Name: {user.get('name', 'N/A')}")
            print()
    else:
        print("⚠️  No users found in database")
        print("\nThis means the users table is empty!")
        print("You need to create an admin user.")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
