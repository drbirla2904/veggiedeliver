from rest_framework import serializers
from .models import User


class RequestOTPSerializer(serializers.Serializer):
    mobile = serializers.RegexField(r'^[6-9]\d{9}$')


class VerifyOTPSerializer(serializers.Serializer):
    mobile = serializers.RegexField(r'^[6-9]\d{9}$')
    code = serializers.RegexField(r'^\d{6}$')
    # Optional — only used the first time, to register a new customer
    first_name = serializers.CharField(required=False, allow_blank=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "mobile", "first_name", "last_name", "role", "referral_code"]
