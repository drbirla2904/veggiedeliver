from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from .models import User
from .serializers import RequestOTPSerializer, VerifyOTPSerializer, UserSerializer
from .services import generate_and_send_otp, verify_otp, OTPCooldownError, OTPAttemptsExceededError


class RequestOTPView(APIView):
    """POST { mobile } -> sends OTP. Used for both login and signup —
    the client doesn't need to know in advance which one it is."""
    permission_classes = []

    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=False))
    def post(self, request):
        if getattr(request, "limited", False):
            return Response({"detail": "Too many OTP requests. Please try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            generate_and_send_otp(serializer.validated_data["mobile"])
        except OTPCooldownError as e:
            return Response(
                {"detail": f"Please wait {e.seconds_remaining}s before requesting another OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response({"detail": "OTP sent."})


class VerifyOTPView(APIView):
    """POST { mobile, code, first_name?, referral_code? }
    -> verifies OTP, creates the customer account on first login,
    applies a referral code if supplied, and returns an auth token."""
    permission_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ok = verify_otp(data["mobile"], data["code"])
        except OTPAttemptsExceededError:
            return Response({"detail": "Too many incorrect attempts. Request a new OTP."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if not ok:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(
            mobile=data["mobile"],
            defaults={
                "username": data["mobile"],
                "first_name": data.get("first_name", ""),
                "role": User.Role.CUSTOMER,
                "mobile_verified": True,
            },
        )
        if not created and not user.mobile_verified:
            user.mobile_verified = True
            user.save(update_fields=["mobile_verified"])

        if created and data.get("referral_code"):
            referrer = User.objects.filter(referral_code=data["referral_code"]).exclude(pk=user.pk).first()
            if referrer:
                user.referred_by = referrer
                user.save(update_fields=["referred_by"])

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": UserSerializer(user).data,
            "is_new_user": created,
        })


# ---------------------------------------------------------------------------
# Template-based (session) auth flow, alongside the JSON API above.
# ---------------------------------------------------------------------------
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required


@ratelimit(key='ip', rate='10/h', method='POST', block=False)
@ratelimit(key='post:mobile', rate='5/h', method='POST', block=False)
def login_page(request):
    """Step 1: collect mobile number, send OTP, move to step 2."""
    if request.user.is_authenticated:
        return redirect("home")

    ref = request.GET.get("ref", "")
    if ref:
        request.session["pending_referral_code"] = ref

    if request.method == "POST":
        if getattr(request, "limited", False):
            messages.error(request, "Too many OTP requests. Please wait a while and try again.")
            return render(request, "accounts/login.html", {"step": "mobile"})

        mobile = request.POST.get("mobile", "").strip()
        if not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
            messages.error(request, "Enter a valid 10-digit mobile number.")
            return render(request, "accounts/login.html", {"step": "mobile"})

        try:
            generate_and_send_otp(mobile)
        except OTPCooldownError as e:
            request.session["pending_mobile"] = mobile
            messages.info(request, f"OTP already sent — you can request a new one in {e.seconds_remaining}s.")
            return redirect("verify_otp_page")

        request.session["pending_mobile"] = mobile
        messages.success(request, "OTP sent to your mobile number.")
        return redirect("verify_otp_page")

    return render(request, "accounts/login.html", {"step": "mobile"})


def verify_otp_page(request):
    """Step 2: verify the OTP, create the customer account on first login,
    apply a pending referral code, and start the session."""
    mobile = request.session.get("pending_mobile")
    if not mobile:
        return redirect("login")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        name = request.POST.get("first_name", "").strip()

        try:
            ok = verify_otp(mobile, code)
        except OTPAttemptsExceededError:
            messages.error(request, "Too many incorrect attempts. Please request a new OTP.")
            request.session.pop("pending_mobile", None)
            return redirect("login")

        if not ok:
            messages.error(request, "Invalid or expired OTP. Please try again.")
            return render(request, "accounts/login.html", {"step": "otp", "mobile": mobile})

        user, created = User.objects.get_or_create(
            mobile=mobile,
            defaults={
                "username": mobile,
                "first_name": name,
                "role": User.Role.CUSTOMER,
                "mobile_verified": True,
            },
        )
        if not created and not user.mobile_verified:
            user.mobile_verified = True
            user.save(update_fields=["mobile_verified"])

        ref_code = request.session.pop("pending_referral_code", None)
        if created and ref_code:
            referrer = User.objects.filter(referral_code=ref_code).exclude(pk=user.pk).first()
            if referrer:
                user.referred_by = referrer
                user.save(update_fields=["referred_by"])

        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.pop("pending_mobile", None)
        messages.success(request, f"Welcome{', ' + name if name else ''}!")

        if user.role == User.Role.AREA_ADMIN:
            return redirect("area_dashboard")
        if user.role == User.Role.DELIVERY_MEMBER:
            return redirect("delivery_dashboard")
        return redirect("home")

    return render(request, "accounts/login.html", {"step": "otp", "mobile": mobile})


def logout_view(request):
    auth_logout(request)
    return redirect("home")


@login_required
def profile_page(request):
    return render(request, "accounts/profile.html")