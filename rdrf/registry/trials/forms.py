import string

from django import forms
from django.utils.translation import ugettext as _

from .models import NofOneTrial, NofOneTreatment


class NofOneTreatmentForm(forms.ModelForm):
    class Meta:
        model = NofOneTreatment
        fields = "__all__"


class NofOneTrialCreationForm(forms.ModelForm):
    patients = forms.IntegerField(help_text=_("Number of patients"))
    cycles = forms.IntegerField(help_text=_("Number of cycles"))
    treatments = forms.IntegerField(help_text=_("Number of treatments"))

    period_length = forms.DurationField(
        help_text=_("Duration of each period"),
        initial="14 00:00:00"
    )
    period_washout_duration = forms.DurationField(
        help_text=_("Duration of the washout after each period"),
        initial="3 00:00:00"
    )

    class Meta:
        model = NofOneTrial
        fields = ["title", "registry", "description"]



