"""
Blacklisted mime types setup
"""

from rdrf.models.definition.models import BlacklistedMimeType


def load_data(**kwargs):
    init_blacklisted_file_types()


def init_blacklisted_file_types():

    mime_types_dict = {
        'application/octet-stream': 'Executable files/Archives/Binary data',
        'application/x-executable': 'Linux executable files',
        'application/x-sharedlib': 'Linux shared libraries',
        'text/x-shellscript': 'Linux/Unix shell scripts',
        'application/x-sh': 'Bourne shell scripts',
        'application/x-bsh': 'Bourne shell scripts',
        'application/x-shar': 'Bourne shell scripts',
        'text/x-script.sh': 'Bourne shell scripts',
        'application/x-csh': 'C shell scripts',
        'text/x-script.csh': 'C shell scripts',
        'application/x-debian-package': 'Debian packages',
        'application/x-msdownload': 'Microsoft applications',
        'application/x-binary': 'Binary files',
        'application/mac-binary': 'Mac binary files',
        'application/macbinary': 'Mac binary files',
        'application/x-macbinary': 'Mac binary files',
        'application/x-javascript': 'JavaScript files',
        'application/javascript': 'JavaScript files',
        'application/ecmascript': 'JavaScript files',
        'text/javascript': 'JavaScript files',
        'text/ecmascript': 'JavaScript files',
        'text/vbscript': 'VisualBasic script files',
        'application/x-ms-application': 'MS application',
        'application/x-java-applet': 'Java applet files',
        'application/vnd.ms-pki.seccat': 'Windows security catalogs'
    }

    for mime_type, desc in mime_types_dict.items():
        BlacklistedMimeType.objects.get_or_create(
            mime_type=mime_type,
            defaults = {
                'description': desc
            }
        )
