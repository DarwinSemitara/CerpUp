from forgot_password_routes import register_forgot_password_routes
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, send_file, make_response
from dotenv import load_dotenv
from services.supabase_service import verify_access_token as verify_id_token, db, supabase
from services.cloudinary_service import upload_member_photo, delete_member_photo
from services.audit_service import log_audit_action, get_recent_audit_logs, mark_audit_log_as_read, mark_all_audit_logs_as_read, AuditAction
from datetime import datetime, timezone
import os
import re
import json
import uuid
import logging
import threading
import time

logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE RETRY HELPER
# ══════════════════════════════════════════════════════════════════════════════


def retry_supabase_query(query_func, max_retries=3, initial_delay=0.5):
    """
    Retry a Supabase query with exponential backoff on network errors.

    Args:
        query_func: A function that returns a Supabase query (before .execute())
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry

    Returns:
        Query result
    """
    last_error = None
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return query_func().execute()
        except Exception as e:
            last_error = e
            error_msg = str(e)

            # Check if it's a retryable error (network/timeout/connection errors)
            if ('WinError 10035' in error_msg or 'ReadError' in error_msg or
                'timeout' in error_msg.lower() or 'ConnectionTerminated' in error_msg or
                    'RemoteProtocolError' in error_msg or 'connection' in error_msg.lower()):
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Supabase query failed (attempt {attempt + 1}/{max_retries}): {type(e).__name__}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue

            # Non-retryable error, raise immediately
            raise

    # All retries failed
    logger.error(
        f"Supabase query failed after {max_retries} attempts: {last_error}")
    raise last_error

# ══════════════════════════════════════════════════════════════════════════════
# GA PROGRESS TRACKING (PHASE 1 FIX #3)
# ══════════════════════════════════════════════════════════════════════════════


ga_progress = {
    'running': False,
    'generation': 0,
    'max_generations': 0,
    'best_fitness': float('inf'),
    'time_elapsed': 0.0,
    'status': 'idle',  # 'idle' | 'running' | 'completed' | 'failed'
    'message': '',
    'hard_violations': 0,
    'soft_violations': 0,
    'schedules': [],  # Generated schedules for live display
}
ga_progress_lock = threading.Lock()


def update_ga_progress(generation=None, best_fitness=None, status=None,
                       message=None, hard_viols=None, soft_viols=None, schedules=None,
                       time_elapsed=None, max_generations=None, time_limit_seconds=None):
    """Thread-safe progress update for GA."""
    with ga_progress_lock:
        if generation is not None:
            ga_progress['generation'] = generation
        if time_elapsed is not None:
            ga_progress['time_elapsed'] = time_elapsed
        if max_generations is not None:
            ga_progress['max_generations'] = max_generations
        if time_limit_seconds is not None:
            ga_progress['time_limit_seconds'] = time_limit_seconds
        if best_fitness is not None:
            ga_progress['best_fitness'] = best_fitness
        if status:
            ga_progress['status'] = status
        if message:
            ga_progress['message'] = message
        if hard_viols is not None:
            ga_progress['hard_viols'] = hard_viols
        if soft_viols is not None:
            ga_progress['soft_viols'] = soft_viols
        if schedules is not None:
            ga_progress['schedules'] = schedules
        ga_progress['timestamp'] = time.time()
    with ga_progress_lock:
        if generation is not None:
            ga_progress['generation'] = generation
        if best_fitness is not None:
            ga_progress['best_fitness'] = best_fitness
        if status is not None:
            ga_progress['status'] = status
        if message is not None:
            ga_progress['message'] = message
        if hard_viols is not None:
            ga_progress['hard_violations'] = hard_viols
        if soft_viols is not None:
            ga_progress['soft_violations'] = soft_viols


def reset_ga_progress():
    """Reset GA progress to initial state."""
    with ga_progress_lock:
        ga_progress['running'] = False
        ga_progress['generation'] = 0
        ga_progress['max_generations'] = 0
        ga_progress['best_fitness'] = float('inf')
        ga_progress['time_elapsed'] = 0.0
        ga_progress['status'] = 'idle'
        ga_progress['message'] = ''
        ga_progress['hard_violations'] = 0
        ga_progress['soft_violations'] = 0

# ══════════════════════════════════════════════════════════════════════════════


# Session Configuration - Prevent session sharing between users
app.config['SESSION_COOKIE_NAME'] = 'cerp_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
# Set to True in production with HTTPS
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_PATH'] = '/'  # Available for entire site
# Auto-refresh on each request
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
# 7 days in seconds (increased from 24 hours)
app.config['PERMANENT_SESSION_LIFETIME'] = 604800


# Prevent caching of protected pages to avoid back button access after logout
@app.after_request
def add_cache_control_headers(response):
    """Add cache control headers to prevent back button access after logout."""
    # Don't cache HTML pages, JSON responses, or protected content
    if response.content_type and ('text/html' in response.content_type or 'application/json' in response.content_type):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


@app.before_request
def refresh_session():
    """Refresh session lifetime on each request to prevent timeout during active use."""
    # Log detailed session information for debugging
    session_data = {
        'path': request.path,
        'method': request.method,
        'has_uid': 'uid' in session,
        'session_keys': list(session.keys()) if session else [],
        'permanent': session.permanent if session else False,
        'cookie_name': app.config.get('SESSION_COOKIE_NAME'),
        'cookies_present': list(request.cookies.keys())
    }

    if 'uid' in session:
        session_data['uid'] = session.get('uid')
        session_data['role'] = session.get('role')
        session.modified = True  # Mark session as modified to update expiry time
        logger.info(
            f"✅ SESSION ACTIVE - Path: {request.path} | UID: {session.get('uid')} | Role: {session.get('role')}")
    else:
        logger.warning(
            f"❌ NO SESSION - Path: {request.path} | Cookies: {list(request.cookies.keys())} | Session Keys: {list(session.keys())}")

    logger.debug(f"SESSION DEBUG: {session_data}")


TAP_SECTIONS = [
    ('tap-capdev',  'Capacity Development'),
    ('tap-modelcom', 'Model Community'),
    ('tap-praxis',  'Praxis'),
]


# Favicon route to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'images'),
        'uplogo.png',
        mimetype='image/png'
    )


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        logger.info(f"� LOGIN_REQUIRED CHECK - Path: {request.path}")
        logger.info(f"   Session exists: {bool(session)}")
        logger.info(f"   Session keys: {list(session.keys())}")
        logger.info(f"   Has 'uid': {'uid' in session}")
        logger.info(f"   Cookies received: {list(request.cookies.keys())}")

        if 'uid' not in session:
            # Clear any stale session data
            logger.error(
                f"❌ AUTHENTICATION FAILED - No 'uid' in session for {request.path}")
            session.clear()

            # For API calls (JSON requests), return 401 instead of redirecting
            if request.is_json or request.headers.get('Accept') == 'application/json' or request.path.startswith('/api/'):
                logger.error(f"   Returning 401 for API call")
                return jsonify({'error': 'Not authenticated', 'debug': 'uid not in session'}), 401

            logger.error(f"   Redirecting to login page")
            return redirect(url_for('login'))

        # Validate session hasn't expired (optional: add timestamp check)
        uid = session.get('uid')
        role = session.get('role')

        logger.info(f"AUTHENTICATION SUCCESS - UID: {uid} | Role: {role}")

        if not uid or not role:
            logger.error(
                f"❌ SESSION INVALID - UID or Role missing: uid={uid}, role={role}")
            session.clear()

            # For API calls, return 401 instead of redirecting
            if request.is_json or request.headers.get('Accept') == 'application/json' or request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated', 'debug': 'uid or role missing'}), 401

            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated


def is_partial():
    return request.headers.get('X-Partial') == '1'


# â”€â”€ Public routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/alumni')
def alumni():
    return render_template('alumni.html')


@app.route('/faculty')
def faculty():
    return render_template('faculty.html')


@app.route('/publications')
def publications():
    return render_template('publications.html')


@app.route('/login')
def login():
    # Always clear session when accessing login page
    # This prevents cached admin/user pages from being accessible via back button
    session.clear()

    # If somehow still authenticated (shouldn't happen after clear), redirect to dashboard
    if 'uid' in session:
        return redirect(url_for('dashboard'))

    # Serve Supabase login page
    response = make_response(render_template('login_supabase.html',
                                             supabase_url=os.getenv(
                                                 'SUPABASE_URL'),
                                             supabase_anon_key=os.getenv(
                                                 'SUPABASE_ANON_KEY')
                                             ))
    # Extra cache control to prevent login page caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    response.headers['Clear-Site-Data'] = '"cache", "storage"'
    return response


# â”€â”€ Auth API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided.'}), 400

    # Check for hardcoded admin credentials
    username = data.get('username')
    password = data.get('password')

    if username and password:
        # Direct username/password login (for admin)
        # Get credentials from environment variables for security
        ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'cerp_admin')
        ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'CerpAdmin783695!')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.permanent = True  # Make session persistent
            session['uid'] = 'admin-hardcoded'
            session['email'] = 'admin'
            session['role'] = 'admin'

            logger.info("=" * 80)
            logger.info(f"� SESSION CREATED (ADMIN)")
            logger.info(f"   UID: admin-hardcoded")
            logger.info(f"   Email: admin")
            logger.info(f"   Role: admin")
            logger.info(f"   Permanent: {session.permanent}")
            logger.info(f"   Session Keys: {list(session.keys())}")
            logger.info(
                f"   Cookie Name: {app.config.get('SESSION_COOKIE_NAME')}")
            logger.info(
                f"   Session Lifetime: {app.config.get('PERMANENT_SESSION_LIFETIME')} seconds")
            logger.info("=" * 80)

            return jsonify({'status': 'ok', 'redirect': '/dashboard/'})
        else:
            return jsonify({'error': 'Invalid username or password.'}), 401

    # Supabase token-based login
    access_token = data.get('accessToken')
    if not access_token:
        return jsonify({'error': 'No token provided.'}), 400

    # Verify Supabase access token
    decoded, error = verify_id_token(access_token)
    if error:
        print(f"Token verification error: {error}")
        return jsonify({'error': error}), 401

    uid = decoded['uid']
    email = decoded.get('email', '')

    # Look up role from Supabase users table
    user_doc = db.collection('users').document(uid).get()
    role = 'user'
    first_login = False

    if user_doc.exists:
        user_data = user_doc.to_dict()
        role = user_data.get('role', 'user')
        # Default to True for new users
        first_login = user_data.get('first_login', True)
    else:
        # New user - mark as first login
        first_login = True

    session.permanent = True  # Make session persistent across browser tabs/windows
    session['uid'] = uid
    session['email'] = email
    session['role'] = role

    logger.info("=" * 80)
    logger.info(f"� SESSION CREATED")
    logger.info(f"   UID: {uid}")
    logger.info(f"   Email: {email}")
    logger.info(f"   Role: {role}")
    logger.info(f"   Permanent: {session.permanent}")
    logger.info(f"   Session Keys: {list(session.keys())}")
    logger.info(f"   Cookie Name: {app.config.get('SESSION_COOKIE_NAME')}")
    logger.info(
        f"   Session Lifetime: {app.config.get('PERMANENT_SESSION_LIFETIME')} seconds")
    logger.info("=" * 80)

    # Check if this is first login and needs verification
    if first_login and role == 'user':
        # Generate and send verification code
        from services.email_service import generate_verification_code, store_verification_code, send_verification_email

        # Get display name
        try:
            from services.supabase_service import supabase
            users_response = supabase.auth.admin.list_users()
            current_user = None

            users_list = []
            if hasattr(users_response, 'data'):
                users_list = users_response.data
            elif hasattr(users_response, '__iter__'):
                users_list = list(users_response)
            else:
                users_list = [users_response]

            for user in users_list:
                if (getattr(user, 'id', None) or user.get('id')) == uid:
                    current_user = user
                    break

            if current_user:
                metadata = getattr(current_user, 'user_metadata', None) or (
                    current_user.get('user_metadata') if isinstance(current_user, dict) else {})
                display_name = metadata.get('display_name', 'User') if isinstance(
                    metadata, dict) else 'User'
            else:
                display_name = 'User'
        except:
            display_name = 'User'

        verification_code = generate_verification_code()
        store_verification_code(email, verification_code)
        send_verification_email(email, display_name, verification_code)

        redirect_url = '/user/dashboard/'
        return jsonify({
            'status': 'ok',
            'redirect': redirect_url,
            'first_login': True,
            'requires_verification': True
        })

    redirect_url = '/dashboard/' if role == 'admin' else '/user/dashboard/'
    return jsonify({'status': 'ok', 'redirect': redirect_url, 'first_login': False})


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user and clear session."""
    session.clear()
    response = jsonify({'status': 'ok', 'redirect': url_for('login')})
    # Add extra cache control headers to ensure logout page isn't cached
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/current-member', methods=['GET'])
@login_required
def get_current_member():
    """Get current logged-in member's data."""
    try:
        uid = session.get('uid')
        role = session.get('role')
        logger.info(f"GET_CURRENT_MEMBER - UID: {uid} | Role: {role}")

        if not uid:
            logger.error(f" GET_CURRENT_MEMBER - No UID in session!")
            return jsonify({'error': 'Not authenticated', 'debug': 'No uid in session'}), 401

        # Handle admin hardcoded user
        if uid == 'admin-hardcoded' and role == 'admin':
            logger.info(f"GET_CURRENT_MEMBER - Admin hardcoded user")
            return jsonify({
                'id': 'admin-hardcoded',
                'uid': 'admin-hardcoded',
                'firstName': 'Admin',
                'lastName': 'User',
                'email': 'admin',
                'role': 'admin'
            })

        # Find member by uid
        members = db.collection('members').where(
            'uid', '==', uid).limit(1).stream()
        member_list = [{'id': d.id, **d.to_dict()} for d in members]

        if member_list:
            member_data = member_list[0]

            # Build fullName from 'first' and 'last' fields (same as staff endpoint does)
            first = member_data.get('first', '')
            last = member_data.get('last', '')
            suffix = member_data.get('suffix', '')

            full_name = f"{first} {last}".strip()
            if suffix and full_name:
                full_name += f", {suffix}"

            # Add standardized name fields to response
            member_data['firstName'] = first
            member_data['lastName'] = last
            member_data['fullName'] = full_name if full_name else member_data.get(
                'email', 'Unknown User')

            # Override 'role' field with session role (admin/user), not job title
            # Use session role, not database role field
            member_data['role'] = role

            logger.info(
                f"✅ GET_CURRENT_MEMBER - Found member: {full_name or member_data.get('email', 'Unknown')}")
            return jsonify(member_data)
        else:
            logger.warning(
                f"⚠️ GET_CURRENT_MEMBER - Member not found for UID: {uid}")
            return jsonify({'error': 'Member not found'}), 404
    except Exception as e:
        logger.error(f"� GET_CURRENT_MEMBER - Exception: {e}")
        return jsonify({'error': str(e)}), 500


# DEBUG ENDPOINT - Remove after fixing
@app.route('/api/session-debug', methods=['GET'])
def session_debug():
    """Debug endpoint to check session status - REMOVE AFTER FIXING"""
    debug_info = {
        'session_exists': bool(session),
        'session_keys': list(session.keys()),
        'has_uid': 'uid' in session,
        'uid': session.get('uid', 'NOT SET'),
        'role': session.get('role', 'NOT SET'),
        'email': session.get('email', 'NOT SET'),
        'permanent': session.permanent if session else False,
        'cookies_received': list(request.cookies.keys()),
        'cookie_name_expected': app.config.get('SESSION_COOKIE_NAME'),
        'session_lifetime': app.config.get('PERMANENT_SESSION_LIFETIME'),
        'request_path': request.path,
        'request_method': request.method
    }
    logger.info(f"SESSION DEBUG ENDPOINT CALLED: {debug_info}")
    return jsonify(debug_info)


# â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/dashboard/')
@login_required
def dashboard():
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    # Add cache buster
    import time
    cache_version = int(time.time())

    response = make_response(render_template('pages/dashboard.html',
                                             email=email,
                                             initial=initial,
                                             page_title='Dashboard',
                                             active_page='dashboard',
                                             cache_version=cache_version))

    # Ensure no caching of admin dashboard
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/dashboard/faculty/<member_id>')
@login_required
def faculty_detail(member_id):
    """Display detailed view of a faculty member."""
    try:
        # Get member data
        member_doc = db.collection('members').document(member_id).get()

        if not member_doc.exists:
            return "Faculty member not found", 404

        member_data = member_doc.to_dict()
        member_data['id'] = member_id

        # Staff data comes from member data (no separate staff table)
        # Extract availability and photo from member data
        staff_data = {
            'photo_url': member_data.get('photo_url', ''),
            'availability': member_data.get('availability', []) if member_data.get('availability') else [],
            'subjects': []  # Subjects are no longer tracked
        }

        # Get research count
        uid = member_data.get('uid', '')
        research_count = 0
        if uid:
            research_docs = db.collection(
                'research').where('uid', '==', uid).stream()
            research_count = len(list(research_docs))

        # Get extensions count
        extensions_count = 0
        if uid:
            ext_docs = db.collection('extensions').where(
                'uid', '==', uid).stream()
            extensions_count = len(list(ext_docs))

        email = session.get('email', '')
        initial = email[0].upper() if email else 'A'

        return render_template('pages/faculty_detail.html',
                               member=member_data,
                               staff=staff_data,
                               research_count=research_count,
                               extensions_count=extensions_count,
                               email=email,
                               initial=initial,
                               page_title=f"{member_data.get('first', '')} {member_data.get('last', '')}",
                               active_page='dashboard')
    except Exception as e:
        logger.error(f"Error loading faculty detail: {e}")
        return f"Error loading faculty: {str(e)}", 500


# â”€â”€ Partial views (AJAX) â€” mirrors Django's X-Partial pattern â”€â”€

@app.route('/research/')
@login_required
def section_research():
    if is_partial():
        return render_template('partials/research.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/research.html',
                           email=email,
                           initial=initial,
                           page_title='Research',
                           active_page='research')


@app.route('/extensions/')
@login_required
def section_extensions():
    if is_partial():
        return render_template('partials/extensions.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/extensions.html',
                           email=email,
                           initial=initial,
                           page_title='Extensions',
                           active_page='extensions')


@app.route('/admin-page/')
@login_required
def admin_page():
    """Admin page for admin dashboard"""
    if is_partial():
        return render_template('partials/admin_page.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/admin_page.html',
                           email=email,
                           initial=initial,
                           page_title='Admin',
                           active_page='admin')


@app.route('/extensions/public-engagements/')
@login_required
def section_pub_eng():
    if is_partial():
        return render_template('partials/pub_eng.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/pub_eng.html',
                           email=email,
                           initial=initial,
                           page_title='Public Engagements',
                           active_page='pub_eng')


@app.route('/extensions/tap-hsp/')
@login_required
def section_tap():
    if is_partial():
        return render_template('partials/tap_hsp.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/tap_hsp.html',
                           email=email,
                           initial=initial,
                           page_title='TAP-HSP',
                           active_page='tap_hsp')


@app.route('/schedule/class/')
@login_required
def section_class_schedule():
    if is_partial():
        return render_template('partials/schedule.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/schedule.html',
                           email=email,
                           initial=initial,
                           page_title='Class Schedule',
                           active_page='schedule')


@app.route('/schedule/section/')
@login_required
def section_schedule_section():
    """Section schedule view (DEPRECATED - redirects to Courses)."""
    return redirect(url_for('schedule_courses'))


@app.route('/schedule/courses/')
@login_required
def schedule_courses():
    """Courses and Faculty management page (V2 - Redesigned with 4-step workflow)."""
    if is_partial():
        return render_template('partials/courses2.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/courses2.html',
                           email=email,
                           initial=initial,
                           page_title='Courses',
                           active_page='courses')


# LEGACY V1 route removed - V2 is now the primary courses page
# Old route: /schedule/courses2/ redirects to /schedule/courses/
@app.route('/schedule/courses2/')
@login_required
def schedule_courses2():
    """Redirect old V2 route to main courses route."""
    return redirect('/schedule/courses/', code=302)


@app.route('/schedule/events/')
@login_required
def section_events():
    if is_partial():
        return render_template('partials/news_events.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/news_events.html',
                           email=email,
                           initial=initial,
                           page_title='News & Events',
                           active_page='events')


@app.route('/fsr/')
@login_required
def section_fsr():
    if is_partial():
        return render_template('partials/fsr.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/fsr.html',
                           email=email,
                           initial=initial,
                           page_title='FSR',
                           active_page='fsr')


# Keep old data route for backwards compatibility (redirects to FSR)
@app.route('/data/')
@login_required
def section_data():
    if is_partial():
        return render_template('partials/fsr.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/fsr.html',
                           email=email,
                           initial=initial,
                           page_title='FSR',
                           active_page='fsr')


@app.route('/manage/')
@login_required
def section_manage():
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/manage.html',
                           email=email,
                           initial=initial,
                           page_title='Manage',
                           active_page='manage')


@app.route('/instructions/')
@login_required
def section_instructions():
    # Redirect old instructions route to manage
    return redirect(url_for('section_manage'))


@app.route('/other/')
@login_required
def section_other():
    return redirect(url_for('dashboard'))


# ── CHE Conversation History API ─────────────────────────────

MAX_CHE_CONVERSATIONS = 7


@app.route('/api/che/conversations', methods=['GET'])
@login_required
def che_list_conversations():
    """List all saved CHE conversations for the current admin (max 7, newest first)."""
    try:
        user_id = session.get('uid', '')

        response = (
            supabase.table('che_conversations')
            .select('id, title, created_at, updated_at, is_system, undeletable')
            .eq('user_id', user_id)
            # Exclude system conversations from CHE page
            .eq('is_system', False)
            .order('updated_at', desc=True)
            .limit(MAX_CHE_CONVERSATIONS)
            .execute()
        )
        return jsonify({'conversations': response.data or []})
    except Exception as e:
        logger.error(f"CHE list conversations error: {e}")
        return jsonify({'conversations': [], 'error': str(e)}), 500


