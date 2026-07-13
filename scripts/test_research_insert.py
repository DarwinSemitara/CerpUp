"""
Test research insert to find the exact error.
"""

from services.supabase_service import db
from datetime import datetime
import traceback


def test_research_insert():
    print("=" * 60)
    print("🧪 TESTING RESEARCH INSERT")
    print("=" * 60)

    # Test data
    uid = '4cc0ae10-2c6b-4880-bf29-997f236435ed'
    member_id = '015400ce-cc60-4fda-90c2-2f15e99e49de'

    print("\n1️⃣ Getting member info...")
    print("-" * 60)
    try:
        members = db.collection('members').where(
            'uid', '==', uid).limit(1).stream()
        member_list = [{'id': d.id, **d.to_dict()} for d in members]

        if not member_list:
            print("❌ Member not found!")
            return

        member = member_list[0]
        print(f"✅ Found member:")
        print(f"   ID: {member.get('id')}")
        print(f"   First: {member.get('first')}")
        print(f"   Last: {member.get('last')}")
        print(f"   UID: {member.get('uid')}")

        # Construct member name
        member_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
        )
        print(f"   Full Name: {member_name}")

    except Exception as e:
        print(f"❌ Error getting member: {e}")
        traceback.print_exc()
        return

    print("\n2️⃣ Creating research document reference...")
    print("-" * 60)
    try:
        doc_ref = db.collection('research').document()
        print(f"✅ Created document reference")
        print(f"   Table: research")
        print(f"   Doc ID: {doc_ref.doc_id}")
        print(f"   Has set method: {hasattr(doc_ref, 'set')}")
    except Exception as e:
        print(f"❌ Error creating doc ref: {e}")
        traceback.print_exc()
        return

    print("\n3️⃣ Preparing research data...")
    print("-" * 60)
    try:
        research_doc = {
            'uid': uid,
            'member_id': member['id'],
            'member_name': member_name,
            'research_type': 'Research',
            'title': 'Test Research Paper',
            'role': 'Principal Investigator',
            'co_workers': '',
            'co_authors': 'John Doe, Jane Smith',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'date_completion': '2026-12-31',
            'funding_agency': 'Test Agency',
            'credit_units': '3',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        print("✅ Research data prepared:")
        for key, value in research_doc.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Error preparing data: {e}")
        traceback.print_exc()
        return

    print("\n4️⃣ Inserting into database...")
    print("-" * 60)
    try:
        doc_ref.set(research_doc)
        print(f"✅ Research saved successfully!")
        print(f"   Document ID: {doc_ref.doc_id}")
    except Exception as e:
        print(f"❌ Error saving research: {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
        return

    print("\n5️⃣ Verifying saved data...")
    print("-" * 60)
    try:
        saved_doc = db.collection('research').document(doc_ref.doc_id).get()
        if saved_doc.exists:
            print("✅ Research verified in database!")
            data = saved_doc.to_dict()
            print(f"   ID: {data.get('id')}")
            print(f"   Title: {data.get('title')}")
            print(f"   Member: {data.get('member_name')}")
        else:
            print("❌ Research not found in database!")
    except Exception as e:
        print(f"❌ Error verifying: {e}")
        traceback.print_exc()
        return

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("""
Research insert is working correctly.
If the web app still fails, the issue might be:
1. Different data being sent from frontend
2. Session/authentication issue
3. Missing fields in request

Check the server console for the actual error!
    """)


if __name__ == '__main__':
    test_research_insert()
