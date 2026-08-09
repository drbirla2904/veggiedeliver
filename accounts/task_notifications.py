from celery import shared_task
from .notifications import send_whatsapp


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_whatsapp_task(self, mobile, message):
    try:
        ok = send_whatsapp(mobile, message)
        if not ok:
            raise RuntimeError(f"WhatsApp gateway reported failure for {mobile}")
        return ok
    except Exception as exc:
        raise self.retry(exc=exc)
