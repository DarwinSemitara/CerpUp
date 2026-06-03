import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin SDK once
if not firebase_admin._apps:
    # Try to load from environment variable first (for Render deployment)
    firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')

    if firebase_creds_json:
        # Parse JSON string from environment variable
        try:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            print("✅ Firebase initialized from environment variable")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse FIREBASE_CREDENTIALS_JSON: {e}")
            raise
    else:
        # Fallback to file path (for local development)
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH',
                              'firebase-credentials.json')

        # Check if file exists before trying to load it
        if not os.path.exists(cred_path):
            raise FileNotFoundError(
                f"❌ Firebase credentials not found!\n"
                f"For production: Set FIREBASE_CREDENTIALS_JSON environment variable\n"
                f"For local dev: Place {cred_path} in project root"
            )

        cred = credentials.Certificate(cred_path)
        print(f"✅ Firebase initialized from file: {cred_path}")

    firebase_admin.initialize_app(cred)

db = firestore.client()


def verify_id_token(id_token):
    """Verify a Firebase ID token and return the decoded token."""
    try:
        # Check if token is valid format
        if not id_token or not isinstance(id_token, str):
            return None, 'Invalid token format.'

        decoded = auth.verify_id_token(
            id_token, check_revoked=False, clock_skew_seconds=10)
        return decoded, None
    except auth.ExpiredIdTokenError:
        return None, 'Token expired. Please sign in again.'
    except auth.InvalidIdTokenError as e:
        error_msg = str(e)
        print(f"Invalid token error: {error_msg}")  # Debug log
        if 'project' in error_msg.lower() or 'audience' in error_msg.lower():
            return None, 'Firebase configuration mismatch. Please contact admin.'
        return None, 'Invalid token. Please sign in again.'
    except auth.RevokedIdTokenError:
        return None, 'Token has been revoked. Please sign in again.'
    except Exception as e:
        error_msg = str(e)
        print(f"Token verification exception: {error_msg}")  # Debug log
        return None, f'Authentication error. Please try again or contact admin.'


def get_user(uid):
    """Get a Firebase Auth user by UID."""
    try:
        return auth.get_user(uid), None
    except Exception as e:
        return None, str(e)
