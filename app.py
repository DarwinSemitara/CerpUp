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
    """Return all members from Firestore (public endpoint for faculty page). 
    Supports filtering by type via query parameter or faculty status."""
    try:
        member_type = request.args.get('type', None)
        faculty_only = request.args.get('faculty', None)

        if faculty_only and faculty_only.lower() == 'true':
            # Filter by is_faculty = true (no order_by to avoid index requirement)
            docs = db.collection('members').where(
                'is_faculty', '==', True).stream()
            members = [{'id': d.id, **d.to_dict()} for d in docs]
            # Sort in Python instead
            members.sort(key=lambda x: x.get('created_at', ''))
        elif member_type:
            # Filter by type
            docs = db.collection('members').where(
                'type', '==', member_type).order_by('created_at').stream()
            members = [{'id': d.id, **d.to_dict()} for d in docs]
        else:
            # Return all members
            docs = db.collection('members').order_by('created_at').stream()
            members = [{'id': d.id, **d.to_dict()} for d in docs]

        return jsonify(members)
    except Exception as e:
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
        db.collection('members').document(member_id).set(member)
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
    """Delete a member and their photo."""
    try:
        doc = db.collection('members').document(member_id).get()
        if not doc.exists:
            return jsonify({'error': 'Member not found.'}), 404

        # Delete photo from Cloudinary
        delete_member_photo(member_id)

        # Delete from Firestore
        db.collection('members').document(member_id).delete()
        return jsonify({'status': 'ok'})
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
        try:
            response = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,  # Auto-confirm email
                "user_metadata": {
                    "display_name": display_name
                }
            })

            if not response.user:
                return jsonify({'error': 'Failed to create user account.'}), 500

            user_id = response.user.id

        except Exception as create_error:
            # If user already exists, try to update
            error_msg = str(create_error)
            if 'already registered' in error_msg.lower() or 'already exists' in error_msg.lower():
                # Try to get existing user and update password
                try:
                    # Get user by email
                    users_response = supabase.auth.admin.list_users()
                    existing_user = None
                    for user in users_response:
                        if hasattr(user, 'email') and user.email == email:
                            existing_user = user
                            break

                    if existing_user:
                        # Update password
                        supabase.auth.admin.update_user_by_id(
                            existing_user.id,
                            {"password": password}
                        )
                        user_id = existing_user.id
                    else:
                        return jsonify({'error': 'User exists but could not be found.'}), 500

                except Exception as update_error:
                    return jsonify({'error': f'User exists. {str(update_error)}'}), 500
            else:
                return jsonify({'error': str(create_error)}), 500

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
        return jsonify({'error': str(e)}), 500


# ── Research API ──────────────────────────────────────────────

