from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.exceptions import ValidationError


def validate_birthdate(value):
    if value > timezone.localdate():
        raise DjangoValidationError("Дата рождения не может быть в будущем.")


def validate_product_age(birthdate):
    """Проверяем дату из проверенного JWT, а не из тела запроса или БД."""
    if birthdate is None or birthdate == "":
        raise ValidationError(
            {"birthdate": "Укажите дату рождения, чтобы создать продукт."}
        )
    try:
        birthday = date.fromisoformat(birthdate)
        if birthday.isoformat() != birthdate:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError(
            {"birthdate": "Некорректная дата рождения в токене."}
        ) from None
    today = timezone.localdate()
    age = today.year - birthday.year - (
        (today.month, today.day) < (birthday.month, birthday.day)
    )
    if age < 18:
        raise ValidationError(
            {"birthdate": "Вам должно быть 18 лет, чтобы создать продукт."}
        )
