from django.contrib.auth.base_user import BaseUserManager

from .validators import normalize_phone_number


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        # В этом проекте email считаем одинаковым независимо от регистра.
        return super().normalize_email(email).strip().lower()

    def get_by_natural_key(self, email):
        return self.get(email=self.normalize_email(email))

    def create_user(self, email, password=None, phone_number="", **extra_fields):
        if not email or not email.strip():
            raise ValueError("Email обязателен.")

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(
            email=self.normalize_email(email),
            phone_number=normalize_phone_number(phone_number),
            **extra_fields,
        )
        # set_password сохраняет хеш, а не исходный пароль.
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, phone_number="", **extra_fields):
        if not phone_number or not phone_number.strip():
            raise ValueError("Для суперпользователя номер телефона обязателен.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя is_staff должен быть True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("У суперпользователя is_superuser должен быть True.")

        return self.create_user(
            email=email,
            password=password,
            phone_number=phone_number,
            **extra_fields,
        )
