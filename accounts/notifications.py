import logging
import requests
from django.conf import settings

logger = logging.getLogger("accounts.notifications")


def send_whatsapp(mobile, message):
    """Send a WhatsApp notification using the configured backend."""
    if not getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", True):
        logger.info("[WhatsApp disabled] to %s: %s", mobile, message)
        return True

    backend = getattr(settings, "WHATSAPP_BACKEND", "console")

    if backend == "console":
        logger.info("[WhatsApp to %s] %s", mobile, message)
        print(f"[DEV WhatsApp] to {mobile}: {message}")
        return True

    if backend == "msg91":
        if not settings.MSG91_AUTH_KEY or not settings.WHATSAPP_FLOW_ID:
            logger.error("MSG91 WhatsApp send failed because auth key or flow ID is not configured.")
            return False

        resp = requests.post(
            "https://control.msg91.com/api/v5/flow/",
            headers={"authkey": settings.MSG91_AUTH_KEY, "Content-Type": "application/json"},
            json={
                "flow_id": settings.WHATSAPP_FLOW_ID,
                "mobiles": f"91{mobile}",
                "VAR1": message,
            },
            timeout=8,
        )
        ok = resp.ok
        if not ok:
            logger.error("MSG91 WhatsApp send failed for %s: %s", mobile, resp.text)
        return ok

    raise ValueError(f"Unknown WHATSAPP_BACKEND: {backend}")
