"""
Upload file types and categories
"""

from rdrf.models.definition.models import (
    BlacklistedMimeType, ConsentConfiguration, 
    Registry, UploadFileTypeCategory, UploadFileType
)


def load_data(**kwargs):
    init_upload_file_types_and_categories()
    for r in Registry.objects.all():
        update_consent_configuration(r)


def init_upload_file_types_and_categories():
    for category, __ in UploadFileTypeCategory.FILE_TYPE_CATEGORY_CHOICES:
        UploadFileTypeCategory.objects.get_or_create(name=category)
    
    UploadFileType.objects.all_types().get_or_create(
        mime_type='application/pdf', defaults={
            'extension': 'pdf',
            'description': 'PDF document',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.DOCUMENT)
        }
    )
    UploadFileType.objects.all_types().get_or_create(
        mime_type='text/plain', defaults={
            'extension': 'txt',
            'description': 'Plain text',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.TEXT)
        }
    )
    UploadFileType.objects.all_types().get_or_create(
        mime_type='application/msword', defaults={
            'extension': 'doc',
            'description': 'Word document (.doc)',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.DOCUMENT)
        }
    )

    UploadFileType.objects.all_types().get_or_create(
        mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', defaults={
            'extension': 'docx',
            'description': 'Word document (.docx)',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.DOCUMENT)
        }
    )

    UploadFileType.objects.all_types().get_or_create(
        mime_type='image/jpeg', extension='jpeg', defaults={
            'description': 'JPEG image(.jpeg)',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.IMAGE)
        }
    )

    UploadFileType.objects.all_types().get_or_create(
        mime_type='image/jpeg', extension='jpg', defaults = {
            'description': 'JPEG image (.jpg)',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.IMAGE)
        }
    )

    UploadFileType.objects.all_types().get_or_create(
        mime_type='image/png', defaults={
            'extension': 'png',
            'description': 'PNG image',
            'category': UploadFileTypeCategory.objects.get(name=UploadFileTypeCategory.IMAGE)
        }
    )

    BlacklistedMimeType.objects.get_or_create(
        mime_type='application/octet-stream',
        description = 'Prevent uploads for executables/archives'
    )


def update_consent_configuration(registry):
    config, __ = ConsentConfiguration.objects.get_or_create(registry=registry)
    config.allowed_file_types.set(UploadFileType.objects.all())
