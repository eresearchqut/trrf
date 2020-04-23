"""Reference data like address types, etc.

Includes:
    - Address Types
"""

from registry.patients.models import AddressType

deps = ['patient_stage', 'blacklisted_mime_types', 'upload_file_types']


def load_data(**kwargs):
    load_address_types()


def load_address_types():
    AddressType.objects.get_or_create(type="Home", description="Home Address")
    AddressType.objects.get_or_create(type="Postal", description="Postal Address")
