from django.core.validators import RegexValidator


phone_number_validator = RegexValidator(
    regex=r"^\+?996[0-9]{9}$",
    message="Введите номер в формате +996700123456 или 996700123456.",
)


def normalize_phone_number(value):
    """Пустой номер разрешён; непустой проверяем и храним с плюсом."""
    value = (value or "").strip()
    if not value:
        return ""
    phone_number_validator(value)
    return value if value.startswith("+") else f"+{value}"
