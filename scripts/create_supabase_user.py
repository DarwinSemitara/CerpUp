"""
Create Supabase Auth User
This script creates a user in Supabase Auth manually.

Usage:
    python create_supabase_user.py

Note: You'll need to set a password for existing members.
      Users will use their email + this password to login.
"""

from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 60)
print("🔐 Create Supabase Auth User")
print("=" * 60)
print()

# Get user details
email = input("Email address: ").strip()
password = input("Password (min 6 characters): ").strip()
display_name = input("Display name (optional): ").strip()

if not email or not password:
    print("❌ Email and password are required")
    exit(1)

if len(password) < 6:
    print("❌ Password must be at least 6 characters")
    exit(1)

print()
print(f"Creating user: {email}")

try:
    # Create user in Supabase Auth
    response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "display_name": display_name or email.split('@')[0]
        }
    })

    if response.user:
        user_id = response.user.id
        print(f"✅ User created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print()

        # Create user record in Supabase database
        user_data = {
            'id': user_id,
            'uid': user_id,
            'email': email,
            'role': 'user',
            'display_name': display_name or email.split('@')[0]
        }

        supabase.table('users').insert(user_data).execute()
        print("✅ User record created in database")
        print()
        print("🎉 User can now login with:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")

    else:
        print("❌ Failed to create user")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    if 'already registered' in str(e).lower():
        print("   This email is already registered")
