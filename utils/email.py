from typing import List
from config import settings
import resend

from utils.logger import logger
from utils.utils import get_secret


FAILURE_TEMPLATE = """
<h2 style="color: red;">Task Failed</h2>
<p>Unfortunately, the task with ID <strong>{task_id}</strong> has failed.</p>
<p>Please check the logs for more details and try again.</p>
<p>Contact support if the issue persists.</p>
"""

SUCCESS_TEMPLATE = """
<h2 style="color: green;">Task Completed</h2>
<p>Congratulations! The task with ID <strong>{task_id}</strong> has been completed successfully.</p>
<p>Thank you for using Tasknode.</p>
<p>Feel free to reach out for any further assistance.</p>
"""

VERIFICATION_TEMPLATE = """
<h2>Verify Your Email</h2>
<p>Welcome to Tasknode! Please click the link below to verify your email address:</p>
<p><a href="{verification_url}">Verify Email</a></p>
<p>If you didn't create this account, please ignore this email.</p>
"""


def send_email(emails: List[str], subject: str, html: str):
    resend_key = settings.RESEND_KEY
    resend.api_key = resend_key
    r = resend.Emails.send(
        {
            "from": "no-reply@tasknode.dev",
            "to": emails,
            "subject": subject,
            "html": html,
        }
    )
    logger.info(f"Email sent: {r}")
