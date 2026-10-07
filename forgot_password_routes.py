"""
Forgot Password API Routes
Handles password reset flow with email verification and CAPTCHA
"""

from flask import jsonify, request
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# In-memory storage for password reset codes
# In production, use Redis or database
_password_reset_codes = {}


def register_forgot_password_routes(app, db):
    """Register forgot password routes with the Flask app"""

    @app.route('/api/forgot-password/send-code', methods=['POST'])
    def forgot_password_send_code():
        """
        Step 1: Send password reset code to user's email
        Requires: user_id (employee/student ID)
        """
        from services.email_service import generate_verification_code, send_password_reset_email

        try:
            data = request.get_json()
            user_id = data.get('user_id', '').strip()

            if not user_id:
                return jsonify({'error': 'User ID is required'}), 400

            # Find member by user_no (User ID)
            members = db.collection('members').where(
                'user_no', '==', user_id).limit(1).stream()
            member_list = [{'id': d.id, **d.to_dict()} for d in members]

            if not member_list:
                return jsonify({'error': 'User ID not found. Please check and try again.'}), 404

            member_data = member_list[0]
            email = member_data.get('email', '')
            first_name = member_data.get('first', 'User')
            last_name = member_data.get('last', '')

            if not email:
                return jsonify({'error': 'No email address associated with this account. Please contact support.'}), 400

            # Generate and store reset code
            reset_code = generate_verification_code()
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

            _password_reset_codes[user_id.lower()] = {
                'code': reset_code,
                'email': email,
                'member_id': member_data['id'],
                'expires_at': expires_at,
                'attempts': 0,
                'verified': False
            }

            # Send email
            full_name = f"{first_name} {last_name}".strip()
            send_password_reset_email(email, full_name, reset_code)

            # Mask email for security (show first 2 chars and domain)
            email_parts = email.split('@')
            if len(email_parts) == 2:
                local = email_parts[0]
                domain = email_parts[1]
                masked_local = local[:2] + '***' if len(local) > 2 else '***'
                email_masked = f"{masked_local}@{domain}"
            else:
                email_masked = '***@***.***'

            logger.info(
                f"Password reset code sent to {email} for user ID: {user_id}")

            return jsonify({
                'success': True,
                'message': 'Reset code sent to your email',
                'email_masked': email_masked
            })

        except Exception as e:
            logger.error(f"Error sending password reset code: {e}")
            return jsonify({'error': 'An error occurred. Please try again.'}), 500

    @app.route('/api/forgot-password/verify-code', methods=['POST'])
    def forgot_password_verify_code():
        """
        Step 2: Verify the reset code
        Requires: user_id, code
        """
        try:
            data = request.get_json()
            user_id = data.get('user_id', '').strip().lower()
            code = data.get('code', '').strip()

            if not user_id or not code:
                return jsonify({'error': 'User ID and code are required'}), 400

            if user_id not in _password_reset_codes:
                return jsonify({'error': 'No reset request found. Please request a new code.'}), 404

            stored = _password_reset_codes[user_id]

            # Check expiration
            if datetime.now(timezone.utc) > stored['expires_at']:
                del _password_reset_codes[user_id]
                return jsonify({'error': 'Code has expired. Please request a new one.'}), 400

            # Check attempts (max 5)
            if stored['attempts'] >= 5:
                del _password_reset_codes[user_id]
                return jsonify({'error': 'Too many failed attempts. Please request a new code.'}), 400

            # Verify code
            if stored['code'] != code:
                stored['attempts'] += 1
                remaining = 5 - stored['attempts']
                return jsonify({'error': f'Invalid code. {remaining} attempts remaining.'}), 400

            # Mark as verified (don't delete yet, need it for password reset)
            stored['verified'] = True
            stored['verified_at'] = datetime.now(timezone.utc)

            logger.info(f"Password reset code verified for user ID: {user_id}")

            return jsonify({
                'success': True,
                'message': 'Code verified successfully'
            })

        except Exception as e:
            logger.error(f"Error verifying password reset code: {e}")
            return jsonify({'error': 'An error occurred. Please try again.'}), 500

    @app.route('/api/forgot-password/reset-password', methods=['POST'])
    def forgot_password_reset_password():
        """
        Step 3: Reset the password (after code verification and CAPTCHA)
        Requires: user_id, new_password
        """
        from services.supabase_service import update_user_password

        try:
            data = request.get_json()
            user_id = data.get('user_id', '').strip().lower()
            new_password = data.get('new_password', '').strip()

            if not user_id or not new_password:
                return jsonify({'error': 'User ID and new password are required'}), 400

            if len(new_password) < 6:
                return jsonify({'error': 'Password must be at least 6 characters'}), 400

            # Verify user has completed code verification
            if user_id not in _password_reset_codes:
                return jsonify({'error': 'Invalid reset session. Please start over.'}), 404

            stored = _password_reset_codes[user_id]

            if not stored.get('verified', False):
                return jsonify({'error': 'Please verify your code first'}), 400

            # Check if verification is still valid (within 30 minutes)
            verified_at = stored.get('verified_at')
            if not verified_at or (datetime.now(timezone.utc) - verified_at).total_seconds() > 1800:
                del _password_reset_codes[user_id]
                return jsonify({'error': 'Verification expired. Please start over.'}), 400

            # Get member data
            member_id = stored['member_id']
            member_doc = db.collection('members').document(member_id).get()

            if not member_doc.exists:
                return jsonify({'error': 'User not found'}), 404

            member_data = member_doc.to_dict()
            uid = member_data.get('uid')
            email = member_data.get('email')

            if not uid:
                return jsonify({'error': 'Account not properly configured. Please contact support.'}), 400

            # Update password in Supabase
            success, error = update_user_password(uid, new_password)

            if not success:
                logger.error(
                    f"Failed to update password for UID {uid}: {error}")
                return jsonify({'error': f'Failed to update password: {error}'}), 500

            # Clean up reset code
            del _password_reset_codes[user_id]

            logger.info(f"Password reset successful for user ID: {user_id}")

            return jsonify({
                'success': True,
                'message': 'Password reset successful',
                'email': email  # Return email for auto-fill (optional)
            })

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return jsonify({'error': 'An error occurred. Please try again.'}), 500
