#!/usr/bin/env python3
"""
Verify Schedules Table Structure and Data
Checks Supabase schedules table for compatibility issues
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from services.supabase_service import supabase

def check_table_structure():
    """Check if the schedules table exists and has correct structure"""
    print("=" * 70)
    print("🔍 SUPABASE SCHEDULES TABLE VERIFICATION")
    print("=" * 70)
    print()
    
    try:
        # Try to fetch one schedule to verify table exists
        result = supabase.table('schedules').select('*').limit(1).execute()
        
        if result.data:
            print("✅ Table 'schedules' exists and is accessible")
            print()
            print("📋 Sample Record Structure:")
            print("-" * 70)
            sample = result.data[0]
            for key, value in sample.items():
                value_type = type(value).__name__
                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"  {key:20s} = {value_str:30s} ({value_type})")
            print()
            
            # Check for required fields
            required_fields = [
                'id', 'prof', 'subj_code', 'subj_name', 'type',
                'day', 'start', 'end', 'room', 'units', 'section',
                'year', 'semester', 'school_year', 'created_at'
            ]
            
            print("📊 Required Fields Check:")
            print("-" * 70)
            missing_fields = []
            for field in required_fields:
                if field in sample:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} - MISSING!")
                    missing_fields.append(field)
            
            if missing_fields:
                print()
                print(f"⚠️  WARNING: Missing {len(missing_fields)} required fields")
                print("   These fields may need to be added to the table schema")
            else:
                print()
                print("✅ All required fields present")
                
        else:
            print("✅ Table 'schedules' exists but is currently empty")
            print("   This is normal if no schedules have been created yet")
            
    except Exception as e:
        print(f"❌ Error accessing schedules table: {e}")
        print()
        print("Possible issues:")
        print("  1. Table doesn't exist - run schema creation SQL")
        print("  2. Permission denied - check RLS policies")
        print("  3. Connection failed - verify SUPABASE_URL and keys in .env")
        return False
    
    print()
    return True

def check_data_counts():
    """Check how many schedules exist and their distribution"""
    print("=" * 70)
    print("📊 DATA STATISTICS")
    print("=" * 70)
    print()
    
    try:
        # Get all schedules
        result = supabase.table('schedules').select('*').execute()
        schedules = result.data
        
        print(f"Total schedules: {len(schedules)}")
        print()
        
        if not schedules:
            print("ℹ️  No schedules in database yet")
            return True
        
        # Group by school year
        by_year = {}
        for s in schedules:
            year = s.get('school_year', 'Unknown')
            by_year[year] = by_year.get(year, 0) + 1
        
        print("By School Year:")
        for year, count in sorted(by_year.items()):
            print(f"  {year}: {count} schedules")
        print()
        
        # Group by semester
        by_semester = {}
        for s in schedules:
            sem = s.get('semester', 'Unknown')
            by_semester[sem] = by_semester.get(sem, 0) + 1
        
        print("By Semester:")
        for sem, count in sorted(by_semester.items()):
            print(f"  Semester {sem}: {count} schedules")
        print()
        
        # Group by professor
        by_prof = {}
        for s in schedules:
            prof = s.get('prof', 'Unknown')
            by_prof[prof] = by_prof.get(prof, 0) + 1
        
        print("By Professor (top 10):")
        for prof, count in sorted(by_prof.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {prof}: {count} schedules")
        print()
        
        # Check for null/empty required fields
        issues = []
        for s in schedules:
            if not s.get('id'):
                issues.append(f"Schedule missing ID")
            if not s.get('prof'):
                issues.append(f"Schedule {s.get('id', 'unknown')} missing professor")
            if not s.get('subj_code'):
                issues.append(f"Schedule {s.get('id', 'unknown')} missing subject code")
            if not s.get('day'):
                issues.append(f"Schedule {s.get('id', 'unknown')} missing day")
            if not s.get('start') or not s.get('end'):
                issues.append(f"Schedule {s.get('id', 'unknown')} missing time slots")
        
        if issues:
            print("⚠️  Data Quality Issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"  • {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
        else:
            print("✅ No data quality issues found")
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False
    
    print()
    return True

def check_duplicate_ids():
    """Check for duplicate IDs (should never happen with UUIDs)"""
    print("=" * 70)
    print("🔍 DUPLICATE ID CHECK")
    print("=" * 70)
    print()
    
    try:
        result = supabase.table('schedules').select('id').execute()
        ids = [s['id'] for s in result.data if s.get('id')]
        
        unique_ids = set(ids)
        
        if len(ids) == len(unique_ids):
            print(f"✅ No duplicate IDs found ({len(ids)} unique IDs)")
        else:
            duplicates = len(ids) - len(unique_ids)
            print(f"❌ Found {duplicates} duplicate IDs!")
            print("   This should never happen with UUID generation")
            
            # Find which IDs are duplicated
            from collections import Counter
            id_counts = Counter(ids)
            for id_val, count in id_counts.items():
                if count > 1:
                    print(f"   • ID {id_val} appears {count} times")
    
    except Exception as e:
        print(f"❌ Error checking duplicates: {e}")
        return False
    
    print()
    return True

def main():
    success = True
    
    # Check table structure
    if not check_table_structure():
        success = False
    
    # Check data statistics
    if not check_data_counts():
        success = False
    
    # Check for duplicates
    if not check_duplicate_ids():
        success = False
    
    print("=" * 70)
    if success:
        print("✅ VERIFICATION COMPLETE - No critical issues found")
    else:
        print("⚠️  VERIFICATION COMPLETE - Issues detected (see above)")
    print("=" * 70)
    print()
    
    if success:
        print("Next steps:")
        print("1. Restart Flask server: python app.py")
        print("2. Test schedule drag-drop in the UI")
        print("3. Verify schedules persist after refresh")
        print("4. Check CHE chat works without errors")
    else:
        print("Required actions:")
        print("1. Fix table structure issues in Supabase")
        print("2. Check RLS policies if permission denied")
        print("3. Verify .env has correct SUPABASE_URL and keys")
    print()
    
    return success

if __name__ == '__main__':
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
