from django.urls import re_path

from . import parent_view, patient_view
from .views import ConsentFileView

urlpatterns = [
    re_path(r"^download/(?P<consent_id>\d+)/(?P<filename>.*)$",
            ConsentFileView.as_view(),
            name="consent-form-download"),

    re_path(r"^(?P<registry_code>\w+)/parent/?$",
            parent_view.ParentView.as_view(), name='parent_page'),
    re_path(r"^(?P<registry_code>\w+)/parent/(?P<parent_id>\d+)/?$",
            parent_view.ParentEditView.as_view(), name='parent_edit'),
    re_path(r"^(?P<registry_code>\w+)/patient/?$",
            patient_view.PatientView.as_view(), name='patient_page'),
]
