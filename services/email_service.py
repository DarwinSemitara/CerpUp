"""
Email Service for CERP
Handles sending verification codes and other email notifications
Uses SMTP (Gmail) for email delivery
"""

import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# In-memory storage for verification codes (expires after 15 minutes)
# In production, use Redis or database
_verification_codes = {}


def generate_verification_code():
    """
    Generate a 6-digit verification code
    For testing/demo: always returns 000000
    For production: uncomment the random generation below
    """
    # Testing mode - fixed code for easy deployment testing
    return '000000'

    # Production mode - uncomment this line for random codes:
    # return ''.join(random.choices(string.digits, k=6))


def store_verification_code(email, code):
    """Store verification code with expiration (15 minutes)"""
    expires_at = datetime.now() + timedelta(minutes=15)
    _verification_codes[email.lower()] = {
        'code': code,
        'expires_at': expires_at,
        'attempts': 0
    }
    logger.info(
        f"Stored verification code for {email} (expires at {expires_at})")


def verify_code(email, code):
    """
    Verify the code for an email
    Returns: (success: bool, message: str)
    """
    email = email.lower()

    if email not in _verification_codes:
        return False, "No verification code found. Please request a new one."

    stored = _verification_codes[email]

    # Check expiration
    if datetime.now() > stored['expires_at']:
        del _verification_codes[email]
        return False, "Verification code has expired. Please request a new one."

    # Check attempts (max 5)
    if stored['attempts'] >= 5:
        del _verification_codes[email]
        return False, "Too many failed attempts. Please request a new code."

    # Check code
    if stored['code'] != code:
        stored['attempts'] += 1
        return False, f"Invalid code. {5 - stored['attempts']} attempts remaining."

    # Success - remove code
    del _verification_codes[email]
    return True, "Verification successful!"


def send_email_via_smtp(to_email, subject, html_body, text_body=None):
    """
    Send email using SMTP (Gmail)
    Returns: (success: bool, message: str)
    """
    try:
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_name = os.getenv('SMTP_FROM_NAME', 'CERP System')

        if not smtp_user or not smtp_password:
            logger.warning("SMTP credentials not configured")
            # For development, just log the email details
            logger.info(f"[DEV MODE] Would send email to {to_email}")
            logger.info(f"[DEV MODE] Subject: {subject}")

            # Print to console with big banner
            print("\n" + "="*70)
            print("📧 EMAIL WOULD BE SENT (Development Mode)")
            print("="*70)
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print("="*70 + "\n")

            return True, "Development mode: Email logged"

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{from_name} <{smtp_user}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add text and HTML parts
        if text_body:
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)

        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email} via SMTP")
        return True, "Email sent successfully"

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed - check username/password")
        return False, "Email authentication failed"
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False, f"Email sending failed: {str(e)}"
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {e}")
        return False, f"Email sending failed: {str(e)}"


