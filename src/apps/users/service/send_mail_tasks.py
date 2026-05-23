import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_verification_task(self, receiver_email, first_name, code):
    """
    Celery task to send email verification
    """
    try:
        subject = "Email Verification Required"
        text_content = f"""
        Hello {first_name},

        Thank you for signing up! To secure your account, please verify your email address.

        Your 4-digit verification code is: {code}

        Enter this code on our website to complete the verification process.

        If you didn't request this, please ignore this email.

        Best regards,
        Your Company Team
        """

        from_email = settings.EMAIL_HOST_USER
        to = [receiver_email]
        html_content = f"""
        <div style="font-family: 'Helvetica Neue', Arial, sans-serif; background: #f9f9f9;
        padding: 40px 20px;">
          <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 10px;
          overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #6D5DF6, #1E90FF); padding: 20px;
            text-align: center;">
              <h1 style="color: #fff; margin: 0; font-size: 28px;">Verify Your Email 🚀</h1>
            </div>
            <!-- Main Content -->
            <div style="padding: 30px; text-align: center;">
              <p style="color: #555; font-size: 16px; margin-bottom: 20px;">
                You're just one step away from activating your account!
              </p>
              <div style="background: #F4F8FF; border-radius: 8px; padding: 15px 20px; display:
              inline-block; margin-bottom: 20px;">
                <span style="color: #1E90FF; font-size: 20px; font-weight: bold;">
                  Your Verification Code:
                </span>
                <div style="color: #6D5DF6; font-size: 36px; font-weight: bold; margin-top: 10px;">
                  {code}
                </div>
              </div>
              <p style="color: #555; font-size: 16px; margin-bottom: 30px;">
                Enter this code on our website to complete the verification process.
              </p>
            </div>
            <!-- Footer -->
            <div style="background: #f1f1f1; padding: 15px 20px; text-align: center;">
              <p style="color: #888; font-size: 12px; margin: 0;">
                If you didn't request this email, please ignore it.
              </p>
              <p style="color: #888; font-size: 12px; margin: 5px 0 0;">
                Need help? <a href="mailto:support@yourcompany.com" style="color: #1E90FF;
                text-decoration: none;">Contact our support team</a>.
              </p>
              <p style="color: #888; font-size: 12px; margin: 15px 0 0;">
                Best regards,<br><strong>Your Company Team</strong>
              </p>
            </div>
          </div>
        </div>
        """

        email = EmailMultiAlternatives(subject, text_content, from_email, to)
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Email verification sent successfully to {receiver_email}")
        return f"Email sent to {receiver_email}"

    except Exception as exc:
        logger.error(f"Failed to send email verification to {receiver_email}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_password_verification_task(self, email, first_name, code):
    """
    Celery task to send password reset verification
    """
    try:
        subject = "Password Reset Request"
        to = [email]
        from_email = settings.EMAIL_HOST_USER

        text_content = f"""
        Hello {first_name},

        We received a request to reset the password for your account.

        Your 4-digit password reset code is: {code}

        Enter this code on our website to set a new password.

        If you did not request a password reset, you can safely ignore this email
        and no changes will be made.

        For your security, do not share this code with anyone. If you need
        assistance, please contact our support team.

        Best regards,
        Your Company Team
        """

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;
        padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
          <h2 style="color: #333;">Hello, {first_name} 👋</h2>
          <p style="color: #555; font-size: 16px;">
            We received a request to reset the password for your account.
          </p>
          <p style="color: #333; font-size: 18px; font-weight: bold; text-align: center;">
            Your 4-digit reset code: <span style="color: #007BFF;">{code}</span>
          </p>
          <p style="color: #555; font-size: 16px;">
            Enter this code on our website to choose a new password for your account.
          </p>
          <p style="color: #777; font-size: 14px;">
            <strong>Note:</strong> For security, do not share this code with anyone.
            The code is valid for a limited time.
          </p>
          <p style="color: #777; font-size: 14px;">
            If you did not request a password reset, you can safely ignore this email
            and your password will remain unchanged.
          </p>
          <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
          <p style="color: #888; font-size: 12px;">
            Need help? Contact our <a href="https://yourcompany.example.com/support"
            style="text-decoration: none;">Support Team</a>.
          </p>
          <p style="color: #888; font-size: 12px;">
            Best regards,<br><strong>Your Company Team</strong>
          </p>
        </div>
        """

        email_msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()

        logger.info(f"Password reset email sent successfully to {email}")
        return f"Password reset email sent to {email}"

    except Exception as exc:
        logger.error(f"Failed to send password reset email to {email}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_email_change_verification_task(self, receiver_new_email, first_name, code):
    """
    Celery task to send email change verification
    """
    try:
        subject = "Confirm Your New Email Address"
        from_email = settings.EMAIL_HOST_USER
        to = [receiver_new_email]

        text_content = f"""
        Hello {first_name},

        You've requested to change your email address associated with your account.

        To verify your new email, please enter the following 4-digit verification code:

        {code}

        If you didn't request this change, please ignore this email.

        Best regards,
        Your Company Team
        """

        html_content = f"""
        <div style="font-family: 'Helvetica Neue', Arial, sans-serif; background: #f9f9f9;
         padding: 40px 20px;">
          <div style="max-width: 600px; margin: auto; background: #ffffff;
           border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #6D5DF6, #1E90FF);
            padding: 20px; text-align: center;">
              <h1 style="color: #fff; margin: 0; font-size: 24px;">
              Confirm Your New Email Address</h1>
            </div>
            <!-- Main Content -->
            <div style="padding: 30px; text-align: center;">
              <p style="color: #555; font-size: 16px; margin-bottom: 20px;">
                You've requested to update your email address.
                To proceed, please enter the following code:
              </p>
              <div style="background: #F4F8FF; border-radius: 8px;
               padding: 15px 20px; display: inline-block; margin-bottom: 20px;">
                <span style="color: #1E90FF; font-size: 20px; font-weight: bold;">
                Your Verification Code:</span>
                <div style="color: #6D5DF6; font-size: 36px; font-weight: bold;
                 margin-top: 10px;">{code}</div>
              </div>
              <p style="color: #555; font-size: 16px; margin-bottom: 30px;">
                Enter this code on our website to verify your new email.
              </p>
            </div>
            <!-- Footer -->
            <div style="background: #f1f1f1; padding: 15px 20px; text-align: center;">
              <p style="color: #888; font-size: 12px; margin: 0;">
                If you didn't request this email change, you can ignore this email.
              </p>
              <p style="color: #888; font-size: 12px; margin: 5px 0 0;">
                Need help? <a href="mailto:support@yourcompany.com"
                style="color: #1E90FF; text-decoration: none;">Contact our support team</a>.
              </p>
              <p style="color: #888; font-size: 12px; margin: 15px 0 0;">
                Best regards,<br><strong>Your Company Team</strong>
              </p>
            </div>
          </div>
        </div>
        """

        email = EmailMultiAlternatives(subject, text_content, from_email, to)
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(f"Email change verification sent successfully to {receiver_new_email}")
        return f"Email change verification sent to {receiver_new_email}"

    except Exception as exc:
        logger.error(
            f"Failed to send email change" f" verification to {receiver_new_email}: {str(exc)}"
        )
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_activation_invite_task(self, email, first_name, uid, token):
    """
    Celery task to send activation invite using EmailMultiAlternatives
    """
    try:
        subject = "Invitation to Join Our Platform"
        from_email = settings.EMAIL_HOST_USER
        frontend_url = settings.FRONTEND_URL
        activation_link = f"{frontend_url.rstrip('/')}/activate?uid={uid}&token={token}"
        to = [email]

        # Plain-text fallback
        text_content = f"""Hi {first_name},

You've been invited to join our platform.

To get started, activate your account:
{activation_link}

If you weren’t expecting this invitation, you can safely ignore this email.

— Your Company Team
"""

        # Minimal, elegant HTML (inline styles for email clients)
        html_content = f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#F5F7FB;">
    <div role="article" aria-roledescription="email" lang="en"
     style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,
     Arial,sans-serif;">
      <!-- Preheader (hidden) -->
      <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
        Activate your account and start using the platform.
      </div>

      <div style="max-width:640px;margin:0 auto;padding:24px 16px;">
        <div style="background:#FFFFFF;border-radius:14px;overflow:hidden;
        box-shadow:0 6px 24px rgba(0,0,0,0.06);">
          <!-- Header -->
          <div style="padding:28px 32px 0 32px;text-align:center;">
            <div style="font-size:13px;color:#6B7280;letter-spacing:.02em;">You're invited</div>
            <h1 style="margin:8px 0 0;font-size:24px;line-height:1.35;
            color:#111827;font-weight:700;">Activate your account</h1>
          </div>

          <!-- Body -->
          <div style="padding:22px 32px 32px 32px;">
            <p style="margin:0 0 12px;font-size:16px;line-height:1.6;color:#374151;">Hi
{first_name},</p>
            <p style="margin:0 0 18px;font-size:16px;line-height:1.6;color:#374151;">
            You've been invited to join our platform. To get started, confirm your
              email and set up your account.
            </p>

            <p style="margin:26px 0;text-align:center;">
              <a href="{activation_link}"
                 style="display:inline-block;padding:14px 22px;border-radius:999px;
                 background:#111827;color:#FFFFFF !important;text-decoration:none;
                 font-weight:600;font-size:15px;line-height:1;">
                 Activate account
                               </a>
            </p>

            <p style="margin:0 0 10px;font-size:13px;line-height:1.6;color:#6B7280;
            text-align:center;">
              Or paste this link into your browser:
            </p>
            <p style="margin:6px 0 0;font-size:13px;line-height:1.6;color:#111827;
            text-align:center;word-break:break-word;">
              <a href="{activation_link}" style="color:#111827;
              text-decoration:underline;">{activation_link}</a>
            </p>
          </div>

          <!-- Footer -->
          <div style="background:#F9FAFB;border-top:1px solid #F3F4F6;padding:16px 24px;
          text-align:center;">
            <p style="margin:0;font-size:12px;line-height:1.6;color:#9CA3AF;">
              If you weren’t expecting this invitation, you can safely ignore this email.
            </p>
            <p style="margin:8px 0 0;font-size:12px;line-height:1.6;color:#9CA3AF;">
              — Your Company Team
            </p>
          </div>
        </div>

        <div style="text-align:center;margin-top:12px;">
          <a href="mailto:support@yourcompany.com" style="font-size:12px;color:#9CA3AF;
          text-decoration:none;">
            Need help? Contact support
          </a>
        </div>
      </div>
    </div>
  </body>
</html>"""

        email_msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        email_msg.attach_alternative(html_content, "text/html")
        # Optional helpful header
        # email_msg.extra_headers = {"List-Unsubscribe": "<mailto:support@yourcompany.com>"}
        email_msg.send()

        logger.info(f"Activation invite sent successfully to {email}")
        return f"Activation invite sent to {email}"

    except Exception as exc:
        logger.error(f"Failed to send activation invite to {email}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_otp_verification_task(self, email, first_name, otp_code):
    """
    Celery task to send 2FA OTP verification code using EmailMultiAlternatives
    """
    try:
        subject = "Your Login Verification Code"
        from_email = settings.EMAIL_HOST_USER
        to = [email]

        text_content = f"""Hi {first_name},

Your verification code is: {otp_code}

Enter this code to complete your login. This code will expire in 10 minutes.

If you didn't request this code, please ignore this email and consider changing your password.

— Your Company Team
"""

        html_content = f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#F5F7FB;">
    <div role="article" aria-roledescription="email" lang="en"
     style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,
     Arial,sans-serif;">
      <!-- Preheader (hidden) -->
      <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
        Your verification code: {otp_code}
      </div>

      <div style="max-width:520px;margin:0 auto;padding:24px 16px;">
        <div style="background:#FFFFFF;border-radius:16px;overflow:hidden;
        box-shadow:0 4px 20px rgba(0,0,0,0.08);">
          <!-- Header -->
          <div style="padding:32px 32px 0 32px;text-align:center;">
            <div style="font-size:13px;color:#6366F1;letter-spacing:.03em;font-weight:500;">
              VERIFICATION CODE
            </div>
            <h1 style="margin:8px 0 0;font-size:26px;line-height:1.3;
            color:#111827;font-weight:700;">Complete your login</h1>
          </div>

          <!-- Body -->
          <div style="padding:24px 32px 32px 32px;">
            <p style="margin:0 0 12px;font-size:16px;line-height:1.6;color:#374151;">Hi
{first_name},</p>
            <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#374151;">
              Enter this verification code to complete your login:
            </p>

            <!-- OTP Code Display -->
            <div style="margin:32px 0;text-align:center;">
              <div style="display:inline-block;background:#F8FAFC;border:2px solid #E2E8F0;
              border-radius:12px;padding:20px 28px;font-family:ui-monospace,SFMono-Regular,
              'SF Mono',Consolas,'Liberation Mono',Menlo,monospace;">
                <div style="font-size:32px;font-weight:700;color:#111827;
                letter-spacing:8px;line-height:1;">{otp_code}</div>
              </div>
            </div>

            <p style="margin:24px 0 12px;font-size:14px;line-height:1.6;color:#6B7280;
            text-align:center;">
              This code will expire in <strong style="color:#374151;">10 minutes</strong>
            </p>

            <div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;
            padding:12px 16px;margin:20px 0 0;">
              <p style="margin:0;font-size:13px;line-height:1.5;color:#92400E;">
                              <strong>Security tip:</strong> Never share this code with anyone.
                Our team will never ask for your verification code.
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div style="background:#F9FAFB;border-top:1px solid #F3F4F6;padding:20px 24px;
          text-align:center;">
            <p style="margin:0 0 6px;font-size:12px;line-height:1.6;color:#9CA3AF;">
              If you didn't request this code, please ignore this email.
            </p>
            <p style="margin:0;font-size:12px;line-height:1.6;color:#9CA3AF;">
              — Your Company Team
            </p>
          </div>
        </div>

        <div style="text-align:center;margin-top:16px;">
          <a href="mailto:security@yourcompany.com" style="font-size:12px;color:#9CA3AF;
          text-decoration:none;">
            Security concerns? Contact us
          </a>
        </div>
      </div>
    </div>
  </body>
</html>"""

        email_msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        email_msg.attach_alternative(html_content, "text/html")
        # Security-focused headers
        email_msg.extra_headers = {
            "X-Priority": "1",  # High priority for security codes
            "X-MSMail-Priority": "High",
        }
        email_msg.send()

        logger.info(f"OTP verification code sent successfully to {email}")
        return f"OTP verification code sent to {email}"

    except Exception as exc:
        logger.error(f"Failed to send OTP verification code to {email}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