@app.route('/api/che/conversations', methods=['POST'])
@login_required
def che_create_conversation():
    """
    Create a new conversation. If already at limit (7), delete the oldest first.
    Body: { "title": str }  (optional — defaults to 'New Conversation')
    """
    try:
        user_id = session.get('uid', '')
        data = request.get_json(silent=True) or {}
        title = data.get(
            'title', 'New Conversation').strip() or 'New Conversation'

        # Check count and prune if at limit
        count_resp = (
            supabase.table('che_conversations')
            .select('id, updated_at')
            .eq('user_id', user_id)
            .order('updated_at', desc=True)
            .execute()
        )
        existing = count_resp.data or []
        if len(existing) >= MAX_CHE_CONVERSATIONS:
            # Delete the oldest (last in desc-sorted list)
            oldest_id = existing[-1]['id']
            supabase.table('che_conversations').delete().eq(
                'id', oldest_id).execute()

        now = datetime.now(timezone.utc).isoformat()
        new_id = str(uuid.uuid4())
        supabase.table('che_conversations').insert({
            'id': new_id,
            'user_id': user_id,
            'title': title,
            'messages': [],
            'created_at': now,
            'updated_at': now,
        }).execute()

        return jsonify({'id': new_id, 'title': title, 'created_at': now, 'updated_at': now})
    except Exception as e:
        logger.error(f"CHE create conversation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/che/conversations/<conv_id>', methods=['GET'])
@login_required
def che_get_conversation(conv_id):
    """Load all messages for a conversation."""
    try:
        user_id = session.get('uid', '')
        resp = (
            supabase.table('che_conversations')
            .select('*')
            .eq('id', conv_id)
            .eq('user_id', user_id)
            .single()
            .execute()
        )
        if not resp.data:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(resp.data)
    except Exception as e:
        logger.error(f"CHE get conversation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/che/conversations/<conv_id>', methods=['PATCH'])
@login_required
def che_update_conversation(conv_id):
    """
    Save messages and optionally update the title.
    Body: { "messages": [...], "title": str (optional) }
    """
    try:
        user_id = session.get('uid', '')
        data = request.get_json(silent=True) or {}

        update_payload = {'updated_at': datetime.utcnow().isoformat()}
        if 'messages' in data:
            update_payload['messages'] = data['messages']
        if 'title' in data and data['title'].strip():
            update_payload['title'] = data['title'].strip()

        supabase.table('che_conversations').update(update_payload).eq(
            'id', conv_id).eq('user_id', user_id).execute()

        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"CHE update conversation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/che/conversations/<conv_id>', methods=['DELETE'])
@login_required
def che_delete_conversation(conv_id):
    """Delete a conversation (unless it's marked as undeletable)."""
    try:
        user_id = session.get('uid', '')

        # Check if conversation is undeletable
        check_resp = (
            supabase.table('che_conversations')
            .select('undeletable')
            .eq('id', conv_id)
            .eq('user_id', user_id)
            .single()
            .execute()
        )

        if check_resp.data and check_resp.data.get('undeletable', False):
            return jsonify({'error': 'This conversation cannot be deleted.', 'undeletable': True}), 403

        supabase.table('che_conversations').delete().eq(
            'id', conv_id).eq('user_id', user_id).execute()
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"CHE delete conversation error: {e}")
        return jsonify({'error': str(e)}), 500


# ── CHE AI Chat API ──────────────────────────────────────────

@app.route('/api/che/chat', methods=['POST'])
@login_required
def che_chat():
    """
    CHE AI chat endpoint with GA scheduling integration.
    Accepts: { "message": str,
        "history": [...], "include_context": bool, "conversation_id": str }
    Returns: { "reply": str, "error": bool,
        "action": dict|null, "action_result": dict|null }
    """
    try:
        from services.che_service import chat as che_chat_fn, extract_action, execute_schedule_action

        data = request.get_json(silent=True) or {}
        message = data.get('message', '').strip()
        history = data.get('history', [])
        include_context = data.get('include_context', False)
        conversation_id = data.get('conversation_id')
        # New: explicit flag for schedule page chat
        is_schedule_page = data.get('is_schedule_page', False)
        # New: user role (admin vs user/member)
        user_role = data.get('user_role', 'admin')
        user_name = data.get('user_name', None)
        # New: semester/year filtering for schedule page queries
        current_school_year = data.get('school_year') or data.get('schoolYear')
        current_semester = data.get('semester')

        if not message:
            return jsonify({'reply': 'Please send a message.', 'error': True}), 400

        # Check if this is the system "Schedule Generation" conversation
        # Default to True if from schedule page
        is_system_conversation = is_schedule_page
        if conversation_id and not is_schedule_page:
            try:
                user_id = session.get('uid', '')
                conv_resp = (
                    supabase.table('che_conversations')
                    .select('is_system, title')
                    .eq('id', conversation_id)
                    .eq('user_id', user_id)
                    .single()
                    .execute()
                )
                if conv_resp.data:
                    is_system_conversation = conv_resp.data.get(
                        'is_system', False)
            except Exception as conv_err:
                logger.warning(
                    f"Could not check conversation type: {conv_err}")

        # Always inject schedule context for scheduling awareness
        context_data = {}

        # Room list for CHE awareness, including rooms added on the courses page
        try:
            context_data['available_rooms'] = get_all_rooms()
        except Exception as room_err:
            logger.warning(f"CHE room context fetch: {room_err}")
            context_data['available_rooms'] = list(DEFAULT_ROOMS)

        try:
            # Schedules (always loaded for GA awareness) - FROM SUPABASE
            query = supabase.table('schedules').select('*')

            # Filter by semester/year if provided (from schedule page context)
            if current_school_year:
                query = query.eq('school_year', current_school_year)
            if current_semester:
                query = query.eq('semester', str(current_semester))

            # DEBUG LOGGING
            print(f"\n=== CHE CHAT DEBUG ===")
            print(f"Message: '{message}'")
            print(f"School Year: {current_school_year}")
            print(f"Semester: {current_semester}")

            result = query.execute()

            print(f"Total schedules fetched: {len(result.data)}")
            if result.data:
                print(
                    f"Sample schedule: prof='{result.data[0].get('prof')}', day='{result.data[0].get('day')}', school_year='{result.data[0].get('school_year')}', semester='{result.data[0].get('semester')}'")

                # Check Aaron Joseph specifically
                aaron_schedules = [s for s in result.data if 'aaron' in s.get(
                    'prof', '').lower() and 'joseph' in s.get('prof', '').lower()]
                print(
                    f"Aaron Joseph total schedules in this semester: {len(aaron_schedules)}")
                if aaron_schedules:
                    monday_aaron = [s for s in aaron_schedules if s.get(
                        'day', '').lower() == 'monday']
                    print(
                        f"Aaron Joseph Monday schedules: {len(monday_aaron)}")
                    if monday_aaron:
                        for s in monday_aaron:
                            print(
                                f"  - {s.get('start')} to {s.get('end')}: {s.get('subj_code')} ({s.get('prof')})")
                    else:
                        print(
                            "  - No Monday classes for Aaron Joseph in this semester")
                        print(
                            f"  - Aaron's days this semester: {list(set([s.get('day') for s in aaron_schedules]))}")

            schedules_raw = []
            for data in result.data:
                # Normalize to camelCase for consistency with GA functions
                schedules_raw.append({
                    'id': data.get('id'),
                    'prof': data.get('prof', ''),
                    'subjCode': data.get('subj_code', data.get('subjCode', '')),
                    'subjName': data.get('subj_name', data.get('subjName', '')),
                    'day': data.get('day', ''),
                    'start': str(data.get('start', '')).rsplit(':', 1)[0] if data.get('start') and str(data.get('start')).count(':') > 1 else data.get('start', ''),
                    'end': str(data.get('end', '')).rsplit(':', 1)[0] if data.get('end') and str(data.get('end')).count(':') > 1 else data.get('end', ''),
                    'room': data.get('room', ''),
                    'section': data.get('section', ''),
                    'units': data.get('units', ''),
                })
            context_data['schedules'] = schedules_raw
        except Exception as ctx_err:
            logger.warning(f"CHE schedule context fetch: {ctx_err}")
            context_data['schedules'] = []

        if include_context:
            # Try to load additional context data, but don't fail if tables don't exist
            try:
                member_docs = db.collection('members').stream()
                context_data['members'] = [
                    {'id': d.id, **d.to_dict()} for d in member_docs]
            except Exception as member_err:
                logger.warning(
                    f"CHE context: members table not available - {member_err}")
                context_data['members'] = []

            try:
                research_docs = db.collection('research').stream()
                context_data['research'] = [
                    {'id': d.id, **d.to_dict()} for d in research_docs]
            except Exception as research_err:
                logger.warning(
                    f"CHE context: research table not available - {research_err}")
                context_data['research'] = []

            try:
                ext_docs = db.collection('extensions').stream()
                context_data['extensions'] = [
                    {'id': d.id, **d.to_dict()} for d in ext_docs]
            except Exception as ext_err:
                logger.warning(
                    f"CHE context: extensions table not available - {ext_err}")
                context_data['extensions'] = []

            try:
                news_docs = db.collection('news').stream()
                context_data['news'] = [
                    {'id': d.id, **d.to_dict()} for d in news_docs]
            except Exception as news_err:
                logger.warning(
                    f"CHE context: news table not available - {news_err}")
                context_data['news'] = []

        result = che_chat_fn(
            message=message,
            history=history,
            context_data=context_data,
            is_system_conversation=is_system_conversation,  # Pass conversation type flag
            user_role=user_role,  # Pass user role (admin or user/member)
            user_name=user_name  # Pass user name for filtering member schedules
        )

        # If CHE returned a scheduling action, pre-execute it for preview
        if result.get('action') and not result.get('error'):
            action_data = result['action']
            # For non-confirm actions (queries), execute immediately
            if not action_data.get('confirm', False):
                action_result = execute_schedule_action(
                    action_data, context_data.get('schedules', []))
                result['action_result'] = action_result
            else:
                # For confirm actions, just pass the action to frontend
                # Frontend will call /api/che/execute-action after user confirms
                result['action_result'] = None

        return jsonify(result)

    except Exception as e:
        logger.error(f"CHE chat route error: {e}")
        return jsonify({'reply': 'An unexpected error occurred.', 'error': True}), 500


@app.route('/api/che/execute-action', methods=['POST'])
@login_required
def che_execute_action():
    """
    Execute a confirmed scheduling action from CHE.
    Called after user confirms via the chat UI.
    """
    try:
        from services.che_service import execute_schedule_action

        data = request.get_json(silent=True) or {}
        action_data = data.get('action', {})

        if not action_data or 'action' not in action_data:
            return jsonify({'success': False, 'message': 'No action provided.'}), 400

        # Get current schedules from Supabase (normalized to camelCase)
        result = supabase.table('schedules').select('*').execute()
        existing_schedules = []
        for data in result.data:
            existing_schedules.append({
                'id': data.get('id'),
                'prof': data.get('prof', ''),
                'subjCode': data.get('subj_code', data.get('subjCode', '')),
                'subjName': data.get('subj_name', data.get('subjName', '')),
                'day': data.get('day', ''),
                'start': str(data.get('start', '')).rsplit(':', 1)[0] if data.get('start') and str(data.get('start')).count(':') > 1 else data.get('start', ''),
                'end': str(data.get('end', '')).rsplit(':', 1)[0] if data.get('end') and str(data.get('end')).count(':') > 1 else data.get('end', ''),
                'room': data.get('room', ''),
                'section': data.get('section', ''),
                'units': data.get('units', ''),
                'semester': data.get('semester', ''),
                'schoolYear': data.get('school_year', data.get('schoolYear', '')),
            })

        # Execute the action
        result = execute_schedule_action(action_data, existing_schedules)

        # If action was successful and modifies data, apply changes to DB
        if result.get('success'):
            action_type = action_data.get('action', '')

            if action_type == 'add_schedule' and result['data'].get('schedule'):
                sched = result['data']['schedule']
                new_id = str(uuid.uuid4())

                # Auto-detect school year: current year to next year (matches frontend default)
                now = datetime.now(timezone.utc)
                school_year = f"{now.year}-{now.year + 1}"
                # Default to 1st semester (admin changes this on the schedule page)
                semester = '1'

                supabase.table('schedules').insert({
                    'id': new_id,
                    'subj_code': sched.get('subjCode', ''),
                    'subj_name': sched.get('subjName', ''),
                    'prof': sched.get('prof', ''),
                    'room': sched.get('room', ''),
                    'section': sched.get('section', ''),
                    'units': int(float(sched.get('units', 0))) if sched.get('units') else 0,
                    'day': sched.get('day', ''),
                    'start': sched.get('start', ''),
                    'end': sched.get('end', ''),
                    'type': 'Lecture',
                    'year': '1',
                    'semester': semester,
                    'school_year': school_year,
                    'created_at': now.isoformat(),
                }).execute()
                result['message'] += f" Added as ID: {new_id[:8]}..."

            elif action_type == 'move_schedule' and result['data'].get('moved_schedules'):
                for moved in result['data']['moved_schedules']:
                    sid = moved.get('id')
                    if sid:
                        supabase.table('schedules').update({
                            'day': moved.get('day', ''),
                            'start': moved.get('start', ''),
                            'end': moved.get('end', ''),
                        }).eq('id', sid).execute()

            elif action_type == 'delete_schedule' and result['data'].get('schedules_to_delete'):
                for sid in result['data']['schedules_to_delete']:
                    supabase.table('schedules').delete().eq(
                        'id', sid).execute()
                result['message'] = f"Deleted {len(result['data']['schedules_to_delete'])} schedule(s)."

            elif action_type == 'generate_full_schedule' and result['data'].get('redirect_to_endpoint'):
                # Instead of executing synchronously (which times out), redirect to async generation
                gen_params = result['data']['params']

                # Start async generation by calling the async endpoint internally
                # This returns immediately and lets the frontend poll for progress
                target_sy = gen_params.get('target_school_year')
                target_sem = gen_params.get('target_semester')
                ref_sy = gen_params.get('reference_school_year')
                ref_sem = gen_params.get('reference_semester')

                # Trigger async generation in background thread
                import threading

                def start_async_generation():
                    try:
                        # Import here to avoid circular dependencies
                        from flask import current_app
                        with current_app.app_context():
                            # Call the async generation endpoint logic
                            from services.scheduler_service import run_full_ga_schedule_generation
                            run_full_ga_schedule_generation(
                                target_sy, target_sem, ref_sy, ref_sem,
                                save_to_db=True, max_minutes=5
                            )
                    except Exception as e:
                        logger.error(f"Async generation error: {e}")
                        update_ga_progress(status='error', message=str(e))

                # Start in background
                thread = threading.Thread(
                    target=start_async_generation, daemon=True)
                thread.start()

                result = {
                    'success': True,
                    'message': f'Started generating schedule for {target_sy} Semester {target_sem}. This will take 1-3 minutes.',
                    'data': {
                        'async': True,
                        'poll_endpoint': '/api/schedule/generate-progress',
                        'target_school_year': target_sy,
                        'target_semester': target_sem
                    }
                }

                # Save if requested
                if gen_params.get('save_to_db', False) and ga_result.get('success'):
                    target_sem = gen_params.get('target_semester', '1')
                    target_sy = gen_params.get('target_school_year',
                                               f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).year + 1}")
                    saved = 0
                    for sched in ga_result['schedules']:
                        new_id = str(uuid.uuid4())
                        supabase.table('schedules').insert({
                            'id': new_id,
                            'subj_code': sched.get('subjCode', ''),
                            'subj_name': sched.get('subjName', ''),
                            'prof': sched.get('prof', ''),
                            'room': sched.get('room', ''),
                            'section': sched.get('section', ''),
                            'units': int(sched.get('units', 0)),
                            'day': sched.get('day', ''),
                            'start': sched.get('start', ''),
                            'end': sched.get('end', ''),
                            'type': 'generated',
                            'year': '1',
                            'semester': target_sem,
                            'school_year': target_sy,
                            'created_at': datetime.now(timezone.utc).isoformat(),
                        }).execute()
                        saved += 1
                    result['message'] += f" | Saved {saved} entries to database."

        return jsonify(result)

    except Exception as e:
        logger.error(f"CHE execute-action error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Staff API ────────────────────────────────────────────────

@app.route('/api/staff', methods=['GET'])
@login_required
def get_staff():
    """Return all members from members collection as faculty."""
    try:
        # Fetch all members from Supabase using the wrapper
        docs = db.collection('members').stream()

        staff = []
        for d in docs:
            data = d.to_dict()
            # Format to match expected staff structure
            staff_member = {
                'id': d.id,
                'memberId': d.id,  # Same as member ID
                'fullName': f"{data.get('first', '')} {data.get('last', '')}".strip(),
                'photo_url': data.get('photo_url', ''),
                'availability': data.get('availability', []) if data.get('availability') else [],
                'subjects': [],  # No longer using subject filtering
                'created_at': data.get('created_at', '')
            }
            # Add suffix if present
            if data.get('suffix'):
                staff_member['fullName'] += f", {data['suffix']}"

            staff.append(staff_member)

        print(f"✅ Found {len(staff)} members (faculty)")
        return jsonify(staff)
    except Exception as e:
        print(f"❌ Error fetching staff: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/staff', methods=['POST'])
@login_required
def add_staff():
    """
    DEPRECATED: Staff are now auto-synced from members with is_faculty=true.
    This endpoint is kept for backward compatibility but does nothing.
    """
    return jsonify({'error': 'Staff are now managed through the Members section. Mark a member as Teaching Personnel/Faculty to add them to the faculty list.'}), 400


@app.route('/api/staff/<staff_id>', methods=['PUT'])
@login_required
def update_staff(staff_id):
    """
    DEPRECATED: Staff are now auto-synced from members.
    Update the member record in the Manage page instead.
    """
    return jsonify({'error': 'Staff are managed through Members. Please update the member in the Manage page.'}), 400


@app.route('/api/staff/<staff_id>', methods=['DELETE'])
@login_required
def delete_staff(staff_id):
    """
    Remove faculty status from a member (set is_faculty=false).
    This unlinks them from the faculty list without deleting the member.
    """
    try:
        # staff_id is the member_id
        doc = db.collection('members').document(staff_id).get()
        if not doc.exists:
            return jsonify({'error': 'Member not found.'}), 404

        # Update member to remove faculty status
        db.collection('members').document(staff_id).update({
            'is_faculty': False
        })

        return jsonify({'status': 'ok', 'message': 'Faculty status removed. Member can be re-added by checking Teaching Personnel checkbox in Manage page.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Members API ───────────────────────────────────────────────

@app.route('/api/members', methods=['GET'])
def get_members():
    """Return all members from Supabase (public endpoint for faculty page).
    Supports filtering by type via query parameter or faculty status."""
    try:
        member_type = request.args.get('type', None)
        faculty_only = request.args.get('faculty', None)

        # Build query function for retry
        def build_query():
            query = supabase.table('members').select('*')

            if faculty_only and faculty_only.lower() == 'true':
                # Filter by is_faculty = true
                query = query.eq('is_faculty', True)
            elif member_type:
                # Filter by type
                query = query.eq('type', member_type)

            # Order by created_at
            query = query.order('created_at', desc=False)
            return query

        # Execute with retry logic
        result = retry_supabase_query(build_query)
        members = result.data or []

        # Ensure 'uid' field exists (use 'id' as fallback for compatibility)
        for m in members:
            if 'uid' not in m and 'id' in m:
                m['uid'] = m['id']

        print(f"\n👥 GET /api/members returned {len(members)} members:")
        for m in members[:3]:  # Show first 3
            print(
                f"   - {m.get('first')} {m.get('last')}: id={m.get('id', 'N/A')}, uid={m.get('uid', 'N/A')}")

        return jsonify(members)
    except Exception as e:
        logger.error(f"Error in get_members: {e}", exc_info=True)
        # Return empty array instead of error to allow UI to load
        return jsonify([]), 200


@app.route('/api/members', methods=['POST'])
@login_required
def add_member():
    """
    Add a new member. Accepts multipart/form-data so the photo
    can be uploaded in the same request.
    """
    try:
        member_id = str(uuid.uuid4())

        # Debug: Log the is_faculty value received
        is_faculty_raw = request.form.get('is_faculty', 'false')
        print(
            f"🔍 Received is_faculty value: '{is_faculty_raw}' (type: {type(is_faculty_raw)})")

        # Build member data from form fields
        # Normalize name casing: store as Title Case
        raw_last = request.form.get('last', '').strip()
        raw_first = request.form.get('first', '').strip()

        member = {
            'last':      raw_last.title() if raw_last.isupper() or raw_last.islower() else raw_last,
            'first':     raw_first.title() if raw_first.isupper() or raw_first.islower() else raw_first,
            'mi':        request.form.get('mi', 'N/A'),
            'role':      request.form.get('role', ''),
            'email':     request.form.get('email', ''),
            'address':   request.form.get('address', '') or None,
            'suffix':    request.form.get('suffix', ''),
            'contact':   request.form.get('contact', '') or None,
            'gender':    request.form.get('gender', '') or None,
            'dob':       request.form.get('dob', '') or None,
            'type':      request.form.get('type', 'admin_staff'),
            'is_faculty': is_faculty_raw.lower() == 'true',
            'availability': request.form.getlist('availability'),
            'photo_url': None,
            'user_no':   request.form.get('user_no', ''),
            'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }

        print(f"✅ Converted is_faculty to boolean: {member['is_faculty']}")

        # Upload photo to Cloudinary if provided
        photo = request.files.get('photo')
        if photo and photo.filename:
            url, err = upload_member_photo(photo.stream, member_id)
            if err:
                return jsonify({'error': f'Photo upload failed: {err}'}), 500
            member['photo_url'] = url

        # Save to Firestore
        try:
            db.collection('members').document(member_id).set(member)
        except Exception as db_err:
            err_msg = str(db_err)
            if 'duplicate' in err_msg.lower() or 'unique' in err_msg.lower() or '23505' in err_msg:
                return jsonify({'error': 'A member with this email already exists. You can leave the email blank or use a different one.'}), 400
            raise db_err
        print(
            f"💾 Saved member {member_id} with is_faculty={member['is_faculty']}")

        # Log audit action
        try:
            admin_email = session.get('email', 'admin')
            admin_uid = session.get('uid', 'unknown')
            member_name = f"{member['first']} {member['last']}".strip()

            log_audit_action(
                supabase=supabase,
                action_type=AuditAction.MEMBER_CREATED,
                description=f"Added new member: {member_name}",
                performed_by=admin_uid,
                performed_by_email=admin_email,
                target_type='member',
                target_id=member_id,
                target_name=member_name,
                metadata={
                    'role': member['role'],
                    'type': member['type'],
                    'is_faculty': member['is_faculty'],
                    'email': member['email']
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to log audit action: {audit_err}")

        return jsonify({'status': 'ok', 'id': member_id, 'member': member}), 201

    except Exception as e:
        print(f"❌ Error adding member: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/members/<member_id>', methods=['PUT'])
@login_required
def update_member(member_id):
    """Update an existing member's details."""
    try:
        doc = db.collection('members').document(member_id).get()
        if not doc.exists:
            return jsonify({'error': 'Member not found.'}), 404

        data = request.get_json() if request.is_json else None
        if not data:
            # Try form data
            data = {}
            for key in ['last', 'first', 'mi', 'role', 'email', 'address',
                        'suffix', 'contact', 'gender', 'dob', 'type', 'user_no']:
                val = request.form.get(key)
                if val is not None:
                    data[key] = val
            is_faculty_raw = request.form.get('is_faculty')
            if is_faculty_raw is not None:
                data['is_faculty'] = is_faculty_raw.lower() == 'true'
            avail = request.form.getlist('availability')
            if avail:
                data['availability'] = avail

        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        # Normalize name casing
        if 'last' in data:
            raw = data['last'].strip()
            data['last'] = raw.title() if raw.isupper() or raw.islower() else raw
        if 'first' in data:
            raw = data['first'].strip()
            data['first'] = raw.title() if raw.isupper() or raw.islower() else raw

        db.collection('members').document(member_id).update(data)

        # Log audit action
        try:
            admin_email = session.get('email', 'admin')
            admin_uid = session.get('uid', 'unknown')
            member_data = doc.to_dict()
            member_name = f"{member_data.get('first', '')} {member_data.get('last', '')}".strip(
            )

            # Check for specific action types
            if 'disabled' in data:
                # Faculty enable/disable action
                is_disabled = data['disabled']
                action_type = AuditAction.MEMBER_DISABLED if is_disabled else AuditAction.MEMBER_ENABLED
                description = f"{'Disabled' if is_disabled else 'Enabled'} member: {member_name}"
            else:
                # General update
                action_type = AuditAction.MEMBER_UPDATED
                # Build a description of what changed
                changes = []
                if 'first' in data or 'last' in data:
                    changes.append('name')
                if 'role' in data:
                    changes.append('role')
                if 'email' in data:
                    changes.append('email')
                if 'type' in data:
                    changes.append('type')
                if 'is_faculty' in data:
                    changes.append('faculty status')
                if 'availability' in data:
                    changes.append('availability')

                change_desc = ', '.join(changes) if changes else 'details'
                description = f"Updated {member_name}: {change_desc}"

            log_audit_action(
                supabase=supabase,
                action_type=action_type,
                description=description,
                performed_by=admin_uid,
                performed_by_email=admin_email,
                target_type='member',
                target_id=member_id,
                target_name=member_name,
                metadata={'changes': data}
            )
        except Exception as audit_err:
            logger.warning(f"Failed to log audit action: {audit_err}")

        return jsonify({'status': 'ok', 'id': member_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/members/<member_id>', methods=['DELETE'])
@login_required
def delete_member(member_id):
    """Delete a member, their photo, and associated user account if any."""
    try:
        doc = db.collection('members').document(member_id).get()
        if not doc.exists:
            return jsonify({'error': 'Member not found.'}), 404

        member_data = doc.to_dict()

        # Delete photo from Cloudinary
        delete_member_photo(member_id)

        # Delete associated user account if exists
        uid = member_data.get('uid')
        if uid:
            try:
                # Delete from users table
                db.collection('users').document(uid).delete()
                # Delete from Supabase Auth
                supabase.auth.admin.delete_user(uid)
            except Exception as auth_err:
                logger.warning(f"Could not delete auth user {uid}: {auth_err}")

        # Delete the member record
        db.collection('members').document(member_id).delete()

        # Log audit action
        try:
            admin_email = session.get('email', 'admin')
            admin_uid = session.get('uid', 'unknown')
            member_name = f"{member_data.get('first', '')} {member_data.get('last', '')}".strip(
            )

            log_audit_action(
                supabase=supabase,
                action_type=AuditAction.MEMBER_DELETED,
                description=f"Deleted member: {member_name}" +
                (" and account" if uid else ""),
                performed_by=admin_uid,
                performed_by_email=admin_email,
                target_type='member',
                target_id=member_id,
                target_name=member_name,
                metadata={
                    'had_account': bool(uid),
                    'email': member_data.get('email', ''),
                    'role': member_data.get('role', '')
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to log audit action: {audit_err}")

        return jsonify({
            'status': 'ok',
            'had_account': bool(uid),
            'message': 'Member and associated account deleted.' if uid else 'Member deleted.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/members/<member_id>/create-account', methods=['POST'])
@login_required
def create_member_account(member_id):
    """
    Admin assigns an email + ID to a member, creating a Supabase Auth account.
    The member ID is used as both username and initial password.
    """
    from services.supabase_service import supabase
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data.'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    faculty_id = data.get('member_id', '').strip()

    if not email or not password or not faculty_id:
        return jsonify({'error': 'Email, password, and member ID are required.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    try:
        # Check member exists
        doc = db.collection('members').document(member_id).get()
        if not doc.exists:
            return jsonify({'error': 'Member not found.'}), 404
        member = doc.to_dict()

        display_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
        )

        # Create Supabase Auth user
        user_id = None
        try:
            logger.info(f"Attempting to create user for email: {email}")
            response = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                # Auto-confirm email (we handle verification via code)
                "email_confirm": True,
                "user_metadata": {
                    "display_name": display_name,
                    "faculty_id": faculty_id
                }
            })

            if not response.user:
                logger.error("No user object in create response")
                return jsonify({'error': 'Failed to create user account.'}), 500

            user_id = response.user.id
            logger.info(f"Created user successfully with ID: {user_id}")

        except Exception as create_error:
            # If user already exists, try to update
            error_msg = str(create_error)
            logger.info(f"Create user error: {error_msg}")

            if 'already registered' in error_msg.lower() or 'already exists' in error_msg.lower() or 'already been registered' in error_msg.lower():
                # Try to get existing user and update password
                logger.info(
                    f"User already exists, attempting update for: {email}")
                try:
                    # Get user by email - Supabase returns response with data attribute
                    users_response = supabase.auth.admin.list_users()
                    existing_user = None

                    # Extract users from response
                    users_list = []
                    if hasattr(users_response, 'data'):
                        users_list = users_response.data
                    elif hasattr(users_response, '__iter__'):
                        users_list = list(users_response)
                    else:
                        users_list = [users_response]

                    logger.info(f"Found {len(users_list)} total users")

                    # Find user by email
                    for user in users_list:
                        user_email = getattr(user, 'email', None) or (
                            user.get('email') if isinstance(user, dict) else None)
                        if user_email == email:
                            existing_user = user
                            logger.info(f"Found existing user: {email}")
                            break

                    if existing_user:
                        # Update password
                        user_id = getattr(existing_user, 'id', None) or (
                            existing_user.get('id') if isinstance(existing_user, dict) else None)
                        if user_id:
                            logger.info(
                                f"Updating password for user: {user_id}")
                            supabase.auth.admin.update_user_by_id(
                                user_id,
                                {"password": password}
                            )
                            logger.info("Password updated successfully")
                        else:
                            logger.error("Could not extract user ID")
                            return jsonify({'error': 'Could not extract user ID.'}), 500
                    else:
                        logger.error(f"User {email} not found in list")
                        return jsonify({'error': 'User exists but could not be found in system.'}), 500

                except Exception as update_error:
                    logger.error(
                        f"Error updating existing user: {update_error}", exc_info=True)
                    return jsonify({'error': f'User exists. {str(update_error)}'}), 500
            else:
                logger.error(
                    f"Error creating user: {create_error}", exc_info=True)
                return jsonify({'error': str(create_error)}), 500

        # Verify we have user_id
        if not user_id:
            logger.error("No user_id after create/update")
            return jsonify({'error': 'Failed to obtain user ID'}), 500

        # Store user profile in Supabase database
        db.collection('users').document(user_id).set({
            'id':          user_id,
            'uid':         user_id,
            'email':       email,
            'role':        'user',
            'member_id':   member_id,
            'display_name': display_name,
            'first_login': True,  # Mark as first login - needs email verification
        }, merge=True)

        # Also create record in Supabase users table
        try:
            supabase.table('users').insert({
                'id': user_id,
                'uid': user_id,
                'email': email,
                'role': 'user',
                'first_login': True
            }).execute()
            logger.info(f"Created Supabase users table record for {user_id}")
        except Exception as supabase_error:
            # Log but don't fail if Supabase insert fails
            logger.warning(
                f"Could not create Supabase users record: {supabase_error}")

        # Link uid back to member doc
        db.collection('members').document(member_id).update(
            {'uid': user_id, 'email': email})

        # Generate and send verification code
        from services.email_service import generate_verification_code, store_verification_code, send_verification_email

        verification_code = generate_verification_code()
        store_verification_code(email, verification_code)

        # Print to console with big banner for easy visibility
        print("\n" + "="*70)
        print("🔐 VERIFICATION CODE GENERATED (New Account)")
        print("="*70)
        print(f"📧 Email: {email}")
        print(f"👤 Name:  {display_name}")
        print(f"🔢 Code:  {verification_code}")
        print(f"⏰ Valid for: 15 minutes")
        print("="*70 + "\n")

        # Send verification email
        success, message = send_verification_email(
            email, display_name, verification_code)

        logger.info(f"Verification code sent: {message}")

        # Log audit action
        try:
            admin_email = session.get('email', 'admin')
            admin_uid = session.get('uid', 'unknown')

            log_audit_action(
                supabase=supabase,
                action_type='ACCOUNT_CREATED',
                description=f"Created account for member: {display_name}",
                performed_by=admin_uid,
                performed_by_email=admin_email,
                target_type='account',
                target_id=user_id,
                target_name=display_name,
                metadata={
                    'email': email,
                    'member_id': member_id,
                    'faculty_id': faculty_id
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to log audit action: {audit_err}")

        return jsonify({
            'status': 'ok',
            'uid': user_id,
            'verification_sent': success,
            'message': 'Account created. Verification code sent to email.' if success else 'Account created but email sending failed.'
        })
    except Exception as e:
        logger.error(
            f"Unexpected error in create_member_account: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/members/<member_id>/activity', methods=['GET'])
@login_required
def get_member_activity(member_id):
    """Get daily and monthly activity counts for a member (research, extensions, admin works)."""
    try:
        from collections import defaultdict
        from datetime import datetime as dt, timezone, timedelta

        # Get rolling 12-month period from today
        now = dt.now(timezone.utc)
        end_date = now
        start_date = now.replace(
            day=1) - timedelta(days=330)  # ~11 months back
        start_date = start_date.replace(day=1)  # First day of that month

        # Initialize counters
        daily = defaultdict(
            lambda: {'total': 0, 'research': 0, 'extensions': 0, 'admin': 0})
        monthly = defaultdict(
            lambda: {'total': 0, 'research': 0, 'extensions': 0, 'admin': 0})

        # Helper to parse date
        def parse_date(value):
            if not value:
                return None
            try:
                if isinstance(value, str):
                    return dt.fromisoformat(value.replace('Z', '+00:00'))
                return value
            except:
                return None

        # Helper to check if date is in range
        def is_in_range(date_obj):
            return date_obj and start_date <= date_obj <= end_date

        # Count research submissions
        try:
            research_query = supabase.table('research').select(
                'created_at, member_id').eq('member_id', member_id).execute()
            for item in (research_query.data or []):
                date_obj = parse_date(item.get('created_at'))
                if is_in_range(date_obj):
                    date_str = date_obj.strftime('%Y-%m-%d')
                    month_str = date_obj.strftime('%Y-%m')
                    daily[date_str]['total'] += 1
                    daily[date_str]['research'] += 1
                    monthly[month_str]['total'] += 1
                    monthly[month_str]['research'] += 1
        except Exception as e:
            logger.warning(f'Research query failed: {e}')

        # Also check Firestore research
        try:
            research_docs = db.collection('research').where(
                'member_id', '==', member_id).stream()
            for doc in research_docs:
                data = doc.to_dict()
                date_obj = parse_date(data.get('created_at'))
                if is_in_range(date_obj):
                    date_str = date_obj.strftime('%Y-%m-%d')
                    month_str = date_obj.strftime('%Y-%m')
                    daily[date_str]['total'] += 1
                    daily[date_str]['research'] += 1
                    monthly[month_str]['total'] += 1
                    monthly[month_str]['research'] += 1
        except Exception as e:
            logger.warning(f'Firestore research query failed: {e}')

        # Count extensions submissions
        try:
            ext_query = supabase.table('extensions').select(
                'created_at, member_id').eq('member_id', member_id).execute()
            for item in (ext_query.data or []):
                date_obj = parse_date(item.get('created_at'))
                if is_in_range(date_obj):
                    date_str = date_obj.strftime('%Y-%m-%d')
                    month_str = date_obj.strftime('%Y-%m')
                    daily[date_str]['total'] += 1
                    daily[date_str]['extensions'] += 1
                    monthly[month_str]['total'] += 1
                    monthly[month_str]['extensions'] += 1
        except Exception as e:
            logger.warning(f'Extensions query failed: {e}')

        # Also check Firestore extensions
        try:
            ext_docs = db.collection('extensions').where(
                'member_id', '==', member_id).stream()
            for doc in ext_docs:
                data = doc.to_dict()
                date_obj = parse_date(data.get('created_at'))
                if is_in_range(date_obj):
                    date_str = date_obj.strftime('%Y-%m-%d')
                    month_str = date_obj.strftime('%Y-%m')
                    daily[date_str]['total'] += 1
                    daily[date_str]['extensions'] += 1
                    monthly[month_str]['total'] += 1
                    monthly[month_str]['extensions'] += 1
        except Exception as e:
            logger.warning(f'Firestore extensions query failed: {e}')

        # Count admin works (FSR submissions)
        try:
            fsr_query = supabase.table('fsr_files').select(
                'created_at, member_id, deleted_at').eq('member_id', member_id).execute()
            for item in (fsr_query.data or []):
                if item.get('deleted_at'):
                    continue
                date_obj = parse_date(item.get('created_at'))
                if is_in_range(date_obj):
                    date_str = date_obj.strftime('%Y-%m-%d')
                    month_str = date_obj.strftime('%Y-%m')
                    daily[date_str]['total'] += 1
                    daily[date_str]['admin'] += 1
                    monthly[month_str]['total'] += 1
                    monthly[month_str]['admin'] += 1
        except Exception as e:
            logger.warning(f'FSR query failed: {e}')

        # Collect actual items for timeline (limit to recent 50)
        research_items = []
        extensions_items = []
        admin_items = []

        try:
            research_query = supabase.table('research').select(
                'id, title, created_at').eq('member_id', member_id).order('created_at', desc=True).limit(50).execute()
            research_items = research_query.data or []
        except Exception as e:
            logger.warning(f'Research items query failed: {e}')

        try:
            ext_query = supabase.table('extensions').select(
                'id, title, created_at').eq('member_id', member_id).order('created_at', desc=True).limit(50).execute()
            extensions_items = ext_query.data or []
        except Exception as e:
            logger.warning(f'Extensions items query failed: {e}')

        try:
            fsr_query = supabase.table('fsr_files').select(
                'id, created_at').eq('member_id', member_id).is_('deleted_at', None).order('created_at', desc=True).limit(50).execute()
            admin_items = fsr_query.data or []
        except Exception as e:
            logger.warning(f'FSR items query failed: {e}')

        # Calculate total counts
        total_research = sum(d['research'] for d in daily.values())
        total_extensions = sum(d['extensions'] for d in daily.values())
        total_admin = sum(d['admin'] for d in daily.values())

        # Convert daily data to simple count format for calendar
        daily_counts = {date: data['total'] for date, data in daily.items()}

        return jsonify({
            'daily': daily_counts,
            'monthly': dict(monthly),
            'research_count': total_research,
            'extensions_count': total_extensions,
            'admin_count': total_admin,
            'research': research_items,
            'extensions': extensions_items,
            'admin': admin_items,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

    except Exception as e:
        logger.error(f"get_member_activity error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/verify-code', methods=['POST'])
def verify_email_code():
    """Verify email verification code"""
    try:
        from services.email_service import verify_code

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email', '').strip()
        code = data.get('code', '').strip()

        if not email or not code:
            return jsonify({'error': 'Email and code are required'}), 400

        success, message = verify_code(email, code)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/resend-code', methods=['POST'])
def resend_verification_code():
    """Resend verification code"""
    try:
        from services.email_service import generate_verification_code, store_verification_code, send_verification_email
        from services.supabase_service import supabase

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email', '').strip()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Get user info from Supabase
        try:
            users_response = supabase.auth.admin.list_users()
            user = None

            users_list = []
            if hasattr(users_response, 'data'):
                users_list = users_response.data
            elif hasattr(users_response, '__iter__'):
                users_list = list(users_response)
            else:
                users_list = [users_response]

            for u in users_list:
                user_email = getattr(u, 'email', None) or (
                    u.get('email') if isinstance(u, dict) else None)
                if user_email == email:
                    user = u
                    break

            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Get display name from metadata
            metadata = getattr(user, 'user_metadata', None) or (
                user.get('user_metadata') if isinstance(user, dict) else {})
            display_name = metadata.get('display_name', 'User') if isinstance(
                metadata, dict) else 'User'

        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            return jsonify({'error': 'Failed to fetch user information'}), 500

        # Generate and send new code
        verification_code = generate_verification_code()
        store_verification_code(email, verification_code)

        # Print to console with big banner for easy visibility
        print("\n" + "="*70)
        print("🔐 VERIFICATION CODE GENERATED")
        print("="*70)
        print(f"📧 Email: {email}")
        print(f"🔢 Code:  {verification_code}")
        print(f"⏰ Valid for: 15 minutes")
        print("="*70 + "\n")

        success, message = send_verification_email(
            email, display_name, verification_code)

        if success:
            return jsonify({'success': True, 'message': 'Verification code sent'})
        else:
            return jsonify({'error': message}), 500

    except Exception as e:
        logger.error(f"Error resending code: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/complete-first-login', methods=['POST'])
@login_required
def complete_first_login():
    """
    Mark first login as complete and optionally change password.
    Called after email verification is successful.
    """
    try:
        from services.supabase_service import supabase
        from datetime import datetime, timezone

        data = request.get_json()
        skip_password_change = False

        # Allow empty data (treat as skip)
        if data:
            skip_password_change = data.get('skip_password_change', False)
        else:
            skip_password_change = True

        uid = session.get('uid')
        email = session.get('email')
        role = session.get('role', 'user')

        if not uid:
            return jsonify({'error': 'Not authenticated'}), 401

        # Email is required for Supabase users table
        if not email:
            logger.error(f"Email not in session for uid {uid}")
            # Try to get email from Supabase Auth
            try:
                users_response = supabase.auth.admin.list_users()
                users_list = []
                if hasattr(users_response, 'data'):
                    users_list = users_response.data
                elif hasattr(users_response, '__iter__'):
                    users_list = list(users_response)
                else:
                    users_list = [users_response]

                for user in users_list:
                    user_id = getattr(user, 'id', None) or user.get('id')
                    if user_id == uid:
                        email = getattr(
                            user, 'email', None) or user.get('email')
                        if email:
                            session['email'] = email  # Update session
                            logger.info(
                                f"Retrieved email from Supabase Auth: {email}")
                        break

                if not email:
                    return jsonify({'error': 'Email not found. Please log in again.'}), 400
            except Exception as e:
                logger.error(f"Failed to retrieve email: {e}")
                return jsonify({'error': 'Unable to complete setup. Please log in again.'}), 400

        # Optional: Change password (only if not skipping and password provided)
        new_password = data.get('new_password', '').strip() if data else ''
        if new_password and not skip_password_change:
            if len(new_password) < 6:
                return jsonify({'error': 'Password must be at least 6 characters'}), 400

            try:
                supabase.auth.admin.update_user_by_id(
                    uid,
                    {"password": new_password}
                )
                logger.info(f"Password changed for user {uid}")
            except Exception as e:
                logger.error(f"Error changing password: {e}")
                return jsonify({'error': 'Failed to change password'}), 500

        # Ensure Supabase users table has proper uid set
        try:
            # Use UPSERT to handle both insert and update cases
            # This prevents duplicate key errors and ensures uid is always set
            supabase.table('users').upsert({
                'id': uid,  # Primary key - Set id to match auth user id
                'uid': uid,  # Also set uid for consistency
                'email': email,
                'role': role,
                'first_login': False
            }, on_conflict='id').execute()
            logger.info(f"Upserted Supabase users record for {uid}")
        except Exception as e:
            logger.error(f"Error upserting Supabase users table: {e}")
            # Try alternative approach - update if exists, insert if not
            try:
                # First try update
                result = supabase.table('users').update({
                    'uid': uid,
                    'email': email,
                    'role': role,
                    'first_login': False
                }).eq('id', uid).execute()

                # If no rows affected, insert
                if not result.data:
                    supabase.table('users').insert({
                        'id': uid,
                        'uid': uid,
                        'email': email,
                        'role': role,
                        'first_login': False
                    }).execute()
                logger.info(f"Fallback upsert successful for {uid}")
            except Exception as fallback_error:
                logger.error(f"Fallback upsert also failed: {fallback_error}")
                # Continue anyway - Firebase update is more critical

        # Mark first login as complete in Firebase
        db.collection('users').document(uid).set({
            'first_login': False,
            'setup_completed_at': datetime.now(timezone.utc).isoformat()
        }, merge=True)

        # Send welcome email
        from services.email_service import send_welcome_email

        # Get faculty ID from metadata
        try:
            users_response = supabase.auth.admin.list_users()
            current_user = None

            users_list = []
            if hasattr(users_response, 'data'):
                users_list = users_response.data
            elif hasattr(users_response, '__iter__'):
                users_list = list(users_response)
            else:
                users_list = [users_response]

            for user in users_list:
                if (getattr(user, 'id', None) or user.get('id')) == uid:
                    current_user = user
                    break

            if current_user:
                metadata = getattr(current_user, 'user_metadata', None) or (
                    current_user.get('user_metadata') if isinstance(current_user, dict) else {})
                display_name = metadata.get('display_name', 'User') if isinstance(
                    metadata, dict) else 'User'
                faculty_id = metadata.get(
                    'faculty_id', 'N/A') if isinstance(metadata, dict) else 'N/A'
            else:
                display_name = 'User'
                faculty_id = 'N/A'
        except:
            display_name = 'User'
            faculty_id = 'N/A'

        send_welcome_email(email, display_name, faculty_id)

        return jsonify({
            'success': True,
            'message': 'First login setup completed successfully'
        })

    except Exception as e:
        logger.error(f"Error completing first login: {e}")
        return jsonify({'error': str(e)}), 500


# ── Audit Log API ─────────────────────────────────────────────

@app.route('/api/audit-log', methods=['GET'])
@login_required
def get_audit_logs():
    """
    Get recent audit logs for admin notifications.
    Query params:
    - unread: 'true' to filter only unread logs
    - limit: number of logs to return (default: 7)
    """
    try:
        # Only admins can view audit logs
        role = session.get('role')
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        unread_only = request.args.get('unread', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 7))

        logs = get_recent_audit_logs(
            supabase, limit=limit, unread_only=unread_only)

        return jsonify({
            'status': 'ok',
            'logs': logs,
            'count': len(logs)
        })

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit-log/<log_id>/read', methods=['POST'])
@login_required
def mark_log_as_read(log_id):
    """Mark a single audit log as read."""
    try:
        # Only admins can mark logs as read
        role = session.get('role')
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        success = mark_audit_log_as_read(supabase, log_id)

        if success:
            return jsonify({'status': 'ok', 'message': 'Marked as read'})
        else:
            return jsonify({'error': 'Failed to mark as read'}), 500

    except Exception as e:
        logger.error(f"Error marking log as read: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit-log/mark-all-read', methods=['POST'])
@login_required
def mark_all_logs_read():
    """Mark all audit logs as read."""
    try:
        # Only admins can mark logs as read
        role = session.get('role')
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        count = mark_all_audit_logs_as_read(supabase)

        return jsonify({
            'status': 'ok',
            'message': f'Marked {count} logs as read',
            'count': count
        })

    except Exception as e:
        logger.error(f"Error marking all logs as read: {e}")
        return jsonify({'error': str(e)}), 500


# ── Courses API ───────────────────────────────────────────────
# Note: Main courses API endpoints are defined later in the file (line ~3304)
# This section is intentionally empty to avoid duplicate route definitions

# ── Research API ──────────────────────────────────────────────

@app.route('/api/research', methods=['GET'])
@login_required
def get_research():
    """Get all research papers for the current logged-in member OR all research for admin."""
    try:
        from services.supabase_service import supabase

        uid = session.get('uid')
        role = session.get('role')
        member_id = request.args.get('member_id')

        print(
            f"🔍 GET Research - UID from session: {uid}, Role: {role}, Member filter: {member_id}")

        if not uid:
            print("❌ No UID in session!")
            return jsonify({'error': 'Not authenticated'}), 401

        # Check if user is admin
        is_admin = role == 'admin'
        print(f"🔐 Is admin: {is_admin}")

        if is_admin:
            # Admin can filter by member_id or see all research
            if member_id:
                print(
                    f"📚 Fetching research for member: {member_id} (admin view)...")
                response = supabase.table('research').select(
                    '*').eq('member_id', member_id).execute()
            else:
                print("📚 Fetching ALL research (admin view)...")
                response = supabase.table('research').select('*').execute()
        else:
            # Find member_id from uid
            member_response = supabase.table('members').select(
                'id').eq('uid', uid).execute()
            if not member_response.data:
                return jsonify({'error': 'Member not found'}), 404
            member_id = member_response.data[0]['id']

            print(
                f"📚 Fetching research for member_id: {member_id} (member view)...")
            response = supabase.table('research').select(
                '*').eq('member_id', member_id).execute()

        research_list = response.data or []

        for item in research_list:
            print(f"  📄 Research: {item.get('title', 'N/A')}")

        print(f"✅ Found {len(research_list)} research items")
        print(f"📤 Returning {len(research_list)} research items to client")

        return jsonify(research_list)

    except Exception as e:
        print(f"❌ Error fetching research: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/research', methods=['POST'])
@login_required
def add_research():
    """Add a new research paper for the current member."""
    try:
        from services.supabase_service import supabase
        from datetime import datetime

        uid = session.get('uid')
        print(f"🔍 Add research - UID from session: {uid}")

        if not uid:
            print("❌ No UID in session!")
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json()
        print(f"📥 Received data: {data}")

        # Find member by uid
        member_response = supabase.table(
            'members').select('*').eq('uid', uid).execute()
        if not member_response.data:
            print(f"❌ Member not found for UID: {uid}")
            return jsonify({'error': 'Member not found'}), 404

        member = member_response.data[0]
        member_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
        )
        print(f"✅ Found member: {member_name} (ID: {member.get('id')})")

        # Prepare research document
        research_doc = {
            'uid': uid,  # Add uid field required by database
            'member_id': member['id'],
            'member_name': member_name,
            'research_type': data.get('research_type'),
            'title': data.get('title', ''),
            'role': data.get('role', ''),
            'co_workers': data.get('co_workers', ''),
            'co_authors': data.get('co_authors', ''),
            'start_date': data.get('start_date') or None,
            'end_date': data.get('end_date') or None,
            'date_completion': data.get('date_completion') or None,
            'funding_agency': data.get('funding_agency', ''),
            'credit_units': data.get('credit_units', ''),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        # Insert into Supabase
        print(f"📄 Inserting research into Supabase...")
        insert_response = supabase.table(
            'research').insert(research_doc).execute()

        if not insert_response.data:
            raise Exception("Failed to insert research")

        new_research = insert_response.data[0]
        print(f"✅ Research added with ID: {new_research.get('id')}")

        return jsonify(new_research), 201

    except Exception as e:
        print(f"❌ Error adding research: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/research/<research_id>', methods=['DELETE'])
@login_required
def delete_research(research_id):
    """Delete a research paper."""
    try:
        from services.supabase_service import supabase

        uid = session.get('uid')
        print(f"🗑️ Delete research - ID: {research_id}, UID: {uid}")

        if not uid:
            print("❌ Not authenticated")
            return jsonify({'error': 'Not authenticated'}), 401

        # Verify ownership by checking member_id
        print(f"🔍 Checking if research exists...")
        research_response = supabase.table('research').select(
            '*').eq('id', research_id).execute()

        if not research_response.data:
            print(f"❌ Research not found: {research_id}")
            return jsonify({'error': 'Research not found'}), 404

        research = research_response.data[0]

        # Get member_id from uid
        member_response = supabase.table('members').select(
            'id').eq('uid', uid).execute()
        if not member_response.data:
            return jsonify({'error': 'Member not found'}), 404
        member_id = member_response.data[0]['id']

        print(
            f"📝 Research member_id: {research.get('member_id')}, Session member_id: {member_id}")

        if research.get('member_id') != member_id:
            print("❌ Unauthorized - member_id mismatch")
            return jsonify({'error': 'Unauthorized'}), 403

        print(f"🗑️ Deleting research...")
        supabase.table('research').delete().eq('id', research_id).execute()
        print(f"✅ Research deleted successfully")

        return jsonify({'status': 'ok'})

    except Exception as e:
        print(f"❌ Error deleting research: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── Extensions API ──────────────────────────────────────────────

@app.route('/api/extensions', methods=['GET'])
@login_required
def get_extensions():
    """Get all extension activities for the current logged-in member OR filtered by member_id for admin."""
    try:
        uid = session.get('uid')
        role = session.get('role')
        # Optional filter by member_id
        member_id = request.args.get('member_id')

        if not uid:
            return jsonify({'error': 'Not authenticated'}), 401

        # Check if user is admin
        is_admin = False
        if role == 'admin':
            is_admin = True
        else:
            user_doc = db.collection('users').where(
                'uid', '==', uid).limit(1).stream()
            user_list = [d.to_dict() for d in user_doc]
            is_admin = user_list and user_list[0].get('role') == 'admin'

        # Get extensions based on admin status and filter
        if is_admin and member_id:
            # Admin filtering by specific member
            docs = db.collection('extensions').where(
                'uid', '==', member_id).stream()
        elif is_admin:
            # Admin viewing all extensions
            docs = db.collection('extensions').stream()
        else:
            # Regular member viewing own extensions
            docs = db.collection('extensions').where('uid', '==', uid).stream()

        extensions_list = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            extensions_list.append(data)

        # Sort in Python instead of Firestore
        extensions_list.sort(
            key=lambda x: x.get('created_at', ''), reverse=True)

        return jsonify(extensions_list)
    except Exception as e:
        print(f"Error fetching extensions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extensions', methods=['POST'])
@login_required
def add_extension():
    """Add a new extension activity for the current member."""
    try:
        from services.supabase_service import supabase
        from datetime import datetime

        uid = session.get('uid')
        print(f"🔍 Add extension - UID from session: {uid}")

        if not uid:
            print("❌ No UID in session!")
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json()
        print(f"📥 Received extension data: {data}")

        # Find member by uid
        member_response = supabase.table(
            'members').select('*').eq('uid', uid).execute()
        if not member_response.data:
            print(f"❌ Member not found for UID: {uid}")
            return jsonify({'error': 'Member not found'}), 404

        member = member_response.data[0]
        member_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
        )
        print(f"✅ Found member: {member_name} (ID: {member.get('id')})")

        # Prepare extension document
        extension_doc = {
            'uid': uid,  # Add uid field required by database
            'member_id': member['id'],
            'member_name': member_name,
            'extension_type': data.get('extension_type'),
            'title': data.get('title', ''),
            'role': data.get('role', ''),
            'co_workers': data.get('co_workers', ''),
            'participants': data.get('participants', ''),
            'hours': data.get('hours', ''),
            'duration': data.get('duration', ''),
            'start_date': data.get('start_date') or None,
            'end_date': data.get('end_date') or None,
            'funding_agency': data.get('funding_agency', ''),
            'credit_units': data.get('credit_units', ''),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        # Insert into Supabase
        print(f"📄 Inserting extension into Supabase...")
        insert_response = supabase.table(
            'extensions').insert(extension_doc).execute()

        if not insert_response.data:
            raise Exception("Failed to insert extension")

        new_extension = insert_response.data[0]
        print(f"✅ Extension added with ID: {new_extension.get('id')}")

        return jsonify(new_extension), 201

    except Exception as e:
        print(f"❌ Error adding extension: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/extensions/<extension_id>', methods=['DELETE'])
@login_required
def delete_extension(extension_id):
    """Delete an extension activity."""
    try:
        from services.supabase_service import supabase

        uid = session.get('uid')
        print(f"🗑️ Delete extension - ID: {extension_id}, UID: {uid}")

        if not uid:
            print("❌ Not authenticated")
            return jsonify({'error': 'Not authenticated'}), 401

        # Verify ownership by checking member_id
        print(f"🔍 Checking if extension exists...")
        extension_response = supabase.table('extensions').select(
            '*').eq('id', extension_id).execute()

        if not extension_response.data:
            print(f"❌ Extension not found: {extension_id}")
            return jsonify({'error': 'Extension not found'}), 404

        extension = extension_response.data[0]

        # Get member to verify ownership
        member_response = supabase.table(
            'members').select('*').eq('uid', uid).execute()
        if not member_response.data:
            print(f"❌ Member not found for UID: {uid}")
            return jsonify({'error': 'Unauthorized'}), 403

        member = member_response.data[0]

        if extension.get('member_id') != member['id']:
            print(
                f"❌ Member mismatch: extension.member_id={extension.get('member_id')}, member.id={member['id']}")
            return jsonify({'error': 'Unauthorized'}), 403

        # Delete from Supabase
        print(f"🗑️ Deleting extension from Supabase...")
        delete_response = supabase.table('extensions').delete().eq(
            'id', extension_id).execute()
        print(f"✅ Extension deleted")

        return jsonify({'status': 'ok'})

    except Exception as e:
        print(f"❌ Error deleting extension: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── Admin Extensions API ──────────────────────────────────────────────

@app.route('/api/admin/extensions', methods=['GET'])
@login_required
def get_all_extensions():
    """Get all extension activities from all members (admin view)."""
    try:
        # Get all extensions without filter
        docs = db.collection('extensions').stream()
        extensions_list = []

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            extensions_list.append(data)

        # Sort in Python instead of Firestore (by submission date, most recent first)
        extensions_list.sort(
            key=lambda x: x.get('created_at', ''), reverse=True)

        return jsonify(extensions_list)
    except Exception as e:
        print(f"Error fetching all extensions: {e}")
        return jsonify({'error': str(e)}), 500


# ── FSR Generation API ──────────────────────────────────────────────

@app.route('/api/generate-fsr/<member_id>', methods=['POST'])
@login_required
def generate_fsr(member_id):
    """Generate Faculty Service Record for a member."""
    try:
        from services.fsr_generator import generate_member_fsr

        data = request.get_json() or {}
        semester = data.get('semester', '2nd Semester')
        academic_year = data.get('academic_year', '2025-2026')

        logger.info(
            f"Generating FSR for member {member_id}, semester: {semester}, year: {academic_year}")

        # Generate FSR - returns file metadata dict with download_url
        result = generate_member_fsr(member_id, semester, academic_year)

        logger.info(f"FSR generated successfully: {result}")

        # Return the download URL for client to fetch
        if isinstance(result, dict) and 'download_url' in result:
            return jsonify({
                'success': True,
                'download_url': result['download_url'],
                'file_name': result.get('file_name', 'FSR.xlsx')
            })
        elif isinstance(result, dict):
            # New behavior: returns metadata dict
            return jsonify(result), 200
        else:
            # Fallback for old behavior (if local file path returned)
            from flask import send_file
            return send_file(
                result,
                as_attachment=True,
                download_name=os.path.basename(result),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    except Exception as e:
        logger.error(f"Error generating FSR: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-fsr-all', methods=['POST'])
@login_required
def generate_fsr_all():
    """Generate FSR for all members (admin only)."""
    try:
        from services.fsr_generator import FSRGenerator
        import zipfile
        from io import BytesIO

        data = request.get_json() or {}
        semester = data.get('semester', '2nd Semester')
        academic_year = data.get('academic_year', '2025-2026')

        # Get all members
        members = db.collection('members').stream()

        # Create zip file in memory
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            generator = FSRGenerator()

            for member_doc in members:
                member_id = member_doc.id
                try:
                    fsr_path = generator.generate_fsr_for_member(
                        member_id, semester, academic_year)
                    # Add to zip
                    zf.write(fsr_path, os.path.basename(fsr_path))
                    # Clean up individual file
                    os.remove(fsr_path)
                except Exception as e:
                    print(f"Error generating FSR for member {member_id}: {e}")
                    continue

        memory_file.seek(0)

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f'FSR_All_Members_{timestamp}.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        print(f"Error generating FSR for all members: {e}")
        return jsonify({'error': str(e)}), 500


# ── FSR Footnotes API ──────────────────────────────────────────────

@app.route('/api/fsr-footnotes', methods=['POST'])
@login_required
def save_fsr_footnotes():
    """Save FSR footnotes for a member."""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        semester = data.get('semester')
        academic_year = data.get('academic_year')
        footnotes = data.get('footnotes', [])

        if not member_id or not semester or not academic_year:
            return jsonify({'error': 'Missing required fields'}), 400

        # Delete existing footnotes for this member/semester/year
        supabase.table('fsr_footnotes').delete().eq(
            'member_id', member_id
        ).eq('semester', semester).eq('academic_year', academic_year).execute()

        # Insert new footnotes
        if footnotes:
            footnotes_to_insert = []
            for fn in footnotes:
                footnotes_to_insert.append({
                    'member_id': member_id,
                    'semester': semester,
                    'academic_year': academic_year,
                    'footnote_number': fn['number'],
                    'footnote_type': fn['type'],
                    'faculty_name': fn['faculty_name'],
                    'subject': fn.get('subject', ''),
                    'load_sharing': fn.get('load_sharing', '')
                })

            supabase.table('fsr_footnotes').insert(
                footnotes_to_insert).execute()

        return jsonify({
            'success': True,
            'message': 'Footnotes saved successfully'
        })

    except Exception as e:
        logger.error(f"Error saving FSR footnotes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/fsr-footnotes/<member_id>', methods=['GET'])
@login_required
def get_fsr_footnotes(member_id):
    """Get FSR footnotes for a member."""
    try:
        semester = request.args.get('semester', '2nd Semester')
        academic_year = request.args.get('academic_year', '2025-2026')

        # Extract semester number (e.g., "1st Semester" -> "1")
        sem_num = semester.split()[0][0]

        # Get footnotes with retry logic for network timeouts
        max_retries = 3
        retry_delay = 1
        footnotes_result = None

        for attempt in range(max_retries):
            try:
                footnotes_result = supabase.table('fsr_footnotes').select(
                    'footnote_number, footnote_type, faculty_name, subject, load_sharing'
                ).eq('member_id', member_id).eq(
                    'semester', sem_num
                ).eq('academic_year', academic_year).order('footnote_number').execute()
                break  # Success, exit retry loop
            except Exception as retry_error:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"FSR footnotes attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise  # Final attempt failed, re-raise

        return jsonify({
            'success': True,
            'footnotes': footnotes_result.data if footnotes_result else []
        })

    except Exception as e:
        logger.error(f"Error getting FSR footnotes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ── Schedule API ──────────────────────────────────────────────

@app.route('/api/schedules/generated', methods=['GET'])
@login_required
def get_generated_schedules():
    """Get generated schedules from generated_schedules table (for review before saving)."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')

        if not school_year or not semester:
            return jsonify({'success': False, 'message': 'School year and semester required'}), 400

        # Query generated_schedules table
        result = supabase.table('generated_schedules').select('*').eq(
            'school_year', school_year).eq('semester', semester).execute()

        schedules = []
        for row in result.data:
            schedules.append({
                'id': row.get('id'),
                'subj_code': row.get('subj_code'),
                'subjCode': row.get('subj_code'),  # Legacy format
                'subj_name': row.get('subj_name'),
                'subjName': row.get('subj_name'),  # Legacy format
                'prof': row.get('prof'),
                'room': row.get('room'),
                'section': row.get('section'),
                'units': row.get('units'),
                'day': row.get('day'),
                'start': row.get('start_time'),
                'start_time': row.get('start_time'),
                'end': row.get('end_time'),
                'end_time': row.get('end_time'),
                'type': row.get('type'),
                'school_year': row.get('school_year'),
                'schoolYear': row.get('school_year'),  # Legacy format
                'semester': row.get('semester'),
                'generation_session_id': row.get('generation_session_id'),
                'ga_fitness_score': row.get('ga_fitness_score'),
            })

        return jsonify({'success': True, 'schedules': schedules, 'count': len(schedules)})

    except Exception as e:
        logger.error(f"Error fetching generated schedules: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/api/schedules', methods=['GET'])
@login_required
def get_schedules():
    """Return all schedule entries from Supabase. Optionally filter by professor name."""
    max_retries = 3
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Get filter parameters
            prof_filter = request.args.get('prof', '').strip().lower()
            semester = request.args.get('semester', '').strip()
            school_year = request.args.get('schoolYear', '').strip()

            # Build Supabase query
            query = supabase.table('schedules').select('*').order('created_at')

            # Apply semester filter if provided
            if semester:
                query = query.eq('semester', semester)

            # Apply school year filter if provided
            if school_year:
                query = query.eq('school_year', school_year)

            # Execute query
            result = query.execute()

            def format_time(time_str):
                if time_str and ':' in str(time_str):
                    parts = str(time_str).split(':')
                    return f"{parts[0]}:{parts[1]}"
                return time_str

            entries = []
            for data in result.data:
                entry = {
                    'id': data.get('id'),
                    'prof': data.get('prof'),
                    'subjCode': data.get('subj_code', data.get('subjCode')),
                    'subjName': data.get('subj_name', data.get('subjName')),
                    'type': data.get('type'),
                    'day': data.get('day'),
                    'start': format_time(data.get('start')),
                    'end': format_time(data.get('end')),
                    'room': data.get('room'),
                    'units': data.get('units'),
                    'section': data.get('section'),
                    'year': data.get('year'),
                    'semester': data.get('semester'),
                    'schoolYear': data.get('school_year', data.get('schoolYear')),
                    'source': data.get('source') or '',
                    'created_at': data.get('created_at')
                }

                # Optional professor filter (case-insensitive partial match)
                if prof_filter:
                    entry_prof = (entry.get('prof') or '').lower()
                    if prof_filter not in entry_prof:
                        continue

                entries.append(entry)

            logger.info(f"Found {len(entries)} schedules from Supabase")

            # Detailed logging for debugging
            print("\n" + "="*80)
            print(f"📊 GET /api/schedules - Returning {len(entries)} schedules")
            print("="*80)
            for i, entry in enumerate(entries, 1):
                print(f"{i}. {entry.get('subjCode')} | Day: {entry.get('day')} | Time: {entry.get('start')}-{entry.get('end')} | Section: {entry.get('section')} | Prof: {entry.get('prof')}")
            print("="*80 + "\n")

            return jsonify(entries)

        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(
                    f"Get schedules retry {retry_count}/{max_retries}: {e}")
                import time
                time.sleep(0.5 * retry_count)  # Exponential backoff
                continue
            else:
                logger.error(
                    f"Get schedules error after {max_retries} retries: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(last_error)}), 500


@app.route('/api/schedules', methods=['POST'])
@login_required
def add_schedule():
    """Add a single schedule entry (manual mode) - SUPABASE VERSION."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        required = ['prof', 'subjCode', 'subjName', 'day',
                    'start', 'end', 'room', 'units', 'section']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing field: {field}'}), 400

        entry_id = str(uuid.uuid4())

        # Save to Supabase with snake_case
        entry_db = {
            'id':        entry_id,
            'prof':      data['prof'],
            'subj_code': data['subjCode'],
            'subj_name': data['subjName'],
            'type':      data.get('type', 'Lecture'),
            'day':       data['day'],
            'start':     data['start'],
            'end':       data['end'],
            'room':      data['room'],
            'units':     int(data['units']),
            'section':   data['section'],
            'year':      data.get('year', '1'),
            'semester':  data.get('semester', '1'),
            'school_year': data.get('schoolYear') or f"{datetime.now(timezone.utc).year}-{datetime.now(timezone.utc).year + 1}",
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        # Insert into Supabase
        result = supabase.table('schedules').insert(entry_db).execute()

        if not result.data:
            return jsonify({'error': 'Failed to insert schedule.'}), 500

        # Return with camelCase (frontend expects)
        entry_response = {
            'id':        entry_id,
            'prof':      data['prof'],
            'subjCode':  data['subjCode'],
            'subjName':  data['subjName'],
            'type':      data.get('type', 'Lecture'),
            'day':       data['day'],
            'start':     data['start'],
            'end':       data['end'],
            'room':      data['room'],
            'units':     int(data['units']),
            'section':   data['section'],
            'year':      data.get('year', '1'),
            'semester':  data.get('semester', '1'),
            'schoolYear': entry_db['school_year'],
            'created_at': entry_db['created_at'],
        }

        logger.info(
            f"✅ Added schedule {entry_id}: {data['prof']} - {data['subjCode']}")
        return jsonify(entry_response), 201

    except Exception as e:
        logger.error(f"Add schedule error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
        return jsonify({'status': 'ok', 'id': entry_id, 'entry': entry_response}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/<entry_id>', methods=['DELETE'])
@login_required
def delete_schedule(entry_id):
    """Delete a single schedule entry - SUPABASE VERSION."""
    try:
        # Check if exists
        existing = supabase.table('schedules').select(
            'id').eq('id', entry_id).execute()
        if not existing.data or len(existing.data) == 0:
            return jsonify({'error': 'Not found.'}), 404

        # Delete from Supabase
        result = supabase.table('schedules').delete().eq(
            'id', entry_id).execute()

        logger.info(f"Deleted schedule {entry_id}")
        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Delete schedule error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/<entry_id>', methods=['PUT'])
@login_required
def update_schedule(entry_id):
    """Update an existing schedule entry (for moving blocks) - SUPABASE VERSION."""
    try:
        # Check if schedule exists
        existing = supabase.table('schedules').select(
            '*').eq('id', entry_id).execute()
        if not existing.data or len(existing.data) == 0:
            return jsonify({'error': 'Schedule not found.'}), 404

        # Get the update data from request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        # Build update payload with only provided fields
        update_data = {}
        if 'day' in data:
            update_data['day'] = data['day']
        if 'start' in data:
            update_data['start'] = data['start']
        if 'end' in data:
            update_data['end'] = data['end']
        if 'room' in data:
            update_data['room'] = data['room']
        if 'units' in data:
            update_data['units'] = data['units']

        if not update_data:
            return jsonify({'error': 'No valid fields to update.'}), 400

        # Update in Supabase
        result = supabase.table('schedules').update(
            update_data).eq('id', entry_id).execute()

        if not result.data:
            return jsonify({'error': 'Update failed.'}), 500

        logger.info(f"Updated schedule {entry_id}: {update_data}")
        return jsonify({'status': 'ok', 'id': entry_id, 'updated': update_data})

    except Exception as e:
        logger.error(f"Update schedule error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/batch-save', methods=['POST'])
@login_required
def batch_save_schedules():
    """
    Batch save schedules - deletes old schedules for the semester/year and saves all new ones atomically.
    This replaces individual POST/PUT/DELETE calls with a single transaction-like operation.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        schedules_to_save = data.get('schedules', [])
        school_year = data.get('school_year')
        semester = data.get('semester')
        professor = data.get('professor')  # Optional: filter by professor

        if not school_year or not semester:
            return jsonify({'error': 'school_year and semester are required'}), 400

        logger.info(
            f"📦 Batch save: {len(schedules_to_save)} schedules for {school_year} sem {semester}")

        # STEP 1: Delete existing schedules for this semester/year (and optionally professor)
        delete_query = supabase.table('schedules').delete().eq(
            'school_year', school_year).eq('semester', semester)

        if professor:
            # Delete only for specific professor
            delete_query = delete_query.eq('prof', professor)

        delete_result = delete_query.execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        logger.info(
            f"🗑️  Deleted {deleted_count} existing schedules")

        # STEP 2: Insert all new schedules
        if schedules_to_save:
            # Ensure all schedules have required fields (check both camelCase and snake_case)
            for schedule in schedules_to_save:
                # Check for required fields (accepting both naming conventions)
                has_prof = 'prof' in schedule
                has_subj_code = 'subjCode' in schedule or 'subj_code' in schedule
                has_subj_name = 'subjName' in schedule or 'subj_name' in schedule
                has_day = 'day' in schedule
                has_start = 'start' in schedule
                has_end = 'end' in schedule
                has_room = 'room' in schedule
                has_section = 'section' in schedule
                has_type = 'type' in schedule

                if not (has_prof and has_subj_code and has_subj_name and has_day and has_start and has_end and has_room and has_section and has_type):
                    logger.error(f"Missing fields in schedule: {schedule}")
                    return jsonify({'error': 'Missing required fields in schedule'}), 400

                # Normalize to snake_case (database format)
                if 'subjCode' in schedule:
                    schedule['subj_code'] = schedule['subjCode']
                    del schedule['subjCode']
                if 'subjName' in schedule:
                    schedule['subj_name'] = schedule['subjName']
                    del schedule['subjName']
                if 'schoolYear' in schedule:
                    schedule['school_year'] = schedule['schoolYear']
                    del schedule['schoolYear']

                # Ensure school_year and semester are set
                schedule['school_year'] = school_year
                schedule['semester'] = semester

            # Batch insert all schedules
            insert_result = supabase.table('schedules').insert(
                schedules_to_save).execute()

            if not insert_result.data:
                return jsonify({'error': 'Batch insert failed'}), 500

            saved_count = len(insert_result.data)
            logger.info(f"Saved {saved_count} schedules")

            return jsonify({
                'status': 'ok',
                'deleted': deleted_count,
                'saved': saved_count,
                'schedules': insert_result.data
            })
        else:
            # No schedules to save, just return success
            logger.info(f"Cleared schedules (no new schedules to save)")
            return jsonify({
                'status': 'ok',
                'deleted': deleted_count,
                'saved': 0,
                'schedules': []
            })

    except Exception as e:
        logger.error(f"Batch save error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/clear', methods=['POST'])
@login_required
def clear_schedules():
    """Delete all schedule entries (used before saving a GA result) - SUPABASE VERSION."""
    try:
        # Get current semester and school year from request or use defaults
        data = request.get_json() or {}
        semester = data.get('semester')
        school_year = data.get('school_year')

        # Build delete query
        query = supabase.table('schedules').delete()

        # If semester/school_year provided, delete only those
        if semester:
            # Need to select first, then delete by IDs (Supabase limitation)
            schedules_to_delete = supabase.table(
                'schedules').select('id').eq('semester', semester)
            if school_year:
                schedules_to_delete = schedules_to_delete.eq(
                    'schoolYear', school_year)
            result = schedules_to_delete.execute()

            if result.data:
                for sched in result.data:
                    supabase.table('schedules').delete().eq(
                        'id', sched['id']).execute()
                logger.info(
                    f"🗑️ Deleted {len(result.data)} schedules for semester {semester}, year {school_year}")
        else:
            # Delete all schedules (no filter)
            all_schedules = supabase.table('schedules').select('id').execute()
            if all_schedules.data:
                for sched in all_schedules.data:
                    supabase.table('schedules').delete().eq(
                        'id', sched['id']).execute()
                logger.info(
                    f"🗑️ Deleted all {len(all_schedules.data)} schedules")

        return jsonify({'status': 'ok', 'message': 'Schedules cleared'})
    except Exception as e:
        logger.error(f"Clear schedules error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/generate', methods=['POST'])
@login_required
def generate_schedule():
    """Run the genetic algorithm and return the generated schedule."""
    try:
        from services.scheduler_service import run_ga
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        subjects = data.get('subjects', [])
        rooms = data.get('rooms', [])
        prof_availability = data.get('prof_availability', {})
        constraints = data.get('constraints', {})

        if not subjects:
            return jsonify({'error': 'No subjects provided.'}), 400

        result = run_ga(
            subjects=subjects,
            rooms=rooms,
            prof_availability=prof_availability,
            constraints=constraints,
        )
        return jsonify({'status': 'ok', 'schedule': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Async GA Schedule Generation API ──────────────────────────────────────────────

@app.route('/api/schedule/ga-generate-async', methods=['POST'])
@login_required
def api_ga_generate_async():
    """
    Start an asynchronous GA schedule generation run.
    Simplified version that works with current scheduler_service.

    Body: {
        "reference_semester": "1"|"2",
        "reference_school_year": "2026-2027",
        "target_semester": "1"|"2",
        "target_school_year": "2026-2027",
        "save_to_db": true|false
    }
    Returns: { "session_id": str, "message": str }
    """
    try:
        data = request.get_json(silent=True) or {}

        # Generate a unique session ID
        import uuid
        session_id = str(uuid.uuid4())

        # For now, return a mock response indicating the feature is being implemented
        # TODO: Implement full async GA generation
        return jsonify({
            'session_id': session_id,
            'message': 'Schedule generation starting (feature in development)',
            'status': 'started',
            'note': 'Full GA async implementation pending'
        })

    except Exception as e:
        logger.error(f"GA async generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/ga-status/<session_id>', methods=['GET'])
@login_required
def api_ga_status(session_id):
    """
    Get the status of an async GA generation run.
    Mock implementation until full GA async is implemented.

    Returns: {
        "status": "running"|"completed"|"failed"|"not_found",
        "progress": GAProgress dict (if running),
        "result": dict (if completed),
        "error": str (if failed)
    }
    """
    try:
        # Mock implementation - always return "not implemented" status
        return jsonify({
            'status': 'failed',
            'error': 'Async GA generation is currently under development',
            'message': 'Please use the synchronous generation endpoint for now',
            'note': 'Full async implementation with progress tracking coming soon'
        }), 501  # 501 = Not Implemented

    except Exception as e:
        logger.error(f"GA status check error: {e}")
        return jsonify({'status': 'failed', 'error': str(e)}), 500


@app.route('/api/schedule/ga-cancel/<session_id>', methods=['POST'])
@login_required
def api_ga_cancel(session_id):
    """
    Cancel a running GA generation session.
    Sets the cancellation flag in _active_ga_runs.

    Returns: { "status": "cancelled"|"not_found", "message": str }
    """
    try:
        from services.scheduler_service import _active_ga_runs

        if session_id not in _active_ga_runs:
            return jsonify({'status': 'not_found', 'message': 'Session not found or already completed.'}), 404

        run_info = _active_ga_runs[session_id]

        if run_info['status'] == 'running':
            # Set cancellation flag (GA loop checks this)
            run_info['cancel_requested'] = True
            return jsonify({
                'status': 'cancelling',
                'message': 'Cancellation requested. Generation will stop after current generation.'
            })
        else:
            return jsonify({
                'status': run_info['status'],
                'message': f"Cannot cancel - session is {run_info['status']}."
            })

    except Exception as e:
        logger.error(f"GA cancellation error: {e}")
        return jsonify({'error': str(e)}), 500


# ── Configured Subjects API ──────────────────────────────────────────────
@app.route('/api/configured-subjects', methods=['GET'])
@login_required
def get_configured_subjects():
    """Get all configured subjects for a specific school year and semester."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')

        if not school_year or not semester:
            return jsonify({'error': 'school_year and semester are required'}), 400

        logger.info(
            f"Fetching configured subjects for {school_year}, semester {semester}")

        # Use direct Supabase query
        try:
            response = supabase.table('configured_subjects')\
                .select('*')\
                .eq('school_year', school_year)\
                .eq('semester', semester)\
                .execute()

            subjects = []
            for data in (response.data or []):
                subjects.append({
                    'id': data.get('id'),
                    'subjCode': data.get('subj_code'),
                    'subjName': data.get('subj_name'),
                    'prof': data.get('prof'),
                    'section': data.get('section'),
                    'units': data.get('units'),
                    'school_year': data.get('school_year'),
                    'semester': data.get('semester')
                })

            logger.info(f"Found {len(subjects)} configured subjects")
            return jsonify(subjects)
        except Exception as table_error:
            # Table might not exist yet, return empty list
            logger.warning(f"Table might not exist yet: {table_error}")
            return jsonify([])

    except Exception as e:
        logger.error(f"Error fetching configured subjects: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/configured-subjects', methods=['POST'])
@login_required
def save_configured_subject():
    """Save a configured subject (unscheduled subject from staging area)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        logger.info(f"Saving configured subject: {data}")

        required = ['subjCode', 'subjName', 'prof',
                    'section', 'units', 'school_year', 'semester']
        for field in required:
            if not data.get(field):
                logger.error(f"Missing required field: {field}")
                return jsonify({'error': f'Missing field: {field}'}), 400

        # Check if entry already exists (to avoid duplicates)
        existing = supabase.table('configured_subjects')\
            .select('id')\
            .eq('subj_code', data['subjCode'])\
            .eq('prof', data['prof'])\
            .eq('school_year', data['school_year'])\
            .eq('semester', data['semester'])\
            .eq('section', data['section'])\
            .execute()

        if existing.data and len(existing.data) > 0:
            # Update existing entry
            entry_id = existing.data[0]['id']
            doc_data = {
                'subj_name': data['subjName'],
                'units': data['units']
            }
            supabase.table('configured_subjects').update(
                doc_data).eq('id', entry_id).execute()
            logger.info(f"Updated configured subject with ID: {entry_id}")
        else:
            # Insert new entry (let DB generate UUID)
            doc_data = {
                'subj_code': data['subjCode'],
                'subj_name': data['subjName'],
                'prof': data['prof'],
                'section': data['section'],
                'units': data['units'],
                'school_year': data['school_year'],
                'semester': data['semester']
            }
            result = supabase.table('configured_subjects').insert(
                doc_data).execute()
            entry_id = result.data[0]['id'] if result.data else None
            logger.info(f"Inserted configured subject with ID: {entry_id}")

        return jsonify({'status': 'ok', 'id': str(entry_id)})
    except Exception as e:
        logger.error(f"Error saving configured subject: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/configured-subjects/<entry_id>', methods=['DELETE'])
@login_required
def delete_configured_subject(entry_id):
    """Delete a configured subject."""
    try:
        logger.info(f"Deleting configured subject: {entry_id}")
        supabase.table('configured_subjects').delete().eq(
            'id', entry_id).execute()
        logger.info(f"Deleted configured subject: {entry_id}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error deleting configured subject: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/configured-subjects/remove', methods=['POST'])
@login_required
def remove_configured_subject():
    """Remove a configured subject by faculty, subject code, school year, and semester."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        faculty_id = data.get('faculty_id')
        subject_code = data.get('subject_code')
        school_year = data.get('school_year')
        semester = data.get('semester')

        if not all([faculty_id, subject_code, school_year, semester]):
            return jsonify({'error': 'Missing required fields'}), 400

        logger.info(
            f"Removing configured subject: prof={faculty_id}, subject={subject_code}, year={school_year}, sem={semester}")

        # Delete matching configured subject (column is 'prof' not 'faculty_id', and 'subj_code' not 'subject_code')
        supabase.table('configured_subjects').delete().eq('prof', faculty_id).eq(
            'subj_code', subject_code).eq('school_year', school_year).eq('semester', semester).execute()

        logger.info(
            f"Removed configured subject: {subject_code} for prof {faculty_id}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error removing configured subject: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/configured-subjects/delete-by-professor', methods=['POST'])
@login_required
def delete_configured_subjects_by_professor():
    """Delete ALL configured subjects for a specific professor, school year, and semester."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        prof = data.get('prof')
        school_year = data.get('school_year')
        semester = data.get('semester')

        if not all([prof, school_year, semester]):
            return jsonify({'error': 'Missing required fields: prof, school_year, semester'}), 400

        logger.info(
            f"Deleting all configured subjects for prof={prof}, year={school_year}, sem={semester}")

        # Delete all matching configured subjects
        result = supabase.table('configured_subjects').delete().eq('prof', prof).eq(
            'school_year', school_year).eq('semester', semester).execute()

        logger.info(
            f"Deleted {len(result.data) if result.data else 0} configured subjects for prof {prof}")
        return jsonify({'status': 'ok', 'deleted_count': len(result.data) if result.data else 0})
    except Exception as e:
        logger.error(f"Error deleting configured subjects by professor: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/all-subjects', methods=['GET'])
@login_required
def get_all_subjects():
    """Get ALL subjects from the subjects collection/table, independent of schedule configuration."""
    try:
        logger.info("Fetching all subjects for courses page")

        # Hardcoded list of all subjects - this can be moved to database later
        all_subjects = [
            # CERP Courses
            {'code': 'CERP 101', 'name': 'Orientation on Research and Extension',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 102', 'name': 'Research Methods',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 103', 'name': 'Technical Writing',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 140', 'name': 'Research Implementation',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 150', 'name': 'Thesis Writing',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 201', 'name': 'Advanced Research Methods',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 202', 'name': 'Quantitative Research Design',
                'units': 3, 'category': 'CERP'},
            {'code': 'CERP 203', 'name': 'Qualitative Research Design',
                'units': 3, 'category': 'CERP'},

            # HUME Courses
            {'code': 'HUME 100', 'name': 'Art Appreciation',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 105', 'name': 'Ethics', 'units': 3, 'category': 'HUME'},
            {'code': 'HUME 111', 'name': 'Philippine History',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 123', 'name': 'Filipino sa Iba\'t Ibang Disiplina',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 130', 'name': 'Literature',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 140', 'name': 'Philosophy',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 150', 'name': 'Logic',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 160', 'name': 'World Literature',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 170', 'name': 'Asian Studies',
                'units': 3, 'category': 'HUME'},
            {'code': 'HUME 180', 'name': 'Philippine Literature',
                'units': 3, 'category': 'HUME'},

            # NSTP Courses
            {'code': 'NSTP 1', 'name': 'National Service Training Program 1',
                'units': 3, 'category': 'NSTP'},
            {'code': 'NSTP 2', 'name': 'National Service Training Program 2',
                'units': 3, 'category': 'NSTP'},
        ]

        logger.info(f"Returning {len(all_subjects)} subjects")
        return jsonify({'subjects': all_subjects})
    except Exception as e:
        logger.error(f"Error fetching all subjects: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/courses', methods=['GET'])
@login_required
def get_all_courses():
    """Get all courses with their available sections from Supabase."""
    try:
        logger.info("Fetching all courses from Supabase")

        # Query courses table with retry logic
        result = retry_supabase_query(
            lambda: supabase.table('courses').select('*').order('course_code')
        )

        # Handle empty or None data
        courses = result.data if result.data else []

        logger.info(f"Fetched {len(courses)} courses")
        return jsonify({'courses': courses})
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        logger.exception("Full traceback:")

        # Return empty array instead of error to allow UI to load
        return jsonify({'courses': [], 'error': str(e)}), 200


# ══════════════════════════════════════════════════════════════════════════════
# FACULTY ELIGIBILITY (faculty_course_units table)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/faculty-course-units', methods=['GET'])
@login_required
def get_faculty_eligibility():
    """Get all faculty eligibility records (V1 table: faculty_eligible_courses)."""
    try:
        result = supabase.table(
            'faculty_eligible_courses').select('*').execute()
        return jsonify(result.data or [])
    except Exception as e:
        logger.error(f"Error fetching faculty eligibility: {e}")
        return jsonify([]), 200


@app.route('/api/faculty-course-units', methods=['POST'])
@login_required
def add_faculty_eligibility():
    """Add faculty eligibility for a course (V1 table: faculty_eligible_courses)."""
    try:
        data = request.get_json() or {}
        faculty_id = data.get('faculty_id')
        course_id = data.get('course_id')

        if not faculty_id or not course_id:
            return jsonify({'error': 'faculty_id and course_id required'}), 400

        # Check if already exists
        existing = supabase.table('faculty_eligible_courses').select('id').eq(
            'faculty_id', faculty_id
        ).eq('course_id', course_id).execute()

        if existing.data:
            return jsonify({'error': 'Eligibility already exists'}), 409

        # Insert new eligibility
        result = supabase.table('faculty_eligible_courses').insert({
            'faculty_id': faculty_id,
            'course_id': course_id
        }).execute()

        logger.info(
            f"Added faculty eligibility: faculty={faculty_id}, course={course_id}")
        return jsonify(result.data[0]), 201

    except Exception as e:
        logger.error(f"Error adding faculty eligibility: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/faculty-course-units/<entry_id>', methods=['DELETE'])
@login_required
def delete_faculty_eligibility(entry_id):
    """Remove faculty eligibility (V1 table: faculty_eligible_courses)."""
    try:
        result = supabase.table('faculty_eligible_courses').delete().eq(
            'id', entry_id).execute()

        if not result.data:
            return jsonify({'error': 'Entry not found'}), 404

        logger.info(f"Deleted faculty eligibility: {entry_id}")
        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error deleting faculty eligibility: {e}")
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# COURSE ASSIGNMENTS (faculty_courses table)
# Maps faculty to specific course sections for a given term
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/allocation/assignments', methods=['GET'])
@login_required
def get_course_assignments():
    """Get all course assignments for a term."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')

        query = supabase.table('faculty_courses').select('*')

        if school_year:
            query = query.eq('school_year', school_year)
        if semester:
            query = query.eq('semester', semester)

        result = query.execute()
        return jsonify(result.data or [])

    except Exception as e:
        logger.error(f"Error fetching course assignments: {e}")
        return jsonify([]), 200


@app.route('/api/allocation/assignments', methods=['POST'])
@login_required
def save_course_assignments():
    """Save multiple course assignments."""
    try:
        data = request.get_json() or {}
        assignments = data.get('assignments', [])

        if not assignments:
            return jsonify({'error': 'No assignments provided'}), 400

        saved = []
        for assignment in assignments:
            faculty_id = assignment.get('faculty_id')
            course_id = assignment.get('course_id')
            section = assignment.get('section')
            school_year = assignment.get('school_year')
            semester = assignment.get('semester')

            if not all([faculty_id, course_id, section, school_year, semester]):
                continue

            # Check if assignment already exists
            existing = supabase.table('faculty_courses').select('id').eq(
                'faculty_id', faculty_id
            ).eq('course_id', course_id).eq(
                'section', section
            ).eq('school_year', school_year).eq(
                'semester', semester
            ).execute()

            if not existing.data:
                # Insert new assignment
                result = supabase.table('faculty_courses').insert({
                    'faculty_id': faculty_id,
                    'course_id': course_id,
                    'section': section,
                    'school_year': school_year,
                    'semester': semester
                }).execute()

                if result.data:
                    saved.append(result.data[0])

        logger.info(f"Saved {len(saved)} course assignments")
        return jsonify({'status': 'ok', 'saved': len(saved), 'assignments': saved}), 201

    except Exception as e:
        logger.error(f"Error saving course assignments: {e}")
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# COURSE SECTIONS CONFIGURATION
# Defines which sections (A, B, C, etc.) are offered for each course
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/course-sections', methods=['GET'])
@login_required
def get_course_sections():
    """Get configured sections for courses (V1 table: course_term_offerings with JSONB array)."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')

        logger.info(
            f"[course-sections] Received params - school_year: '{school_year}' (type: {type(school_year).__name__}), semester: '{semester}' (type: {type(semester).__name__})")

        query = supabase.table('course_term_offerings').select('*')

        if school_year:
            query = query.eq('school_year', school_year)
        if semester:
            # Handle both string and integer semester values
            # Database stores as text, but might be just "1", "2", "3"
            query = query.eq('semester', semester)

        result = query.execute()
        logger.info(
            f"[course-sections] Query returned {len(result.data or [])} records")

        if result.data and len(result.data) > 0:
            logger.info(f"[course-sections] Sample record: {result.data[0]}")
        else:
            # Debug: Try query without filters
            debug_result = supabase.table('course_term_offerings').select(
                'school_year, semester').limit(5).execute()
            logger.warning(
                f"[course-sections] No data found! Sample of what's in table: {debug_result.data}")

        # Convert JSONB array format to individual section objects for V2 frontend
        # V1 format: {course_id, school_year, semester, available_sections: ["A", "B", ...]}
        # V2 format: [{course_id, section_letter: "A", school_year, semester, is_custom_block, ...}, ...]
        sections = []
        for offering in (result.data or []):
            course_id = offering.get('course_id')
            school_year = offering.get('school_year')
            semester = offering.get('semester')
            available_sections = offering.get('available_sections', [])
            section_metadata = offering.get(
                'section_metadata') or {}  # Handle None

            for section_letter in available_sections:
                # Get metadata for this section if exists
                metadata = section_metadata.get(
                    section_letter, {}) if section_metadata else {}

                sections.append({
                    # Synthetic ID
                    'id': f"{course_id}_{section_letter}_{school_year}_{semester}",
                    'course_id': course_id,
                    'section_letter': section_letter,
                    'school_year': school_year,
                    'semester': semester,
                    'is_custom_block': metadata.get('is_custom_block', False),
                    'units': metadata.get('units'),
                    'custom_room_name': metadata.get('custom_room_name')
                })

        return jsonify(sections)

    except Exception as e:
        logger.error(f"Error fetching course sections: {e}")
        return jsonify([]), 200


@app.route('/api/course-sections', methods=['POST'])
@login_required
def add_course_section():
    """Enable a section for a course (V1 table: course_term_offerings JSONB array)."""
    try:
        data = request.get_json() or {}
        course_id = data.get('course_id')
        section_letter = data.get('section_letter')
        school_year = data.get('school_year')
        semester = data.get('semester')
        is_custom_block = data.get('is_custom_block', False)
        units = data.get('units')
        custom_room_name = data.get('custom_room_name')

        if not all([course_id, section_letter, school_year, semester]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Get existing offering record for this course+term
        existing = supabase.table('course_term_offerings').select('*').eq(
            'course_id', course_id
        ).eq('school_year', school_year).eq('semester', semester).execute()

        if existing.data:
            # Update existing offering by adding section to JSONB array
            offering = existing.data[0]
            available_sections = offering.get('available_sections', [])
            section_metadata = offering.get('section_metadata', {})

            if section_letter in available_sections:
                return jsonify({'error': 'Section already configured'}), 409

            # Add section to array
            available_sections.append(section_letter)

            # Add metadata if custom block or has custom room
            if is_custom_block or units or custom_room_name:
                section_metadata[section_letter] = {
                    'is_custom_block': is_custom_block,
                    'units': units,
                    'custom_room_name': custom_room_name
                }

            # Update the record
            result = supabase.table('course_term_offerings').update({
                'available_sections': available_sections,
                'section_metadata': section_metadata,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', offering['id']).execute()

            logger.info(
                f"Added section {section_letter} to course {course_id}")

            # Return in V2 format
            return jsonify({
                'id': f"{course_id}_{section_letter}_{school_year}_{semester}",
                'course_id': course_id,
                'section_letter': section_letter,
                'school_year': school_year,
                'semester': semester,
                'is_custom_block': is_custom_block,
                'units': units,
                'custom_room_name': custom_room_name
            }), 201
        else:
            # Create new offering record
            section_metadata = {}
            if is_custom_block or units or custom_room_name:
                section_metadata[section_letter] = {
                    'is_custom_block': is_custom_block,
                    'units': units,
                    'custom_room_name': custom_room_name
                }

            result = supabase.table('course_term_offerings').insert({
                'course_id': course_id,
                'school_year': school_year,
                'semester': semester,
                'available_sections': [section_letter],
                'section_metadata': section_metadata
            }).execute()

            logger.info(
                f"Created offering for course {course_id} with section {section_letter}")

            # Return in V2 format
            return jsonify({
                'id': f"{course_id}_{section_letter}_{school_year}_{semester}",
                'course_id': course_id,
                'section_letter': section_letter,
                'school_year': school_year,
                'semester': semester,
                'is_custom_block': is_custom_block,
                'units': units,
                'custom_room_name': custom_room_name
            }), 201

    except Exception as e:
        logger.error(f"Error adding course section: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/course-sections/<entry_id>', methods=['DELETE'])
@login_required
def delete_course_section(entry_id):
    """Disable a section for a course (V1 table: course_term_offerings JSONB array).
    Entry ID format: {course_id}_{section_letter}_{school_year}_{semester}
    """
    try:
        # Parse synthetic ID
        parts = entry_id.split('_')
        if len(parts) < 4:
            return jsonify({'error': 'Invalid entry ID format'}), 400

        # Handle UUIDs with underscores - course_id is parts[0] through the last UUID segment
        # Then section_letter, school_year (may have dash), semester
        section_letter = parts[-3]
        school_year = parts[-2]
        semester = parts[-1]
        course_id = '_'.join(parts[:-3])

        # Get the offering record
        existing = supabase.table('course_term_offerings').select('*').eq(
            'course_id', course_id
        ).eq('school_year', school_year).eq('semester', semester).execute()

        if not existing.data:
            return jsonify({'error': 'Offering not found'}), 404

        offering = existing.data[0]
        available_sections = offering.get('available_sections', [])
        section_metadata = offering.get('section_metadata', {})

        if section_letter not in available_sections:
            return jsonify({'error': 'Section not found'}), 404

        # Remove section from array
        available_sections.remove(section_letter)

        # Remove metadata if exists
        if section_letter in section_metadata:
            del section_metadata[section_letter]

        # Update the record (or delete if no sections left)
        if available_sections:
            supabase.table('course_term_offerings').update({
                'available_sections': available_sections,
                'section_metadata': section_metadata,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', offering['id']).execute()
        else:
            # No sections left, delete the offering record
            supabase.table('course_term_offerings').delete().eq(
                'id', offering['id']).execute()

        logger.info(
            f"Deleted section {section_letter} from course {course_id}")
        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error deleting course section: {e}")
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# SECTION ROOM ALLOCATIONS
# Maps course sections to specific rooms for scheduling
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/section-rooms', methods=['GET'])
@login_required
def get_section_room_allocations():
    """Get room allocations for course sections."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')

        query = supabase.table('section_room_allocations').select('*')

        if school_year:
            query = query.eq('school_year', school_year)
        if semester:
            query = query.eq('semester', semester)

        result = query.execute()
        return jsonify(result.data or [])

    except Exception as e:
        # Table might not exist yet
        if _table_is_missing(e):
            logger.warning("section_room_allocations table not found")
            return jsonify([]), 200
        logger.error(f"Error fetching room allocations: {e}")
        return jsonify([]), 200


@app.route('/api/section-rooms', methods=['POST'])
@login_required
def save_section_room_allocation():
    """Save or update room allocation for a section."""
    try:
        data = request.get_json() or {}
        course_id = data.get('course_id')
        section_letter = data.get('section_letter')
        school_year = data.get('school_year')
        semester = data.get('semester')
        room_id = data.get('room_id')  # Can be null
        custom_room_name = data.get('custom_room_name')

        if not all([course_id, section_letter, school_year, semester]):
            return jsonify({'error': 'Missing required fields'}), 400

        if not room_id and not custom_room_name:
            return jsonify({'error': 'Either room_id or custom_room_name required'}), 400

        # Check if allocation already exists
        existing = supabase.table('section_room_allocations').select('id').eq(
            'course_id', course_id
        ).eq('section_letter', section_letter).eq(
            'school_year', school_year
        ).eq('semester', semester).execute()

        payload = {
            'course_id': course_id,
            'section_letter': section_letter,
            'school_year': school_year,
            'semester': semester,
            'room_id': room_id,
            'custom_room_name': custom_room_name
        }

        if existing.data:
            # Update existing
            result = supabase.table('section_room_allocations').update(payload).eq(
                'id', existing.data[0]['id']
            ).execute()
            logger.info(
                f"Updated room allocation for {course_id}/{section_letter}")
        else:
            # Insert new
            result = supabase.table(
                'section_room_allocations').insert(payload).execute()
            logger.info(
                f"Created room allocation for {course_id}/{section_letter}")

        return jsonify(result.data[0]), 201

    except Exception as e:
        logger.error(f"Error saving room allocation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/section-rooms/<allocation_id>', methods=['DELETE'])
@login_required
def delete_section_room_allocation(allocation_id):
    """Remove room allocation."""
    try:
        result = supabase.table('section_room_allocations').delete().eq(
            'id', allocation_id).execute()

        if not result.data:
            return jsonify({'error': 'Allocation not found'}), 404

        logger.info(f"Deleted room allocation: {allocation_id}")
        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error deleting room allocation: {e}")
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM SECTIONS & ROOMS
# Managed from the courses page. Both tables are optional: until sql/
# rooms_and_sections.sql has been run the app falls back to the A-Z sections
# and the built-in room list.
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_ROOMS = [
    'CERP AVR',
    'DCERP Conference Room',
    'CLH',
    'Geomatics Room',
    'TCC-01',
    'TCC-02',
    'TCC-03',
    'TCC-04',
    'TCC-10',
    'TCC-11',
    'CHE REC',
]


def _table_is_missing(error) -> bool:
    """True when Supabase reports the table itself does not exist."""
    message = str(error)
    return 'PGRST205' in message or 'Could not find the table' in message


def _fetch_named_rows(table: str):
    """Rows of an optional (id, name) table; None when the table is absent."""
    try:
        result = supabase.table(table).select(
            'id, name').order('name').execute()
        return result.data or []
    except Exception as e:
        if _table_is_missing(e):
            return None
        raise


def get_custom_sections() -> list:
    """Section names added on top of A-Z."""
    rows = _fetch_named_rows('sections')
    return [r['name'] for r in rows] if rows else []


def get_all_rooms() -> list:
    """Built-in rooms plus any room added from the courses page."""
    rooms = list(DEFAULT_ROOMS)
    rows = _fetch_named_rows('rooms')
    for row in rows or []:
        if row['name'] not in rooms:
            rooms.append(row['name'])
    return rooms


def _named_table_list(table: str, label: str):
    rows = _fetch_named_rows(table)
    if rows is None:
        return jsonify({
            'available': False,
            label: [],
            'setup_hint': 'Run sql/rooms_and_sections.sql in the Supabase SQL editor to enable this.',
        })
    return jsonify({'available': True, label: rows})


# Names end up in schedule rows, element ids and course-section keys, so keep
# them to characters that are safe everywhere.
NAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._/-]*$')


def _named_table_add(table: str, reserved: list, kind: str):
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()

    if not name:
        return jsonify({'error': f'{kind} name is required'}), 400
    if len(name) > 40:
        return jsonify({'error': f'{kind} name must be 40 characters or fewer'}), 400
    if not NAME_PATTERN.match(name):
        return jsonify({
            'error': f'{kind} name may only use letters, numbers, spaces and . _ - /'
        }), 400
    if any(name.lower() == r.lower() for r in reserved):
        return jsonify({'error': f'{name} already exists'}), 409

    existing = _fetch_named_rows(table)
    if existing is None:
        return jsonify({
            'error': 'Storage is not set up yet.',
            'setup_hint': 'Run sql/rooms_and_sections.sql in the Supabase SQL editor.',
        }), 503
    if any(row['name'].lower() == name.lower() for row in existing):
        return jsonify({'error': f'{name} already exists'}), 409

    try:
        result = supabase.table(table).insert({'name': name}).execute()
    except Exception as e:
        logger.error(f"Error adding {kind.lower()} {name}: {e}")
        return jsonify({'error': str(e)}), 500

    logger.info(f"Added {kind.lower()}: {name}")
    return jsonify({'status': 'ok', 'item': result.data[0]}), 201


def _named_table_delete(table: str, item_id: str, kind: str):
    try:
        result = supabase.table(table).delete().eq('id', item_id).execute()
    except Exception as e:
        logger.error(f"Error deleting {kind.lower()} {item_id}: {e}")
        return jsonify({'error': str(e)}), 500

    if not result.data:
        return jsonify({'error': f'{kind} not found'}), 404
    return jsonify({'status': 'ok'})


@app.route('/api/sections', methods=['GET'])
@login_required
def list_custom_sections():
    """Sections available on top of the built-in A-Z list."""
    return _named_table_list('sections', 'sections')


@app.route('/api/sections', methods=['POST'])
@login_required
def add_custom_section():
    """Add a section name that courses can then be offered for."""
    letters = [chr(c) for c in range(ord('A'), ord('Z') + 1)]
    return _named_table_add('sections', letters, 'Section')


@app.route('/api/sections/<section_id>', methods=['DELETE'])
@login_required
def delete_custom_section(section_id):
    """
    Remove a custom section.

    Courses already configured for it keep their configuration, so nothing
    that is allocated or scheduled is touched.
    """
    return _named_table_delete('sections', section_id, 'Section')


@app.route('/api/rooms', methods=['GET'])
@login_required
def list_rooms():
    """Rooms added from the courses page, plus the built-in list for reference."""
    rows = _fetch_named_rows('rooms')
    payload = {'default_rooms': DEFAULT_ROOMS}
    if rows is None:
        payload.update({
            'available': False,
            'rooms': [],
            'setup_hint': 'Run sql/rooms_and_sections.sql in the Supabase SQL editor to enable this.',
        })
    else:
        payload.update({'available': True, 'rooms': rows})
    return jsonify(payload)


@app.route('/api/rooms', methods=['POST'])
@login_required
def add_room():
    """Add a room the scheduler can place classes in."""
    return _named_table_add('rooms', DEFAULT_ROOMS, 'Room')


@app.route('/api/rooms/<room_id>', methods=['DELETE'])
@login_required
def delete_room(room_id):
    """Remove a room. Existing schedules keep their room assignment."""
    return _named_table_delete('rooms', room_id, 'Room')


def _letter_sections():
    return [chr(c) for c in range(ord('A'), ord('Z') + 1)]


def _validate_new_name(name: str, kind: str):
    name = (name or '').strip()
    if not name:
        raise ValueError(f'{kind} name is required')
    if len(name) > 40:
        raise ValueError(f'{kind} name must be 40 characters or fewer')
    if not NAME_PATTERN.match(name):
        raise ValueError(
            f'{kind} name may only use letters, numbers, spaces and . _ - /')
    return name


def _ensure_named_resource(table: str, name: str, reserved: list, kind: str):
    """Return (canonical name, created?). Inserts the name when it is new."""
    name = _validate_new_name(name, kind)
    for reserved_name in reserved:
        if reserved_name.lower() == name.lower():
            return reserved_name, False
    existing = _fetch_named_rows(table)
    if existing:
        for row in existing:
            if (row.get('name') or '').lower() == name.lower():
                return row['name'], False
    if existing is None:
        raise RuntimeError(
            f'{kind} storage is not set up yet. Run sql/rooms_and_sections.sql.')
    supabase.table(table).insert({'name': name}).execute()
    logger.info(f"Added {kind.lower()}: {name}")
    return name, True


def _find_course_by_code(course_code: str):
    want = normalize_course_code((course_code or '').strip()).upper()
    if not want:
        return None
    for course in _course_catalog().values():
        have = normalize_course_code(course.get('course_code') or '').upper()
        if have == want:
            return course
    return None


def _create_course(course_code: str, course_name: str, units: int, section: str):
    code = normalize_course_code((course_code or '').strip())
    if not code:
        raise ValueError('Course code is required')
    if len(code) > 40:
        raise ValueError('Course code must be 40 characters or fewer')
    if not NAME_PATTERN.match(code):
        raise ValueError(
            'Course code may only use letters, numbers, spaces and . _ - /')
    existing = _find_course_by_code(code)
    if existing:
        return existing, False

    name = (course_name or '').strip() or code
    try:
        units = int(units)
    except (TypeError, ValueError):
        units = 3
    if units < 1 or units > 12:
        raise ValueError('Units must be between 1 and 12')

    payload = {
        'course_code': code,
        'course_name': name,
        'units': units,
        'available_sections': [section] if section else [],
    }
    try:
        result = supabase.table('courses').insert(payload).execute()
    except Exception as e:
        logger.warning(f"Course insert with sections failed, retrying: {e}")
        payload.pop('available_sections', None)
        result = supabase.table('courses').insert(payload).execute()
    if not result.data:
        raise RuntimeError('Could not create the course')
    logger.info(f"Created course {code}")
    return result.data[0], True


def _as_section_list(value):
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return [value]
    return list(value) if isinstance(value, list) else [value]


def _offer_section(course_id: str, section: str, school_year: str, semester: str):
    course = supabase.table('courses').select(
        'id, available_sections').eq('id', course_id).execute()
    if not course.data:
        raise ValueError('Course not found')
    current = _as_section_list(course.data[0].get('available_sections'))
    if section not in current:
        current.append(section)
        supabase.table('courses').update(
            {'available_sections': current}).eq('id', course_id).execute()

    caps = allocation_capabilities()
    if not (caps['term_offerings_table'] and school_year and semester):
        return current

    existing = supabase.table('course_term_offerings')\
        .select('id, available_sections')\
        .eq('course_id', course_id)\
        .eq('school_year', school_year)\
        .eq('semester', semester)\
        .execute()
    offered = _as_section_list(
        existing.data[0].get(
            'available_sections') if existing.data else current
    )
    if section not in offered:
        offered.append(section)
    payload = {
        'course_id': course_id,
        'school_year': school_year,
        'semester': semester,
        'available_sections': offered,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    if existing.data:
        supabase.table('course_term_offerings')\
            .update({'available_sections': offered,
                     'updated_at': payload['updated_at']})\
            .eq('id', existing.data[0]['id'])\
            .execute()
    else:
        supabase.table('course_term_offerings').insert(payload).execute()
    return offered


@app.route('/api/allocation/offering', methods=['POST'])
@login_required
def add_allocation_offering():
    """
    Add a course+section+room combo for this term and assign one faculty.

    Each of course, section, and room can be an existing value or a new one.
    A new course can reuse an existing section and room, and vice versa.
    The same custom course+section may be assigned to more than one faculty.
    """
    try:
        data = request.get_json() or {}
        default_year, default_sem = current_default_term()
        school_year = (data.get('school_year') or '').strip() or default_year
        semester = (data.get('semester') or '').strip() or default_sem
        faculty_id = (data.get('faculty_id') or '').strip()
        section_in = (data.get('section') or '').strip()
        room_in = (data.get('room') or '').strip()
        course_id = (data.get('course_id') or '').strip()
        course_payload = data.get('course') or {}

        if not faculty_id:
            return jsonify({'error': 'Choose which faculty will handle this course+section'}), 400
        if not section_in:
            return jsonify({'error': 'Section is required'}), 400

        created = {'course': False, 'section': False, 'room': False}

        try:
            section, created['section'] = _ensure_named_resource(
                'sections', section_in, _letter_sections(), 'Section')
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except RuntimeError as e:
            if section_in.upper() in _letter_sections():
                section = section_in.upper()
                created['section'] = False
            else:
                return jsonify({'error': str(e)}), 503

        room = None
        if room_in:
            try:
                room, created['room'] = _ensure_named_resource(
                    'rooms', room_in, DEFAULT_ROOMS, 'Room')
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except RuntimeError as e:
                match = next(
                    (r for r in DEFAULT_ROOMS if r.lower() == room_in.lower()),
                    None,
                )
                if match:
                    room = match
                    created['room'] = False
                else:
                    return jsonify({'error': str(e)}), 503

        course = None
        if course_id:
            course = _course_catalog().get(course_id)
            if not course:
                return jsonify({'error': 'Course not found'}), 404
        else:
            try:
                course, created['course'] = _create_course(
                    course_payload.get('course_code'),
                    course_payload.get('course_name'),
                    course_payload.get('units', 3),
                    section,
                )
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

        _offer_section(course['id'], section, school_year, semester)

        units = data.get('units', course.get('units') or 3)
        try:
            block, created_block = _save_custom_block(
                faculty_id, course, section, units, room, school_year, semester)
        except ValueError as e:
            return jsonify({
                'error': str(e),
                'created': created,
                'course': course,
                'section': section,
                'room': room,
            }), 409

        return jsonify({
            'status': 'ok',
            'created': created,
            'assigned': created_block,
            'is_custom': True,
            'course': {
                'id': course['id'],
                'course_code': course.get('course_code'),
                'course_name': course.get('course_name'),
                'units': block.get('units') or units,
            },
            'section': section,
            'room': room,
            'faculty_id': faculty_id,
            'school_year': school_year,
            'semester': semester,
        }), 201 if created_block or created['course'] else 200
    except Exception as e:
        logger.error(f"Error adding offering: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/allocation/offering/<block_id>', methods=['DELETE'])
@login_required
def delete_allocation_offering(block_id):
    """Remove a custom staging block."""
    try:
        if not _delete_custom_block(block_id):
            return jsonify({'error': 'Custom block not found'}), 404
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error deleting custom block: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/allocation/assignment-units', methods=['PUT'])
@login_required
def update_allocation_assignment_units():
    """Set contact-hour units for one assigned course+section."""
    try:
        data = request.get_json() or {}
        units = _parse_assignment_units(data.get('units'))
        is_custom = bool(data.get('is_custom'))
        block_id = (data.get('id') or data.get('block_id') or '').strip()
        faculty_id = (data.get('faculty_id') or '').strip()
        course_code = (data.get('course_code') or '').strip()
        section = (data.get('section') or '').strip()

        if is_custom:
            row = _update_custom_block_units(
                block_id,
                units,
                faculty_id=faculty_id,
                course_code=course_code,
                section=section,
                school_year=(data.get('school_year') or '').strip() or None,
                semester=(data.get('semester') or '').strip() or None,
            )
        else:
            if not faculty_id or not course_code or not section:
                return jsonify({
                    'error': 'faculty_id, course_code, and section are required'
                }), 400
            row = _update_regular_assignment_units(
                faculty_id, course_code, section, units, block_id or None)

        return jsonify({'status': 'ok', 'units': units, 'row': row})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating assignment units: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# COURSE ALLOCATION (eligibility + term-specific sections)
# Faculty are assigned to a course first. Which section they teach is stored
# per school year / semester. Custom sections from the courses page are valid.
# ══════════════════════════════════════════════════════════════════════════════

def normalize_course_code(code: str) -> str:
    """CERP101 -> CERP 101 so keys match the frontend."""
    return re.sub(r'([A-Z]+)(\d)', r'\1 \2', code or '')


def _column_is_missing(error) -> bool:
    message = str(error)
    return (
        'PGRST204' in message
        or '42703' in message
        or 'schema cache' in message.lower()
        or 'does not exist' in message.lower()
    )


_ALLOC_CAPS = None


def _set_alloc_cap(key, value):
    global _ALLOC_CAPS
    if _ALLOC_CAPS is None:
        _ALLOC_CAPS = {}
    _ALLOC_CAPS[key] = value


def allocation_capabilities():
    """Which optional tables/columns exist. Recheck any that are still missing."""
    global _ALLOC_CAPS
    if _ALLOC_CAPS is not None and all(_ALLOC_CAPS.values()):
        return _ALLOC_CAPS

    caps = dict(_ALLOC_CAPS) if _ALLOC_CAPS else {
        'eligibility_table': False,
        'term_offerings_table': False,
        'term_columns': False,
        'custom_blocks_table': False,
        'faculty_courses_units': False,
    }

    if not caps.get('eligibility_table'):
        try:
            supabase.table('faculty_eligible_courses').select(
                'id').limit(1).execute()
            caps['eligibility_table'] = True
        except Exception as e:
            if not _table_is_missing(e):
                logger.warning(f"eligibility table probe: {e}")

    if not caps.get('term_offerings_table'):
        try:
            supabase.table('course_term_offerings').select(
                'id').limit(1).execute()
            caps['term_offerings_table'] = True
        except Exception as e:
            if not _table_is_missing(e):
                logger.warning(f"term offerings table probe: {e}")

    if not caps.get('term_columns'):
        try:
            supabase.table('faculty_courses').select(
                'id, school_year, semester').limit(1).execute()
            caps['term_columns'] = True
        except Exception as e:
            if not (_column_is_missing(e) or _table_is_missing(e)):
                logger.warning(f"faculty_courses term columns probe: {e}")

    if not caps.get('custom_blocks_table'):
        try:
            supabase.table('custom_term_blocks').select(
                'id').limit(1).execute()
            caps['custom_blocks_table'] = True
        except Exception as e:
            if not _table_is_missing(e):
                logger.warning(f"custom_term_blocks probe: {e}")

    if not caps.get('faculty_courses_units'):
        try:
            supabase.table('faculty_courses').select(
                'id, units').limit(1).execute()
            caps['faculty_courses_units'] = True
        except Exception as e:
            if not (_column_is_missing(e) or _table_is_missing(e)):
                logger.warning(f"faculty_courses units probe: {e}")

    _ALLOC_CAPS = caps
    return caps


def current_default_term():
    year = datetime.now().year
    return f"{year}-{year + 1}", '1'


def _course_catalog() -> dict:
    """id -> course row. Used instead of PostgREST embeds when no FK exists."""
    rows = supabase.table('courses').select(
        'id, course_code, course_name, units, available_sections').execute()
    return {c['id']: c for c in (rows.data or [])}


def _with_course_fields(row: dict, catalog: dict) -> dict:
    course = catalog.get(row.get('course_id')) or {}
    assigned_units = row.get('units')
    return {
        **row,
        'course_code': course.get('course_code'),
        'course_name': course.get('course_name'),
        'units': assigned_units if assigned_units is not None else course.get('units'),
    }


def fetch_term_offerings(school_year: str = None, semester: str = None) -> dict:
    """course_id -> [section names]. Regular section lists are global."""
    catalog = _course_catalog()
    return {
        course_id: _as_section_list(course.get('available_sections'))
        for course_id, course in catalog.items()
    }


def fetch_eligibility_rows():
    """[{faculty_id, course_id, course_code, course_name, units}]"""
    caps = allocation_capabilities()
    catalog = _course_catalog()

    if caps['eligibility_table']:
        result = supabase.table('faculty_eligible_courses')\
            .select('faculty_id, course_id')\
            .execute()
        source = result.data or []
    else:
        result = supabase.table('faculty_courses')\
            .select('faculty_id, course_id')\
            .execute()
        source = result.data or []

    seen = set()
    rows = []
    for item in source:
        key = (item['faculty_id'], item['course_id'])
        if key in seen:
            continue
        seen.add(key)
        decorated = _with_course_fields(item, catalog)
        if not decorated.get('course_code'):
            continue
        rows.append({
            'faculty_id': decorated['faculty_id'],
            'course_id': decorated['course_id'],
            'course_code': decorated['course_code'],
            'course_name': decorated['course_name'],
            'units': decorated['units'],
        })
    return rows


def fetch_section_assignments(school_year=None, semester=None):
    """Regular faculty_courses rows. Term args are ignored — allocation is global."""
    catalog = _course_catalog()
    caps = allocation_capabilities()
    columns = 'id, faculty_id, course_id, section, units' if caps.get(
        'faculty_courses_units') else 'id, faculty_id, course_id, section'
    result = supabase.table('faculty_courses').select(columns).execute()
    rows = []
    for item in result.data or []:
        if not item.get('section'):
            continue
        decorated = _with_course_fields(item, catalog)
        if not decorated.get('course_code'):
            continue
        rows.append({
            'id': decorated.get('id'),
            'faculty_id': decorated['faculty_id'],
            'course_id': decorated['course_id'],
            'section': decorated['section'],
            'course_code': decorated['course_code'],
            'course_name': decorated['course_name'],
            'units': decorated.get('units') or 3,
            'is_custom': False,
        })
    return rows


def _faculty_display_name(faculty_id: str) -> str:
    result = supabase.table('members').select(
        'first, last, suffix').eq('id', faculty_id).execute()
    if not result.data:
        return ''
    member = result.data[0]
    name = f"{member.get('first', '')} {member.get('last', '')}".strip()
    if member.get('suffix'):
        name += f", {member['suffix']}"
    return name


def _dedupe_custom_blocks(rows: list) -> list:
    """One row per faculty + course + section; later rows win."""
    unique = {}
    for row in rows:
        key = (
            row.get('faculty_id'),
            row.get('course_id'),
            row.get('section'),
        )
        unique[key] = row
    return list(unique.values())


def fetch_custom_blocks(school_year: str = None, semester: str = None) -> list:
    """All custom course+section+faculty blocks. Year/semester are not filtered."""
    catalog = _course_catalog()
    caps = allocation_capabilities()
    rows = []

    if caps.get('custom_blocks_table'):
        result = supabase.table('custom_term_blocks')\
            .select('id, faculty_id, course_id, section, units, room, school_year, semester')\
            .execute()
        for item in result.data or []:
            custom_units = item.get('units')
            decorated = _with_course_fields(item, catalog)
            if not decorated.get('course_code'):
                continue
            rows.append({
                'id': decorated.get('id'),
                'faculty_id': decorated['faculty_id'],
                'course_id': decorated['course_id'],
                'section': decorated['section'],
                'course_code': decorated['course_code'],
                'course_name': decorated['course_name'],
                'units': custom_units if custom_units is not None else (decorated.get('units') or 3),
                'room': decorated.get('room'),
                'school_year': decorated.get('school_year'),
                'semester': decorated.get('semester'),
                'is_custom': True,
            })
        return _dedupe_custom_blocks(rows)

    try:
        query = supabase.table('configured_subjects').select('*')
        if school_year:
            query = query.eq('school_year', school_year)
        if semester:
            query = query.eq('semester', semester)
        result = query.execute()
    except Exception as e:
        if _table_is_missing(e):
            return []
        raise

    members = supabase.table('members').select(
        'id, first, last, suffix').execute()
    name_to_id = {}
    for member in members.data or []:
        full = f"{member.get('first', '')} {member.get('last', '')}".strip()
        name_to_id[full] = member['id']
        if member.get('suffix'):
            name_to_id[f"{full}, {member['suffix']}"] = member['id']

    course_by_code = {
        normalize_course_code(c.get('course_code') or '').upper(): c
        for c in catalog.values()
    }
    for item in result.data or []:
        code = normalize_course_code(item.get('subj_code') or '')
        course = course_by_code.get(code.upper())
        faculty_id = name_to_id.get((item.get('prof') or '').strip())
        if not course or not faculty_id or not item.get('section'):
            continue
        rows.append({
            'id': item.get('id'),
            'faculty_id': faculty_id,
            'course_id': course['id'],
            'section': item.get('section'),
            'course_code': course.get('course_code'),
            'course_name': item.get('subj_name') or course.get('course_name'),
            'units': item.get('units') or course.get('units') or 3,
            'room': None,
            'school_year': item.get('school_year') or school_year,
            'semester': item.get('semester') or semester,
            'is_custom': True,
        })
    return _dedupe_custom_blocks(rows)


def _save_custom_block(faculty_id, course, section, units, room, school_year, semester):
    """Insert a custom block. Same faculty+course+section is global, not per term."""
    caps = allocation_capabilities()
    existing_regular = [
        a for a in fetch_section_assignments()
        if a['course_id'] == course['id']
        and a['section'] == section
        and a['faculty_id'] == faculty_id
    ]
    if existing_regular:
        raise ValueError(
            f"{course.get('course_code')} Section {section} is already in "
            'Faculty Assignment for this faculty. Custom blocks are extras, '
            'not replacements.'
        )

    try:
        units = float(units)
    except (TypeError, ValueError):
        units = float(course.get('units') or 3)
    if units < 0.5 or units > 12:
        raise ValueError('Units must be between 0.5 and 12')

    for other in fetch_custom_blocks():
        if (other['course_id'] == course['id']
                and other['section'] == section
                and other['faculty_id'] == faculty_id):
            if other.get('id') and caps.get('custom_blocks_table'):
                supabase.table('custom_term_blocks').update({
                    'units': units,
                    'room': room,
                }).eq('id', other['id']).eq('faculty_id', faculty_id).execute()
            other = dict(other)
            other['units'] = units
            other['room'] = room
            return other, False

    if caps.get('custom_blocks_table'):
        try:
            result = supabase.table('custom_term_blocks').insert({
                'faculty_id': faculty_id,
                'course_id': course['id'],
                'section': section,
                'units': units,
                'room': room,
                'school_year': school_year,
                'semester': semester,
            }).execute()
        except Exception as e:
            message = str(e)
            if '23505' in message or 'unique' in message.lower():
                raise ValueError(
                    'This custom course+section is already assigned to another '
                    'faculty. Run sql/shared_custom_blocks.sql in the Supabase '
                    'SQL editor to allow sharing.'
                ) from e
            raise
        row = (result.data or [{}])[0]
        return {
            'id': row.get('id'),
            'faculty_id': faculty_id,
            'course_id': course['id'],
            'section': section,
            'course_code': course.get('course_code'),
            'course_name': course.get('course_name'),
            'units': units,
            'room': room,
            'is_custom': True,
        }, True

    prof = _faculty_display_name(faculty_id)
    result = supabase.table('configured_subjects').insert({
        'subj_code': course.get('course_code'),
        'subj_name': course.get('course_name') or course.get('course_code'),
        'prof': prof,
        'section': section,
        'units': units,
        'school_year': school_year,
        'semester': semester,
    }).execute()
    row = (result.data or [{}])[0]
    return {
        'id': row.get('id'),
        'faculty_id': faculty_id,
        'course_id': course['id'],
        'section': section,
        'course_code': course.get('course_code'),
        'course_name': course.get('course_name'),
        'units': units,
        'room': room,
        'is_custom': True,
    }, True


def _delete_custom_block(block_id: str):
    caps = allocation_capabilities()
    if caps.get('custom_blocks_table'):
        result = supabase.table('custom_term_blocks').delete().eq(
            'id', block_id).execute()
        return bool(result.data)
    result = supabase.table('configured_subjects').delete().eq(
        'id', block_id).execute()
    return bool(result.data)


def _parse_assignment_units(value):
    try:
        units = float(value)
    except (TypeError, ValueError):
        raise ValueError('Units must be a number')
    if units < 0.5 or units > 12:
        raise ValueError('Units must be between 0.5 and 12')
    return units


def _update_regular_assignment_units(faculty_id, course_code, section, units, row_id=None):
    catalog = _course_catalog()
    course = next(
        (c for c in catalog.values() if c.get('course_code') == course_code),
        None
    )
    if not course:
        raise ValueError(f'Course {course_code} not found')
    query = supabase.table('faculty_courses').update({'units': units})
    if row_id:
        query = query.eq('id', row_id)
    else:
        query = query.eq('faculty_id', faculty_id)\
            .eq('course_id', course['id'])\
            .eq('section', section)
    try:
        result = query.execute()
    except Exception as e:
        if _column_is_missing(e):
            raise ValueError(
                'The units column is not visible to the API yet. '
                'In the Supabase SQL editor run: NOTIFY pgrst, \'reload schema\';'
            ) from e
        raise
    if not result.data:
        raise ValueError(
            f'{course_code} Section {section} is not assigned to this faculty')
    _set_alloc_cap('faculty_courses_units', True)
    return result.data[0]


def _update_custom_block_units(block_id, units, faculty_id=None,
                               course_code=None, section=None,
                               school_year=None, semester=None):
    """Update units for one faculty's custom block only."""
    caps = allocation_capabilities()
    if caps.get('custom_blocks_table'):
        query = supabase.table('custom_term_blocks').update({'units': units})
        if block_id:
            query = query.eq('id', block_id)
            if faculty_id:
                query = query.eq('faculty_id', faculty_id)
        elif faculty_id and course_code and section:
            catalog = _course_catalog()
            course = next(
                (c for c in catalog.values() if c.get(
                    'course_code') == course_code),
                None
            )
            if not course:
                raise ValueError(f'Course {course_code} not found')
            query = query.eq('faculty_id', faculty_id)\
                .eq('course_id', course['id'])\
                .eq('section', section)
        else:
            raise ValueError(
                'Custom block id or faculty + course + section is required')
        result = query.execute()
        if not result.data:
            raise ValueError('Custom block not found for this faculty')
        return result.data[0]
    if not block_id:
        raise ValueError('Custom block id is required')
    result = supabase.table('configured_subjects').update(
        {'units': units}).eq('id', block_id).execute()
    if not result.data:
        raise ValueError('Custom block not found')
    return result.data[0]


def replace_faculty_eligibility(faculty_id, course_ids):
    caps = allocation_capabilities()
    if not caps['eligibility_table']:
        return False
    supabase.table('faculty_eligible_courses')\
        .delete().eq('faculty_id', faculty_id).execute()
    if course_ids:
        supabase.table('faculty_eligible_courses').insert([
            {'faculty_id': faculty_id, 'course_id': cid} for cid in course_ids
        ]).execute()
    return True


def _assignment_key(course_code, section) -> str:
    return f"{normalize_course_code(course_code)}-{section}"


@app.route('/api/allocation', methods=['GET'])
@login_required
def get_allocation_state():
    """Regular allocation and custom blocks are both global."""
    try:
        school_year = request.args.get(
            'school_year') or current_default_term()[0]
        semester = request.args.get('semester') or current_default_term()[1]
        caps = allocation_capabilities()

        offerings = fetch_term_offerings()
        eligibility = fetch_eligibility_rows()
        assignments = fetch_section_assignments()
        custom_blocks = fetch_custom_blocks()

        assigned = [_assignment_key(a['course_code'], a['section'])
                    for a in assignments + custom_blocks if a.get('course_code')]

        return jsonify({
            'school_year': school_year,
            'semester': semester,
            'setup': caps,
            'setup_complete': caps.get('eligibility_table', False),
            'setup_hint': None,
            'offerings': offerings,
            'eligibility': eligibility,
            'assignments': assignments,
            'custom_blocks': custom_blocks,
            'assigned': assigned,
        })
    except Exception as e:
        logger.error(f"Error fetching allocation state: {e}", exc_info=True)
        caps = allocation_capabilities()
        return jsonify({
            'setup': caps,
            'setup_complete': caps.get('eligibility_table', False),
            'setup_hint': None,
            'offerings': {},
            'eligibility': [],
            'assignments': [],
            'custom_blocks': [],
            'assigned': [],
            'error': str(e),
        }), 200


@app.route('/api/assigned-course-sections', methods=['GET'])
@login_required
def get_assigned_course_sections():
    """Assigned course-section keys for a term (or all rows in legacy mode)."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')
        assignments = fetch_section_assignments()
        custom = fetch_custom_blocks()
        assigned = [_assignment_key(a['course_code'], a['section'])
                    for a in assignments + custom if a.get('course_code')]
        return jsonify({'assigned': assigned})
    except Exception as e:
        logger.error(f"Error fetching assigned course-sections: {e}")
        return jsonify({'assigned': [], 'error': str(e)}), 200


@app.route('/api/courses/<course_id>/sections', methods=['PUT'])
@login_required
def update_course_sections(course_id):
    """Offer a course for a set of sections. Term-specific when the table exists."""
    try:
        data = request.get_json() or {}
        available_sections = data.get('available_sections', [])
        school_year = data.get('school_year')
        semester = data.get('semester')

        if not available_sections:
            return jsonify({'error': 'At least one section must be provided'}), 400

        result = supabase.table('courses')\
            .update({'available_sections': available_sections})\
            .eq('id', course_id)\
            .execute()
        if not result.data:
            return jsonify({'error': 'Course not found'}), 404

        return jsonify({'status': 'ok', 'course': result.data[0]})
    except Exception as e:
        logger.error(f"Error updating course sections: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/courses/<course_id>/eligible-faculty', methods=['PUT'])
@login_required
def update_course_eligible_faculty(course_id):
    """Set which faculty may teach this course. Does not assign a section."""
    try:
        data = request.get_json() or {}
        faculty_ids = list(
            {fid for fid in (data.get('faculty_ids') or []) if fid})
        caps = allocation_capabilities()
        if not caps['eligibility_table']:
            return jsonify({
                'error': 'Course assignment is not set up yet.',
                'setup_hint': 'Run sql/term_assignments.sql in the Supabase SQL editor.',
            }), 503

        existing = supabase.table('faculty_eligible_courses')\
            .select('faculty_id')\
            .eq('course_id', course_id)\
            .execute()
        previous = {row['faculty_id'] for row in (existing.data or [])}
        incoming = set(faculty_ids)

        supabase.table('faculty_eligible_courses')\
            .delete().eq('course_id', course_id).execute()
        if faculty_ids:
            supabase.table('faculty_eligible_courses').insert([
                {'faculty_id': fid, 'course_id': course_id} for fid in faculty_ids
            ]).execute()

        # Faculty who lost this course should not keep a section of it.
        removed = previous - incoming
        for faculty_id in removed:
            supabase.table('faculty_courses')\
                .delete()\
                .eq('faculty_id', faculty_id)\
                .eq('course_id', course_id)\
                .execute()

        logger.info(
            f"Course {course_id} eligible faculty: {len(faculty_ids)}")
        return jsonify({'status': 'ok', 'faculty_ids': faculty_ids})
    except Exception as e:
        logger.error(f"Error updating eligible faculty: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/faculty/<faculty_id>/courses', methods=['GET'])
@login_required
def get_faculty_courses(faculty_id):
    """Section assignments for one faculty, optionally limited to a term."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')
        assignments = [
            a for a in fetch_section_assignments()
            if a['faculty_id'] == faculty_id
        ]
        custom = [
            a for a in fetch_custom_blocks()
            if a['faculty_id'] == faculty_id
        ]
        eligibility = [
            e for e in fetch_eligibility_rows()
            if e['faculty_id'] == faculty_id
        ]
        return jsonify({
            'courses': [{
                'course_code': a['course_code'],
                'course_name': a['course_name'],
                'units': a['units'],
                'section': a['section'],
                'is_custom': a.get('is_custom', False),
                'room': a.get('room'),
            } for a in assignments + custom],
            'eligibility': eligibility,
        })
    except Exception as e:
        logger.error(f"Error fetching faculty courses: {e}")
        return jsonify({'courses': [], 'eligibility': [], 'error': str(e)}), 200


@app.route('/api/faculty/by-name/<professor_name>/courses', methods=['GET'])
@login_required
def get_faculty_courses_by_name(professor_name):
    """Section assignments for a faculty member looked up by display name."""
    try:
        school_year = request.args.get('school_year')
        semester = request.args.get('semester')
        members_result = retry_supabase_query(
            lambda: supabase.table('members').select('id, first, last')
        )

        faculty_id = None
        for member in members_result.data or []:
            full_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
            )
            if full_name == professor_name:
                faculty_id = member['id']
                break

        if not faculty_id:
            return jsonify({'courses': []})

        assignments = [
            a for a in fetch_section_assignments()
            if a['faculty_id'] == faculty_id
        ]
        custom = [
            a for a in fetch_custom_blocks()
            if a['faculty_id'] == faculty_id
        ]
        return jsonify({'courses': [{
            'course_code': a['course_code'],
            'course_name': a['course_name'],
            'units': a['units'],
            'section': a['section'],
            'is_custom': a.get('is_custom', False),
            'room': a.get('room'),
        } for a in assignments + custom]})
    except Exception as e:
        logger.error(f"Error fetching faculty courses by name: {e}")
        return jsonify({'courses': [], 'error': str(e)}), 200


@app.route('/api/faculty/<faculty_id>/courses', methods=['POST'])
@login_required
def assign_faculty_courses(faculty_id):
    """
    Save this faculty's regular (global) course+section assignments.
    The same course+section may be saved for more than one faculty.

    Body:
      assignments: [{course_code, section}, ...]
      eligibility: [course_code, ...]  — optional

    Regular allocation is not school-year specific. Custom term blocks are
    added separately via /api/allocation/offering.
    The same course+section may be shared by more than one faculty.
    """
    try:
        data = request.get_json() or {}
        assignments = data.get('assignments')
        eligibility_codes = data.get('eligibility')
        caps = allocation_capabilities()

        # Manage page still posts {course_id} to mark a faculty eligible.
        if data.get('course_id') and assignments is None and eligibility_codes is None:
            if caps['eligibility_table']:
                existing = supabase.table('faculty_eligible_courses')\
                    .select('id')\
                    .eq('faculty_id', faculty_id)\
                    .eq('course_id', data['course_id'])\
                    .execute()
                if not existing.data:
                    supabase.table('faculty_eligible_courses').insert({
                        'faculty_id': faculty_id,
                        'course_id': data['course_id'],
                    }).execute()
                return jsonify({'status': 'ok', 'eligible': True})
            return jsonify({
                'error': 'Assign a section on the courses page, or run '
                         'sql/term_assignments.sql to enable course-only eligibility.'
            }), 400

        courses_result = retry_supabase_query(
            lambda: supabase.table('courses')
            .select('id, course_code, available_sections')
        )
        course_by_code = {c['course_code']: c for c in (courses_result.data or [])}
        course_by_id = {c['id']: c for c in (courses_result.data or [])}

        if eligibility_codes is not None:
            course_ids = []
            for code in eligibility_codes:
                course = course_by_code.get(code)
                if not course:
                    return jsonify({'error': f'Course {code} not found'}), 400
                course_ids.append(course['id'])
            if not replace_faculty_eligibility(faculty_id, course_ids):
                logger.info(
                    "Eligibility table missing; section rows still record who teaches")

        if assignments is None:
            return jsonify({'status': 'ok', 'assigned_count': 0,
                            'eligibility_saved': eligibility_codes is not None})

        seen_pairs = set()
        for assignment in assignments:
            pair = (assignment.get('course_code'), assignment.get('section'))
            if pair in seen_pairs:
                return jsonify({
                    'error': f'{pair[0]} Section {pair[1]} is listed more than once'
                }), 400
            seen_pairs.add(pair)

        offerings = fetch_term_offerings()
        eligible_ids = {
            e['course_id'] for e in fetch_eligibility_rows()
            if e['faculty_id'] == faculty_id
        }

        validated_records = []
        for assignment in assignments:
            course_code = assignment.get('course_code')
            section = (assignment.get('section') or '').strip()
            if not course_code or not section:
                return jsonify({'error': 'Each assignment needs a course and a section'}), 400

            course = course_by_code.get(course_code)
            if not course:
                return jsonify({'error': f'Course {course_code} not found'}), 400

            offered = offerings.get(course['id'])
            if offered is None:
                offered = list(course.get('available_sections') or [])
            if section not in offered:
                return jsonify({
                    'error': f'Section {section} is not offered for {course_code}. '
                    f'Offered: {", ".join(offered) or "(none)"}'
                }), 400

            if caps['eligibility_table'] and course['id'] not in eligible_ids:
                # Saving eligibility in this same request should have added them.
                if eligibility_codes is None or course_code not in eligibility_codes:
                    return jsonify({
                        'error': f'This faculty is not assigned to {course_code}. '
                        'Assign them to the course before picking a section.'
                    }), 400

            record = {
                'faculty_id': faculty_id,
                'course_id': course['id'],
                'section': section,
            }
            if caps.get('faculty_courses_units'):
                try:
                    record['units'] = float(assignment.get('units')
                                            if assignment.get('units') is not None
                                            else (course.get('units') or 3))
                except (TypeError, ValueError):
                    record['units'] = float(course.get('units') or 3)
            validated_records.append(record)

        # Without the eligibility table, an empty assignments list would wipe
        # every section this faculty already has. Refuse that so "assign to a
        # course, section later" cannot destroy existing rows.
        if not validated_records and not caps['eligibility_table']:
            return jsonify({
                'status': 'ok',
                'assigned_count': 0,
                'warning': 'Pick one section to save this assignment, or run '
                           'sql/term_assignments.sql so a faculty can be assigned '
                           'to a course before a section is chosen.'
            })

        retry_supabase_query(
            lambda: supabase.table('faculty_courses').delete().eq(
                'faculty_id', faculty_id)
        )

        if validated_records:
            retry_supabase_query(
                lambda: supabase.table(
                    'faculty_courses').insert(validated_records)
            )

        logger.info(
            f"Assigned {len(validated_records)} section(s) to faculty {faculty_id}")
        return jsonify({
            'status': 'ok',
            'assigned_count': len(validated_records),
        })
    except Exception as e:
        message = str(e)
        if 'faculty_courses_course_id_section_key' in message or '23505' in message:
            return jsonify({
                'error': 'This course+section is already assigned to another faculty. '
                         'Run sql/shared_course_section.sql in the Supabase SQL editor '
                         'to allow two faculty to share it.'
            }), 409
        logger.error(f"Error assigning courses: {e}", exc_info=True)
        return jsonify({'error': message}), 500


@app.route('/api/schedule/generate-preview', methods=['GET'])
@login_required
def api_generate_preview():
    """Counts for the CHE confirm card: allocations, reference rows, existing target blocks."""
    try:
        reference_semester = (request.args.get(
            'reference_semester') or '1').strip()
        reference_school_year = (request.args.get(
            'reference_school_year') or '').strip()
        target_semester = (request.args.get('target_semester') or '1').strip()
        target_school_year = (request.args.get(
            'target_school_year') or '').strip()

        existing = 0
        reference = 0
        if target_school_year:
            existing_res = supabase.table('schedules').select('id').eq(
                'semester', str(target_semester)).eq('school_year', target_school_year).execute()
            existing = len(existing_res.data or [])
        if reference_school_year:
            ref_res = supabase.table('schedules').select('id').eq(
                'semester', str(reference_semester)).eq('school_year', reference_school_year).execute()
            reference = len(ref_res.data or [])

        regular = fetch_section_assignments()
        custom = fetch_custom_blocks()
        faculty_ids = {row.get('faculty_id') for row in (
            regular + custom) if row.get('faculty_id')}
        course_sections = {
            f"{row.get('course_code')}-{row.get('section')}"
            for row in (regular + custom)
            if row.get('course_code') and row.get('section')
        }

        return jsonify({
            'success': True,
            'existing_target_blocks': existing,
            'reference_blocks': reference,
            'allocated_course_sections': len(course_sections),
            'faculty_count': len(faculty_ids),
            'will_replace': existing > 0,
            'estimated_minutes': 4,
        })
    except Exception as e:
        logger.error(f"Generate preview error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/schedule/generate-full', methods=['POST'])
@login_required
def api_generate_full_schedule():
    """
    Full semester schedule generation using enhanced GA with Phase 2 integration.
    Runs in background with real-time progress updates.
    """
    print("=" * 80, flush=True)
    print("🎯 /api/schedule/generate-full ENDPOINT CALLED", flush=True)
    print("=" * 80, flush=True)
    logger.info("/api/schedule/generate-full called")
    try:
        from services.scheduler_service import run_full_ga_v3, FullGAConfig, SubjectInput

        data = request.get_json()

        print(f"📦 Request data received: {data}", flush=True)
        logger.info(f"� Request data: {data}")
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400

        target_semester = data.get('target_semester', '1')
        target_school_year = data.get('target_school_year', '2026-2027')
        reference_semester = data.get('reference_semester', '1')
        reference_school_year = data.get('reference_school_year', '2026-2027')
        save_to_db = data.get('save_to_db', True)

        print(
            f"🎯 Target: {target_school_year} Sem {target_semester}, Reference: {reference_school_year} Sem {reference_semester}", flush=True)
        logger.info(
            f"Target: {target_school_year} Sem {target_semester}, Reference: {reference_school_year} Sem {reference_semester}")

        # CRITICAL FIX: Capture user_id BEFORE entering background thread
        # (session is not available outside request context)
        current_user_id = session.get('user_id')

        # Check if GA is already running
        with ga_progress_lock:
            if ga_progress['running']:
                return jsonify({
                    'success': False,
                    'message': 'Schedule generation already in progress',
                    'progress': ga_progress.copy()
                }), 409  # Conflict

        # Start GA in background thread
        reset_ga_progress()
        update_ga_progress(status='starting',
                           message='Initializing GA with Phase 2...')

        def run_ga_background():
            """Run GA with Phase 2 in background thread."""
            logger.info(f"run_ga_background() started at {datetime.now()}")

            try:
                logger.info("Setting ga_progress running flag")

                with ga_progress_lock:
                    ga_progress['running'] = True

                logger.info("Updating progress: Loading reference schedules")

                update_ga_progress(
                    status='running', message='Loading reference schedules...')

                # Load reference semester schedules
                reference_schedules = []

                logger.info("About to query Supabase for reference schedules")

                try:
                    logger.info(
                        f"Querying: semester={reference_semester}, school_year={reference_school_year}")

                    ref_result = supabase.table('schedules').select('*').eq(
                        'semester', reference_semester).eq('school_year', reference_school_year).execute()

                    logger.info(
                        f"Query successful: {len(ref_result.data)} records")

                    for rd in ref_result.data:
                        reference_schedules.append({
                            'subjCode': rd.get('subj_code', rd.get('subjCode', '')),
                            'subjName': rd.get('subj_name', rd.get('subjName', '')),
                            'prof': rd.get('prof', ''),
                            'room': rd.get('room', ''),
                            'section': rd.get('section', ''),
                            'units': rd.get('units', 3),
                            'day': rd.get('day', ''),
                            'start': str(rd.get('start', '')).rsplit(':', 1)[0] if rd.get('start') and str(rd.get('start')).count(':') > 1 else rd.get('start', ''),
                            'end': str(rd.get('end', '')).rsplit(':', 1)[0] if rd.get('end') and str(rd.get('end')).count(':') > 1 else rd.get('end', ''),
                        })

                    logger.info(
                        f"Finished processing {len(reference_schedules)} reference schedules")

                except Exception as e:
                    logger.warning(f"ERROR loading reference schedules: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())

                logger.info(
                    f"Calling update_ga_progress with {len(reference_schedules)} schedules")

                update_ga_progress(
                    status='running', message=f'Loaded {len(reference_schedules)} reference schedules')

                logger.info(
                    f"📚 Reference schedules loaded: {len(reference_schedules)} from {reference_school_year} Semester {reference_semester}")

                # Load faculty data
                prof_availability = {}
                teaching_loads_map = {}
                try:
                    member_docs = db.collection('members').where(
                        'is_faculty', '==', True).stream()

                    faculty_count = 0
                    for d in member_docs:
                        faculty_count += 1
                        md = d.to_dict()
                        full_name = f"{md.get('first', '')} {md.get('last', '')}".strip(
                        )
                        if md.get('suffix'):
                            full_name += f", {md['suffix']}"
                        avail = md.get('availability', [])
                        if avail:
                            prof_availability[full_name] = avail
                        load = md.get('teaching_load')
                        if load:
                            teaching_loads_map[full_name] = int(load)

                except Exception as e:
                    logger.warning(f"ERROR loading faculty: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())

                # Load faculty course-section assignments from Supabase.
                # The same course+section may be taught by more than one faculty.
                faculty_course_assignments = {}
                # {"COURSE-SECTION": [faculty names]}
                course_section_assignments = {}
                course_catalog = {}  # {"COURSE-SECTION::faculty_id": {name, units, faculty}}
                try:
                    term_assignments = fetch_section_assignments()
                    custom_assignments = fetch_custom_blocks()

                    members_result = supabase.table('members')\
                        .select('id, first, last, suffix')\
                        .execute()

                    faculty_id_to_name = {}
                    for member in members_result.data:
                        full_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
                        )
                        if member.get('suffix'):
                            full_name += f", {member['suffix']}"
                        faculty_id_to_name[member['id']] = full_name

                    def record_ga_assignment(assignment, is_custom=False):
                        faculty_id = assignment['faculty_id']
                        course_code = assignment.get('course_code')
                        section = assignment.get('section')
                        if not course_code or not section:
                            return
                        faculty_name = faculty_id_to_name.get(faculty_id)
                        if not faculty_name:
                            return
                        course_section_key = f"{course_code}-{section}"
                        faculty_course_assignments.setdefault(
                            faculty_name, []).append(course_section_key)
                        names = course_section_assignments.setdefault(
                            course_section_key, [])
                        if faculty_name not in names:
                            names.append(faculty_name)
                        course_catalog[f"{course_section_key}::{faculty_id}"] = {
                            'code': course_code,
                            'section': section,
                            'name': assignment.get('course_name') or course_code,
                            'units': float(assignment.get('units') or 3),
                            'is_custom': is_custom,
                            'room': assignment.get('room') if is_custom else None,
                            'faculty_id': faculty_id,
                            'faculty_name': faculty_name,
                        }

                    for assignment in term_assignments:
                        record_ga_assignment(assignment, is_custom=False)
                    for assignment in custom_assignments:
                        record_ga_assignment(assignment, is_custom=True)

                    logger.info(
                        f"Loaded {len(course_catalog)} faculty course-section "
                        f"assignments ({len(course_section_assignments)} unique "
                        f"course+sections), including custom blocks")
                except Exception as e:
                    logger.warning(
                        f"Error loading faculty course assignments: {e}")
                    import traceback
                    traceback.print_exc()

                # Built-in rooms plus anything added on the courses page
                try:
                    rooms_list = get_all_rooms()
                except Exception as e:
                    logger.warning(f"Falling back to built-in rooms: {e}")
                    rooms_list = list(DEFAULT_ROOMS)

                # One GA subject per faculty share of a course+section
                subjects_dict = {}
                for key, course in course_catalog.items():
                    faculty_name = course.get('faculty_name')
                    if not faculty_name:
                        continue
                    subjects_dict[key] = {
                        'code': course['code'],
                        'name': course['name'],
                        'section': course['section'],
                        'units': course['units'],
                        'weekly_hours': course['units'],
                        'allocated_professors': [faculty_name],
                        'is_custom': bool(course.get('is_custom')),
                        'preferred_room': course.get('room'),
                    }

                def _faculty_names_match(ref_name, allocated_name):
                    if not ref_name or not allocated_name:
                        return False
                    if ref_name == allocated_name:
                        return True
                    return allocated_name.startswith(ref_name) or ref_name in allocated_name

                # Match a reference row to that faculty's share only
                filtered_reference = []
                for rs in reference_schedules:
                    matched = None
                    for key, subj in subjects_dict.items():
                        if subj['code'] != rs['subjCode'] or subj['section'] != rs['section']:
                            continue
                        if _faculty_names_match(rs.get('prof', ''), subj['allocated_professors'][0]):
                            matched = key
                            break
                    if not matched:
                        continue
                    rs = dict(rs)
                    rs['prof'] = subjects_dict[matched]['allocated_professors'][0]
                    rs['units'] = subjects_dict[matched]['units']
                    filtered_reference.append(rs)

                if len(filtered_reference) != len(reference_schedules):
                    logger.info(
                        f"Using {len(filtered_reference)} of {len(reference_schedules)} "
                        "reference rows for continuity (rest are no longer allocated)")
                reference_schedules = filtered_reference

                day_patterns = {}
                for rs in reference_schedules:
                    key = f"{rs['subjCode']}-{rs['section']}::{rs['prof']}"
                    if key not in day_patterns:
                        day_patterns[key] = {}
                    day = rs['day']
                    if day not in day_patterns[key] and len(day_patterns[key]) < 2:
                        day_patterns[key][day] = {
                            'day': day,
                            'start': rs['start'],
                            'end': rs['end'],
                            'room': rs['room']
                        }

                for key in day_patterns:
                    day_patterns[key] = list(day_patterns[key].values())[:2]

                subjects = [SubjectInput(**s) for s in subjects_dict.values()]

                allocated_keys = {
                    f"{c['code']}-{c['section']}::{c.get('faculty_name')}"
                    for c in course_catalog.values() if c.get('faculty_name')
                }
                reference_keys = set(day_patterns)
                new_this_semester = sorted(allocated_keys - reference_keys)
                dropped_from_allocation = sorted(
                    reference_keys - allocated_keys)

                logger.info(
                    f"Scheduling {len(subjects)} allocated course-sections "
                    f"({len(allocated_keys & reference_keys)} also ran in the reference semester)")
                if new_this_semester:
                    logger.info(
                        f"{len(new_this_semester)} course-section(s) are new this semester "
                        f"(no continuity reference): {', '.join(new_this_semester[:10])}")
                if dropped_from_allocation:
                    logger.info(
                        f"{len(dropped_from_allocation)} course-section(s) from the reference "
                        f"are no longer allocated and will not be scheduled: "
                        f"{', '.join(dropped_from_allocation[:10])}")

                update_ga_progress(
                    status='running', message=f'Building GA config for {len(subjects)} subjects...')

                from services.scheduler_service import QualificationMatrix
                qualification_matrix = QualificationMatrix()
                qualification_matrix.course_section_to_faculty = course_section_assignments
                qualification_matrix.faculty_to_course_sections = faculty_course_assignments

                for course_section_key, faculty_names in course_section_assignments.items():
                    names = faculty_names if isinstance(
                        faculty_names, list) else [faculty_names]
                    course_code = course_section_key.rsplit('-', 1)[0]
                    for faculty_name in names:
                        if not faculty_name:
                            continue
                        qualification_matrix.course_to_faculty.setdefault(
                            course_code, [])
                        if faculty_name not in qualification_matrix.course_to_faculty[course_code]:
                            qualification_matrix.course_to_faculty[course_code].append(
                                faculty_name)
                        qualification_matrix.faculty_to_courses.setdefault(
                            faculty_name, [])
                        if course_code not in qualification_matrix.faculty_to_courses[faculty_name]:
                            qualification_matrix.faculty_to_courses[faculty_name].append(
                                course_code)

                # Build GA config
                config = FullGAConfig(
                    subjects=subjects,
                    rooms_legacy=rooms_list,  # Use rooms_legacy for simple string list
                    prof_availability=prof_availability,
                    teaching_loads=teaching_loads_map,
                    reference_schedules=reference_schedules,
                    qualification_matrix=qualification_matrix,  # ADD QUALIFICATION MATRIX
                    pop_size=100,
                    max_generations=500,
                    time_limit_seconds=240.0
                )

                # Progress callback
                def progress_callback(progress):
                    feasible = 'conflict-free' if progress.is_feasible else \
                        f'{int(progress.best_hard_penalty // 1000)} conflicts'
                    update_ga_progress(
                        status='running',
                        generation=progress.generation,
                        best_fitness=progress.best_score,
                        message=f'Gen {progress.generation}: fitness {progress.best_score:.1f} ({feasible})',
                        hard_viols=progress.best_hard_penalty,
                        soft_viols=progress.best_soft_penalty,
                        time_elapsed=progress.elapsed_seconds
                    )

                # RUN PHASE 2 GA!
                update_ga_progress(
                    status='running', message='Starting schedule optimization...',
                    max_generations=config.max_generations,
                    time_limit_seconds=config.time_limit_seconds)

                logger.info("About to call run_full_ga_v3()")
                logger.info(
                    f"Config: {len(subjects)} subjects, {len(rooms_list)} rooms")

                logger.info(f"� About to call run_full_ga_v3()")
                logger.info(
                    f"� Config: {len(subjects)} subjects, {len(rooms_list)} rooms")

                result = run_full_ga_v3(
                    config, progress_callback=progress_callback)

                logger.info(
                    f"run_full_ga_v3() returned: success={result.get('success')}")

                logger.info(
                    f"run_full_ga_v3() returned: success={result.get('success')}, message={result.get('message')}")

                logger.info(
                    f"run_full_ga_v3() returned: success={result.get('success')}, message={result.get('message')}")

                if result['success']:
                    schedules = result.get('schedules', [])

                    logger.info(
                        f"GA returned {len(schedules)} meeting rows (paired days already expanded)")

                    # Schedules already include both days of MW/TTH/WF pairs.

                    logger.info(
                        "Checking generated rows for exact professor double-bookings")
                    conflict_check = []
                    leftover_conflicts = []
                    for sched in schedules:
                        prof = sched.get('prof', '')
                        day = sched.get('day', '')
                        start = sched.get('start', '')
                        end = sched.get('end', '')
                        for existing in conflict_check:
                            if (existing['prof'] == prof and
                                existing['day'] == day and
                                existing['start'] == start and
                                    existing['end'] == end):
                                leftover_conflicts.append(
                                    f"{prof}: {sched.get('subjCode')} vs {existing['subjCode']} on {day} {start}-{end}"
                                )
                        conflict_check.append({
                            'prof': prof, 'day': day, 'start': start, 'end': end,
                            'subjCode': sched.get('subjCode')
                        })

                    if leftover_conflicts:
                        logger.warning(
                            f"{len(leftover_conflicts)} overlapping meeting(s) remain; saving best-effort timetable"
                        )
                        for msg in leftover_conflicts[:5]:
                            logger.warning(f"  {msg}")
                    else:
                        logger.info(
                            "No exact professor double-bookings in generated rows")

                    # Save directly to main schedules table (so users can see and review on timetable)
                    if save_to_db and schedules:
                        logger.info(
                            f"Starting save: {len(schedules)} schedules to main schedules table")

                        update_ga_progress(
                            status='running', message=f'Saving {len(schedules)} schedules to timetable...')

                        saved = 0
                        save_errors = []

                        # Clear any existing schedules for this semester first
                        try:
                            logger.info(
                                f"Clearing old schedules for {target_school_year} Semester {target_semester}")
                            delete_result = supabase.table('schedules').delete().eq(
                                'semester', str(target_semester)).eq('school_year', target_school_year).execute()
                            logger.info(f"Cleared old schedules")
                        except Exception as e:
                            logger.warning(
                                f"Error clearing old schedules: {e}")

                        # BATCH INSERT: Prepare all schedule records first
                        schedule_records = []
                        for idx, sched in enumerate(schedules):
                            try:
                                new_id = str(uuid.uuid4())
                                # CRITICAL: Normalize room names to consistent format (TCC - 01, not TCC-01)
                                room_name = sched.get('room', '')
                                import re
                                normalized_room = re.sub(
                                    # TCC-01 → TCC - 01
                                    r'(\w+)-(\d+)', r'\1 - \2', room_name)

                                schedule_data = {
                                    'id': new_id,
                                    'subj_code': sched.get('subjCode', ''),
                                    'subj_name': sched.get('subjName', ''),
                                    'prof': sched.get('prof', ''),
                                    'room': normalized_room,
                                    'section': sched.get('section', ''),
                                    'units': float(sched.get('units', 0)) if sched.get('units') else 0,
                                    'day': sched.get('day', ''),
                                    'start': sched.get('start', ''),
                                    'end': sched.get('end', ''),
                                    'type': 'Lecture',
                                    'semester': str(target_semester),
                                    'school_year': target_school_year,
                                    'year': '1',
                                    'source': 'GA Generated',
                                    'created_at': datetime.now(timezone.utc).isoformat(),
                                    'pairedWith': None
                                }
                                schedule_records.append(schedule_data)

                                # Log first schedule for debugging
                                if idx == 0:
                                    logger.info(
                                        f"First schedule data: {schedule_data}")
                            except Exception as e:
                                error_msg = f"Failed to prepare schedule {idx}: {e}"
                                logger.error(error_msg)
                                save_errors.append(error_msg)

                        logger.info(
                            f"Prepared {len(schedule_records)} schedule records for batch insert")

                        # Insert in chunks of 100. Retry without `source` if that column is not in the schema yet.
                        chunk_size = 100
                        include_source = True
                        i = 0
                        while i < len(schedule_records):
                            chunk = schedule_records[i:i + chunk_size]
                            try:
                                supabase.table('schedules').insert(
                                    chunk).execute()
                                saved += len(chunk)
                                logger.info(
                                    f"Batch inserted chunk {i//chunk_size + 1}: {len(chunk)} schedules (total: {saved})")
                                i += chunk_size
                            except Exception as e:
                                err = str(e)
                                if include_source and ('source' in err.lower() or 'PGRST204' in err):
                                    logger.warning(
                                        'schedules.source is missing; saving without the GA label. '
                                        'Run sql/schedule_source.sql in Supabase.')
                                    include_source = False
                                    for rec in schedule_records:
                                        rec.pop('source', None)
                                    continue
                                error_msg = f"Failed to insert batch starting at {i}: {e}"
                                logger.error(error_msg)
                                save_errors.append(error_msg)
                                i += chunk_size

                        logger.info(
                            f"Saved {saved} schedules to main schedules table (Target: {target_school_year} Semester {target_semester})")

                        if save_errors:
                            logger.error(
                                f"{len(save_errors)} schedules failed to save:")
                            for err in save_errors[:5]:  # Log first 5 errors
                                logger.error(f"  - {err}")

                        if saved == 0:
                            update_ga_progress(
                                status='failed',
                                message=('Schedule was generated but nothing could be saved: '
                                         f'{save_errors[0] if save_errors else "database insert returned no rows"}')
                            )
                            return

                        requested = result.get('course_sections_requested', 0)
                        scheduled = result.get('course_sections_scheduled', 0)
                        summary = (f'Generated {saved} schedule entries for {target_school_year} '
                                   f'Semester {target_semester}')
                        if requested:
                            summary += f' covering {scheduled} of {requested} allocated course-sections'
                        summary += '. Review them on the timetable.'

                        unscheduled = result.get(
                            'unscheduled_course_sections') or []
                        if unscheduled:
                            summary += (f' {len(unscheduled)} could not be placed: '
                                        + ', '.join(unscheduled[:5])
                                        + (' ...' if len(unscheduled) > 5 else ''))
                        if save_errors:
                            summary += f' ({len(save_errors)} batch(es) failed to save — check server logs.)'

                        update_ga_progress(
                            status='completed',
                            message=summary,
                            hard_viols=result.get('hard_violations', 0),
                            soft_viols=result.get('soft_violations', 0),
                            schedules=schedules  # Include schedules for frontend to display
                        )
                    elif not schedules:
                        update_ga_progress(
                            status='failed',
                            message='Generation finished but produced no schedule entries.'
                        )
                    else:
                        update_ga_progress(
                            status='completed',
                            message=(f'Generated {len(schedules)} schedule entries. '
                                     'Saving to the database was turned off for this run.'),
                            schedules=schedules
                        )
                else:
                    update_ga_progress(
                        status='failed',
                        message=f'❌ Generation failed: {result.get("message", "Unknown error")}'
                    )

            except Exception as e:
                logger.error(f"GA background error: {e}")
                import traceback
                traceback.print_exc()
                update_ga_progress(
                    status='failed',
                    message=f'❌ Error: {str(e)}'
                )
            finally:
                with ga_progress_lock:
                    ga_progress['running'] = False

        # Start background thread WITH app context
        print("=" * 80, flush=True)
        print("🎬 About to create background thread...", flush=True)
        print("=" * 80, flush=True)
        logger.info(f"🎬 About to create background thread...")

        def run_with_context():
            logger.info(f"Thread started at {datetime.now()}")

            print("🚀 Background thread started, acquiring app context...", flush=True)
            logger.info(
                f"🧵 Background thread started, acquiring app context...")
            try:
                with app.app_context():
                    print("✅ App context acquired, starting GA...", flush=True)
                    logger.info("App context acquired, starting GA...")
                    run_ga_background()
            except Exception as e:
                logger.error(f"ERROR in thread: {e}")
                import traceback
                logger.error(traceback.format_exc())

                print(f"❌ Fatal error in background thread: {e}", flush=True)
                logger.error(f"❌ Fatal error in background thread: {e}")
                import traceback
                traceback.print_exc()

        print("🔧 Creating thread object...", flush=True)
        logger.info(f"🔧 Creating thread object...")
        thread = threading.Thread(target=run_with_context, daemon=True)

        print("▶️ Starting thread...", flush=True)
        logger.info("Starting thread...")
        thread.start()

        print("📤 Background thread dispatched", flush=True)
        logger.info(f"📤 Background thread dispatched")

        return jsonify({
            'success': True,
            'message': 'Schedule generation started with Phase 2',
            'note': 'Poll /api/schedule/generate-progress. Completed runs are written to the schedules table and labeled GA Generated.'
        })

    except Exception as e:
        logger.error(f"Generate full schedule error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/schedule/save-generated', methods=['POST'])
@login_required
def api_save_generated_schedule():
    """
    Acknowledge completion of schedule generation.
    Schedules are already saved to main table during generation,
    so this just returns a success message.
    """
    try:
        data = request.get_json()
        school_year = data.get('school_year')
        semester = data.get('semester')

        if not school_year or not semester:
            return jsonify({'success': False, 'message': 'School year and semester required'}), 400

        # Verify schedules exist in main table
        result = supabase.table('schedules').select('id').eq(
            'school_year', school_year).eq('semester', str(semester)).limit(1).execute()

        if not result.data:
            return jsonify({'success': False, 'message': f'No schedules found for {school_year} Semester {semester}'}), 404

        # Count total schedules for this semester
        count_result = supabase.table('schedules').select('id', count='exact').eq(
            'school_year', school_year).eq('semester', str(semester)).execute()

        schedule_count = count_result.count if hasattr(
            count_result, 'count') else len(count_result.data)

        return jsonify({
            'success': True,
            'message': f'✅ Generation complete! {schedule_count} schedules are now on the timetable for {school_year} Semester {semester}.',
            'count': schedule_count
        })

    except Exception as e:
        logger.error(f"Error confirming saved schedules: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Generate full schedule error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/schedule/generate-progress', methods=['GET'])
@login_required
def get_ga_progress():
    """Poll GA generation progress."""
    with ga_progress_lock:
        progress_data = ga_progress.copy()
        # Convert infinity to None for JSON serialization
        if progress_data.get('best_fitness') == float('inf'):
            progress_data['best_fitness'] = None
        return jsonify(progress_data)


# ── AI Chat API ────────────────────────────────────────────────

# ── Dashboard Stats API ────────────────────────────────────────

@app.route('/api/debug/extensions', methods=['GET'])
@login_required
def debug_extensions():
    """Debug endpoint to see actual extension types in database."""
    try:
        ext_docs = db.collection('extensions').stream()
        extensions = []
        for d in ext_docs:
            ed = d.to_dict()
            extensions.append({
                'id': d.id,
                'type': ed.get('type', ''),
                'type_repr': repr(ed.get('type', '')),
                'created_at': ed.get('created_at', ''),
                'title': ed.get('title', '')
            })
        return jsonify({'extensions': extensions, 'count': len(extensions)})
    except Exception as e:
        logger.error(f"debug_extensions error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/forecast', methods=['GET'])
@login_required
def dashboard_forecast():
    """Yearly ARIMA outlook for papers, projects, extensions, and FSRs."""
    try:
        from services.forecast_service import build_forecast_payload

        uid = session.get('uid')
        role = session.get('role')
        scope = (request.args.get('scope') or '').strip().lower()
        member_id = None
        filter_uid = None

        if role != 'admin' or scope == 'member':
            member_response = supabase.table('members').select(
                'id').eq('uid', uid).execute()
            if member_response.data:
                member_id = member_response.data[0]['id']
            filter_uid = uid

        payload = build_forecast_payload(
            supabase, db, member_id=member_id, uid=filter_uid)
        return jsonify(payload)
    except Exception as e:
        logger.error(f"dashboard_forecast error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    """Return real counts for dashboard charts (research by month + extensions count)."""
    try:
        from collections import defaultdict

        # Research/publications by month for current year
        research_docs = db.collection('research').stream()
        monthly_counts = defaultdict(int)
        for d in research_docs:
            rd = d.to_dict()
            created = rd.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if dt.year == datetime.now(timezone.utc).year:
                        monthly_counts[dt.month] += 1
                except (ValueError, TypeError):
                    pass

        pub_this_year = [monthly_counts.get(m, 0) for m in range(1, 13)]

        # Extensions submitted count (total number of all member-submitted extensions)
        ext_docs = db.collection('extensions').stream()
        total_extensions = sum(1 for _ in ext_docs)

        return jsonify({
            'pub_this_year': pub_this_year,
            # [total_extensions, 0, 0] for now - can be expanded later
            'tap': [total_extensions, 0, 0]
        })
    except Exception as e:
        return jsonify({'pub_this_year': [0]*12, 'tap': [0, 0, 0], 'error': str(e)})


@app.route('/api/dashboard/stats-by-year', methods=['GET'])
@login_required
def dashboard_stats_by_year():
    """Return chart data grouped by year for admin dashboard (2000 to current year)."""
    try:
        from collections import defaultdict

        current_year = datetime.now(timezone.utc).year
        publications_by_year = {}
        extensions_by_year = {}

        # Initialize years from 2000 to current
        for year in range(2000, current_year + 1):
            publications_by_year[year] = {
                'proposal': [0] * 12,
                'implementation': [0] * 12,
                'oral_poster': [0] * 12,
                'proceedings': [0] * 12,
                'monographs': [0] * 12,
                'journals': [0] * 12,
                'chapters': [0] * 12,
                'books': [0] * 12,
            }
            extensions_by_year[year] = {
                'extensions': 0,
                'training': 0,
                'information_dissemination': 0,
                'workshop': 0,
                'symposium': 0,
                'others': 0
            }

        # Count research/publications by year, month, and type
        research_docs = db.collection('research').stream()
        for d in research_docs:
            rd = d.to_dict()
            created = rd.get('created_at', '')
            # Default to implementation
            research_type = rd.get('research_type', 'implementation')

            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    year = dt.year
                    if 2000 <= year <= current_year:
                        if research_type in publications_by_year[year]:
                            publications_by_year[year][research_type][dt.month - 1] += 1
                        else:
                            # If type not recognized, count as implementation
                            publications_by_year[year]['implementation'][dt.month - 1] += 1
                except (ValueError, TypeError):
                    pass

        # Count extensions by type and year
        ext_docs = db.collection('extensions').stream()
        for d in ext_docs:
            ed = d.to_dict()
            # Read from 'extension_type' field (the actual column in database)
            ext_type_raw = ed.get('extension_type', '').strip()
            ext_type = ext_type_raw.lower()

            # Get the date - try multiple fields
            created = ed.get('created_at') or ed.get(
                'start_date') or ed.get('date_submitted')

            # Debug logging
            logger.info(
                f"Extension ID: {d.id}, Type raw: '{ext_type_raw}', Normalized: '{ext_type}', Date: {created}")

            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    year = dt.year
                    if 2000 <= year <= current_year:
                        # Map extension types (case-insensitive with multiple variations)
                        if ext_type in ['extensions', 'extension', 'extension/community service', 'community service']:
                            extensions_by_year[year]['extensions'] += 1
                            logger.info(
                                f"✓ Counted as 'extensions' for year {year}")
                        elif ext_type == 'training':
                            extensions_by_year[year]['training'] += 1
                            logger.info(
                                f"✓ Counted as 'training' for year {year}")
                        elif ext_type in ['information_dissemination', 'information dissemination']:
                            extensions_by_year[year]['information_dissemination'] += 1
                            logger.info(
                                f"✓ Counted as 'information_dissemination' for year {year}")
                        elif ext_type == 'workshop':
                            extensions_by_year[year]['workshop'] += 1
                            logger.info(
                                f"✓ Counted as 'workshop' for year {year}")
                        elif ext_type == 'symposium':
                            extensions_by_year[year]['symposium'] += 1
                            logger.info(
                                f"✓ Counted as 'symposium' for year {year}")
                        else:
                            logger.warning(
                                f"✗ Extension type '{ext_type_raw}' (normalized: '{ext_type}') NOT recognized, categorizing as 'others'")
                            extensions_by_year[year]['others'] += 1
                    else:
                        logger.info(
                            f"Extension year {year} outside range 2000-{current_year}")
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Date parsing error for extension {d.id}: {e}, date value: {created}")
            else:
                logger.warning(
                    f"Extension {d.id} has no date field (checked: created_at, start_date, date_submitted)")

        return jsonify({
            'publications_by_year': publications_by_year,
            'extensions_by_year': extensions_by_year
        })
    except Exception as e:
        logger.error(f"dashboard_stats_by_year error: {e}")
        return jsonify({'publications_by_year': {}, 'extensions_by_year': {}, 'error': str(e)}), 500


@app.route('/api/news', methods=['GET'])
def get_news():
    """Return all news/events from Firestore for public display."""
    try:
        docs = db.collection('news').order_by(
            'created_at', direction='DESCENDING').stream()
        news = [{'id': d.id, **d.to_dict()} for d in docs]
        return jsonify(news)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/news', methods=['POST'])
@login_required
def add_news():
    """Add a new news/event entry."""
    try:
        from services.cloudinary_service import upload_member_photo

        news_id = str(uuid.uuid4())

        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        media_type = request.form.get('media_type', 'text')

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        news = {
            'title': title,
            'description': description,
            'media_type': media_type,
            'media_url': None,
            'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }

        # Upload media if provided
        if media_type == 'image':
            media = request.files.get('media')
            if media and media.filename:
                url, err = upload_member_photo(media.stream, f'news_{news_id}')
                if err:
                    return jsonify({'error': f'Media upload failed: {err}'}), 500
                news['media_url'] = url
        elif media_type == 'video':
            # For video, store the URL directly
            video_url = request.form.get('video_url', '').strip()
            if video_url:
                news['media_url'] = video_url

        # Save to Firestore
        db.collection('news').document(news_id).set(news)
        return jsonify({'status': 'ok', 'id': news_id, 'news': news}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/news/<news_id>', methods=['DELETE'])
@login_required
def delete_news(news_id):
    """Delete a news/event entry."""
    try:
        doc = db.collection('news').document(news_id).get()
        if not doc.exists:
            return jsonify({'error': 'News not found.'}), 404

        news_data = doc.to_dict()

        # Delete media from Cloudinary if it's an image
        if news_data.get('media_type') == 'image' and news_data.get('media_url'):
            from services.cloudinary_service import delete_member_photo
            delete_member_photo(f'news_{news_id}')

        # Delete from Firestore
        db.collection('news').document(news_id).delete()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Public Engagements API ───────────────────────────────────

@app.route('/api/engagements', methods=['GET'])
@login_required
def get_engagements():
    """Return all public engagements from Firestore."""
    try:
        docs = db.collection('engagements').order_by('created_at').stream()
        engagements = [{'id': d.id, **d.to_dict()} for d in docs]
        return jsonify(engagements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/engagements', methods=['POST'])
@login_required
def add_engagement():
    """Add a new public engagement."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        engagement_id = str(uuid.uuid4())
        engagement = {
            'type': data.get('type', '').strip(),
            'designation': data.get('designation', '').strip(),
            'event_name': data.get('event_name', '').strip(),
            'partner': data.get('partner', '').strip(),
            'person_involved': data.get('person_involved', '').strip(),
            'period': data.get('period', '').strip(),
            'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }

        # Validate required fields
        if not all([engagement['type'], engagement['designation'], engagement['event_name'],
                    engagement['partner'], engagement['person_involved'], engagement['period']]):
            return jsonify({'error': 'All fields are required.'}), 400

        db.collection('engagements').document(engagement_id).set(engagement)
        return jsonify({'status': 'ok', 'id': engagement_id, 'engagement': engagement}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/engagements/<engagement_id>', methods=['DELETE'])
@login_required
def delete_engagement(engagement_id):
    """Delete a public engagement."""
    try:
        doc = db.collection('engagements').document(engagement_id).get()
        if not doc.exists:
            return jsonify({'error': 'Engagement not found.'}), 404

        db.collection('engagements').document(engagement_id).delete()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── TAP-HSP Projects API ─────────────────────────────────────

@app.route('/api/tap-projects', methods=['GET'])
@login_required
def get_tap_projects():
    """Return all TAP-HSP projects from Firestore."""
    try:
        docs = db.collection('tap_projects').order_by('created_at').stream()
        projects = [{'id': d.id, **d.to_dict()} for d in docs]
        return jsonify(projects)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tap-projects', methods=['POST'])
@login_required
def add_tap_project():
    """Add a new TAP-HSP project."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        project_id = str(uuid.uuid4())
        project = {
            'title': data.get('title', '').strip(),
            'province': data.get('province', '').strip(),
            'municipality': data.get('municipality', '').strip(),
            'period': data.get('period', '').strip(),
            'partner_agency': data.get('partner_agency', '').strip(),
            'person_involved': data.get('person_involved', '').strip(),
            'role': data.get('role', '').strip(),
            'document_url': data.get('document_url'),
            'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }

        # Validate required fields
        if not all([project['title'], project['province'], project['municipality'],
                    project['period'], project['partner_agency'], project['person_involved'], project['role']]):
            return jsonify({'error': 'All required fields must be filled.'}), 400

        db.collection('tap_projects').document(project_id).set(project)
        return jsonify({'status': 'ok', 'id': project_id, 'project': project}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tap-projects/<project_id>', methods=['DELETE'])
@login_required
def delete_tap_project(project_id):
    """Delete a TAP-HSP project."""
    try:
        doc = db.collection('tap_projects').document(project_id).get()
        if not doc.exists:
            return jsonify({'error': 'Project not found.'}), 404

        db.collection('tap_projects').document(project_id).delete()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── AI Chat API ────────────────────────────────────────────────

@app.route('/api/chat/process', methods=['POST'])
@login_required
def process_chat_message():
    """Process natural language chat message and execute scheduling action"""
    try:
        from services.nlp_service import process_message
        from services.scheduler_service import run_ga

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        message = data.get('message', '').strip()
        if not message:
            return jsonify({'error': 'Empty message.'}), 400

        # Get current semester/year from request (passed from frontend)
        current_school_year = data.get('school_year') or data.get('schoolYear')
        current_semester = data.get('semester')

        # Get current schedules for context - FILTERED BY CURRENT SEMESTER/YEAR
        current_schedules = []
        query = supabase.table('schedules').select('*')

        # Filter by semester/year if provided
        if current_school_year:
            query = query.eq('school_year', current_school_year)
        if current_semester:
            query = query.eq('semester', str(current_semester))

        result = query.execute()
        for sched_data in result.data:
            current_schedules.append(sched_data)

        # DEBUG LOGGING
        print(f"\n=== CHAT DEBUG ===")
        print(f"Received school_year: {current_school_year}")
        print(f"Received semester: {current_semester}")
        print(f"Total schedules fetched: {len(current_schedules)}")
        if current_schedules:
            print(f"Sample schedule: {current_schedules[0]}")

        # Process message with NLP
        intent_data = process_message(message)
        intent_type = intent_data.get('intent')
        params = intent_data.get('params', {})
        confidence = intent_data.get('confidence', 0.0)

        # DEBUG LOGGING
        print(f"Message: '{message}'")
        print(f"Intent: {intent_type}")
        print(f"Params: {params}")
        print(f"Confidence: {confidence}")

        response = {
            'status': 'ok',
            'intent': intent_type,
            'confidence': confidence,
            'action': None,
            'message': '',
            'data': {}
        }

        # Execute action based on intent
        if intent_type == 'generate_full':
            response['action'] = 'generate_full'
            response['message'] = "I'll generate a full schedule using the Genetic Algorithm. Please provide the subjects, professors, and constraints, or I can work with the existing data."
            response['data'] = {'requires_input': True}

        elif intent_type == 'add_schedule':
            response['action'] = 'add_schedule'
            if params and 'professor' in params:
                # We have enough info, try to add with GA
                from services.scheduler_service import add_schedule_smart

                schedule_to_add = {
                    'subjCode': params.get('subject_code', 'TBA'),
                    'subjName': params.get('subject_name', params.get('subject_code', 'TBA')),
                    'prof': params['professor'],
                    'room': params.get('room', 'TBA'),
                    'section': params.get('section', 'TBA'),
                    'units': params.get('units', 1.5)
                }

                success, msg, result = add_schedule_smart(
                    schedule_to_add, current_schedules)

                if success:
                    response['message'] = msg + " Ready to add!"
                    response['data'] = {'schedule': result, 'should_add': True}
                else:
                    response['message'] = msg
                    response['data'] = {'error': True}
            else:
                response['message'] = "I can add a schedule block. Please provide at least: professor name. Optional: subject code, room, section."
                response['data'] = {'requires_input': True, 'provided': params}

        elif intent_type == 'remove_schedule':
            response['action'] = 'remove_schedule'
            # Find matching schedules
            matches = []
            for sched in current_schedules:
                match = True
                if 'professor' in params and params['professor'].lower() not in sched.get('prof', '').lower():
                    match = False
                if 'subject_code' in params and params['subject_code'] not in sched.get('subjCode', ''):
                    match = False
                if 'day' in params and params['day'] != sched.get('day'):
                    match = False
                if match:
                    matches.append(sched)

            if matches:
                response['message'] = f"Found {len(matches)} schedule(s) matching your criteria. I'll remove them."
                response['data'] = {
                    'schedules_to_remove': [s['id'] for s in matches]}
            else:
                response['message'] = "I couldn't find any schedules matching your criteria. Can you be more specific?"
                response['data'] = {'requires_clarification': True}

        elif intent_type == 'move_schedule':
            response['action'] = 'move_schedule'
            # Find matching schedules
            matches = []
            for sched in current_schedules:
                match = True
                if 'professor' in params and params['professor'].lower() not in sched.get('prof', '').lower():
                    match = False
                if 'subject_code' in params and params['subject_code'] not in sched.get('subjCode', ''):
                    match = False
                if match:
                    matches.append(sched)

            if matches:
                from services.scheduler_service import move_schedule_smart

                # Move each matching schedule
                moved_schedules = []
                for sched in matches:
                    success, msg, result = move_schedule_smart(
                        sched['id'],
                        current_schedules,
                        target_day=params.get('target_day'),
                        target_time_period=params.get('target_time_period')
                    )
                    if success and result:
                        moved_schedules.append(result)

                if moved_schedules:
                    target_info = []
                    if 'target_day' in params:
                        target_info.append(f"to {params['target_day']}")
                    if 'target_time_period' in params:
                        target_info.append(
                            f"in the {params['target_time_period']}")

                    response['message'] = f"Successfully moved {len(moved_schedules)} schedule(s) {' '.join(target_info)}!"
                    response['data'] = {
                        'schedules_to_move': moved_schedules,
                        'should_update': True
                    }
                else:
                    response['message'] = "Could not find conflict-free slots for the move. Try a different time or day."
                    response['data'] = {'error': True}
            else:
                response['message'] = "I couldn't find any schedules matching your criteria."
                response['data'] = {'requires_clarification': True}

        elif intent_type == 'show_conflicts':
            response['action'] = 'show_conflicts'
            # Check for conflicts
            conflicts = []
            for i, sched1 in enumerate(current_schedules):
                for sched2 in current_schedules[i+1:]:
                    if sched1['day'] == sched2['day']:
                        # Check time overlap
                        if (sched1['start'] < sched2['end'] and sched1['end'] > sched2['start']):
                            # Check if same professor or same room
                            if sched1['prof'] == sched2['prof']:
                                conflicts.append({
                                    'type': 'professor',
                                    'professor': sched1['prof'],
                                    'schedule1': sched1,
                                    'schedule2': sched2
                                })
                            if sched1['room'] == sched2['room']:
                                conflicts.append({
                                    'type': 'room',
                                    'room': sched1['room'],
                                    'schedule1': sched1,
                                    'schedule2': sched2
                                })

            if conflicts:
                response['message'] = f"I found {len(conflicts)} conflict(s) in the schedule."
                response['data'] = {'conflicts': conflicts}
            else:
                response['message'] = "Great news! I didn't find any conflicts in the current schedule."
                response['data'] = {'conflicts': []}

        elif intent_type == 'modify_constraint':
            response['action'] = 'modify_constraint'
            response['message'] = f"I'll apply the constraint: {params}"
            response['data'] = params

        elif intent_type == 'query_info':
            response['action'] = 'query_info'
            query_type = params.get('query_type', 'general')

            if query_type == 'conflicts':
                response['message'] = "Let me check for conflicts..."
                # Reuse conflict detection logic
                response['data'] = {'redirect_to': 'show_conflicts'}
            elif query_type == 'professor_schedule':
                prof = params.get('professor', '')
                prof_schedules = [
                    s for s in current_schedules if prof.lower() in s.get('prof', '').lower()]
                response['message'] = f"Found {len(prof_schedules)} schedule(s) for {prof}."
                response['data'] = {'schedules': prof_schedules}
            else:
                response['message'] = f"Current schedule has {len(current_schedules)} blocks."
                response['data'] = {'total_schedules': len(current_schedules)}

        # NEW: Handle enhanced query intents with human-like responses
        elif intent_type in ['query_schedule_by_day', 'query_faculty_schedule', 'query_faculty_load', 'query_free_slots', 'query_faculty_free_time']:
            from services.nlp_service import generate_human_response_for_schedules, generate_human_response_for_free_time

            response['action'] = 'query_result'

            if intent_type == 'query_schedule_by_day':
                day = params.get('day')
                day_schedules = [
                    s for s in current_schedules if s.get('day') == day]
                response['message'] = generate_human_response_for_schedules(
                    day_schedules, 'schedule_by_day', params)
                response['data'] = {'schedules': day_schedules}

            elif intent_type == 'query_faculty_schedule':
                faculty_name = params.get('faculty_name', '')
                day = params.get('day')

                # Flexible matching: match if any part of the name matches
                faculty_name_parts = faculty_name.lower().split()
                faculty_schedules = [
                    s for s in current_schedules
                    if any(part in s.get('prof', '').lower() for part in faculty_name_parts)
                ]
                if day:
                    # Case-insensitive day matching
                    faculty_schedules = [
                        s for s in faculty_schedules if s.get('day', '').lower() == day.lower()]
                response['message'] = generate_human_response_for_schedules(
                    faculty_schedules, 'faculty_schedule', params)
                response['data'] = {'schedules': faculty_schedules}

            elif intent_type == 'query_faculty_load':
                faculty_name = params.get('faculty_name', '')

                # Flexible matching: match if any part of the name matches
                faculty_name_parts = faculty_name.lower().split()
                faculty_schedules = [
                    s for s in current_schedules
                    if any(part in s.get('prof', '').lower() for part in faculty_name_parts)
                ]
                response['message'] = generate_human_response_for_schedules(
                    faculty_schedules, 'faculty_load', params)
                response['data'] = {'schedules': faculty_schedules}

            elif intent_type == 'query_faculty_free_time':
                faculty_name = params.get('faculty_name', '')
                day = params.get('day')

                # DEBUG LOGGING
                print(f"\n=== FACULTY FREE TIME QUERY ===")
                print(f"Faculty name from params: {faculty_name}")
                print(f"Day from params: {day}")

                # Flexible matching: match if any part of the name matches
                faculty_name_parts = faculty_name.lower().split()
                print(f"Name parts for matching: {faculty_name_parts}")

                faculty_schedules = [
                    s for s in current_schedules
                    if any(part in s.get('prof', '').lower() for part in faculty_name_parts)
                ]
                print(f"Schedules after name match: {len(faculty_schedules)}")
                if faculty_schedules:
                    print(
                        f"Sample matched schedule: prof='{faculty_schedules[0].get('prof')}', day='{faculty_schedules[0].get('day')}'")

                if day:
                    # Case-insensitive day matching
                    before_day_filter = len(faculty_schedules)
                    faculty_schedules = [
                        s for s in faculty_schedules if s.get('day', '').lower() == day.lower()]
                    print(
                        f"Schedules after day filter ({day}): {before_day_filter} -> {len(faculty_schedules)}")
                    if faculty_schedules:
                        print(
                            f"Monday schedules found: {[s.get('start', '') + '-' + s.get('end', '') for s in faculty_schedules]}")

                # Calculate free periods (simplified - gaps between classes)
                free_periods = []
                if faculty_schedules:
                    # Sort by day and start time
                    sorted_scheds = sorted(faculty_schedules, key=lambda x: (
                        x.get('day', ''), x.get('start', '')))

                    # Find gaps (this is simplified - you might want more sophisticated logic)
                    for i in range(len(sorted_scheds) - 1):
                        current = sorted_scheds[i]
                        next_sched = sorted_scheds[i + 1]

                        # If same day and there's a gap
                        if current.get('day') == next_sched.get('day'):
                            gap_start = current.get('end')
                            gap_end = next_sched.get('start')
                            # Only include significant gaps (more than 30 mins)
                            if gap_start and gap_end:
                                free_periods.append({
                                    'day': current.get('day'),
                                    'start': gap_start,
                                    'end': gap_end
                                })

                response['message'] = generate_human_response_for_free_time(
                    faculty_name, free_periods, day, has_schedules=len(faculty_schedules) > 0)
                response['data'] = {
                    'free_periods': free_periods, 'schedules': faculty_schedules}

            elif intent_type == 'query_free_slots':
                day = params.get('day')
                response['message'] = generate_human_response_for_schedules(
                    current_schedules, 'free_slots', params)
                response['data'] = {'schedules': current_schedules}

        else:
            response['message'] = "I'm not sure what you want me to do. Try asking me to:\n- Generate a full schedule\n- Add a class\n- Remove a class\n- Move a class\n- Show conflicts"
            response['data'] = {'suggestions': [
                'Generate a full schedule',
                'Add ENRP 101 on Monday at 8am',
                'Remove Dr. Santos from Tuesday',
                'Move Dr. Cruz to afternoons',
                'Show conflicts'
            ]}

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── User (member) dashboard ────────────────────────────────────

@app.route('/api/member-fsr-data')
def member_fsr_data():
    """Return FSR data (research, extensions, schedules) for the logged-in member."""
    if 'uid' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    try:
        uid = session['uid']
        email = session.get('email', '')

        # Member profile
        member_doc = db.collection('members').document(uid).get()
        if not member_doc.exists:
            # Try finding by email
            docs = list(db.collection('members').where(
                'email', '==', email).stream())
            member_data = docs[0].to_dict() if docs else {}
        else:
            member_data = member_doc.to_dict()

        # Research
        research_docs = db.collection(
            'research').where('uid', '==', uid).stream()
        research = [d.to_dict() for d in research_docs]

        # Extensions
        ext_docs = db.collection('extensions').where('uid', '==', uid).stream()
        extensions = [d.to_dict() for d in ext_docs]

        # Schedules — match by last name and filter by semester/year if provided
        semester = request.args.get('semester')
        school_year = request.args.get('school_year')

        last_name = (member_data.get('last') or '').strip().lower()
        schedules = []
        if last_name:
            # Build query with optional filters
            query = supabase.table('schedules').select('*')

            # Apply filters if provided
            if semester:
                query = query.eq('semester', semester)
            if school_year:
                query = query.eq('school_year', school_year)

            all_sched = query.execute()

            for s in (all_sched.data or []):
                prof = (s.get('prof') or '').lower()
                if last_name in prof:
                    schedules.append({
                        'subjCode': s.get('subj_code') or s.get('subjCode', ''),
                        'subjName': s.get('subj_name') or s.get('subjName', ''),
                        'room':     s.get('room', ''),
                        'day':      s.get('day', ''),
                        'start':    s.get('start', ''),
                        'end':      s.get('end', ''),
                        'section':  s.get('section', ''),
                        'units':    s.get('units', ''),
                        'semester': s.get('semester', ''),
                        'school_year': s.get('school_year', ''),
                    })

        return jsonify({
            'member':     member_data,
            'research':   research,
            'extensions': extensions,
            'schedules':  schedules,
        })
    except Exception as e:
        logger.error(f"member_fsr_data error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/fsr-footnotes', methods=['GET', 'POST', 'DELETE'])
@login_required
def fsr_footnotes_api():
    """
    Manage FSR footnotes for a member.
    GET: Retrieve footnotes for member/semester/year
    POST: Save/update footnotes
    DELETE: Delete a footnote
    """
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({'error': 'Not authenticated'}), 401

        if request.method == 'GET':
            # Get footnotes for specific member/semester/year
            semester = request.args.get('semester')
            academic_year = request.args.get('academic_year')
            member_id = request.args.get('member_id', uid)

            if not semester or not academic_year:
                return jsonify({'error': 'semester and academic_year required'}), 400

            print(f"\n🔍 QUERYING FOOTNOTES:")
            print(
                f"   member_id: {member_id} (type: {type(member_id).__name__})")
            print(f"   semester: {semester} (type: {type(semester).__name__})")
            print(
                f"   academic_year: {academic_year} (type: {type(academic_year).__name__})")

            # Query footnotes directly using member_id, semester, academic_year
            footnotes_result = supabase.table('fsr_footnotes').select(
                'footnote_number, footnote_type, faculty_name, subject, member_id, semester, academic_year'
            ).eq('member_id', member_id).eq(
                'semester', semester
            ).eq('academic_year', academic_year).order('footnote_number').execute()

            print(
                f"   📊 Query returned: {len(footnotes_result.data or [])} footnotes")
            if footnotes_result.data:
                for fn in footnotes_result.data:
                    print(
                        f"      - Footnote {fn.get('footnote_number')}: {fn.get('faculty_name')} ({fn.get('subject')})")

            # Also check what's in the table without filters
            all_footnotes = supabase.table('fsr_footnotes').select(
                'member_id, semester, academic_year').execute()
            print(
                f"\n   📋 All footnotes in table ({len(all_footnotes.data or [])} total):")
            for fn in (all_footnotes.data or [])[:5]:  # Show first 5
                print(
                    f"      member_id: {fn.get('member_id')}, semester: {fn.get('semester')}, year: {fn.get('academic_year')}")

            return jsonify({'footnotes': footnotes_result.data or []}), 200

        elif request.method == 'POST':
            # Save/update multiple footnotes at once
            data = request.get_json()
            member_id = data.get('member_id')
            semester = data.get('semester')  # Should be "1" or "2"
            academic_year = data.get('academic_year')
            footnotes = data.get('footnotes', [])

            if not all([member_id, semester, academic_year]):
                return jsonify({'error': 'member_id, semester, and academic_year required'}), 400

            # Delete existing footnotes for this member/semester/year
            supabase.table('fsr_footnotes').delete().eq(
                'member_id', member_id
            ).eq('semester', semester).eq('academic_year', academic_year).execute()

            # Insert new footnotes
            if footnotes:
                footnote_records = []
                for fn in footnotes:
                    footnote_records.append({
                        'member_id': member_id,
                        'semester': semester,
                        'academic_year': academic_year,
                        'footnote_number': fn.get('number'),
                        'footnote_type': fn.get('type'),
                        'faculty_name': fn.get('faculty_name'),
                        'subject': fn.get('subject', '')
                    })

                result = supabase.table('fsr_footnotes').insert(
                    footnote_records).execute()

                return jsonify({'success': True, 'footnotes': result.data}), 200

            return jsonify({'success': True, 'footnotes': []}), 200

    except Exception as e:
        logger.error(f"fsr_footnotes_api error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/member-dashboard-stats')
def member_dashboard_stats():
    """Return chart data for member dashboard (research by month + extensions count)."""
    if 'uid' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from collections import defaultdict
        uid = session['uid']
        current_year = datetime.now(timezone.utc).year
        last_year = current_year - 1

        # Research by month for current year and last year
        research_docs = db.collection(
            'research').where('uid', '==', uid).stream()
        this_year_counts = defaultdict(int)
        last_year_counts = defaultdict(int)

        for d in research_docs:
            rd = d.to_dict()
            created = rd.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if dt.year == current_year:
                        this_year_counts[dt.month] += 1
                    elif dt.year == last_year:
                        last_year_counts[dt.month] += 1
                except (ValueError, TypeError):
                    pass

        research_this_year = [this_year_counts.get(m, 0) for m in range(1, 13)]
        research_last_year = [last_year_counts.get(m, 0) for m in range(1, 13)]

        # Total extensions count
        ext_docs = db.collection('extensions').where('uid', '==', uid).stream()
        total_extensions = sum(1 for _ in ext_docs)

        return jsonify({
            'research_this_year': research_this_year,
            'research_last_year': research_last_year,
            'total_extensions': total_extensions
        })
    except Exception as e:
        logger.error(f"member_dashboard_stats error: {e}")
        return jsonify({
            'research_this_year': [0]*12,
            'research_last_year': [0]*12,
            'total_extensions': 0,
            'error': str(e)
        }), 500


@app.route('/api/member-dashboard-stats-by-year')
def member_dashboard_stats_by_year():
    """Return chart data grouped by year for member dashboard (2000 to current year)."""
    if 'uid' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from collections import defaultdict

        uid = session['uid']
        current_year = datetime.now(timezone.utc).year
        publications_by_year = {}
        extensions_by_year = {}

        # Initialize years from 2000 to current
        for year in range(2000, current_year + 1):
            publications_by_year[year] = [0] * 12
            extensions_by_year[year] = {
                'extensions': 0,
                'training': 0,
                'information_dissemination': 0,
                'workshop': 0,
                'symposium': 0,
                'others': 0
            }

        # Count research/publications by year and month for this member
        research_docs = db.collection(
            'research').where('uid', '==', uid).stream()
        for d in research_docs:
            rd = d.to_dict()
            created = rd.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    year = dt.year
                    if 2000 <= year <= current_year:
                        publications_by_year[year][dt.month - 1] += 1
                except (ValueError, TypeError):
                    pass

        # Count extensions by type and year for this member
        ext_docs = db.collection('extensions').where('uid', '==', uid).stream()
        for d in ext_docs:
            ed = d.to_dict()
            created = ed.get('created_at', '')
            # Read from 'extension_type' field (the actual column in database)
            ext_type_raw = ed.get('extension_type', '').strip()
            ext_type = ext_type_raw.lower()

            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    year = dt.year
                    if 2000 <= year <= current_year:
                        # Map extension types (case-insensitive with multiple variations)
                        if ext_type in ['extensions', 'extension', 'extension/community service', 'community service']:
                            extensions_by_year[year]['extensions'] += 1
                        elif ext_type == 'training':
                            extensions_by_year[year]['training'] += 1
                        elif ext_type in ['information_dissemination', 'information dissemination']:
                            extensions_by_year[year]['information_dissemination'] += 1
                        elif ext_type == 'workshop':
                            extensions_by_year[year]['workshop'] += 1
                        elif ext_type == 'symposium':
                            extensions_by_year[year]['symposium'] += 1
                        else:
                            extensions_by_year[year]['others'] += 1
                except (ValueError, TypeError):
                    pass

        return jsonify({
            'publications_by_year': publications_by_year,
            'extensions_by_year': extensions_by_year
        })
    except Exception as e:
        logger.error(f"member_dashboard_stats_by_year error: {e}")
        return jsonify({'publications_by_year': {}, 'extensions_by_year': {}, 'error': str(e)}), 500


def user_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if 'uid' not in session:
            # Clear any stale session data
            session.clear()

            # For API calls (JSON requests), return 401 instead of redirecting
            if request.is_json or request.headers.get('Accept') == 'application/json' or request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated'}), 401

            return redirect(url_for('login'))

        # Validate session hasn't expired and user role is correct
        uid = session.get('uid')
        role = session.get('role')

        if not uid or not role:
            session.clear()

            # For API calls, return 401 instead of redirecting
            if request.is_json or request.headers.get('Accept') == 'application/json' or request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated'}), 401

            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated


@app.route('/user/dashboard/')
@user_required
def user_dashboard():
    email = session.get('email', '')
    initial = email[0].upper() if email else 'U'

    # Check if this is first login
    uid = session.get('uid')
    first_login = False

    if uid:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            first_login = user_data.get('first_login', False)

    response = make_response(render_template('user_dashboard.html',
                                             email=email,
                                             initial=initial,
                                             first_login=first_login))

    # Ensure no caching of user dashboard
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/user/admin/')
@user_required
def user_admin_page():
    """Admin page for user/member dashboard"""
    email = session.get('email', '')
    initial = email[0].upper() if email else 'U'
    return render_template('user_admin_page.html',
                           email=email,
                           initial=initial)


# ══════════════════════════════════════════════════════════════════════════════
# Register Forgot Password Routes
# ══════════════════════════════════════════════════════════════════════════════
register_forgot_password_routes(app, db)


if __name__ == '__main__':
    app.run(debug=True)
