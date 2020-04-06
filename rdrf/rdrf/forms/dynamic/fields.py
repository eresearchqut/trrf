# Custom Fields
from itertools import zip_longest
import datetime
import magic
import os

from django.conf import settings
from django.forms import CharField
from django.forms import ChoiceField
from django.forms import FileField
from django.forms import URLField
from django.forms import DateField
from rdrf.forms.widgets.widgets import MultipleFileInput
from django.core.exceptions import ValidationError


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
            raise ValidationError("A value must be selected")


class FileTypeRestrictedFileField(FileField):

    ALLOWED_TYPES = [s['mime-type'] for s in settings.ALLOWED_FILE_TYPES]
    ALLOWED_TYPES_MAPPING = {
        s['mime-type']: s['extension'] for s in settings.ALLOWED_FILE_TYPES
    }

    def validate(self, value):
        allowed_types = self.ALLOWED_TYPES
        if getattr(self, 'cde', None):
            allowed_types = self.cde.widget_settings.get('allowed_file_types', self.ALLOWED_TYPES)
        __, ext = os.path.splitext(value._name)
        mime_type = magic.from_buffer(value.file.read(2048), mime=True)
        value.file.seek(0)
        if mime_type not in allowed_types:
            raise ValidationError("File type not allowed. Only pdf, doc, docx or plain text files are allowed.")
        if self.ALLOWED_TYPES_MAPPING[mime_type] != ext:
            raise ValidationError("File extension does not match the file type !")
        return super().validate(value)


class MultipleFileField(FileTypeRestrictedFileField):
    """
    A field made from multiple file fields.
    Values go in and out as lists of files.
    """
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        return [super(MultipleFileField, self).clean(item, init)
                for (item, init) in zip_longest(data, initial or [])]

    def bound_data(self, data, initial):
        return [super(MultipleFileField, self).bound_data(item, init)
                for (item, init) in zip_longest(data, initial or [])]

    def has_changed(self, initial, data):
        return any(super(MultipleFileField, self).has_changed(initial, item)
                   for item in data)


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
