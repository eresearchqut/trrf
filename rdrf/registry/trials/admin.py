import logging

from django.contrib import admin
from django.db import transaction

from .services import setup_trial
from .forms import NofOneTrialCreationForm
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
    pass


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
                form.cleaned_data["patients"],
                form.cleaned_data["cycles"],
                form.cleaned_data["treatments"],
                form.cleaned_data["period_length"],
                form.cleaned_data["period_washout_duration"],
                obj
            )


admin.site.register(NofOnePeriod, NofOnePeriodAdmin)
admin.site.register(NofOneCycle, NofOneCycleAdmin)
admin.site.register(NofOneArm, NofOneArmAdmin)
admin.site.register(NofOneTreatment, NofOneTreatmentAdmin)
admin.site.register(NofOneTrial, NofOneTrialAdmin)
