"""Check for duplicate schedule entries in Supabase."""
from services.supabase_service import supabase

# Query all HUME 100 schedules for Devanadera
result = supabase.table('schedules').select('*').eq('subjCode', 'HUME 100').execute()

print(f"\n{'='*80}")
print(f"HUME 100 Schedules for Devanadera:")
print(f"{'='*80}\n")

if result.data:
    for idx, sched in enumerate(result.data, 1):
        print(f"Entry #{idx}:")
        print(f"  ID: {sched.get('id')}")
        print(f"  Prof: {sched.get('prof')}")
        print(f"  Day: {sched.get('day')}")
        print(f"  Time: {sched.get('start')} - {sched.get('end')}")
        print(f"  Year: {sched.get('schoolYear', sched.get('school_year'))}")
        print(f"  Semester: {sched.get('semester')}")
        print(f"  Room: {sched.get('room')}")
        print()
    print(f"Total: {len(result.data)} entries")
    
    # Check for duplicates (same subject, prof, year, semester but different IDs)
    if len(result.data) > 1:
        print(f"\n⚠️  WARNING: Found {len(result.data)} HUME 100 entries!")
        print("This is causing the conflict detection to trigger.")
        print("\nRECOMMENDATION: Delete old/duplicate entries, keep only the latest one.")
else:
    print("No HUME 100 schedules found.")

print(f"\n{'='*80}")
print("Checking ALL schedules for duplicates...")
print(f"{'='*80}\n")

# Check all schedules for duplicates
all_schedules = supabase.table('schedules').select('*').execute()

if all_schedules.data:
    # Group by subject code + prof + year + semester
    from collections import defaultdict
    groups = defaultdict(list)
    
    for sched in all_schedules.data:
        key = (
            sched.get('subjCode'),
            sched.get('prof'),
            sched.get('schoolYear', sched.get('school_year')),
            sched.get('semester')
        )
        groups[key].append(sched)
    
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate groups:\n")
        for key, schedules in duplicates.items():
            subj, prof, year, sem = key
            print(f"📚 {subj} - {prof} - {year} Sem {sem}:")
            print(f"   {len(schedules)} duplicate entries found!")
            for s in schedules:
                print(f"     - ID: {s.get('id')} | Day: {s.get('day')} | Time: {s.get('start')}-{s.get('end')}")
            print()
    else:
        print("✅ No duplicates found!")
else:
    print("No schedules found in database.")
