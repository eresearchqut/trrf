import logging

from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import render, redirect

from .utils import setup_trial, setup_patient_arm
from .forms import NofOneTrialCreationForm, AddPatientForm
from .models import NofOneTrial, NofOneArm, NofOneCycle, NofOnePeriod, NofOneTreatment

logger = logging.getLogger(__name__)


class NofOneTreatmentInlineAdmin(admin.StackedInline):
    model = NofOneTreatment
    extra = 0
    show_change_link = True


class NofOneTreatmentAdmin(admin.ModelAdmin):
    list_display = ["title", "blinded_title", "trial"]
    list_filter = ["trial", "trial__registry"]


class NofOnePeriodAdmin(admin.ModelAdmin):
    list_filter = ["cycle__arm__trial"]


class NofOnePeriodInlineAdmin(admin.StackedInline):
    model = NofOnePeriod
    extra = 0
    show_change_link = True


class NofOneCycleAdmin(admin.ModelAdmin):
    inlines = [NofOnePeriodInlineAdmin]


class NofOneCycleInlineAdmin(admin.StackedInline):
    readonly_fields = ["periods"]
    model = NofOneCycle
    extra = 0
    show_change_link = True

    def periods(self, instance):
        return instance.formatted_treatments


class NofOneArmInlineAdmin(admin.StackedInline):
    fields = [("patient", "cycles")]
    readonly_fields = ("patient", "cycles",)
    model = NofOneArm
    extra = 0
    show_change_link = True

    def cycles(self, instance):
        return instance.formatted_treatments


class NofOneArmAdmin(admin.ModelAdmin):
    inlines = [NofOneCycleInlineAdmin]
    list_display = ("trial", "patient", "cycles")
    list_filter = ["trial"]

    def cycles(self, instance):
        return instance.formatted_treatments


class NofOneTrialAdmin(admin.ModelAdmin):
    actions = ["add_patient"]
    list_display = ["title", "registry"]

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

    def get_form(self, request, obj=None, **kwargs):
        """Custom add form"""
        if not obj:
            kwargs["form"] = NofOneTrialCreationForm
        return super().get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        """Only show inlines on change form"""
        inlines = [NofOneTreatmentInlineAdmin, NofOneArmInlineAdmin] if obj else []
        return [inline(self.model, self.admin_site) for inline in inlines]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        with transaction.atomic():
            setup_trial(
                obj,
                form.cleaned_data["patients"],
                form.cleaned_data["cycles"],
                form.cleaned_data["treatments"],
                form.cleaned_data["period_length"],
                form.cleaned_data["period_washout_duration"],
            )

    def add_patient(self, request, queryset):
        trial = queryset.first()

        errors = []
        if queryset.count() != 1:
            errors.append("You must select 1 trial to add a patient to")
        else:
            if 'apply' in request.POST:
                form = AddPatientForm(request.POST, trial=trial)
                if form.is_valid():
                    if arm := setup_patient_arm(trial, form.cleaned_data["patient"], form.cleaned_data["start_time"]):
                        messages.success(request, f"Successfully added {arm}")
                    else:
                        messages.error(request, "Could not find arm to assign patient to")
                    return redirect(request.get_full_path())
                else:
                    errors.extend(form.errors)

        return render(request, "admin/trial_add_patient_form.html", context={
            "form": AddPatientForm(trial=trial),
            "trial": trial,
            "errors": errors
        })


admin.site.register(NofOnePeriod, NofOnePeriodAdmin)
admin.site.register(NofOneCycle, NofOneCycleAdmin)
admin.site.register(NofOneArm, NofOneArmAdmin)
admin.site.register(NofOneTreatment, NofOneTreatmentAdmin)
admin.site.register(NofOneTrial, NofOneTrialAdmin)
