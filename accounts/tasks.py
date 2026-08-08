from celery import shared_task
from .sms import send_sms


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_otp_sms_task(self, mobile, message):
    """
    Fires the actual SMS gateway call in the background so a slow provider
    response never stalls the login page. Retries up to 3 times (5s apart)
    if the gateway call raises — e.g. a transient network blip to Fast2SMS.
    """
    try:
        ok = send_sms(mobile, message)
        if not ok:
            raise RuntimeError(f"SMS gateway reported failure for {mobile}")
        return ok
    except Exception as exc:
        raise self.retry(exc=exc)