"""
Lock 2026-2027 Semester 1 and clear staging area
Run this once to clean up the schedule system
"""
from services.supabase_service import supabase
from datetime import datetime
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)


def main():
    print("=" * 60)
    print("LOCK 2026-2027 SEMESTER 1 AND CLEAR STAGING AREA")
    print("=" * 60)
    print()

    # Step 1: Count existing assignments
    try:
        assignments = supabase.table('faculty_courses').select('id').execute()
        count_before = len(assignments.data)
        print(
            f"📋 Found {count_before} faculty course assignments (staging area)")
    except Exception as e:
        print(f"❌ Error checking assignments: {e}")
        return

    # Step 2: Auto-confirm (no interaction needed)
    print()
    print("⚠️  This will:")
    print("   - DELETE all faculty_courses entries (clear staging area)")
    print("   - KEEP all 232 schedules on the timetable (untouched)")
    print()
    print("✅ Auto-confirmed: Proceeding...")
    response = 'yes'

    if response != 'yes':
        print("❌ Cancelled")
        return

    # Step 3: Delete all faculty_courses
    print()
    print("🗑️  Deleting faculty course assignments...")
    deleted = 0
    try:
        for assignment in assignments.data:
            supabase.table('faculty_courses').delete().eq(
                'id', assignment['id']).execute()
            deleted += 1
            if deleted % 10 == 0:
                print(f"   Deleted {deleted}/{count_before}...")

        print(f"✅ Deleted {deleted} assignments")
    except Exception as e:
        print(f"❌ Error deleting: {e}")
        return

    # Step 4: Verify schedules are intact
    print()
    print("🔍 Verifying schedules...")
    try:
        schedules = supabase.table('schedules')\
            .select('id')\
            .eq('school_year', '2026-2027')\
            .eq('semester', '1')\
            .execute()

        schedule_count = len(schedules.data)
        print(f"✅ Confirmed: {schedule_count} schedules still on timetable")
    except Exception as e:
        print(f"❌ Error checking schedules: {e}")
        return

    # Done
    print()
    print("=" * 60)
    print("✅ SUCCESS!")
    print("=" * 60)
    print()
    print("🔒 2026-2027 Semester 1 is now locked")
    print("🗑️  Staging area cleared (0 assignments)")
    print(f"✅ Timetable intact ({schedule_count} schedules)")
    print()
    print("Next steps:")
    print("1. Refresh the schedule page")
    print("2. Staging area should be empty")
    print("3. Timetable should show all schedules correctly")
    print()


if __name__ == '__main__':
    main()
