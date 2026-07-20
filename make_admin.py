"""
Update a user to admin role

Usage: python make_admin.py <email>
Example: python make_admin.py darwinsemitara16@gmail.com
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


def make_admin(email):
    print("=" * 60)
    print(f"🔧 Making {email} an admin")
    print("=" * 60)
    print()

    try:
        # Find user by email
        print(f"1. Looking for user: {email}")
        response = supabase.table('users').select(
            '*').eq('email', email).execute()

        if not response.data or len(response.data) == 0:
            print(f"❌ User with email '{email}' not found")
            print("\nAvailable users:")
            all_users = supabase.table('users').select('email').execute()
            for u in all_users.data:
                print(f"  - {u.get('email')}")
            return False

        user = response.data[0]
        user_id = user.get('id')
        current_role = user.get('role', 'user')

        print(f"✅ Found user:")
        print(f"   ID: {user_id}")
        print(f"   Email: {user.get('email')}")
        print(f"   Current Role: {current_role}")
        print()

        if current_role == 'admin':
            print("ℹ️  User is already an admin!")
            return True

        # Update to admin
        print("2. Updating role to 'admin'...")
        update_response = supabase.table('users').update({
            'role': 'admin'
        }).eq('id', user_id).execute()

        if update_response.data:
            print("✅ Successfully updated user to admin!")
            print()
            print("Updated user:")
            print(f"   Email: {update_response.data[0].get('email')}")
            print(f"   Role: {update_response.data[0].get('role')}")
            print()
            print("🎉 Done! User can now access admin features.")
            print("   Please log out and log back in for changes to take effect.")
            return True
        else:
            print("❌ Failed to update user")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 60)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        print("Example: python make_admin.py darwinsemitara16@gmail.com")
        sys.exit(1)

    email = sys.argv[1]
    success = make_admin(email)
    sys.exit(0 if success else 1)
