"""
Firebase Data Restore Script

This script restores Firebase Firestore data from a backup JSON folder.

Usage:
    python scripts/restore_firebase_backup.py <backup_folder>
    
Example:
    python scripts/restore_firebase_backup.py firebase_backup/20240112_143000

⚠️  WARNING: This will overwrite existing data in Firebase!
"""

from services.firebase_service import db
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


print("=" * 60)
print("🔄 Firebase Data Restore")
print("=" * 60)
print()


def restore_collection(collection_name, backup_file):
    """
    Restore a Firebase collection from a JSON backup file.

    Args:
        collection_name: Name of the collection to restore
        backup_file: Path to the backup JSON file
    """
    print(f"📦 Restoring '{collection_name}'...")

    try:
        # Read backup file
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data:
            print(f"   ⚠️  No data in backup file")
            return 0

        # Restore each document
        restored = 0
        for doc_data in data:
            # Get the original Firestore ID
            doc_id = doc_data.pop('_firestore_id', None)

            if not doc_id:
                print(f"   ⚠️  Document missing '_firestore_id', skipping")
                continue

            # Restore to Firestore
            db.collection(collection_name).document(doc_id).set(doc_data)
            restored += 1

        print(f"   ✅ Restored {restored} documents")
        return restored

    except FileNotFoundError:
        print(f"   ⚠️  Backup file not found: {backup_file}")
        return 0
    except Exception as e:
        print(f"   ❌ Error restoring '{collection_name}': {str(e)}")
        return 0


def main():
    """Run the restore process."""

    if len(sys.argv) < 2:
        print("❌ Error: Backup folder path required")
        print()
        print("Usage:")
        print("  python scripts/restore_firebase_backup.py <backup_folder>")
        print()
        print("Example:")
        print("  python scripts/restore_firebase_backup.py firebase_backup/20240112_143000")
        print()
        sys.exit(1)

    backup_dir = sys.argv[1]

    if not os.path.exists(backup_dir):
        print(f"❌ Error: Backup directory not found: {backup_dir}")
        sys.exit(1)

    print(f"📁 Backup directory: {backup_dir}")
    print()

    # Check for metadata file
    metadata_file = os.path.join(backup_dir, '_backup_metadata.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"📋 Backup Info:")
        print(f"   - Date: {metadata.get('backup_date', 'unknown')}")
        print(f"   - Project: {metadata.get('firebase_project', 'unknown')}")
        print(f"   - Total documents: {metadata.get('total_documents', 0)}")
        print()

    print("⚠️  WARNING: This will OVERWRITE existing data in Firebase!")
    print()
    response = input(
        "Are you sure you want to continue? (type 'yes' to confirm): ")

    if response.lower() != 'yes':
        print("❌ Restore cancelled")
        return

    print()
    print("🔄 Starting restore...")
    print()

    # List of collections to restore
    collections = [
        'users',
        'members',
        'research',
        'extensions',
        'schedules',
        'news',
        'engagements',
        'tap_projects'
    ]

    total_docs = 0

    # Restore each collection
    for collection in collections:
        backup_file = os.path.join(backup_dir, f"{collection}.json")
        if os.path.exists(backup_file):
            count = restore_collection(collection, backup_file)
            total_docs += count
        else:
            print(f"⚠️  No backup file for '{collection}', skipping")

    print()
    print("=" * 60)
    print(f"✅ Restore completed!")
    print("=" * 60)
    print()
    print(f"📊 Summary:")
    print(f"   - Total documents restored: {total_docs}")
    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Restore failed: {str(e)}")
        sys.exit(1)
