from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from services.supabase_service import verify_access_token as verify_id_token, db, supabase
from services.cloudinary_service import upload_member_photo, delete_member_photo
from datetime import datetime
import os
import uuid
import logging

logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

TAP_SECTIONS = [
    ('tap-capdev',  'Capacity Development'),
    ('tap-modelcom', 'Model Community'),
    ('tap-praxis',  'Praxis'),
]


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if 'uid' not in session:
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
    if 'uid' in session:
        return redirect(url_for('dashboard'))

    # Serve Supabase login page
    return render_template('login_supabase.html',
                           supabase_url=os.getenv('SUPABASE_URL'),
                           supabase_anon_key=os.getenv('SUPABASE_ANON_KEY')
                           )


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
        if username == 'admin' and password == 'admin123':
            session['uid'] = 'admin-hardcoded'
            session['email'] = 'admin'
            session['role'] = 'admin'
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
    if user_doc.exists:
        user_data = user_doc.to_dict()
        role = user_data.get('role', 'user')

    session['uid'] = uid
    session['email'] = email
    session['role'] = role

    redirect_url = '/dashboard/' if role == 'admin' else '/user/dashboard/'
    return jsonify({'status': 'ok', 'redirect': redirect_url})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'ok'})


@app.route('/api/current-member', methods=['GET'])
@login_required
def get_current_member():
    """Get current logged-in member's data."""
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({'error': 'Not authenticated'}), 401

        # Find member by uid
        members = db.collection('members').where(
            'uid', '==', uid).limit(1).stream()
        member_list = [{'id': d.id, **d.to_dict()} for d in members]

        if member_list:
            return jsonify(member_list[0])
        else:
            return jsonify({'error': 'Member not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/dashboard/')
@login_required
def dashboard():
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/dashboard.html',
                           email=email,
                           initial=initial,
                           page_title='Dashboard',
                           active_page='dashboard')


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
    if is_partial():
        return render_template('partials/placeholder.html', label='Section')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/placeholder.html',
                           email=email,
                           initial=initial,
                           page_title='Section',
                           active_page='section')


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
    return redirect(url_for('section_che'))


