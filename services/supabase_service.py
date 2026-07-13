"""
Supabase Service
Replacement for Firebase service using Supabase Python client.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import jwt
from datetime import datetime, timedelta

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError(
        "❌ Supabase credentials not found!\n"
        "Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env file"
    )

# Create Supabase client with service role key (for backend operations)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print(f"✅ Supabase initialized: {SUPABASE_URL}")


def verify_access_token(access_token):
    """
    Verify a Supabase JWT access token and return the user info.

    Returns:
        tuple: (user_data, error_message)
        - user_data: dict with 'uid', 'email', etc. if valid
        - error_message: string if error, None if success
    """
    try:
        if not access_token or not isinstance(access_token, str):
            return None, 'Invalid token format.'

        # Get user from Supabase Auth
        response = supabase.auth.get_user(access_token)

        if response and response.user:
            user = response.user
            return {
                'uid': user.id,
                'email': user.email,
                'email_verified': user.email_confirmed_at is not None,
            }, None
        else:
            return None, 'Invalid token.'

    except Exception as e:
        error_msg = str(e)
        print(f"Token verification exception: {error_msg}")

        if 'expired' in error_msg.lower():
            return None, 'Token expired. Please sign in again.'
        elif 'invalid' in error_msg.lower():
            return None, 'Invalid token. Please sign in again.'
        else:
            return None, 'Authentication error. Please try again.'


def get_user_by_id(uid):
    """
    Get a user from Supabase Auth by UID.

    Returns:
        tuple: (user_data, error_message)
    """
    try:
        # Query users table
        response = supabase.table('users').select(
            '*').eq('uid', uid).single().execute()

        if response.data:
            return response.data, None
        else:
            return None, 'User not found.'

    except Exception as e:
        return None, str(e)


def create_user(email, password, display_name=None):
    """
    Create a new user in Supabase Auth.

    Returns:
        tuple: (user, error)
    """
    try:
        response = supabase.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': {
                    'display_name': display_name
                }
            }
        })

        if response.user:
            return response.user, None
        else:
            return None, 'Failed to create user.'

    except Exception as e:
        return None, str(e)


def update_user_password(uid, new_password):
    """
    Update user password (admin function).

    Returns:
        tuple: (success, error)
    """
    try:
        # Use admin API to update password
        response = supabase.auth.admin.update_user_by_id(
            uid,
            {'password': new_password}
        )

        if response:
            return True, None
        else:
            return False, 'Failed to update password.'

    except Exception as e:
        return False, str(e)


# Database query helpers using Supabase client

class SupabaseDB:
    """Wrapper class for Supabase database operations."""

    def __init__(self, client: Client):
        self.client = client

    def collection(self, table_name):
        """Return a table reference (similar to Firestore's collection method)."""
        return SupabaseTable(self.client, table_name)


class SupabaseTable:
    """Represents a Supabase table with query methods similar to Firestore."""

    def __init__(self, client: Client, table_name: str):
        self.client = client
        self.table_name = table_name
        self._query = None
        self._filters = []
        self._order = None
        self._limit_val = None

    def where(self, field, op, value):
        """Add a filter condition."""
        self._filters.append((field, op, value))
        return self

    def order_by(self, field, direction='asc'):
        """Add ordering."""
        desc = direction.lower() in ['desc', 'descending']
        self._order = (field, desc)
        return self

    def limit(self, count):
        """Limit results."""
        self._limit_val = count
        return self

    def stream(self):
        """Execute query and return results as generator (similar to Firestore)."""
        results = self._execute()
        for item in results:
            yield SupabaseDocument(item)

    def get(self):
        """Execute query and return all results."""
        results = self._execute()
        return [SupabaseDocument(item) for item in results]

    def _execute(self):
        """Execute the query with all filters."""
        query = self.client.table(self.table_name).select('*')

        # Apply filters
        for field, op, value in self._filters:
            if op == '==':
                query = query.eq(field, value)
            elif op == '!=':
                query = query.neq(field, value)
            elif op == '>':
                query = query.gt(field, value)
            elif op == '>=':
                query = query.gte(field, value)
            elif op == '<':
                query = query.lt(field, value)
            elif op == '<=':
                query = query.lte(field, value)

        # Apply ordering
        if self._order:
            field, desc = self._order
            query = query.order(field, desc=desc)

        # Apply limit
        if self._limit_val:
            query = query.limit(self._limit_val)

        response = query.execute()
        return response.data if response.data else []

    def document(self, doc_id=None):
        """Return a document reference."""
        if doc_id is None:
            # Generate a new UUID for new documents
            import uuid
            doc_id = str(uuid.uuid4())
        return SupabaseDocumentRef(self.client, self.table_name, doc_id)


class SupabaseDocument:
    """Represents a document returned from a query."""

    def __init__(self, data, exists=None):
        self.data = data
        self.id = data.get('id') if data else None
        self._exists = exists if exists is not None else (data is not None)

    def to_dict(self):
        """Return document data as dictionary."""
        return self.data

    @property
    def exists(self):
        """Check if document exists."""
        return self._exists


class SupabaseDocumentRef:
    """Represents a reference to a specific document."""

    def __init__(self, client: Client, table_name: str, doc_id: str):
        self.client = client
        self.table_name = table_name
        self.doc_id = doc_id
        self.id = doc_id  # Alias for compatibility

    def get(self):
        """Get the document."""
        try:
            response = self.client.table(self.table_name).select(
                '*').eq('id', self.doc_id).single().execute()
            if response.data:
                return SupabaseDocument(response.data, exists=True)
            else:
                return SupabaseDocument(None, exists=False)
        except Exception as e:
            print(f"Error getting document: {e}")
            return SupabaseDocument(None, exists=False)

    def set(self, data, merge=False):
        """Set document data (insert or upsert)."""
        data['id'] = self.doc_id
        if merge:
            response = self.client.table(
                self.table_name).upsert(data).execute()
        else:
            response = self.client.table(
                self.table_name).insert(data).execute()
        return response

    def update(self, data):
        """Update document data."""
        data['updated_at'] = datetime.utcnow().isoformat()
        response = self.client.table(self.table_name).update(
            data).eq('id', self.doc_id).execute()
        return response

    def delete(self):
        """Delete the document."""
        response = self.client.table(self.table_name).delete().eq(
            'id', self.doc_id).execute()
        return response


# Create database instance (similar to Firestore's db)
db = SupabaseDB(supabase)
