"""
Run once to create the admin account in Firebase Auth + Firestore.
Usage: python scripts/create_admin.py
"""
from firebase_admin import credentials, auth, firestore
import firebase_admin
from dotenv import load_dotenv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()


if not firebase_admin._apps:
    cred = credentials.Certificate(
        os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json'))
    firebase_admin.initialize_app(cred)

db = firestore.client()

ADMIN_EMAIL = 'admin@cerp.dev'
ADMIN_PASSWORD = 'admin123'
ADMIN_USERNAME = 'admin'

try:
    user = auth.get_user_by_email(ADMIN_EMAIL)
    print(f'Admin already exists: {user.uid}')
except auth.UserNotFoundError:
    user = auth.create_user(
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
        display_name='Admin',
        email_verified=True
    )
    print(f'Created admin user: {user.uid}')

# Store admin profile in Firestore
db.collection('users').document(user.uid).set({
    'uid':      user.uid,
    'email':    ADMIN_EMAIL,
    'username': ADMIN_USERNAME,
    'role':     'admin',
    'display_name': 'Admin',
}, merge=True)

print('Admin account ready in Firebase.')
print(f'  Email:    {ADMIN_EMAIL}')
print(f'  Password: {ADMIN_PASSWORD}')
print(f'  UID:      {user.uid}')
