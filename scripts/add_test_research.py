"""
Add test research data to the database.
"""

from services.supabase_service import db
from datetime import datetime, timedelta


def add_test_research():
    print("=" * 60)
    print("➕ ADDING TEST RESEARCH DATA")
    print("=" * 60)

    print("\n1️⃣ Getting members...")
    print("-" * 60)
    try:
        members = db.collection('members').stream()
        member_list = [{'id': d.id, **d.to_dict()} for d in members]

        if not member_list:
            print("❌ No members found! Please create members first.")
            return

        print(f"✅ Found {len(member_list)} members")

        # Use first member
        member = member_list[0]
        print(f"\n👤 Using member: {member.get('first')} {member.get('last')}")
        print(f"   UID: {member.get('uid')}")
        print(f"   ID: {member.get('id')}")

    except Exception as e:
        print(f"❌ Error getting members: {e}")
        return

    print("\n2️⃣ Creating test research data...")
    print("-" * 60)

    # Test research data
    test_research = [
        {
            'title': 'Sustainable Agriculture Practices in Tropical Regions',
            'research_type': 'research',
            'role': 'Principal Investigator',
            'co_authors': 'Dr. Maria Santos, Dr. John Cruz',
            'co_workers': '',
            'start_date': '2025-01-15',
            'end_date': '2026-12-31',
            'date_completion': None,
            'funding_agency': 'National Science Foundation',
            'credit_units': '3',
        },
        {
            'title': 'Climate Change Impact on Rice Production',
            'research_type': 'publication',
            'role': 'Co-Author',
            'co_authors': 'Dr. Anna Lee, Prof. Robert Tan',
            'co_workers': '',
            'start_date': '2024-06-01',
            'end_date': '2025-05-31',
            'date_completion': '2025-05-31',
            'funding_agency': 'Department of Agriculture',
            'credit_units': '2',
        },
        {
            'title': 'Biodiversity Conservation in Protected Areas',
            'research_type': 'project',
            'role': 'Research Associate',
            'co_authors': '',
            'co_workers': 'Environmental Team, Field Researchers',
            'start_date': '2025-03-01',
            'end_date': None,
            'date_completion': None,
            'funding_agency': 'Wildlife Conservation Society',
            'credit_units': '1.5',
        },
        {
            'title': 'Integrated Pest Management Systems',
            'research_type': 'research',
            'role': 'Lead Researcher',
            'co_authors': 'Dr. Pedro Reyes',
            'co_workers': 'Lab Assistants',
            'start_date': '2024-09-01',
            'end_date': '2026-08-31',
            'date_completion': None,
            'funding_agency': 'Agricultural Research Institute',
            'credit_units': '3',
        },
        {
            'title': 'Water Quality Assessment in Coastal Ecosystems',
            'research_type': 'publication',
            'role': 'Principal Investigator',
            'co_authors': 'Dr. Lisa Garcia, Dr. Mark Wilson',
            'co_workers': '',
            'start_date': '2023-11-01',
            'end_date': '2024-10-31',
            'date_completion': '2024-10-31',
            'funding_agency': 'Marine Research Foundation',
            'credit_units': '2.5',
        }
    ]

    member_name = f"{member.get('first', '')} {member.get('last', '')}".strip()

    added_count = 0
    for i, research_data in enumerate(test_research, 1):
        try:
            print(f"\n   {i}. Adding: {research_data['title'][:50]}...")

            # Add member info
            research_doc = {
                **research_data,
                'uid': member.get('uid'),
                'member_id': member.get('id'),
                'member_name': member_name,
                'created_at': (datetime.utcnow() - timedelta(days=len(test_research) - i)).isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Save to database
            doc_ref = db.collection('research').document()
            doc_ref.set(research_doc)

            print(f"      ✅ Added with ID: {doc_ref.doc_id}")
            added_count += 1

        except Exception as e:
            print(f"      ❌ Error: {e}")

    print("\n" + "=" * 60)
    print(
        f"✅ Successfully added {added_count} of {len(test_research)} research items")
    print("=" * 60)
    print("\n💡 You can now view them in the admin panel!")


if __name__ == '__main__':
    add_test_research()
