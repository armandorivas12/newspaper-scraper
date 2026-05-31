import logging

import resend

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str, api_key: str) -> bool:
    resend.api_key = api_key
    try:
        resend.Emails.send({
            "from": "Dominican Digest <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "html": html_body,
        })
        logger.info("Email sent to %s", to)
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
