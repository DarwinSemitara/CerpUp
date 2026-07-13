"""
Firebase to Supabase Data Migration Script

This script migrates all data from Firebase Firestore to Supabase PostgreSQL.

Usage:
    python scripts/migrate_firebase_to_supabase.py

Requirements:
    1. Firebase credentials configured
    2. Supabase credentials in .env file
    3. Supabase database schema already created
"""

from dotenv import load_dotenv
from supabase import create_client
from services.firebase_service import db as firebase_db
import sys
import os
from datetime import datetime

# Add parent directory to Python path FIRST
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import modules

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env file")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 60)
print("🚀 Firebase to Supabase Migration")
print("=" * 60)
print()


def migrate_collection(firebase_collection, supabase_table, transform_fn=None):
    """
    Migrate a Firebase collection to a Supabase table.

    Args:
        firebase_collection: Name of Firebase collection
        supabase_table: Name of Supabase table
        transform_fn: Optional function to transform document data
    """
    print(f"📦 Migrating {firebase_collection} → {supabase_table}")

    try:
        # Get all documents from Firebase
        docs = firebase_db.collection(firebase_collection).stream()
        documents = []

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id  # Preserve original Firebase ID

            # Apply transformation if provided
            if transform_fn:
                data = transform_fn(data)

            documents.append(data)

        if not documents:
            print(f"   ⚠️  No documents found in {firebase_collection}")
            return

        # Insert into Supabase (batch insert)
        response = supabase.table(supabase_table).insert(documents).execute()

        if response.data:
            print(f"   ✅ Migrated {len(documents)} documents")
        else:
            print(f"   ❌ Failed to migrate {firebase_collection}")

    except Exception as e:
        print(f"   ❌ Error migrating {firebase_collection}: {str(e)}")


def transform_users(data):
    """Transform users document for Supabase."""
    # Ensure required fields
    return {
        'id': data.get('id'),
        'uid': data.get('uid'),
        'email': data.get('email'),
        'role': data.get('role', 'user'),
        'member_id': data.get('member_id'),
        'display_name': data.get('display_name'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
        'updated_at': data.get('updated_at', datetime.utcnow().isoformat()),
    }


def transform_members(data):
    """Transform members document for Supabase."""
    return {
        'id': data.get('id'),
        'uid': data.get('uid'),
        'user_no': data.get('user_no'),
        'last': data.get('last', ''),
        'first': data.get('first', ''),
        'mi': data.get('mi', 'N/A'),
        'suffix': data.get('suffix'),
        'role': data.get('role'),
        'email': data.get('email'),
        'contact': data.get('contact'),
        'address': data.get('address'),
        'gender': data.get('gender'),
        'dob': data.get('dob'),
        'type': data.get('type', 'admin_staff'),
        'is_faculty': data.get('is_faculty', False),
        'availability': data.get('availability', []),
        'photo_url': data.get('photo_url'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
        'updated_at': data.get('updated_at', datetime.utcnow().isoformat()),
    }


def transform_research(data):
    """Transform research document for Supabase."""
    return {
        'id': data.get('id'),
        'uid': data.get('uid'),
        'member_id': data.get('member_id'),
        'member_name': data.get('member_name'),
        'research_type': data.get('research_type'),
        'title': data.get('title', ''),
        'role': data.get('role'),
        'co_workers': data.get('co_workers'),
        'co_authors': data.get('co_authors'),
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'date_completion': data.get('date_completion'),
        'funding_agency': data.get('funding_agency'),
        'credit_units': data.get('credit_units'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
        'updated_at': data.get('updated_at', datetime.utcnow().isoformat()),
    }


def transform_extensions(data):
    """Transform extensions document for Supabase."""
    return {
        'id': data.get('id'),
        'uid': data.get('uid'),
        'member_id': data.get('member_id'),
        'member_name': data.get('member_name'),
        'extension_type': data.get('extension_type'),
        'title': data.get('title', ''),
        'role': data.get('role'),
        'co_workers': data.get('co_workers'),
        'participants': data.get('participants'),
        'hours': data.get('hours'),
        'duration': data.get('duration'),
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'funding_agency': data.get('funding_agency'),
        'credit_units': data.get('credit_units'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
        'updated_at': data.get('updated_at', datetime.utcnow().isoformat()),
    }


def transform_schedules(data):
    """Transform schedules document for Supabase."""
    return {
        'id': data.get('id'),
        'prof': data.get('prof', ''),
        'subj_code': data.get('subjCode', ''),
        'subj_name': data.get('subjName', ''),
        'type': data.get('type', 'Lecture'),
        'day': data.get('day', ''),
        'start': data.get('start', ''),
        'end': data.get('end', ''),
        'room': data.get('room', ''),
        'units': data.get('units', 0),
        'section': data.get('section', ''),
        'year': data.get('year', '1'),
        'semester': data.get('semester', '1'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
    }


def transform_news(data):
    """Transform news document for Supabase."""
    return {
        'id': data.get('id'),
        'title': data.get('title', ''),
        'content': data.get('content'),
        'date': data.get('date'),
        'photo_url': data.get('photo_url'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
        'updated_at': data.get('updated_at', datetime.utcnow().isoformat()),
    }


def transform_engagements(data):
    """Transform engagements document for Supabase."""
    return {
        'id': data.get('id'),
        'title': data.get('title', ''),
        'description': data.get('description'),
        'date': data.get('date'),
        'location': data.get('location'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
    }


def transform_tap_projects(data):
    """Transform tap_projects document for Supabase."""
    return {
        'id': data.get('id'),
        'title': data.get('title', ''),
        'section': data.get('section', ''),
        'description': data.get('description'),
        'location': data.get('location'),
        'date_start': data.get('dateStart'),
        'date_end': data.get('dateEnd'),
        'created_at': data.get('created_at', datetime.utcnow().isoformat()),
    }


def main():
    """Run the migration."""

    print("⚠️  WARNING: This will migrate all data from Firebase to Supabase.")
    print("   Make sure you have:")
    print("   1. Created the Supabase database schema")
    print("   2. Backed up your Firebase data")
    print("   3. Tested on a development database first")
    print()

    response = input("Do you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        return

    print()
    print("🔄 Starting migration...")
    print()

    # Migrate each collection
    migrate_collection('users', 'users', transform_users)
    migrate_collection('members', 'members', transform_members)
    migrate_collection('research', 'research', transform_research)
    migrate_collection('extensions', 'extensions', transform_extensions)
    migrate_collection('schedules', 'schedules', transform_schedules)
    migrate_collection('news', 'news', transform_news)
    migrate_collection('engagements', 'engagements', transform_engagements)
    migrate_collection('tap_projects', 'tap_projects', transform_tap_projects)

    print()
    print("=" * 60)
    print("✅ Migration completed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify data in Supabase dashboard")
    print("2. Test your application with Supabase")
    print("3. Update environment variables for production")
    print("4. Keep Firebase as backup until fully tested")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
