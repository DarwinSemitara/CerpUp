"""
Check Research Data in Supabase

Quick script to verify research data exists in the database.
"""

import sys
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Supabase credentials not found in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    print("=" * 60)
    print("🔍 Checking Research Data")
    print("=" * 60)
    print()

    try:
        # Check research table
        print("Querying research table...")
        response = supabase.table('research').select('*').execute()

        if response.data:
            print(f"✅ Found {len(response.data)} research records\n")

            # Display first few records
            for i, record in enumerate(response.data[:5], 1):
                print(f"Research {i}:")
                print(f"  ID: {record.get('id')}")
                print(f"  Title: {record.get('title', 'N/A')}")
                print(f"  Type: {record.get('research_type', 'N/A')}")
                print(f"  Member: {record.get('member_name', 'N/A')}")
                print(f"  UID: {record.get('uid', 'N/A')}")
                print(f"  Created: {record.get('created_at', 'N/A')}")
                print()

            if len(response.data) > 5:
                print(f"... and {len(response.data) - 5} more records")
        else:
            print("⚠️  No research records found in database")
            print("\nPossible reasons:")
            print("1. Members haven't submitted research yet")
            print("2. Migration from Firebase to Supabase not completed")
            print("3. Data is in a different table or format")
            print(
                "\nTo add test data, members can submit research through the member dashboard.")

        print()

        # Check table structure
        print("Checking table columns...")
        sample = supabase.table('research').select('*').limit(1).execute()
        if sample.data and len(sample.data) > 0:
            columns = sample.data[0].keys()
            print(f"Available columns: {', '.join(columns)}")
        else:
            print("Could not determine table structure (no data)")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)


if __name__ == '__main__':
    main()
