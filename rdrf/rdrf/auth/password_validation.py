import logging
import re
from abc import ABC, abstractmethod

from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from rdrf.auth.pwned_passwords import pwned_passwords

logger = logging.getLogger(__name__)


class BaseHasCharacterValidator(ABC):
    name = None
    pattern = None

    def __init__(self, min_occurrences=1):
        self.min_occurrences = min_occurrences

    @staticmethod
    @abstractmethod
    def validation_error_text(min_occurrences):
        pass

    def validate(self, password, user=None):
        if len(self.pattern.findall(password)) < self.min_occurrences:
            raise ValidationError(
                self.validation_error_text(self.min_occurrences),
                code="password_does_not_have_enough_%ss" % self.name,
                params={"min_occurrences": self.min_occurrences},
            )

    def get_help_text(self):
        return self.validation_error_text(self.min_occurrences)


class HasNumberValidator(BaseHasCharacterValidator):
    name = "number"
    pattern = re.compile(r"\d")

    @staticmethod
    def validation_error_text(min_occurrences):
        return ngettext(
            "Your password must contain at least {min_occurrences} number",
            "Your password must contain at least {min_occurrences} numbers",
            min_occurrences,
        ).format(min_occurrences=min_occurrences)


class HasUppercaseLetterValidator(BaseHasCharacterValidator):
    name = "uppercase letter"
    pattern = re.compile(r"[A-Z]")

    @staticmethod
    def validation_error_text(min_occurrences):
        return ngettext(
            "Your password must contain at least {min_occurrences} uppercase letter",
            "Your password must contain at least {min_occurrences} uppercase letters",
            min_occurrences,
        ).format(min_occurrences=min_occurrences)


class HasLowercaseLetterValidator(BaseHasCharacterValidator):
    name = "lowercase letter"
    pattern = re.compile(r"[a-z]")

    @staticmethod
    def validation_error_text(min_occurrences):
        return ngettext(
            "Your password must contain at least {min_occurrences} lowercase letter",
            "Your password must contain at least {min_occurrences} lowercase letters",
            min_occurrences,
        ).format(min_occurrences=min_occurrences)


class HasSpecialCharacterValidator(BaseHasCharacterValidator):
    name = "special character"
    pattern = re.compile(r"[^A-Za-z0-9\s]")

    @staticmethod
    def validation_error_text(min_occurrences):
        return ngettext(
            "Your password must contain at least {min_occurrences} special character",
            "Your password must contain at least {min_occurrences} special characters",
            min_occurrences,
        ).format(min_occurrences=min_occurrences)


class ConsecutivelyRepeatingCharacterValidator:
    def __init__(self, length=3):
        self.length = length
        assert (
            self.length > 1
        ), "Length should be at least 2 for consecutively repeating character validators!"
        self.repeating_char = re.compile(
            r"""
            (.)   # any character, in a group so we can backreference
            \1    # backreference to the character
            {%s,} # repeated length-1 times (subtract 1 for the initial match)
        """
            % (self.length - 1),
            re.VERBOSE,
        )

    def validate(self, password, user=None):
        if re.search(self.repeating_char, password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return _(
            "Your password must not contain {length} repeating characters."
        ).format(length=self.length)


class NumberRuleValidator(ABC):
    def __init__(self, length=3):
        self.length = length
        assert (
            self.length > 1
        ), "Length should be at least 2 for numbers related password validators!"

    @staticmethod
    @abstractmethod
    def validation_func(prev, cur):
        pass

    @staticmethod
    @abstractmethod
    def validation_error_text(min_occurrences):
        pass

    def validate(self, password, user=None):
        digit_groups = re.findall(r"\d{%s,}" % self.length, password)
        for digits in digit_groups:
            self.validate_digits(digits)

    def validate_digits(self, digits):
        count = 1
        for prev, cur in zip(digits, digits[1:]):
            if not self.validation_func(prev, cur):
                count = 1
                continue
            count += 1
            if count >= self.length:
                raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return self.validation_error_text(self.length)


class ConsecutivelyIncreasingNumberValidator(NumberRuleValidator):
    @staticmethod
    def validation_func(prev, cur):
        return int(prev) + 1 == int(cur) or prev == "9" and cur == "0"

    @staticmethod
    def validation_error_text(max_consecutive):
        return _(
            "Your password must not contain {max_consecutive} consecutively increasing numbers."
        ).format(max_consecutive=max_consecutive)


class ConsecutivelyDecreasingNumberValidator(NumberRuleValidator):
    @staticmethod
    def validation_func(prev, cur):
        return int(prev) - 1 == int(cur) or prev == "0" and cur == "9"

    @staticmethod
    def validation_error_text(max_consecutive):
        return _(
            "Your password must not contain {max_consecutive} consecutively decreasing numbers."
        ).format(max_consecutive=max_consecutive)


class DifferentToPrevious:
    def validate(self, password, user=None):
        if user and user.check_password(password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return _(
            "You must change the password to something other than your current password."
        )


class EnhancedCommonPasswordValidator:
    breached_password_detection = None
    max_breach_threshold = None

    def __init__(self, breached_password_detection, max_breach_threshold=0):
        self.breached_password_detection = breached_password_detection
        self.max_breach_threshold = max_breach_threshold

    def validate(self, password, user=None):
        validated = False
        if self.breached_password_detection:
            breached_cnt = None
            try:
                breached_cnt = pwned_passwords.check_breaches(password)
            except Exception as e:
                logger.error(
                    e
                )  # Log the error, but fall back to the common password validator

            if breached_cnt is not None:
                validated = True
                if breached_cnt > self.max_breach_threshold:
                    raise ValidationError(_("This password is too insecure."))

        if not validated:
            CommonPasswordValidator().validate(password, user)

    def get_help_text(self):
        return _("Your password can't be a commonly used password.")
