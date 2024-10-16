# Custom Fields
import datetime
import os
from itertools import zip_longest

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import CharField, ChoiceField, DateField, FileField, URLField
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from rdrf.forms.widgets.widgets import CustomFileInput, MultipleFileInput
from rdrf.models.definition.models import WhitelistedFileExtension


class DatatypeFieldAlphanumericxxsx(URLField):
    pass


class ChoiceWithOtherPleaseSpecify(ChoiceField):
    pass


class CustomFieldC18587(CharField):
    def to_python(self, value):
        return value + "haha"


class ChoiceFieldNoValidation(ChoiceField):
    def validate(self, value):
        pass


class ChoiceFieldNonBlankValidation(ChoiceField):
    def validate(self, value):
        if not value:
            raise ValidationError(_("A value must be selected"))


class FileTypeRestrictedFileField(FileField):
    def _find_whitelisted_file_types(self, file_extension):
        return WhitelistedFileExtension.objects.filter(
            file_extension__iexact=file_extension
        )

    def validate(self, value):
        if not value:
            return super().validate(value)
        __, ext = os.path.splitext(value.name)
        value.file.seek(0)

        if not self._find_whitelisted_file_types(ext):
            raise ValidationError(
                mark_safe(
                    _(
                        (
                            f"{ext} is not a supported file extension. "
                            f"Please contact {settings.CURATOR_EMAIL} if you believe this is an error."
                        )
                    )
                )
            )

        return super().validate(value)


class CustomFileField(FileTypeRestrictedFileField):
    widget = CustomFileInput


class MultipleFileField(CustomFileField):
    """
    A field made from multiple file fields.
    Values go in and out as lists of files.
    """

    widget = MultipleFileInput

    def clean(self, data, initial=None):
        return [
            super(MultipleFileField, self).clean(item, init)
            for (item, init) in zip_longest(data, initial or [])
        ]

    def bound_data(self, data, initial):
        return [
            super(MultipleFileField, self).bound_data(item, init)
            for (item, init) in zip_longest(data, initial or [])
        ]

    def has_changed(self, initial, data):
        return any(
            super(MultipleFileField, self).has_changed(initial, item)
            for item in data
        )


class IsoDateField(DateField):
    """
    A date field which stores dates as strings in iso format, instead
    of as date objects.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", []).append("%Y-%m-%d")
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, str):
            for fmt in self.input_formats:
                try:
                    return self.strptime(value, fmt) if value else None
                except (ValueError, TypeError):
                    continue
        return value

    def to_python(self, value):
        value = super().to_python(value)
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value
