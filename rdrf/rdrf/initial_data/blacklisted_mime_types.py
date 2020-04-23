"""
Blacklisted mime types setup
"""

from rdrf.models.definition.models import BlacklistedMimeType


def load_data(**kwargs):
    init_blacklisted_file_types()


def init_blacklisted_file_types():

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/octet-stream',
        defaults = {
            'description': 'Executables files/Archives/Binary data'
        }
    )
