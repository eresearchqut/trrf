# Custom Fields
from collections import defaultdict
from itertools import zip_longest
import datetime
import json
import magic
import os

from django.core.exceptions import ValidationError
from django.forms import CharField
from django.forms import ChoiceField
from django.forms import FileField
from django.forms import URLField
from django.forms import DateField
from django.utils.translation import gettext as _

from rdrf.forms.widgets.widgets import MultipleFileInput, CustomFileInput


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

    def _find_blacklisted_mime_type(self, mt):
        from rdrf.models.definition.models import BlacklistedMimeType
        return BlacklistedMimeType.objects.filter(mime_type=mt).first()

    def _init_structures(self):
        self.allowed_mime_types = [t.mime_type for t in self.allowed_types]
        self.allowed_extensions = [t.extension for t in self.allowed_types]
        self.allowed_types_mapping = defaultdict(list)
        for t in self.allowed_types:
            self.allowed_types_mapping[t.mime_type].append(t.extension)

    def set_allowed_types(self, allowed_types):
        self.allowed_types = allowed_types

    def validate(self, value):
        if not value:
            return super().validate(value)
        __, ext = os.path.splitext(value._name)
        mime_type = magic.from_buffer(value.file.read(2048), mime=True)
        value.file.seek(0)

        blacklisted_mime_type = self._find_blacklisted_mime_type(mime_type)
        if blacklisted_mime_type:
            raise ValidationError(_(f"{blacklisted_mime_type.description} file types aren't allowed to be uploaded into the system !"))

        matched_type = mime_type
        for t in allowed_mime_types:
            if mime_type == t or mime_type.startswith(t):
                matched_type = t
                break

        allowed_extensions = {
            mt for mime_type in allowed_mime_types for mt in self.allowed_types_mapping[mime_type]
        }
        if matched_type not in allowed_mime_types:
            if not allowed_extensions:
                raise ValidationError(f"No file types allowed. Please check your configuration.")
            else:
                raise ValidationError(f"File type not allowed. Only {', '.join(allowed_extensions)} files are allowed.")
        if ext[1:] not in self.allowed_types_mapping[matched_type]:
            raise ValidationError(f"File extension not allowed. Only {', '.join(allowed_extensions)} files are allowed.")
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
