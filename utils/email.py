from typing import List
from config import settings
import resend

from utils.logger import logger
from utils.utils import get_secret

FILE_GENERATED_TEMPLATE = """
<li>{file_name}</li>
"""

FILE_GENERATED_CONTAINER_TEMPLATE = """
<ul>
    {file_list}
</ul>
"""

FILE_LINK_TEMPLATE = """
<li><a href="{signed_url}">{file_name}</a></li>
"""

FAILURE_TEMPLATE = """
<h2 style="color: red;">Task Failed</h2>
<p>The task with ID <strong>{task_id}</strong> has failed. It ran for {runtime_minutes} minutes.</p>
<p>Please check the logs for more details and try again.</p>
<p>You can download the logs using these links:</p>
{file_list_container}
<ul>
    {output_log_link}
    {error_log_link}
    {generated_files_link}
</ul>
<p><strong>Note:</strong> These download links will expire in 72 hours.</p>
<p>Thank you for using Tasknode.</p>
"""

SUCCESS_TEMPLATE = """
<h2 style="color: green;">Task Completed</h2>
<p>The task with ID <strong>{task_id}</strong> completed successfully in {runtime_minutes} minutes.</p>
<p>The following files were generated:</p>
{file_list_container}
<p>You can download your outputs using these links:</p>
<ul>
    {output_log_link}
    {error_log_link}
    {generated_files_link}
</ul>
<p><strong>Note:</strong> These download links will expire in 72 hours.</p>
<p>Thank you for using Tasknode.</p>
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
