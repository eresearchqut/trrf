import logging
from itertools import groupby

from django.urls import reverse

from rdrf.events.events import EventType
from rdrf.helpers.utils import make_full_url
from rdrf.models.definition.models import (
    CDEFile,
    CommonDataElement,
    EmailNotification,
    RegistryForm,
    Section,
)

from .email_notification import process_given_notification

logger = logging.getLogger(__name__)


def handle_file_notifications(registry, patient, storage):
    uploaded_cde_files = storage.uploads
    if not uploaded_cde_files:
        return

    notifications = EmailNotification.objects.filter(
        registry=registry, description=EventType.FILE_UPLOADED
    )
    if not notifications.exists():
        return

    for notification in notifications:
        uploads = [
            u
            for u in uploaded_cde_files
            if _notification_interested_in_upload(notification, u)
        ]
        if uploads:
            template_data = _setup_template_data(registry, patient, uploads)
            process_given_notification(
                notification, template_data=template_data
            )


def _notification_interested_in_upload(notification, cde_file):
    if not notification.file_uploaded_cdes.exists():
        return True
    return cde_file.cde_code in set(
        notification.file_uploaded_cdes.values_list("code", flat=True)
    )


def _setup_template_data(registry, patient, uploads):
    patient_edit_url = reverse(
        "patient_edit",
        kwargs={"registry_code": registry.code, "patient_id": patient.pk},
    )
    patient_url = make_full_url(patient_edit_url)

    def location(cde_file):
        return (cde_file.form_name, cde_file.section_code, cde_file.cde_code)

    template_data = {
        "registry": registry.code,
        "patient": patient,
        "patient_url": patient_url,
        "file_info": [
            (_cde_info(registry, *loc), [f.filename for f in files])
            for loc, files in groupby(uploads, location)
        ],
    }

    return template_data


def _cde_info(registry, form_name, section_code, cde_code):
    is_registry_specific = form_name == CDEFile.REGISTRY_SPECIFIC_KEY

    if is_registry_specific:
        form_name = None
        form_display_name = "Demographics"
        section_code = None
        section_display_name = registry.specific_fields_section_title
    else:
        form = RegistryForm.objects.filter(name=form_name).first()
        section = Section.objects.filter(code=section_code).first()

        form_name = form.name
        form_display_name = form.display_name
        section_code = section.code
        section_display_name = section.display_name

    cde = CommonDataElement.objects.filter(code=cde_code).first()
    cde_display_name = cde.name

    display_name = " --- ".join(
        (form_display_name, section_display_name, cde_display_name)
    )

    return {
        "display_name": display_name,
        "form_code": form_name,
        "form_display_name": form_display_name,
        "section_code": section_code,
        "section_display_name": section_display_name,
        "cde_code": cde.code,
        "cde_display_name": cde.name,
    }
