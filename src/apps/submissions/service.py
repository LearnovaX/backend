import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_answer_status_notification_task(
    self, receiver_email, first_name, task_name, task_number, status, feedback_text=None
):
    """
    Celery task to send answer status notification email
    """
    try:
        # Clean, minimalistic status configuration
        status_config = {
            "approved": {
                "subject": "Answer Approved - Task #" + str(task_number),
                "status_text": "Approved",
                "message": "Your answer has been approved.",
                "color": "#16a34a",  # Green
            },
            "rejected": {
                "subject": "Answer Needs Revision - Task #" + str(task_number),
                "status_text": "Needs Revision",
                "message": "Your answer requires changes before approval.",
                "color": "#dc2626",  # Red
            },
            "have_flaws": {
                "subject": "Answer Under Review - Task #" + str(task_number),
                "status_text": "Under Review",
                "message": "Your answer has been reviewed with feedback.",
                "color": "#d97706",  # Orange
            },
        }

        config_data = status_config.get(status, status_config["have_flaws"])
        subject = config_data["subject"]

        # Plain text content
        text_content = f"""
Hello {first_name},

Your answer for Task #{task_number} - {task_name} has been reviewed.

Status: {config_data['status_text']}
{config_data['message']}

{f'Feedback: {feedback_text}' if feedback_text else ''}

Please log into your account to view details and take any necessary actions.

Best regards,
The Review Team
        """

        from_email = settings.EMAIL_HOST_USER
        to = [receiver_email]

        # Clean, modern HTML template
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Update</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont,
 'Segoe UI', Roboto, sans-serif; background-color: #f8f9fa; color: #212529;">

    <div style="max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 8px;
    overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">

        <!-- Header -->
        <div style="padding: 32px 32px 24px; border-bottom: 1px solid #e9ecef;">
            <h1 style="margin: 0; font-size: 24px; font-weight: 600;
             color: #212529;">Task Update</h1>
        </div>

        <!-- Content -->
        <div style="padding: 32px;">

            <!-- Greeting -->
            <p style="margin: 0 0 24px; font-size: 16px; color: #495057;">Hello {first_name},</p>

            <!-- Task Info -->
            <div style="margin-bottom: 24px; padding: 20px; background-color: #f8f9fa;
             border-radius: 6px; border-left: 4px solid {config_data['color']};">
                <h3 style="margin: 0 0 8px; font-size: 18px; font-weight: 600; color: #212529;">
                Task #{task_number}</h3>
                <p style="margin: 0; font-size: 14px; color: #6c757d;">{task_name}</p>
            </div>

            <!-- Status -->
            <div style="margin-bottom: 24px;">
                <div style="display: inline-block; padding: 6px 12px;
                background-color: {config_data['color']}; color: #ffffff;
                border-radius: 4px; font-size: 14px; font-weight: 500; margin-bottom: 12px;">
                    {config_data['status_text']}
                </div>
                <p style="margin: 0; font-size: 16px; color: #495057; line-height: 1.5;">
                    {config_data['message']}
                </p>
            </div>

            {f'''
            <!-- Feedback -->
                        <div style="margin-bottom: 32px;">
            <h4 style="margin: 0 0 12px; font-size: 16px; font-weight: 600;
                color: #212529;">Feedback</h4>
                <div style="padding: 16px; background-color: #f8f9fa;
                border-radius: 6px; border: 1px solid #dee2e6;">
                    <p style="margin: 0; font-size: 14px; color: #495057;
                     line-height: 1.5; white-space: pre-wrap;">{feedback_text}</p>
                </div>
            </div>
            ''' if feedback_text else ''}

            <!-- Action Button -->
            <div style="margin-bottom: 32px;">
                <a href="#" style="display: inline-block; padding: 12px 24px;
                background-color: {config_data['color']}; color: #ffffff;
                text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: 500;">
                    View Details
                </a>
            </div>

            <!-- Closing -->
            <p style="margin: 0; font-size: 16px; color: #495057;">
                Please log into your account to take any necessary actions.
            </p>
        </div>

        <!-- Footer -->
        <div style="padding: 24px 32px; background-color: #f8f9fa;
         border-top: 1px solid #e9ecef;">
            <p style="margin: 0 0 8px; font-size: 14px; color: #6c757d;">
                Best regards,<br>
                The Review Team
            </p>
            <p style="margin: 0; font-size: 12px; color: #adb5bd;">
                This is an automated notification. Please do not reply to this email.
            </p>
        </div>

    </div>

    <!-- Email Footer -->
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; text-align: center;">
        <p style="margin: 0; font-size: 12px; color: #adb5bd;">
            © 2024 Your Company. All rights reserved.
        </p>
    </div>

</body>
</html>
        """

        email = EmailMultiAlternatives(subject, text_content, from_email, to)
        email.attach_alternative(html_content, "text/html")
        email.send()

        logger.info(
            f"Answer status notification sent successfully to {receiver_email} "
            f"for task #{task_number}"
        )
        return (
            f"Status notification sent to {receiver_email} for task #{task_number} "
            f"with status: {status}"
        )

    except Exception as exc:
        logger.error(f"Failed to send answer status notification to {receiver_email}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


def send_answer_status_notification(
    receiver_email, first_name, task_name, task_number, status, feedback_text=None
):
    """
    Queue answer status notification task
    """
    return send_answer_status_notification_task.delay(
        receiver_email, first_name, task_name, task_number, status, feedback_text
    )
