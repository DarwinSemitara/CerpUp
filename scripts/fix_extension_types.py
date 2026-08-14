"""
Script to fix extension type fields in the database.
Copies extension_type to type field for all extensions that have extension_type but missing/empty type.
"""
from services.firebase_service import db
from dotenv import load_dotenv

load_dotenv()


def fix_extension_types():
    """Copy extension_type to type field for all extensions missing the type field."""
    try:
        print("Starting extension type fix...")

        extensions = db.collection('extensions').stream()

        fixed_count = 0
        already_ok_count = 0

        for doc in extensions:
            doc_data = doc.to_dict()
            doc_id = doc.id

            # Get current values
            current_type = (doc_data.get('type') or '').strip()
            extension_type = (doc_data.get('extension_type') or '').strip()

            # If type is empty but extension_type has a value, copy it
            if not current_type and extension_type:
                print(
                    f"Fixing extension {doc_id}: copying '{extension_type}' to type field")
                db.collection('extensions').document(doc_id).update({
                    'type': extension_type
                })
                fixed_count += 1
            elif current_type:
                already_ok_count += 1
                print(
                    f"Extension {doc_id}: type already set to '{current_type}'")
            else:
                print(
                    f"Warning: Extension {doc_id} has no type or extension_type value")

        print(f"\n✓ Fix complete!")
        print(f"  - Fixed: {fixed_count} extensions")
        print(f"  - Already OK: {already_ok_count} extensions")

    except Exception as e:
        print(f"Error fixing extension types: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    fix_extension_types()
