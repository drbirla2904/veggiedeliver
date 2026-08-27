from django.urls import path
from .views import (
    RequestOTPView, VerifyOTPView,
    login_page, verify_otp_page, logout_view, profile_page, delete_address,
)

urlpatterns = [
    # JSON API (for a future mobile app)
    path("api/otp/request/", RequestOTPView.as_view(), name="request-otp"),
    path("api/otp/verify/", VerifyOTPView.as_view(), name="verify-otp"),

    # Web (session) auth
    path("login/", login_page, name="login"),
    path("login/verify/", verify_otp_page, name="verify_otp_page"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile_page, name="profile"),
    path("profile/addresses/<int:address_id>/delete/", delete_address, name="delete_address"),
]
