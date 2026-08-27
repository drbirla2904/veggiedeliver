import random
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import OTP
from .tasks import send_otp_sms_task

OTP_VALIDITY_MINUTES = 5


class OTPCooldownError(Exception):
    """Raised when a resend is requested before the cooldown window elapses."""
    def __init__(self, seconds_remaining):
        self.seconds_remaining = seconds_remaining


class OTPAttemptsExceededError(Exception):
    """Raised when too many wrong codes have been tried against the latest OTP."""
    pass


def generate_and_send_otp(mobile):
    cooldown = timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
    recent = OTP.objects.filter(mobile=mobile).order_by("-created_at").first()
    if recent and timezone.now() - recent.created_at < cooldown:
        remaining = cooldown - (timezone.now() - recent.created_at)
        raise OTPCooldownError(seconds_remaining=int(remaining.total_seconds()))

    code = f"{random.randint(100000, 999999)}"
    OTP.objects.create(mobile=mobile, code=code)
    message = f"Your Paytmcart OTP is {code}. Valid for {OTP_VALIDITY_MINUTES} minutes. Do not share this code."
    send_otp_sms_task.delay(mobile, message)
    return code


def verify_otp(mobile, code):
    cutoff = timezone.now() - timedelta(minutes=OTP_VALIDITY_MINUTES)
    otp = OTP.objects.filter(
        mobile=mobile, is_used=False, created_at__gte=cutoff
    ).order_by("-created_at").first()

    if not otp:
        return False

    if otp.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
        raise OTPAttemptsExceededError()

    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        return False

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return True