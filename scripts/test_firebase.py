"""
Test Firebase configuration and credentials
"""
from dotenv import load_dotenv
from services.firebase_service import db, auth
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()


def test_firebase():
    print("Testing Firebase configuration...")
    print("-" * 50)

    # Test 1: Check if Firebase is initialized
    try:
        import firebase_admin
        if firebase_admin._apps:
            print("✓ Firebase Admin SDK initialized")
        else:
            print("✗ Firebase Admin SDK not initialized")
            return
    except Exception as e:
        print(f"✗ Error checking Firebase: {e}")
        return

    # Test 2: Check Firestore connection
    try:
        # Try to read from a collection
        test_ref = db.collection('_test_connection').document('test')
        test_ref.set({'test': True})
        test_ref.delete()
        print("✓ Firestore connection working")
    except Exception as e:
        print(f"✗ Firestore connection failed: {e}")

    # Test 3: Check Auth
    try:
        # Try to list users (just to test connection)
        users = auth.list_users(max_results=1)
        print(
            f"✓ Firebase Auth working (found {len(list(users.users))} user(s))")
    except Exception as e:
        print(f"✗ Firebase Auth failed: {e}")

    # Test 4: Check environment variables
    print("\nEnvironment Variables:")
    print(
        f"  FIREBASE_API_KEY: {'Set' if os.getenv('FIREBASE_API_KEY') else 'Not set'}")
    print(
        f"  FIREBASE_AUTH_DOMAIN: {'Set' if os.getenv('FIREBASE_AUTH_DOMAIN') else 'Not set'}")
    print(
        f"  FIREBASE_PROJECT_ID: {'Set' if os.getenv('FIREBASE_PROJECT_ID') else 'Not set'}")
    print(
        f"  FIREBASE_CREDENTIALS_PATH: {os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')}")

    # Test 5: Check if credentials file exists
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH',
                          'firebase-credentials.json')
    if os.path.exists(cred_path):
        print(f"✓ Credentials file exists: {cred_path}")
    else:
        print(f"✗ Credentials file not found: {cred_path}")

    print("-" * 50)
    print("\nIf you see errors above, check:")
    print("1. firebase-credentials.json is in the project root")
    print("2. .env file has correct Firebase configuration")
    print("3. Firebase project settings match your credentials")


if __name__ == '__main__':
    test_firebase()
