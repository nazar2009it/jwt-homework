from datetime import date
from unittest.mock import patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from common.validators import validate_birthdate, validate_product_age


class AgeValidatorTests(SimpleTestCase):
    def setUp(self):
        self.today = patch("common.validators.timezone.localdate", return_value=date(2026, 10, 13))
        self.today.start()
        self.addCleanup(self.today.stop)

    def test_adult_and_eighteenth_birthday_are_allowed(self):
        for birthday in ("2000-01-01", "2008-10-13"):
            with self.subTest(birthday=birthday):
                validate_product_age(birthday)

    def test_one_day_before_eighteenth_birthday_is_rejected(self):
        with self.assertRaises(ValidationError) as error:
            validate_product_age("2008-10-14")
        self.assertEqual(str(error.exception.detail["birthdate"]), "Вам должно быть 18 лет, чтобы создать продукт.")

    def test_year_difference_alone_does_not_make_user_an_adult(self):
        with self.assertRaises(ValidationError):
            validate_product_age("2008-12-31")

    def test_missing_birthdate_has_required_message(self):
        for value in (None, ""):
            with self.subTest(value=value), self.assertRaises(ValidationError) as error:
                validate_product_age(value)
            self.assertEqual(str(error.exception.detail["birthdate"]), "Укажите дату рождения, чтобы создать продукт.")

    def test_malformed_claim_is_rejected(self):
        for value in ("wrong", "2000-02-30", "20000101", 20000101, [], {}, True):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_product_age(value)

    def test_future_birthdate_cannot_pass_age_check(self):
        with self.assertRaises(ValidationError):
            validate_product_age("2030-01-01")

    def test_leap_day_birthday_requires_march_first_in_non_leap_year(self):
        with patch("common.validators.timezone.localdate", return_value=date(2026, 2, 28)):
            with self.assertRaises(ValidationError):
                validate_product_age("2008-02-29")
        with patch("common.validators.timezone.localdate", return_value=date(2026, 3, 1)):
            validate_product_age("2008-02-29")

    def test_birthdate_field_rejects_future_but_accepts_minor(self):
        validate_birthdate(date(2015, 1, 1))
        with self.assertRaises(DjangoValidationError):
            validate_birthdate(date(2026, 10, 14))
