"""
Simple Firebase Backup Script - Run from project root
Usage: python backup_data.py
"""

from services.firebase_service import db
import json
import os
from datetime import datetime

print("=" * 60)
print("🔄 Firebase Data Backup")
print("=" * 60)
print()

# Create backup directory
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_dir = os.path.join('firebase_backup', timestamp)
os.makedirs(backup_dir, exist_ok=True)

print(f"📁 Backup directory: {backup_dir}")
print()

# Collections to backup
collections = ['users', 'members', 'research', 'extensions',
               'schedules', 'news', 'engagements', 'tap_projects']

total_docs = 0

for collection_name in collections:
    print(f"📦 Backing up '{collection_name}'...")

    try:
        docs = db.collection(collection_name).stream()
        data = []

        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['_firestore_id'] = doc.id
            data.append(doc_data)

        if not data:
            print(f"   ⚠️  Empty")
            continue

        output_file = os.path.join(backup_dir, f"{collection_name}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"   ✅ Backed up {len(data)} documents")
        total_docs += len(data)

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print()
print("=" * 60)
print(f"✅ Backup completed! Total: {total_docs} documents")
print(f"📁 Location: {backup_dir}")
print("=" * 60)
