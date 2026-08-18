from services.supabase_service import supabase

# Check all footnotes in database
result = supabase.table('fsr_footnotes').select('*').execute()

print(f"\n📋 Total footnotes in database: {len(result.data)}")
for fn in result.data:
    print(f"\n  Footnote #{fn.get('footnote_number')}:")
    print(f"    Member ID: {fn.get('member_id')}")
    print(f"    Semester: {fn.get('semester')}")
    print(f"    Academic Year: {fn.get('academic_year')}")
    print(f"    Type: {fn.get('footnote_type')}")
    print(f"    Faculty: {fn.get('faculty_name')}")
    print(f"    Subject: {fn.get('subject')}")
