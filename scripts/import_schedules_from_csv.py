"""
Import schedules from CSV file to Supabase database
"""
import os
import sys
import csv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def parse_entry_field(entry_text):
    """
    Parse the 'Entry' field which contains course info like:
    'CERP 221 SAMAR | PLGU Catarman / CERP 221 DAVAO | PSAE Davao'
    
    Returns list of (course_code, section, room) tuples
    """
    if not entry_text or entry_text.strip() == '':
        return []
    
    # Split by '/' to handle multiple entries
    entries = entry_text.split('/')
    parsed = []
    
    for entry in entries:
        entry = entry.strip()
        if not entry or entry == '|':
            continue
            
        # Split by '|' to separate course info and room
        parts = [p.strip() for p in entry.split('|')]
        
        if len(parts) >= 1:
            # Extract course code and section from first part
            course_info = parts[0].strip()
            room = parts[1] if len(parts) >= 2 else 'TBA'
            
            # Parse course code and section
            # Examples: "CERP 221 SAMAR", "HUME 114 Y2", "NSTP 2 HEL 1 (LTS 2)"
            tokens = course_info.split()
            
            if len(tokens) >= 2:
                # Course code is first two tokens (e.g., "CERP 221", "HUME 114")
                course_code = f"{tokens[0]} {tokens[1]}"
                # Section is the rest (e.g., "SAMAR", "Y2", "HEL 1 (LTS 2)")
                section = ' '.join(tokens[2:]) if len(tokens) > 2 else ''
                
                parsed.append((course_code, section, room))
    
    return parsed

def import_csv_schedules(csv_path, school_year='2026-2027', semester='1'):
    """
    Import schedules from CSV file to Supabase
    
    Args:
        csv_path: Path to CSV file
        school_year: School year (e.g., '2026-2027')
        semester: Semester ('1' or '2')
    """
    print(f"\n{'='*80}")
    print(f"IMPORTING SCHEDULES FROM CSV")
    print(f"{'='*80}")
    print(f"CSV File: {csv_path}")
    print(f"School Year: {school_year}")
    print(f"Semester: {semester}")
    print(f"{'='*80}\n")
    
    # Read CSV file
    schedules_to_insert = []
    skipped_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            faculty = row['Faculty'].strip()
            day = row['Day'].strip()
            start_time = row['Start'].strip()
            end_time = row['End'].strip()
            entry_type = row['Type'].strip()
            entry_text = row['Entry'].strip()
            
            # Skip consultation hours - only import classes
            if entry_type.lower() == 'consultation':
                skipped_count += 1
                continue
            
            # Parse the entry field to extract course info
            parsed_entries = parse_entry_field(entry_text)
            
            if not parsed_entries:
                print(f"⚠️  Row {row_num}: Could not parse entry '{entry_text}'")
                skipped_count += 1
                continue
            
            # Create a schedule entry for each parsed course
            for course_code, section, room in parsed_entries:
                schedule = {
                    'prof': faculty,
                    'subj_code': course_code,
                    'subj_name': '',  # Not in CSV, will be empty
                    'day': day,
                    'start': start_time,
                    'end': end_time,
                    'room': room,
                    'section': section,
                    'units': '3',  # Default to 3 units
                    'semester': semester,
                    'school_year': school_year
                }
                schedules_to_insert.append(schedule)
    
    print(f"📊 Parsed {len(schedules_to_insert)} schedule entries from CSV")
    print(f"⏭️  Skipped {skipped_count} consultation/unparseable entries\n")
    
    if not schedules_to_insert:
        print("❌ No schedules to insert!")
        return
    
    # Insert into database in batches
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(schedules_to_insert), batch_size):
        batch = schedules_to_insert[i:i + batch_size]
        
        try:
            result = supabase.table('schedules').insert(batch).execute()
            total_inserted += len(batch)
            print(f"✅ Inserted batch {i//batch_size + 1}: {len(batch)} schedules")
        except Exception as e:
            print(f"❌ Error inserting batch {i//batch_size + 1}: {e}")
    
    print(f"\n{'='*80}")
    print(f"✅ IMPORT COMPLETE: {total_inserted} schedules inserted")
    print(f"{'='*80}\n")

def main():
    # Get parameters from command line or use defaults
    csv_path = 'static/reference/class_schedule.csv'
    school_year = input("Enter school year (default: 2026-2027): ").strip() or '2026-2027'
    semester = input("Enter semester (1 or 2, default: 1): ").strip() or '1'
    
    # Confirm before proceeding
    print(f"\n⚠️  This will import schedules from {csv_path}")
    print(f"   School Year: {school_year}, Semester: {semester}")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Import cancelled")
        return
    
    import_csv_schedules(csv_path, school_year, semester)

if __name__ == '__main__':
    main()
