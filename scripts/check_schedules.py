"""
Quick script to check schedule data in Supabase
Usage: python check_schedules.py
"""

from services.supabase_service import db
import json

print("=" * 60)
print("🔍 Checking Schedule Data in Supabase")
print("=" * 60)
print()

try:
    docs = db.collection('schedules').stream()
    schedules = []

    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        schedules.append(data)

    if not schedules:
        print("⚠️  No schedules found in database")
    else:
        print(f"✅ Found {len(schedules)} schedule(s)\n")

        for i, sched in enumerate(schedules, 1):
            print(f"Schedule #{i}:")
            print(f"  ID: {sched.get('id')}")
            print(f"  Professor: {sched.get('prof')}")

            # Check both field name formats
            subj_code = sched.get('subj_code') or sched.get(
                'subjCode') or 'NOT FOUND'
            subj_name = sched.get('subj_name') or sched.get(
                'subjName') or 'NOT FOUND'

            print(f"  Subject Code: {subj_code}")
            print(f"  Subject Name: {subj_name}")
            print(f"  Day: {sched.get('day')}")
            print(f"  Time: {sched.get('start')} - {sched.get('end')}")
            print(f"  Room: {sched.get('room')}")
            print(f"  Section: {sched.get('section')}")

            # Show ALL fields to debug
            print(f"  All fields: {list(sched.keys())}")
            print()

    # Show raw JSON
    print("\n" + "=" * 60)
    print("Raw JSON (first schedule):")
    print("=" * 60)
    if schedules:
        print(json.dumps(schedules[0], indent=2, default=str))

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
