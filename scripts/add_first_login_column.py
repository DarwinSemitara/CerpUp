"""
Add first_login column to users table for email verification tracking
"""

from dotenv import load_dotenv
from services.supabase_service import supabase
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


load_dotenv()


def add_first_login_column():
    """Add first_login column to users table"""

    print("="*60)
    print("FIRST LOGIN COLUMN SETUP")
    print("="*60)
    print("\nThis script updates user records to support email verification.")
    print("If you already ran the SQL in Supabase, this is optional.\n")

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    print("\nChecking users table...")

    try:
        # Add the column using raw SQL
        sql = """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS first_login BOOLEAN DEFAULT TRUE;
        """

        result = supabase.rpc('exec_sql', {'query': sql}).execute()
        print("✅ Column added successfully!")

    except Exception as e:
        # If RPC doesn't work, try direct table update approach
        print(f"RPC method failed: {e}")
        print("\nTrying alternative method...")

        try:
            # Get all users
            response = supabase.table('users').select('id').execute()
            users = response.data if hasattr(response, 'data') else []

            print(f"Found {len(users)} users")

            # Update each user to add first_login field
            for user in users:
                user_id = user['id']
                try:
                    supabase.table('users').update({
                        'first_login': True
                    }).eq('id', user_id).execute()
                    print(f"  ✓ Updated user {user_id}")
                except Exception as update_error:
                    print(
                        f"  ✗ Failed to update user {user_id}: {update_error}")

            print("\n✅ Alternative method completed!")
            print("\nNOTE: You still need to add the column to your Supabase schema.")
            print("Go to Supabase Dashboard → Table Editor → users table")
            print("Add a new column:")
            print("  - Name: first_login")
            print("  - Type: bool")
            print("  - Default value: true")
            print("  - Allow nullable: No")

        except Exception as alt_error:
            print(f"❌ Alternative method also failed: {alt_error}")
            print("\n" + "="*60)
            print("MANUAL STEPS REQUIRED:")
            print("="*60)
            print("\n1. Go to your Supabase Dashboard")
            print("2. Navigate to: Table Editor → users")
            print("3. Click 'Add Column' or edit the table")
            print("4. Add these columns:")
            print("\n   Column 1:")
            print("   - Name: first_login")
            print("   - Type: bool")
            print("   - Default value: true")
            print("   - Allow nullable: No")
            print("\n   Column 2 (optional):")
            print("   - Name: setup_completed_at")
            print("   - Type: timestamptz")
            print("   - Default value: (leave empty)")
            print("   - Allow nullable: Yes")
            print("\n5. Save the changes")
            print("6. Run this script again to verify")
            print("="*60)


if __name__ == '__main__':
    add_first_login_column()
