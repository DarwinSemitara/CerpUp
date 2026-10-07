"""
Verify Test Data for Black Box Testing (D06_BBT)
Checks if all required data exists for testers to successfully complete all test cases
"""
from dotenv import load_dotenv
from supabase import create_client
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def check_result(test_name, condition, details=""):
    """Print test result with status"""
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  {status} - {test_name}")
    if details:
        print(f"         {details}")
    return condition


def main():
    print("\n" + "="*80)
    print("BLACK BOX TESTING - DATA VERIFICATION")
    print("="*80 + "\n")

    all_passed = True

    # ========================================================================
    # TC-01: USER AUTHENTICATION
    # ========================================================================
    print("TC-01: User Authentication and Access Control")
    print("-" * 80)

    # Check for admin account
    admin_result = supabase.table('members').select(
        'id, email, role').eq('role', 'admin').execute()
    all_passed &= check_result(
        "Admin account exists",
        len(admin_result.data) > 0,
        f"Found {len(admin_result.data)} admin(s)" if admin_result.data else "No admin found"
    )

    # Check for faculty accounts
    faculty_result = supabase.table('members').select(
        'id, first, last, role').eq('role', 'member').execute()
    all_passed &= check_result(
        "Faculty accounts exist",
        len(faculty_result.data) > 0,
        f"Found {len(faculty_result.data)} faculty member(s)" if faculty_result.data else "No faculty found"
    )

    print()

    # ========================================================================
    # TC-02: AUTOMATED CLASS SCHEDULING (4-STEP WORKFLOW)
    # ========================================================================
    print("TC-02: Automated Class Scheduling Using Genetic Algorithm")
    print("-" * 80)

    # Step 1: Faculty Eligibility
    courses_result = supabase.table('courses').select(
        'id, course_code, course_title').execute()
    all_passed &= check_result(
        "Courses exist for eligibility configuration",
        len(courses_result.data) > 0,
        f"Found {len(courses_result.data)} courses"
    )

    eligibility_result = supabase.table(
        'faculty_eligible_courses').select('*').execute()
    check_result(
        "Faculty eligibilities configured",
        len(eligibility_result.data) > 0,
        f"Found {len(eligibility_result.data)} eligibility records"
    )

    # Step 2: Section Configuration
    sections_result = supabase.table(
        'course_sections_config').select('*').execute()
    check_result(
        "Course sections configured",
        len(sections_result.data) > 0,
        f"Found {len(sections_result.data)} sections"
    )

    rooms_result = supabase.table('rooms').select('*').execute()
    all_passed &= check_result(
        "Rooms available for allocation",
        len(rooms_result.data) > 0,
        f"Found {len(rooms_result.data)} rooms"
    )

    # Step 3: Faculty Assignments (optional - can be empty before generation)
    assignments_result = supabase.table(
        'faculty_course_assignments').select('*').execute()
    check_result(
        "Faculty assignments exist (optional)",
        True,  # Always pass, just informational
        f"Found {len(assignments_result.data)} assignments"
    )

    # Step 4: Check if GA can run (needs eligibilities + sections)
    can_generate = len(eligibility_result.data) > 0 and len(
        sections_result.data) > 0
    all_passed &= check_result(
        "Ready for GA schedule generation",
        can_generate,
        "Eligibilities and sections both configured" if can_generate else "Missing eligibilities or sections"
    )

    print()

    # ========================================================================
    # TC-03: FITNESS EVALUATION
    # ========================================================================
    print("TC-03: Schedule Generation Fitness Evaluation")
    print("-" * 80)

    # Check for overlapping eligibilities (multiple faculty for same course)
    if eligibility_result.data:
        course_faculty_count = {}
        for elig in eligibility_result.data:
            course_id = elig['course_id']
            course_faculty_count[course_id] = course_faculty_count.get(
                course_id, 0) + 1

        overlapping_courses = sum(
            1 for count in course_faculty_count.values() if count > 1)
        check_result(
            "Overlapping eligibilities exist (for GA optimization)",
            overlapping_courses > 0,
            f"{overlapping_courses} courses have multiple eligible faculty"
        )

    print()

    # ========================================================================
    # TC-04: COMPLETE 4-STEP WORKFLOW
    # ========================================================================
    print("TC-04: Complete 4-Step Scheduling Workflow")
    print("-" * 80)

    # Already verified above, just summary
    check_result(
        "Step 1 data ready (Faculty & Courses)",
        len(faculty_result.data) > 0 and len(courses_result.data) > 0,
        f"{len(faculty_result.data)} faculty, {len(courses_result.data)} courses"
    )

    check_result(
        "Step 2 data ready (Sections & Rooms)",
        len(sections_result.data) > 0 and len(rooms_result.data) > 0,
        f"{len(sections_result.data)} sections, {len(rooms_result.data)} rooms"
    )

    # Check for custom blocks
    custom_blocks_result = supabase.table(
        'custom_sections').select('*').execute()
    check_result(
        "Custom term blocks available",
        len(custom_blocks_result.data) > 0,
        f"Found {len(custom_blocks_result.data)} custom blocks"
    )

    print()

    # ========================================================================
    # TC-05: NLP CHATBOT
    # ========================================================================
    print("TC-05: NLP Chatbot for Schedule Generation Commands")
    print("-" * 80)

    # Check if NLP service exists
    nlp_service_path = Path(__file__).parent.parent / \
        'services' / 'nlp_service.py'
    check_result(
        "NLP service module exists",
        nlp_service_path.exists(),
        str(nlp_service_path)
    )

    # Check if chatbot route exists in app.py
    app_path = Path(__file__).parent.parent / 'app.py'
    if app_path.exists():
        with open(app_path, 'r', encoding='utf-8') as f:
            app_content = f.read()
            has_chat_route = '/api/chat/process' in app_content
            check_result(
                "Chatbot API route exists",
                has_chat_route,
                "/api/chat/process route found" if has_chat_route else "Route not found"
            )

    print()

    # ========================================================================
    # TC-06: FSR GENERATION
    # ========================================================================
    print("TC-06: Report and Document Generation (FSR)")
    print("-" * 80)

    # Check for FSR template
    fsr_template_path = Path(__file__).parent.parent / \
        'static' / 'reference' / 'FSRFORMAT.xlsx'
    all_passed &= check_result(
        "FSR template exists",
        fsr_template_path.exists(),
        str(fsr_template_path)
    )

    # Check for research records
    research_result = supabase.table('research').select('*').execute()
    check_result(
        "Research records exist",
        len(research_result.data) > 0,
        f"Found {len(research_result.data)} research records"
    )

    # Check for extension records
    extensions_result = supabase.table('extensions').select('*').execute()
    check_result(
        "Extension records exist",
        len(extensions_result.data) > 0,
        f"Found {len(extensions_result.data)} extension records"
    )

    print()

    # ========================================================================
    # TC-07: ADMINISTRATIVE DASHBOARD
    # ========================================================================
    print("TC-07: Centralized Administrative Dashboard")
    print("-" * 80)

    # Check for generated schedules
    generated_schedules_result = supabase.table(
        'generated_schedules').select('*').execute()
    check_result(
        "Generated schedules exist for viewing",
        len(generated_schedules_result.data) > 0,
        f"Found {len(generated_schedules_result.data)} generated schedule entries"
    )

    print()

    # ========================================================================
    # TC-08: CUSTOM TERM BLOCKS
    # ========================================================================
    print("TC-08: Custom Term Blocks Configuration")
    print("-" * 80)

    # Already checked above
    check_result(
        "Custom sections table exists and accessible",
        True,  # Table exists if we got here
        f"{len(custom_blocks_result.data)} custom blocks configured"
    )

    # Check for sections using custom blocks
    custom_sections_with_units = [
        cb for cb in custom_blocks_result.data if cb.get('units')]
    check_result(
        "Custom blocks with custom units exist",
        len(custom_sections_with_units) > 0,
        f"Found {len(custom_sections_with_units)} blocks with custom units"
    )

    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    if all_passed:
        print("✅ ALL CRITICAL TESTS PASSED - Ready for Black Box Testing!")
    else:
        print("⚠️  SOME CRITICAL TESTS FAILED - Please review and add missing data")
    print("=" * 80)

    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================
    print("\nRECOMMENDATIONS:")
    print("-" * 80)

    if len(admin_result.data) == 0:
        print("❌ CRITICAL: Create admin account using scripts/create_admin.py")

    if len(faculty_result.data) < 3:
        print("⚠️  Recommend: Add more faculty members (at least 3-5 for realistic demo)")

    if len(courses_result.data) < 5:
        print("⚠️  Recommend: Add more courses (at least 5-10 for realistic demo)")

    if len(eligibility_result.data) < 10:
        print("⚠️  Recommend: Configure more faculty eligibilities (at least 10-15)")

    if len(sections_result.data) < 5:
        print("⚠️  Recommend: Configure more sections (at least 5-10)")

    if len(rooms_result.data) < 3:
        print("⚠️  Recommend: Add more rooms (at least 3-5)")

    if len(generated_schedules_result.data) == 0:
        print("ℹ️  Info: No generated schedules yet - run GA generation once for TC-07 testing")

    if len(research_result.data) == 0:
        print("ℹ️  Info: Add research records for comprehensive FSR generation testing")

    if len(extensions_result.data) == 0:
        print("ℹ️  Info: Add extension records for comprehensive FSR generation testing")

    print()


if __name__ == '__main__':
    main()
