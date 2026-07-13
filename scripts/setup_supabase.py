"""
Supabase Setup Helper Script

This script helps you verify your Supabase connection and setup.

Usage:
    python scripts/setup_supabase.py
"""

from supabase import create_client
from dotenv import load_dotenv
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


load_dotenv()


def main():
    print("=" * 60)
    print("🔧 Supabase Setup Verification")
    print("=" * 60)
    print()

    # Check environment variables
    print("1️⃣ Checking environment variables...")

    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

    if not SUPABASE_URL:
        print("   ❌ SUPABASE_URL not found in .env")
        print("   Please add: SUPABASE_URL=https://xxxxx.supabase.co")
        return False
    else:
        print(f"   ✅ SUPABASE_URL: {SUPABASE_URL}")

    if not SUPABASE_ANON_KEY:
        print("   ❌ SUPABASE_ANON_KEY not found in .env")
        print("   Please add your Supabase anon key")
        return False
    else:
        print(f"   ✅ SUPABASE_ANON_KEY: {SUPABASE_ANON_KEY[:20]}...")

    if not SUPABASE_SERVICE_KEY:
        print("   ❌ SUPABASE_SERVICE_KEY not found in .env")
        print("   Please add your Supabase service role key")
        return False
    else:
        print(f"   ✅ SUPABASE_SERVICE_KEY: {SUPABASE_SERVICE_KEY[:20]}...")

    print()

    # Test connection
    print("2️⃣ Testing connection...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("   ✅ Successfully created Supabase client")
    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")
        return False

    print()

    # Check tables
    print("3️⃣ Checking database tables...")

    required_tables = [
        'users',
        'members',
        'research',
        'extensions',
        'schedules',
        'news',
        'engagements',
        'tap_projects'
    ]

    tables_ok = True
    for table in required_tables:
        try:
            response = supabase.table(table).select('id').limit(1).execute()
            print(f"   ✅ Table '{table}' exists")
        except Exception as e:
            print(f"   ❌ Table '{table}' not found or error: {e}")
            tables_ok = False

    print()

    if not tables_ok:
        print("⚠️  Some tables are missing!")
        print("   Please run the SQL schema from SUPABASE_MIGRATION_GUIDE.md")
        print("   in your Supabase SQL Editor")
        return False

    # Test insert/delete
    print("4️⃣ Testing write permissions...")
    try:
        import uuid
        test_id = str(uuid.uuid4())
        test_data = {
            'id': test_id,
            'title': 'Test Connection',
            'description': 'Testing Supabase connection',
            'date': '2024-01-01',
            'location': 'Test'
        }

        # Insert test data
        supabase.table('engagements').insert(test_data).execute()
        print("   ✅ Successfully inserted test data")

        # Delete test data
        supabase.table('engagements').delete().eq(
            'id', test_id).execute()
        print("   ✅ Successfully deleted test data")

    except Exception as e:
        print(f"   ❌ Write test failed: {e}")
        print("   Check your Row Level Security (RLS) policies")
        return False

    print()
    print("=" * 60)
    print("✅ Supabase setup verified successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run migration: python scripts/migrate_firebase_to_supabase.py")
    print("2. Update app.py to use supabase_service instead of firebase_service")
    print("3. Test your application locally")
    print()

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
