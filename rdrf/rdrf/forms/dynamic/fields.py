# Custom Fields
from itertools import zip_longest
import datetime
import magic
import os

from django.core.exceptions import ValidationError
from django.forms import CharField
from django.forms import ChoiceField
from django.forms import FileField
from django.forms import URLField
from django.forms import DateField

from rdrf.forms.widgets.widgets import MultipleFileInput
from rdrf.models.definition.models import UploadFileType


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_allowed_types(kwargs.get('allowed_types', []))

    def set_allowed_types(self, allowed_types):
        self.allowed_types = allowed_types
        all_allowed_types = UploadFileType.objects.all()
        if not self.allowed_types:
            self.allowed_types = all_allowed_types
        else:
            all_allowed_mime_types = set(t.mime_type for t in all_allowed_types)
            self.allowed_types = [t for t in allowed_types if t.mime_type in all_allowed_mime_types]
        self.allowed_mime_types = [t.mime_type for t in self.allowed_types]
        self.allowed_extensions = [t.extension for t in self.allowed_types]
        self.allowed_types_mapping = {t.mime_type: t.extension for t in self.allowed_types}

    def validate(self, value):
        allowed_mime_types = self.allowed_mime_types
        if getattr(self, 'cde', None):
            cde_mime_types = self.cde.widget_settings.get('allowed_file_types', self.allowed_mime_types)
            allowed_mime_types = set(allowed_mime_types) & set(cde_mime_types)
        __, ext = os.path.splitext(value._name)
        mime_type = magic.from_buffer(value.file.read(2048), mime=True)
        value.file.seek(0)
        if mime_type not in allowed_mime_types:
            raise ValidationError(f"File type not allowed. Only {', '.join(self.allowed_extensions)} files are allowed.")
        if self.allowed_types_mapping[mime_type] != ext[1:]:
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