@app.route('/che/')
@login_required
def section_che():
    if is_partial():
        return render_template('partials/che.html')
    email = session.get('email', '')
    initial = email[0].upper() if email else 'A'
    return render_template('pages/che.html',
                           email=email,
                           initial=initial,
                           page_title='CHE Assistant',
                           active_page='che')


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
            .select('id, title, created_at, updated_at')
            .eq('user_id', user_id)
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

        now = datetime.utcnow().isoformat()
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
    """Delete a conversation."""
    try:
        user_id = session.get('uid', '')
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
    Accepts: { "message": str, "history": [...], "include_context": bool }
    Returns: { "reply": str, "error": bool, "action": dict|null, "action_result": dict|null }
    """
    try:
        from services.che_service import chat as che_chat_fn, extract_action, execute_schedule_action

        data = request.get_json(silent=True) or {}
        message = data.get('message', '').strip()
        history = data.get('history', [])
        include_context = data.get('include_context', False)

        if not message:
            return jsonify({'reply': 'Please send a message.', 'error': True}), 400

        # Always inject schedule context for scheduling awareness
        context_data = {}
        try:
            # Schedules (always loaded for GA awareness)
            sched_docs = db.collection('schedules').stream()
            schedules_raw = []
            for d in sched_docs:
                data = d.to_dict()
                # Normalize to camelCase for consistency with GA functions
                schedules_raw.append({
                    'id': d.id,
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
            try:
                member_docs = db.collection('members').stream()
                context_data['members'] = [
                    {'id': d.id, **d.to_dict()} for d in member_docs]

                research_docs = db.collection('research').stream()
                context_data['research'] = [
                    {'id': d.id, **d.to_dict()} for d in research_docs]

                ext_docs = db.collection('extensions').stream()
                context_data['extensions'] = [
                    {'id': d.id, **d.to_dict()} for d in ext_docs]

                news_docs = db.collection('news').stream()
                context_data['news'] = [
                    {'id': d.id, **d.to_dict()} for d in news_docs]
            except Exception as ctx_err:
                logger.warning(f"CHE context fetch partial failure: {ctx_err}")

        result = che_chat_fn(
            message=message,
            history=history,
            context_data=context_data
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

        # Get current schedules (normalized to camelCase)
        sched_docs = db.collection('schedules').stream()
        existing_schedules = []
        for d in sched_docs:
            data = d.to_dict()
            existing_schedules.append({
                'id': d.id,
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
                now = datetime.utcnow()
                school_year = f"{now.year}-{now.year + 1}"
                # Default to 1st semester (admin changes this on the schedule page)
                semester = '1'

                db.collection('schedules').document(new_id).set({
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
                    'created_at': datetime.utcnow().isoformat(),
                })
                result['message'] += f" Added as ID: {new_id[:8]}..."

            elif action_type == 'move_schedule' and result['data'].get('moved_schedules'):
                for moved in result['data']['moved_schedules']:
                    sid = moved.get('id')
                    if sid:
                        db.collection('schedules').document(sid).update({
                            'day': moved.get('day', ''),
                            'start': moved.get('start', ''),
                            'end': moved.get('end', ''),
                        })

            elif action_type == 'delete_schedule' and result['data'].get('schedules_to_delete'):
                for sid in result['data']['schedules_to_delete']:
                    db.collection('schedules').document(sid).delete()
                result['message'] = f"Deleted {len(result['data']['schedules_to_delete'])} schedule(s)."

            elif action_type == 'generate_full_schedule' and result['data'].get('redirect_to_endpoint'):
                # Execute full generation directly here
                from services.scheduler_service import run_full_ga, FullGAConfig, SubjectInput

                gen_params = result['data']['params']

                # Load reference semester
                reference_schedules = []
                ref_sem = gen_params.get('reference_semester')
                ref_sy = gen_params.get('reference_school_year')
                if ref_sem and ref_sy:
                    try:
                        ref_docs = db.collection('schedules').stream()
                        for d in ref_docs:
                            rd = d.to_dict()
                            if rd.get('semester') == ref_sem and rd.get('school_year') == ref_sy:
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
                    except Exception as e:
                        logger.warning(f"Ref semester load error: {e}")

                # Load faculty data
                prof_availability = {}
                teaching_loads_map = {}
                try:
                    member_docs = db.collection('members').where(
                        'is_faculty', '==', True).stream()
                    for d in member_docs:
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
                except Exception:
                    pass

                # Parse subjects
                subjects_input = []
                for s in gen_params.get('subjects', []):
                    subjects_input.append(SubjectInput(
                        code=s.get('code', s.get('subjCode', '')),
                        name=s.get('name', s.get('subjName', '')),
                        section=s.get('section', 'A'),
                        units=int(s.get('units', 3)),
                        weekly_hours=float(
                            s.get('weekly_hours', s.get('units', 3))),
                        allocated_professors=s.get('professors', []),
                    ))

                config = FullGAConfig(
                    subjects=subjects_input,
                    rooms=gen_params.get('rooms', []),
                    prof_availability=prof_availability,
                    teaching_loads=teaching_loads_map,
                    subject_allocations=gen_params.get(
                        'subject_allocations', {}),
                    reference_schedules=reference_schedules,
                    faculty_overrides=gen_params.get('faculty_overrides', {}),
                )

                ga_result = run_full_ga(config)
                result = ga_result

                # Save if requested
                if gen_params.get('save_to_db', False) and ga_result.get('success'):
                    target_sem = gen_params.get('target_semester', '1')
                    target_sy = gen_params.get('target_school_year',
                                               f"{datetime.utcnow().year}-{datetime.utcnow().year + 1}")
                    saved = 0
                    for sched in ga_result['schedules']:
                        new_id = str(uuid.uuid4())
                        db.collection('schedules').document(new_id).set({
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
                            'created_at': datetime.utcnow().isoformat(),
                        })
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

        # Query Supabase instead of Firestore
        query = supabase.table('members').select('*')

        if faculty_only and faculty_only.lower() == 'true':
            # Filter by is_faculty = true
            query = query.eq('is_faculty', True)
        elif member_type:
            # Filter by type
            query = query.eq('type', member_type)

        # Order by created_at
        query = query.order('created_at', desc=False)

        result = query.execute()
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
        return jsonify({'error': str(e)}), 500


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
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
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
    Admin assigns an email + password to a member, creating a Supabase Auth
    account and storing the role in Supabase users collection.
    """
    from services.supabase_service import supabase
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data.'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
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
                "email_confirm": True,  # Auto-confirm email
                "user_metadata": {
                    "display_name": display_name
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
        }, merge=True)

        # Link uid back to member doc
        db.collection('members').document(member_id).update(
            {'uid': user_id, 'email': email})

        return jsonify({'status': 'ok', 'uid': user_id})
    except Exception as e:
        logger.error(
            f"Unexpected error in create_member_account: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
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
        doc_ref = db.collection('research').document()
        print(f"✅ Doc ref created with ID: {doc_ref.doc_id}")

        print(f"💾 Saving to database...")
        doc_ref.set(research_doc)
        print(f"✅ Research saved successfully!")

        research_doc['id'] = doc_ref.doc_id

        return jsonify(research_doc), 201
    except Exception as e:
        print(f"❌ ERROR adding research: {e}")
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
        uid = session.get('uid')
        if not uid:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json()

        # Get current member info
        members = db.collection('members').where(
            'uid', '==', uid).limit(1).stream()
        member_list = [{'id': d.id, **d.to_dict()} for d in members]

        if not member_list:
            return jsonify({'error': 'Member not found'}), 404

        member = member_list[0]

        # Prepare extension document
        from datetime import datetime
        extension_doc = {
            'uid': uid,
            'member_id': member['id'],
            'member_name': f"{member.get('first', '')} {member.get('last', '')}".strip(),
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
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Add to database
        doc_ref = db.collection('extensions').document()
        doc_ref.set(extension_doc)

        extension_doc['id'] = doc_ref.doc_id

        return jsonify(extension_doc), 201
    except Exception as e:
        print(f"Error adding extension: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extensions/<extension_id>', methods=['DELETE'])
@login_required
def delete_extension(extension_id):
    """Delete an extension activity."""
    try:
        uid = session.get('uid')
        if not uid:
            return jsonify({'error': 'Not authenticated'}), 401

        # Verify ownership
        doc = db.collection('extensions').document(extension_id).get()
        if not doc.exists:
            return jsonify({'error': 'Extension not found'}), 404

        if doc.to_dict().get('uid') != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        db.collection('extensions').document(extension_id).delete()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error deleting extension: {e}")
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

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
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

        # Get footnotes directly
        footnotes_result = supabase.table('fsr_footnotes').select(
            'footnote_number, footnote_type, faculty_name, subject, load_sharing'
        ).eq('member_id', member_id).eq(
            'semester', sem_num
        ).eq('academic_year', academic_year).order('footnote_number').execute()

        return jsonify({
            'success': True,
            'footnotes': footnotes_result.data or []
        })

    except Exception as e:
        logger.error(f"Error getting FSR footnotes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ── Schedule API ──────────────────────────────────────────────

@app.route('/api/schedules', methods=['GET'])
@login_required
def get_schedules():
    """Return all schedule entries from database. Optionally filter by professor name."""
    try:
        docs = db.collection('schedules').order_by('created_at').stream()
        entries = []
        prof_filter = request.args.get('prof', '').strip().lower()

        for d in docs:
            data = d.to_dict()

            def format_time(time_str):
                if time_str and ':' in str(time_str):
                    parts = str(time_str).split(':')
                    return f"{parts[0]}:{parts[1]}"
                return time_str

            entry = {
                'id': d.id,
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
                'created_at': data.get('created_at')
            }

            # Optional professor filter (case-insensitive partial match)
            if prof_filter:
                entry_prof = (entry.get('prof') or '').lower()
                if prof_filter not in entry_prof:
                    continue

            entries.append(entry)
        return jsonify(entries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules', methods=['POST'])
@login_required
def add_schedule():
    """Add a single schedule entry (manual mode)."""
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

        # Save to database with snake_case (Supabase format)
        entry_db = {
            'id':        entry_id,
            'prof':      data['prof'],
            'subj_code': data['subjCode'],  # Convert camelCase to snake_case
            'subj_name': data['subjName'],  # Convert camelCase to snake_case
            'type':      data.get('type', 'Lecture'),
            'day':       data['day'],
            'start':     data['start'],
            'end':       data['end'],
            'room':      data['room'],
            'units':     int(data['units']),
            'section':   data['section'],
            'year':      data.get('year', '1'),
            'semester':  data.get('semester', '1'),
            'school_year': data.get('schoolYear') or f"{__import__('datetime').datetime.utcnow().year}-{__import__('datetime').datetime.utcnow().year + 1}",
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
        }
        db.collection('schedules').document(entry_id).set(entry_db)

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
            'created_at': entry_db['created_at'],
        }
        return jsonify({'status': 'ok', 'id': entry_id, 'entry': entry_response}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/<entry_id>', methods=['DELETE'])
@login_required
def delete_schedule(entry_id):
    """Delete a single schedule entry."""
    try:
        doc = db.collection('schedules').document(entry_id).get()
        if not doc.exists:
            return jsonify({'error': 'Not found.'}), 404
        db.collection('schedules').document(entry_id).delete()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/<entry_id>', methods=['PUT'])
@login_required
def update_schedule(entry_id):
    """Update an existing schedule entry (for moving blocks)."""
    try:
        doc_ref = db.collection('schedules').document(entry_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'error': 'Not found.'}), 404

        # Get the update data from request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided.'}), 400

        # Update only the provided fields
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

        # Don't add updated_at for Supabase - it doesn't have this field by default
        # Update the document
        try:
            doc_ref.update(update_data)
        except Exception as e:
            logger.error(f"Supabase update error: {e}")
            # If update fails, try to get current doc and use upsert instead
            current_doc = doc.to_dict()
            current_doc.update(update_data)
            current_doc['id'] = entry_id
            doc_ref.set(current_doc, merge=True)

        return jsonify({'status': 'ok', 'id': entry_id})
    except Exception as e:
        logger.error(f"Update schedule error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules/clear', methods=['POST'])
@login_required
def clear_schedules():
    """Delete all schedule entries (used before saving a GA result)."""
    try:
        docs = db.collection('schedules').stream()
        for d in docs:
            d.reference.delete()
        return jsonify({'status': 'ok'})
    except Exception as e:
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


@app.route('/api/schedule/generate-full', methods=['POST'])
@login_required
def api_generate_full_schedule():
    """
    Full semester schedule generation using enhanced GA.
    Considers: faculty availability, teaching loads, subject allocation,
    room conflicts, block spreading, reference semester seeding.
    """
    try:
        from services.scheduler_service import run_full_ga, FullGAConfig, SubjectInput

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400

        # Load reference semester if specified
        reference_schedules = []
        ref_semester = data.get('reference_semester')
        ref_school_year = data.get('reference_school_year')
        if ref_semester and ref_school_year:
            try:
                ref_docs = db.collection('schedules').stream()
                for d in ref_docs:
                    rd = d.to_dict()
                    if rd.get('semester') == ref_semester and rd.get('school_year') == ref_school_year:
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
            except Exception as e:
                logger.warning(f"Failed to load reference semester: {e}")

        # Load faculty data (availability + teaching loads)
        prof_availability = {}
        teaching_loads = {}
        try:
            member_docs = db.collection('members').where(
                'is_faculty', '==', True).stream()
            for d in member_docs:
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
                    teaching_loads[full_name] = int(load)
        except Exception as e:
            logger.warning(f"Failed to load faculty data: {e}")

        # Parse subjects
        subjects_input = []
        raw_subjects = data.get('subjects', [])
        for s in raw_subjects:
            subjects_input.append(SubjectInput(
                code=s.get('code', s.get('subjCode', '')),
                name=s.get('name', s.get('subjName', '')),
                section=s.get('section', 'A'),
                units=int(s.get('units', 3)),
                weekly_hours=float(s.get('weekly_hours', s.get('units', 3))),
                allocated_professors=s.get(
                    'professors', s.get('allocated_professors', [])),
            ))

        # Build config
        config = FullGAConfig(
            subjects=subjects_input,
            rooms=data.get('rooms', []),
            prof_availability=prof_availability,
            teaching_loads=teaching_loads,
            subject_allocations=data.get('subject_allocations', {}),
            reference_schedules=reference_schedules,
            faculty_overrides=data.get('faculty_overrides', {}),
            pop_size=data.get('pop_size', 100),
            max_generations=data.get('max_generations', 500),
            time_limit_seconds=data.get('time_limit', 10.0),
        )

        # Run GA
        result = run_full_ga(config)

        # Optionally save to database
        target_semester = data.get('target_semester', '1')
        target_school_year = data.get('target_school_year',
                                      f"{datetime.utcnow().year}-{datetime.utcnow().year + 1}")

        if data.get('save_to_db', False) and result.get('success'):
            saved_count = 0
            for sched in result['schedules']:
                new_id = str(uuid.uuid4())
                db.collection('schedules').document(new_id).set({
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
                    'semester': target_semester,
                    'school_year': target_school_year,
                    'created_at': datetime.utcnow().isoformat(),
                })
                saved_count += 1
            result['message'] += f" | Saved {saved_count} entries to DB."

        return jsonify(result)

    except Exception as e:
        logger.error(f"Full schedule generation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ── AI Chat API ────────────────────────────────────────────────

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
                    if dt.year == datetime.utcnow().year:
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

        current_year = datetime.utcnow().year
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
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
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
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
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
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
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

        # Get current schedules for context
        current_schedules = []
        docs = db.collection('schedules').stream()
        for d in docs:
            current_schedules.append({'id': d.id, **d.to_dict()})

        # Process message with NLP
        intent_data = process_message(message)
        intent_type = intent_data.get('intent')
        params = intent_data.get('params', {})
        confidence = intent_data.get('confidence', 0.0)

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

        # Schedules — match by last name
        last_name = (member_data.get('last') or '').strip().lower()
        schedules = []
        if last_name:
            all_sched = supabase.table('schedules').select('*').execute()
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
        current_year = datetime.utcnow().year
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
        current_year = datetime.utcnow().year
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
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/user/dashboard/')
@user_required
def user_dashboard():
    email = session.get('email', '')
    initial = email[0].upper() if email else 'U'
    return render_template('user_dashboard.html', email=email, initial=initial)


if __name__ == '__main__':
    app.run(debug=True)
