from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.validators import validate_birthdate

from .managers import UserManager
from .validators import normalize_phone_number, phone_number_validator


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("Email", unique=True)
    birthdate = models.DateField(
        "Дата рождения", null=True, blank=True, validators=[validate_birthdate]
    )
    phone_number = models.CharField(
        "Номер телефона",
        max_length=13,
        blank=True,
        default="",
        validators=[phone_number_validator],
        help_text="Для суперпользователя обязателен. Пример: +996700123456.",
    )
    is_staff = models.BooleanField("Доступ к админке", default=False)
    is_active = models.BooleanField("Активен", default=True)
    date_joined = models.DateTimeField("Дата регистрации", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    # Это список вопросов команды createsuperuser, а не обязательных полей API.
    REQUIRED_FIELDS = ["phone_number"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["email"]
        # Защищает обязательность телефона даже при записи напрямую в БД.
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_superuser=False) | ~models.Q(phone_number=""),
                name="superuser_requires_phone_number",
            )
        ]

    def clean(self):
        super().clean()
        self.email = type(self).objects.normalize_email(self.email)
        try:
            self.phone_number = normalize_phone_number(self.phone_number)
        except ValidationError as error:
            raise ValidationError({"phone_number": error.messages}) from error
        if self.is_superuser and not self.phone_number:
            raise ValidationError(
                {"phone_number": "Для суперпользователя номер телефона обязателен."}
            )

    def __str__(self):
        return self.email