@app.route('/api/research', methods=['GET'])
@login_required
def get_research():
    """Get all research papers for the current logged-in member OR all research for admin."""
    try:
        uid = session.get('uid')
        role = session.get('role')  # Get role directly from session
        # Optional filter by member_id
        member_id = request.args.get('member_id')
        print(
            f"🔍 GET Research - UID from session: {uid}, Role: {role}, Member filter: {member_id}")

        if not uid:
            print("❌ No UID in session!")
            return jsonify({'error': 'Not authenticated'}), 401

        # Check if user is admin (check session role first for hardcoded admin)
        print(f"🔍 Checking if user is admin...")
        is_admin = False

        if role == 'admin':
            # Admin from session (hardcoded or from database)
            is_admin = True
            print(f"🔐 Is admin (from session): True")
        else:
            # For regular users, double-check from database
            user_doc = db.collection('users').where(
                'uid', '==', uid).limit(1).stream()
            user_list = [d.to_dict() for d in user_doc]
            print(f"👤 User list from DB: {user_list}")
            is_admin = user_list and user_list[0].get('role') == 'admin'
            print(f"🔐 Is admin (from DB): {is_admin}")

        if is_admin:
            # Admin can filter by member_id or see all research
            if member_id:
                print(
                    f"📚 Fetching research for member: {member_id} (admin view)...")
                docs = db.collection('research').where(
                    'uid', '==', member_id).stream()
            else:
                print("📚 Fetching ALL research (admin view)...")
                docs = db.collection('research').stream()
        else:
            # Members see only their own research
            print(f"📚 Fetching research for UID: {uid} (member view)...")
            docs = db.collection('research').where('uid', '==', uid).stream()

        research_list = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            research_list.append(data)
            print(
                f"  📄 Added research: {data.get('title', 'N/A')} (ID: {data.get('id')})")

        print(f"✅ Found {len(research_list)} research items")

        # Sort in Python instead of Firestore
        research_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)

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
        uid = session.get('uid')
        print(f"🔍 Add research - UID from session: {uid}")

        if not uid:
            print("❌ No UID in session!")
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json()
        print(f"📥 Received data: {data}")

        # Get current member info
        print(f"🔍 Querying members with UID: {uid}")
        members = db.collection('members').where(
            'uid', '==', uid).limit(1).stream()
        member_list = [{'id': d.id, **d.to_dict()} for d in members]

        if not member_list:
            print(f"❌ Member not found for UID: {uid}")
            return jsonify({'error': 'Member not found'}), 404

        member = member_list[0]
        print(
            f"✅ Found member: {member.get('first')} {member.get('last')} (ID: {member.get('id')})")

        # Prepare research document
        from datetime import datetime

        # Get member name properly
        member_name = f"{member.get('first', '')} {member.get('last', '')}".strip(
        )
        print(f"📝 Member name: {member_name}")

        research_doc = {
            'uid': uid,
            'member_id': member['id'],
            'member_name': member_name,
            'research_type': data.get('research_type'),
            'title': data.get('title', ''),
            'role': data.get('role', ''),
            'co_workers': data.get('co_workers', ''),
            'co_authors': data.get('co_authors', ''),
            # Convert empty string to None
            'start_date': data.get('start_date') or None,
            # Convert empty string to None
            'end_date': data.get('end_date') or None,
            # Convert empty string to None
            'date_completion': data.get('date_completion') or None,
            'funding_agency': data.get('funding_agency', ''),
            'credit_units': data.get('credit_units', ''),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Add to database
        print(f"📄 Creating document reference...")
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
        uid = session.get('uid')
        print(f"🗑️ Delete research - ID: {research_id}, UID: {uid}")

        if not uid:
            print("❌ Not authenticated")
            return jsonify({'error': 'Not authenticated'}), 401

        # Verify ownership
        print(f"🔍 Checking if research exists...")
        doc = db.collection('research').document(research_id).get()
        print(f"📄 Doc exists: {doc.exists}")

        if not doc.exists:
            print(f"❌ Research not found: {research_id}")
            return jsonify({'error': 'Research not found'}), 404

        doc_data = doc.to_dict()
        print(f"📝 Research UID: {doc_data.get('uid')}, Session UID: {uid}")

        if doc_data.get('uid') != uid:
            print("❌ Unauthorized - UID mismatch")
            return jsonify({'error': 'Unauthorized'}), 403

        print(f"🗑️ Deleting research...")
        db.collection('research').document(research_id).delete()
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

        # Generate FSR
        output_path = generate_member_fsr(member_id, semester, academic_year)

        # Return file for download
        from flask import send_file
        return send_file(
            output_path,
            as_attachment=True,
            download_name=os.path.basename(output_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"Error generating FSR: {e}")
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
            'school_year': data.get('schoolYear', f"{__import__('datetime').datetime.utcnow().year}-{__import__('datetime').datetime.utcnow().year + 1}"),
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

        # Update the document
        doc_ref.update(update_data)

        return jsonify({'status': 'ok', 'id': entry_id})
    except Exception as e:
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
