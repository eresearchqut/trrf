import re

from django.core.exceptions import ValidationError
from django.utils.translation import ungettext
from django.utils.translation import ugettext as _


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
                ungettext(self.msg, self.msg_plural, self.min_occurences),
                code='password_does_not_have_enough_%ss' % self.name,
                params={'min_occurences': self.min_occurences},
            )

    def get_help_text(self):
        return ungettext(self.help_text, self.help_text_plural, self.min_occurences) % {
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
    pattern = re.compile(r'[!@#\$%\^&\*]')


class ConsecutivelyRepeatingCharacterValidator(BaseHasCharacterValidator):

    def __init__(self, length):
        self.length = length
        assert self.length > 1, "Length should be at least 2 for consecutively repeating character validators !"

    def validate(self, password, user=None):
        for c in password:
            if password.count(c) >= self.length:
                to_check = c * self.length
                if to_check in password:
                    raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return _(f"Your password must not contain {self.length} repeating characters")


class NumberRuleValidator(BaseHasCharacterValidator):

    def __init__(self, length):
        self.length = length
        assert self.length > 1, "Length should be at least 2 for numbers related password validators !"

    def validation_func(self, digits):
        raise NotImplementedError("subclass responsibility")

    def _validate_number_rule(self, password):
        digits = []
        for idx, c in enumerate(password):
            if c.isdigit():
                digits.append(int(c))
            else:
                if len(digits) >= self.length:
                    self.validation_func(digits)
                digits.clear()

        if len(digits) >= self.length:
            self.validation_func(digits)

    def validate(self, password, user=None):
        return self._validate_number_rule(password)


class ConsecutivelyIncreasingNumberValidator(NumberRuleValidator):

    def __init__(self, length):
        super().__init__(length)

    def validation_func(self, digits):
        count = 1
        prev = digits[0]
        for idx in range(1, len(digits)):
            d = digits[idx]
            if d == prev + 1:
                count += 1
                prev = d
                if count >= self.length:
                    raise ValidationError(self.get_help_text())
            else:
                prev = d
                count = 1

    def get_help_text(self):
        return _(f"Your password must not contain {self.length} consecutively increasing characters")


class ConsecutivelyDecreasingNumberValidator(NumberRuleValidator):

    def __init__(self, length):
        super().__init__(length)

    def validation_func(self, digits):
        count = 1
        prev = digits[0]
        for idx in range(1, len(digits)):
            d = digits[idx]
            if d == prev - 1:
                count += 1
                prev = d
                if count >= self.length:
                    raise ValidationError(self.get_help_text())
            else:
                prev = d
                count = 1

    def get_help_text(self):
        return _(f"Your password must not contain {self.length} consecutively decreasing characters")
