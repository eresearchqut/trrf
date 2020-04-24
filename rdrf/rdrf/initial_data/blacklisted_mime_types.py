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
            'description': 'Executable files/Archives/Binary data'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-executable',
        defaults = {
            'description': 'Linux executable files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-sharedlib',
        defaults = {
            'description': 'Linux shared libraries'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='text/x-shellscript',
        defaults = {
            'description': 'Linux/Unix shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-sh',
        defaults = {
            'description': 'Bourne shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-bsh',
        defaults = {
            'description': 'Bourne shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-shar',
        defaults = {
            'description': 'Bourne shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='text/x-script.sh',
        defaults = {
            'description': 'Bourne shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-csh',
        defaults = {
            'description': 'C shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='text/x-script.csh',
        defaults = {
            'description': 'C shell scripts'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-debian-package',
        defaults = {
            'description': 'Debian packages'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-msdownload',
        defaults = {
            'description': 'Microsoft applications'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-binary',
        defaults = {
            'description': 'Binary files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/mac-binary',
        defaults = {
            'description': 'Mac binary files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/macbinary',
        defaults = {
            'description': 'Mac binary files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-macbinary',
        defaults = {
            'description': 'Mac binary files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/x-javascript',
        defaults = {
            'description': 'JavaScript files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/javascript',
        defaults = {
            'description': 'JavaScript files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/ecmascript',
        defaults = {
            'description': 'JavaScript files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='text/javascript',
        defaults = {
            'description': 'JavaScript files'
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='text/ecmascript',
        defaults = {
            'description': 'JavaScript files'
        }
    )
