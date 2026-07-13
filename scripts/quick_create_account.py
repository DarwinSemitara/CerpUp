"""
Quick create account for darwin SEMITARA
"""

from services.supabase_service import supabase, db
from dotenv import load_dotenv

load_dotenv()


def create_account():
    print("=" * 60)
    print("👤 CREATING SUPABASE ACCOUNT")
    print("=" * 60)

    # Get the member
    member_id = '015400ce-cc60-4fda-90c2-2f15e99e49de'

    try:
        doc = db.collection('members').document(member_id).get()
        if not doc.exists:
            print("❌ Member not found!")
            return

        member = doc.to_dict()
        member_email = member.get('email', '').strip()
        display_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
        )

        print(f"\n✅ Member: {display_name}")
        print(f"📧 Email: {member_email}")

        # Set a default password
        password = "changeme123"

        print(f"\n🔄 Creating Supabase Auth account...")
        print(f"   Default password: {password}")
        print(f"   (You can change this later)")

        # Create Supabase Auth user
        response = supabase.auth.admin.create_user({
            "email": member_email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "display_name": display_name
            }
        })

        if not response.user:
            print("❌ Failed to create user account!")
            return

        user_id = response.user.id
        print(f"✅ Created Supabase Auth user!")
        print(f"   🆔 User ID: {user_id}")

        # Store user profile in database
        print("🔄 Creating user record in database...")
        db.collection('users').document(user_id).set({
            'id': user_id,
            'uid': user_id,
            'email': member_email,
            'role': 'user',
            'member_id': member_id,
            'display_name': display_name,
        }, merge=True)
        print("✅ User record created!")

        # Link uid back to member doc
        print("🔄 Linking user to member...")
        db.collection('members').document(member_id).update({
            'uid': user_id,
            'email': member_email
        })
        print("✅ Member linked to user!")

        print("\n" + "=" * 60)
        print("🎉 SUCCESS!")
        print("=" * 60)
        print(f"""
Account created successfully!

👤 Name: {display_name}
📧 Email: {member_email}
🔑 Password: {password}

⚠️  IMPORTANT: Change your password after first login!

Login at: http://localhost:5000/login
        """)

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Error: {error_msg}")

        if 'already registered' in error_msg.lower() or 'already been registered' in error_msg.lower():
            print("\n✅ Good news! This email already has a Supabase account.")
            print("\n💡 Options:")
            print("   1. Try logging in (maybe you already created it)")
            print("   2. Reset password in Supabase dashboard")
            print("   3. Use admin panel to update password")
            print("\n🔍 Check existing users:")
            print("   Run: python check_supabase_users.py")


if __name__ == '__main__':
    create_account()
