"""
Create Supabase Auth account for an existing member.
"""

from services.supabase_service import supabase, db
from dotenv import load_dotenv

load_dotenv()


def create_account_for_member():
    print("=" * 60)
    print("👤 CREATE SUPABASE ACCOUNT FOR MEMBER")
    print("=" * 60)

    # Get all members
    docs = db.collection('members').stream()
    members = [{'id': d.id, **d.to_dict()} for d in docs]

    if not members:
        print("❌ No members found in database!")
        return

    print(f"\n✅ Found {len(members)} member(s):\n")
    for i, member in enumerate(members, 1):
        name = f"{member.get('first', '')} {member.get('last', '')}".strip()
        email = member.get('email', 'No email')
        print(f"{i}. {name} - {email}")

    # Select member
    print("\n" + "-" * 60)
    choice = input(
        f"Select member number (1-{len(members)}) or 0 to cancel: ").strip()

    if choice == '0':
        print("❌ Cancelled")
        return

    try:
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(members):
            print("❌ Invalid choice!")
            return
    except ValueError:
        print("❌ Invalid input!")
        return

    selected_member = members[choice_idx]
    member_id = selected_member['id']
    member_email = selected_member.get('email', '').strip()

    if not member_email:
        print("❌ This member has no email address!")
        print("   Please add an email first in the admin panel.")
        return

    print(
        f"\n✅ Selected: {selected_member.get('first')} {selected_member.get('last')}")
    print(f"📧 Email: {member_email}")

    # Get password
    print("\n" + "-" * 60)
    password = input(
        "Enter password for this user (min 6 characters): ").strip()

    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return

    confirm_password = input("Confirm password: ").strip()

    if password != confirm_password:
        print("❌ Passwords don't match!")
        return

    print("\n" + "-" * 60)
    print("🔄 Creating Supabase Auth account...")

    try:
        # Create Supabase Auth user
        display_name = f"{selected_member.get('first', '')} {selected_member.get('last', '')}".strip(
        )

        response = supabase.auth.admin.create_user({
            "email": member_email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email
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

Login Credentials:
📧 Email: {member_email}
🔑 Password: {password}

You can now login at: http://localhost:5000/login
        """)

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")

        if 'already registered' in error_msg.lower():
            print("\n💡 This email is already registered in Supabase Auth.")
            print("   Options:")
            print("   1. Use a different email")
            print("   2. Reset the password in Supabase dashboard")
            print("   3. Delete the existing user and try again")


if __name__ == '__main__':
    create_account_for_member()
