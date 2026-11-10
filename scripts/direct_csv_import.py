"""
Direct CSV import - reads CSV and inserts all schedules at once
"""
from dotenv import load_dotenv
from supabase import create_client
import os
import sys
import csv
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Parse the CSV and prepare all schedules
csv_path = 'static/reference/class_schedules.csv'
school_year = '2026-2027'
semester = '1'

schedules = []

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for row in reader:
        faculty = row['Faculty'].strip()
        day = row['Day'].strip()
        start_time = row['Start'].strip()
        end_time = row['End'].strip()
        course = row['Course'].strip()
        section = row['Section'].strip()
        room = row['Room'].strip()

        schedules.append({
            'prof': faculty,
            'subj_code': course,
            'subj_name': '',
            'day': day,
            'start': start_time,
            'end': end_time,
            'room': room,
            'section': section,
            'units': '3',
            'semester': semester,
            'school_year': school_year
        })

print(f"Parsed {len(schedules)} schedules from CSV")
print(f"Inserting into database...")

# Insert in batches of 500 (Supabase limit)
batch_size = 500
total_inserted = 0

for i in range(0, len(schedules), batch_size):
    batch = schedules[i:i + batch_size]
    try:
        result = supabase.table('schedules').insert(batch).execute()
        total_inserted += len(batch)
        print(f"✅ Inserted batch {i//batch_size + 1}: {len(batch)} schedules")
    except Exception as e:
        print(f"❌ Error inserting batch {i//batch_size + 1}: {e}")

print(f"\n✅ Successfully inserted {total_inserted} total schedules!")
