"""
Check what users exist in Supabase and help create new accounts.
"""

from services.supabase_service import supabase, db
from dotenv import load_dotenv

load_dotenv()


def check_users():
    print("=" * 60)
    print("🔍 CHECKING SUPABASE USERS")
    print("=" * 60)

    # Check Supabase Auth users
    print("\n1️⃣ Supabase Auth Users:")
    print("-" * 60)
    try:
        response = supabase.auth.admin.list_users()
        if response and len(response) > 0:
            print(f"✅ Found {len(response)} user(s) in Supabase Auth:\n")
            for user in response:
                print(f"   📧 Email: {user.email}")
                print(f"   🆔 ID: {user.id}")
                print(
                    f"   ✉️ Confirmed: {user.email_confirmed_at is not None}")
                print(f"   📅 Created: {user.created_at}")
                print()
        else:
            print("❌ No users found in Supabase Auth")
    except Exception as e:
        print(f"❌ Error checking Auth users: {e}")

    # Check users table
    print("\n2️⃣ Users Table (Database):")
    print("-" * 60)
    try:
        docs = db.collection('users').stream()
        users = [{'id': d.id, **d.to_dict()} for d in docs]
        if users:
            print(f"✅ Found {len(users)} user(s) in database:\n")
            for user in users:
                print(f"   📧 Email: {user.get('email')}")
                print(f"   🆔 UID: {user.get('uid')}")
                print(f"   👤 Role: {user.get('role')}")
                print(f"   👔 Member ID: {user.get('member_id')}")
                print()
        else:
            print("❌ No users found in users table")
    except Exception as e:
        print(f"❌ Error checking users table: {e}")

    # Check members table
    print("\n3️⃣ Members Table:")
    print("-" * 60)
    try:
        docs = db.collection('members').stream()
        members = [{'id': d.id, **d.to_dict()} for d in docs]
        if members:
            print(f"✅ Found {len(members)} member(s):\n")
            for member in members:
                name = f"{member.get('first', '')} {member.get('last', '')}".strip(
                )
                email = member.get('email', 'No email')
                uid = member.get('uid', 'No UID')
                print(f"   👤 Name: {name}")
                print(f"   📧 Email: {email}")
                print(f"   🔗 UID: {uid}")
                print(f"   🆔 Member ID: {member.get('id')}")
                print()
        else:
            print("❌ No members found")
    except Exception as e:
        print(f"❌ Error checking members: {e}")

    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS")
    print("=" * 60)
    print("""
Option 1: Create Account from Admin Panel (EASIEST)
    1. Login as admin (admin / admin123)
    2. Go to Manage page
    3. Find or add a member
    4. Click "Create Account" button
    5. Set email and password
    6. Use those credentials to login!

Option 2: Use Python Script
    Run: python create_supabase_user.py

Option 3: Supabase Dashboard
    1. Go to https://supabase.com
    2. Open your project
    3. Go to Authentication > Users
    4. Click "Add User"
    5. Set email and password
    6. Copy the user ID
    7. Add to users table and link to member
    
⚠️  IMPORTANT: Firebase and Supabase passwords are NOT compatible!
    You need to create NEW accounts in Supabase for all users.
    """)


if __name__ == '__main__':
    check_users()
