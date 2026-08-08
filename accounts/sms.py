"""
Pluggable SMS gateway. Set SMS_BACKEND in settings (env var SMS_BACKEND)
to 'console' (dev — logs instead of sending), 'fast2sms', or 'msg91'.
Add the matching API key as an env var and you're live — no other code
changes needed anywhere else in the app.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger("accounts.sms")


def send_sms(mobile, message):
    backend = getattr(settings, "SMS_BACKEND", "console")

    if backend == "console":
        logger.info("[SMS to %s] %s", mobile, message)
        print(f"[DEV SMS] to {mobile}: {message}")  # visible in runserver logs
        return True

    if backend == "fast2sms":
        # https://docs.fast2sms.com/ — Quick SMS route
        resp = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": settings.FAST2SMS_API_KEY},
            data={"route": "q", "message": message, "language": "english", "flash": 0, "numbers": mobile},
            timeout=8,
        )
        ok = resp.ok and resp.json().get("return") is True
        if not ok:
            logger.error("Fast2SMS send failed for %s: %s", mobile, resp.text)
        return ok

    if backend == "msg91":
        # https://docs.msg91.com/ — adjust template_id / flow to your MSG91 setup
        resp = requests.post(
            "https://control.msg91.com/api/v5/flow/",
            headers={"authkey": settings.MSG91_AUTH_KEY, "Content-Type": "application/json"},
            json={
                "flow_id": settings.MSG91_FLOW_ID,
                "mobiles": f"91{mobile}",
                "VAR1": message,
            },
            timeout=8,
        )
        ok = resp.ok
        if not ok:
            logger.error("MSG91 send failed for %s: %s", mobile, resp.text)
        return ok

    raise ValueError(f"Unknown SMS_BACKEND: {backend}")