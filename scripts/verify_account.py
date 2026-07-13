"""
Verify the account was created correctly and test login.
"""

from services.supabase_service import supabase, db
from dotenv import load_dotenv
import os

load_dotenv()


def verify_account():
    print("=" * 60)
    print("🔍 VERIFYING ACCOUNT SETUP")
    print("=" * 60)

    email = "darwinsemitara16@gmail.com"
    password = "changeme123"

    # Check environment variables
    print("\n1️⃣ Checking Environment Variables:")
    print("-" * 60)
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    if supabase_url and supabase_key:
        print(f"✅ SUPABASE_URL: {supabase_url}")
        print(f"✅ SUPABASE_ANON_KEY: {supabase_key[:20]}...")
    else:
        print("❌ Missing Supabase credentials in .env!")
        return

    # Check Supabase Auth
    print("\n2️⃣ Checking Supabase Auth Users:")
    print("-" * 60)
    try:
        response = supabase.auth.admin.list_users()
        if response and len(response) > 0:
            print(f"✅ Found {len(response)} user(s):\n")
            for user in response:
                print(f"   📧 Email: {user.email}")
                print(f"   🆔 ID: {user.id}")
                print(
                    f"   ✉️ Confirmed: {user.email_confirmed_at is not None}")
                is_target = user.email == email
                if is_target:
                    print(f"   👉 THIS IS YOUR ACCOUNT!")
                print()
        else:
            print("❌ No users found in Supabase Auth!")
            print("   The account creation may have failed.")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Test login with Supabase Auth
    print("\n3️⃣ Testing Login with Supabase Auth:")
    print("-" * 60)
    print(f"Trying: {email} / {password}")

    try:
        from supabase import create_client
        test_client = create_client(supabase_url, supabase_key)

        result = test_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if result.user:
            print("✅ LOGIN SUCCESSFUL!")
            print(f"   User ID: {result.user.id}")
            print(f"   Email: {result.user.email}")
            print(f"   Token: {result.session.access_token[:30]}...")
        else:
            print("❌ Login failed - no user returned")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Login failed: {error_msg}")

        if "Invalid login credentials" in error_msg:
            print("\n💡 Possible reasons:")
            print("   1. Wrong password")
            print("   2. User was created but password wasn't set correctly")
            print("   3. Email not confirmed (but should be auto-confirmed)")
            print("\n🔧 Solutions:")
            print("   1. Reset password in Supabase dashboard")
            print("   2. Delete user and recreate with script")
            print("   3. Try admin login (admin/admin123) instead")
        return

    # Check users table
    print("\n4️⃣ Checking Users Table:")
    print("-" * 60)
    try:
        docs = db.collection('users').where('email', '==', email).stream()
        users = [{'id': d.id, **d.to_dict()} for d in docs]

        if users:
            print(f"✅ Found user record:\n")
            user = users[0]
            print(f"   Email: {user.get('email')}")
            print(f"   UID: {user.get('uid')}")
            print(f"   Role: {user.get('role')}")
            print(f"   Member ID: {user.get('member_id')}")
        else:
            print("⚠️  No user record in database")
            print("   This might cause issues after login")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Check member link
    print("\n5️⃣ Checking Member Link:")
    print("-" * 60)
    try:
        docs = db.collection('members').where('email', '==', email).stream()
        members = [{'id': d.id, **d.to_dict()} for d in docs]

        if members:
            member = members[0]
            print(f"✅ Found member:\n")
            print(f"   Name: {member.get('first')} {member.get('last')}")
            print(f"   Email: {member.get('email')}")
            print(f"   UID: {member.get('uid')}")
        else:
            print("❌ No member found with this email")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print("""
If login test was successful:
✅ Account is set up correctly
✅ You can login at http://localhost:5000/login
✅ Use: darwinsemitara16@gmail.com / changeme123

If login test failed:
❌ Need to fix the account setup
💡 Try these solutions:
   1. Reset password in Supabase dashboard
   2. Delete and recreate account
   3. Check Supabase project URL is correct
    """)


if __name__ == '__main__':
    verify_account()
