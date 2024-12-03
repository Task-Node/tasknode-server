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
