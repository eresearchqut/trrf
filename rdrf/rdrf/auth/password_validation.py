import re

from django.core.exceptions import ValidationError
from django.utils.translation import ngettext
from django.utils.translation import gettext as _


class BaseHasCharacterValidator:
    name = None
    pattern = None

    def __init__(self, min_occurences=1):
        self.min_occurences = min_occurences

    @property
    def msg(self):
        return 'The password must contain at least %(min_occurences)s ' + self.name + '.'

    @property
    def msg_plural(self):
        return 'The password must contain at least %(min_occurences)s ' + self.name + 's.'

    @property
    def help_text(self):
        return 'Your password must contain at least %(min_occurences)s ' + self.name + '.'

    @property
    def help_text_plural(self):
        return 'Your password must contain at least %(min_occurences)s ' + self.name + 's.'

    def validate(self, password, user=None):
        if len(self.pattern.findall(password)) < self.min_occurences:
            raise ValidationError(
                ngettext(self.msg, self.msg_plural, self.min_occurences),
                code='password_does_not_have_enough_%ss' % self.name,
                params={'min_occurences': self.min_occurences},
            )

    def get_help_text(self):
        return ngettext(self.help_text, self.help_text_plural, self.min_occurences) % {
            'min_occurences': self.min_occurences}


class HasNumberValidator(BaseHasCharacterValidator):
    name = 'number'
    pattern = re.compile(r'\d')


class HasUppercaseLetterValidator(BaseHasCharacterValidator):
    name = 'uppercase letter'
    pattern = re.compile(r'[A-Z]')


class HasLowercaseLetterValidator(BaseHasCharacterValidator):
    name = 'lowercase letter'
    pattern = re.compile(r'[a-z]')


class HasSpecialCharacterValidator(BaseHasCharacterValidator):
    name = 'special character'
    pattern = re.compile(r'[^A-Za-z0-9\s]')


class ConsecutivelyRepeatingCharacterValidator:

    def __init__(self, length=3):
        self.length = length
        assert self.length > 1, "Length should be at least 2 for consecutively repeating character validators!"
        self.repeating_char = re.compile(r'''
            (.)   # any character, in a group so we can backreference
            \1    # backreference to the character
            {%s,} # repeated length-1 times (subtract 1 for the initial match)
        ''' % (self.length - 1), re.VERBOSE)

    def validate(self, password, user=None):
        if re.search(self.repeating_char, password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return _(f"Your password must not contain {self.length} repeating characters.")


class NumberRuleValidator:
    def __init__(self, length=3):
        self.length = length
        assert self.length > 1, "Length should be at least 2 for numbers related password validators!"

    def validation_func(self, prev, cur):
        raise NotImplementedError("subclass responsibility")

    def validate(self, password, user=None):
        digit_groups = re.findall(r'\d{%s,}' % self.length, password)
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
        return _(f"Your password must not contain {self.length} consecutively {self.name} numbers.")


class ConsecutivelyIncreasingNumberValidator(NumberRuleValidator):
    name = 'increasing'

    def validation_func(self, prev, cur):
        return int(prev) + 1 == int(cur) or prev == '9' and cur == '0'


class ConsecutivelyDecreasingNumberValidator(NumberRuleValidator):
    name = 'decreasing'

    def validation_func(self, prev, cur):
        return int(prev) - 1 == int(cur) or prev == '0' and cur == '9'


class DifferentToPrevious:
    def validate(self, password, user=None):
        if user and user.check_password(password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return _("You must change the password to something other than your current password.")
