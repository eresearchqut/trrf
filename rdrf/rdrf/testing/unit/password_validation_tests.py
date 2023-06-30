from unittest import TestCase, mock
from unittest.mock import Mock

import pwnedpasswords
from django.contrib.auth.password_validation import (
    CommonPasswordValidator, MinimumLengthValidator, UserAttributeSimilarityValidator
)
from django.forms import ValidationError

from rdrf.auth import password_validation
from rdrf.auth.password_validation import (
    ConsecutivelyRepeatingCharacterValidator, ConsecutivelyIncreasingNumberValidator,
    ConsecutivelyDecreasingNumberValidator, HasNumberValidator, HasUppercaseLetterValidator,
    HasLowercaseLetterValidator, HasSpecialCharacterValidator, EnhancedCommonPasswordValidator
)
from registry.groups.models import CustomUser


class PasswordValidationTests(TestCase):

    def test_consecutively_repeating_chars(self):
        validator = ConsecutivelyRepeatingCharacterValidator(3)
        with self.assertRaises(ValidationError):
            # consecutive repeating 3 characters should raise a ValidationError
            validator.validate("12TestaaaCde")
        # Two repeating characters is fine
        validator.validate("12TestaaCde")
        with self.assertRaises(ValidationError):
            # Three consecutive numbers should raise the same exception
            validator.validate("12Test333Cde")

    def test_increasing_number_validation(self):
        validator = ConsecutivelyIncreasingNumberValidator(3)
        with self.assertRaises(ValidationError):
            # consecutively increasing 3 numbers raise error
            validator.validate("12Test123Cde")
        # Two increasing numbers is fine
        validator.validate("12Test")
        with self.assertRaises(ValidationError):
            # Four consecutive numbers raise an error
            validator.validate("12Test4567Cde")
        with self.assertRaises(ValidationError):
            # 0 is considered 10 in series like 890...
            validator.validate("T2es3t4bde890")
        with self.assertRaises(ValidationError):
            # Special case, running up to 0 then continue from 0 ex. 89012.
            validator = ConsecutivelyIncreasingNumberValidator(5)
            validator.validate("T2es3t4bde89012")

    def test_decreasing_number_validation(self):
        validator = ConsecutivelyDecreasingNumberValidator(3)
        with self.assertRaises(ValidationError):
            # consecutively decreasing 3 numbers raise error
            validator.validate("12Test654Cde")
        # Two decreasing characters is fine
        validator.validate("Tes2t1aa21e")
        with self.assertRaises(ValidationError):
            # Four consecutive numbers raise an error
            validator.validate("T2es3t4b9876Cde")
        with self.assertRaises(ValidationError):
            # 0 is considered 10 in series like 098...
            validator.validate("T2es3t4bde098")
        with self.assertRaises(ValidationError):
            # Special case, running down to 0 then continue from 9 ex. 21098.
            validator = ConsecutivelyDecreasingNumberValidator(5)
            validator.validate("T2es3t4bde21098")

    def test_has_number_validation(self):
        validator = HasNumberValidator(3)  # at least 3 numbers
        with self.assertRaises(ValidationError):
            # No numbers raises an exception
            validator.validate("AbcDef")
        validator.validate("Tes2t1cd3")
        with self.assertRaises(ValidationError):
            # Two numbers still raise an exception
            validator.validate("Abc12Def")

    def test_uppercase_validation(self):
        validator = HasUppercaseLetterValidator(2)  # at least 2 uppercase letters
        with self.assertRaises(ValidationError):
            # No uppercase letters raises an exception
            validator.validate("2131bcef")
        validator.validate("TeS2")
        with self.assertRaises(ValidationError):
            # 1 uppercase letter still raises an exception
            validator.validate("Abc12def")

    def test_lowercase_validation(self):
        validator = HasLowercaseLetterValidator(2)  # at least 2 lowercase letters
        with self.assertRaises(ValidationError):
            # No lowercase letters raises an exception
            validator.validate("2131BCD")
        validator.validate("TeS2a")
        with self.assertRaises(ValidationError):
            # 1 lowercase letter still raises an exception
            validator.validate("ABc12DEF")

    def test_special_characters_validation(self):
        validator = HasSpecialCharacterValidator(2)  # at least 2 special chars
        with self.assertRaises(ValidationError):
            # No special chars
            validator.validate("2131BCD")
        validator.validate("&@TeS2a")
        with self.assertRaises(ValidationError):
            # 1 special char still raises an exception
            validator.validate("$ABc12DEF")

    def test_minimum_length_validation(self):
        validator = MinimumLengthValidator(8)  # at least 8 charcaters
        with self.assertRaises(ValidationError):
            # No special chars
            validator.validate("abc12")
        validator.validate("abcd1234")

    def test_common_password_validation(self):
        validator = CommonPasswordValidator()
        with self.assertRaises(ValidationError):
            validator.validate("Password")
        validator.validate("12Tes$3289321DF")

    def test_similarity_validation(self):
        validator = UserAttributeSimilarityValidator()
        user = CustomUser(username="clinical")
        with self.assertRaises(ValidationError):
            # Similar to username
            validator.validate("clinician123", user=user)

    def test_insecure_validation(self):
        # Given standard password validator, which essentially uses the Django CommonPasswordValidator
        # Then Password12! passes validation
        validator = EnhancedCommonPasswordValidator(breached_password_detection=False)
        validator.validate('Password12!')
        # And password123 fails validation
        with self.assertRaises(ValidationError):
            validator.validate('password123')

        # When  we switch on enhanced password validation:
        # Then Password12! fails validation
        validator = EnhancedCommonPasswordValidator(breached_password_detection=True, max_breach_threshold=1)
        with self.assertRaises(ValidationError):
            validator.validate('Password12!')
        # And password123 fails validation
        with self.assertRaises(ValidationError):
            validator.validate('password123')
        # And a complex password passes validation
        validator.validate('R3a1!y S3CuRE P@$$w0rd!')

    @mock.patch(f'{password_validation.__name__}.pwnedpasswords', wraps=pwnedpasswords)
    def test_pwnedpasswords_api_is_down(self, *args, **kwargs):
        validator = EnhancedCommonPasswordValidator(breached_password_detection=True, max_breach_threshold=1)

        # Given the API is working, then expect Password12! to be throw a Validation Error when checked against the API
        with self.assertRaises(ValidationError) as e:
            validator.validate('Password12!')
        self.assertEqual(e.exception.message, 'This password is too insecure.')

        # Given the API is down,
        password_validation.pwnedpasswords.check = Mock(side_effect=Exception('Mock API Exception'))
        # Then expect the validation to fall back to the CommonPasswordValidator
        validator.validate('Password12!')
        with self.assertRaises(ValidationError) as e:
            validator.validate('password123')
        self.assertEqual(e.exception.message, 'This password is too common.')