def send_verification_email(email, name, code):
    """
    Send verification code email
    Returns: (success: bool, message: str)
    """
    subject = 'CERP Account Verification Code'

    # Plain text version
    text_body = f"""
Hello {name},

Your CERP account verification code is: {code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

Best regards,
CERP Team
    """

    # HTML version
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6; 
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f3f4f6;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 40px auto; 
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #6b0f1a 0%, #014421 100%);
            color: white; 
            padding: 30px 20px; 
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 700;
        }}
        .content {{ 
            padding: 40px 30px;
        }}
        .code-box {{ 
            background: linear-gradient(135deg, #f0fdf4 0%, #fef3f2 100%);
            border: 3px solid #6b0f1a;
            border-radius: 12px; 
            padding: 30px; 
            margin: 30px 0; 
            text-align: center;
        }}
        .code {{ 
            font-size: 42px; 
            font-weight: bold; 
            color: #6b0f1a; 
            letter-spacing: 12px;
            font-family: 'Courier New', monospace;
        }}
        .info {{
            background: #f9fafb;
            border-left: 4px solid #fb923c;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{ 
            text-align: center; 
            padding: 20px;
            background: #f9fafb;
            font-size: 13px; 
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 CERP Account Verification</h1>
        </div>
        <div class="content">
            <p style="font-size: 16px; margin: 0 0 20px 0;">Hello <strong>{name}</strong>,</p>
            <p style="font-size: 15px; color: #4b5563;">Your CERP account verification code is:</p>
            
            <div class="code-box">
                <div class="code">{code}</div>
            </div>
            
            <div class="info">
                <strong>⏰ Important:</strong> This code will expire in <strong>15 minutes</strong>.
            </div>
            
            <p style="font-size: 14px; color: #6b7280;">
                Enter this code in your dashboard to complete the verification process.
            </p>
            
            <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
                If you didn't request this code, please ignore this email.
            </p>
            
            <p style="font-size: 15px; margin-top: 30px;">
                Best regards,<br>
                <strong>CERP Team</strong>
            </p>
        </div>
        <div class="footer">
            <p style="margin: 0;">This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
    """

    # Always print code to console for easy testing
    print("\n" + "="*70)
    print("🔐 VERIFICATION CODE GENERATED")
    print("="*70)
    print(f"📧 Email: {email}")
    print(f"👤 Name:  {name}")
    print(f"🔢 Code:  {code}")
    print(f"⏰ Valid for: 15 minutes")
    print("="*70 + "\n")

    success, message = send_email_via_smtp(
        email, subject, html_body, text_body)

    # Always log the code for development
    logger.info(f"Verification code for {email}: {code}")

    return success, message


def send_welcome_email(email, name, faculty_id):
    """
    Send welcome email after first login completion
    Returns: (success: bool, message: str)
    """
    subject = 'Welcome to CERP! 🎉'

    text_body = f"""
Hello {name},

Welcome to the CERP (Center for Extension and Research in the Philippines) system!

Your account has been successfully activated.
Faculty ID: {faculty_id}

You can now access all features of the CERP dashboard.

Best regards,
CERP Team
    """

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6; 
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f3f4f6;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 40px auto; 
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white; 
            padding: 40px 20px; 
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .content {{ 
            padding: 40px 30px;
        }}
        .info-box {{ 
            background: #f0fdf4;
            border-left: 5px solid #10b981;
            padding: 20px;
            margin: 25px 0;
            border-radius: 4px;
        }}
        .feature-list {{
            background: #f9fafb;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
        }}
        .feature-list ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .feature-list li {{
            margin: 8px 0;
            color: #4b5563;
        }}
        .footer {{ 
            text-align: center; 
            padding: 20px;
            background: #f9fafb;
            font-size: 13px; 
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to CERP!</h1>
        </div>
        <div class="content">
            <p style="font-size: 16px; margin: 0 0 20px 0;">Hello <strong>{name}</strong>,</p>
            
            <p style="font-size: 15px; color: #4b5563;">
                Your CERP account has been successfully activated! We're excited to have you on board.
            </p>
            
            <div class="info-box">
                <strong>👤 Your Faculty ID:</strong> <span style="font-family: 'Courier New', monospace; font-size: 16px; color: #059669;">{faculty_id}</span>
            </div>
            
            <div class="feature-list">
                <strong style="color: #111827; font-size: 16px;">🚀 You now have access to:</strong>
                <ul>
                    <li>📊 Research project management</li>
                    <li>🤝 Extension activities tracking</li>
                    <li>📝 Faculty study reports (FSR)</li>
                    <li>📰 News and events updates</li>
                    <li>👥 Team collaboration tools</li>
                    <li>📈 Progress analytics and insights</li>
                </ul>
            </div>
            
            <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
                If you have any questions or need assistance, feel free to reach out to our support team.
            </p>
            
            <p style="font-size: 15px; margin-top: 30px;">
                Best regards,<br>
                <strong>CERP Team</strong>
            </p>
        </div>
        <div class="footer">
            <p style="margin: 0;">This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
    """

    success, message = send_email_via_smtp(
        email, subject, html_body, text_body)

    if not os.getenv('SMTP_USER'):
        logger.info(f"[DEV MODE] Welcome email would be sent to {email}")
        return True, "Development mode: Welcome email skipped"

    return success, message
