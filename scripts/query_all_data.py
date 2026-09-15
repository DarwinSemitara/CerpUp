"""
Query all faculty, courses, and sections from the database
"""
import os
import sys
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

def main():
    print("\n" + "="*80)
    print("FACULTY MEMBERS")
    print("="*80)
    
    # Get all faculty
    faculty_result = supabase.table('member_profiles')\
        .select('id, display_name, email')\
        .eq('role', 'faculty')\
        .order('display_name')\
        .execute()
    
    if faculty_result.data:
        for i, faculty in enumerate(faculty_result.data, 1):
            print(f"{i}. {faculty['display_name']}")
            print(f"   Email: {faculty['email']}")
            print(f"   ID: {faculty['id']}")
            print()
    else:
        print("No faculty members found.")
    
    print(f"Total Faculty: {len(faculty_result.data)}")
    
    print("\n" + "="*80)
    print("COURSES & AVAILABLE SECTIONS")
    print("="*80)
    
    # Get all courses
    courses_result = supabase.table('courses')\
        .select('id, course_code, course_title, available_sections')\
        .order('course_code')\
        .execute()
    
    if courses_result.data:
        for i, course in enumerate(courses_result.data, 1):
            sections = ', '.join(course['available_sections']) if course['available_sections'] else 'None'
            print(f"{i}. {course['course_code']} - {course['course_title']}")
            print(f"   Sections: {sections}")
            print(f"   ID: {course['id']}")
            print()
    else:
        print("No courses found.")
    
    print(f"Total Courses: {len(courses_result.data)}")
    
    # Get section statistics
    print("\n" + "="*80)
    print("SECTION STATISTICS")
    print("="*80)
    
    total_sections = 0
    for course in courses_result.data:
        if course['available_sections']:
            total_sections += len(course['available_sections'])
    
    print(f"Total Sections across all courses: {total_sections}")
    
    # Get faculty course assignments
    print("\n" + "="*80)
    print("FACULTY COURSE ASSIGNMENTS")
    print("="*80)
    
    assignments_result = supabase.table('faculty_courses')\
        .select('faculty_id, course_id, section')\
        .execute()
    
    # Group by faculty
    faculty_assignments = {}
    for assignment in assignments_result.data:
        faculty_id = assignment['faculty_id']
        if faculty_id not in faculty_assignments:
            faculty_assignments[faculty_id] = []
        faculty_assignments[faculty_id].append(assignment)
    
    # Create lookup maps
    faculty_map = {f['id']: f['display_name'] for f in faculty_result.data}
    course_map = {c['id']: c['course_code'] for c in courses_result.data}
    
    if faculty_assignments:
        for faculty_id, assignments in faculty_assignments.items():
            faculty_name = faculty_map.get(faculty_id, 'Unknown')
            print(f"\n{faculty_name}:")
            total_units = len(assignments) * 3
            print(f"  Total Units: {total_units}")
            print(f"  Courses:")
            for assignment in assignments:
                course_code = course_map.get(assignment['course_id'], 'Unknown')
                print(f"    - {course_code} Section {assignment['section']} (3 units)")
    else:
        print("No course assignments found.")
    
    print("\n" + "="*80)
    print(f"Total Assignments: {len(assignments_result.data)}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
