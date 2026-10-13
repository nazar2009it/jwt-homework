from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .validators import normalize_phone_number


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "phone_number", "birthdate", "is_staff", "is_superuser")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message="Пользователь с таким email уже существует.",
            )
        ],
        help_text="Используется для регистрации и входа.",
    )
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=13,
        help_text="Необязательный. Формат: +996700123456 или 996700123456.",
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("email", "phone_number", "birthdate", "password", "password_confirm")

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        candidate = User(email=attrs["email"], phone_number=attrs.get("phone_number", ""))
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        try:
            return User.objects.create_user(**validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error


class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].trim_whitespace = False

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["birthdate"] = user.birthdate.isoformat() if user.birthdate else None
        return token

    def validate(self, attrs):
        attrs["email"] = User.objects.normalize_email(attrs["email"])
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
