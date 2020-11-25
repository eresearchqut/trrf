import logging

from django.contrib import admin

from .models import NofOneTrial, NofOneArm, NofOneCycle, NofOnePeriod, NofOneTreatment

logger = logging.getLogger(__name__)


class NofOneTreatmentAdmin(admin.ModelAdmin):
    pass


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
        return "".join(period.treatment.blinded_title for period in instance.periods.all())


class NofOneArmInlineAdmin(admin.StackedInline):
    fields = [("patient", "cycles")]
    readonly_fields = ("patient", "cycles",)
    model = NofOneArm
    extra = 0
    show_change_link = True

    def cycles(self, instance):
        return ", ".join("".join(period.treatment.blinded_title for period in cycle.periods.all()) for cycle in
                         instance.cycles.all())


class NofOneArmAdmin(admin.ModelAdmin):
    inlines = [NofOneCycleInlineAdmin]
    list_display = ("trial", "patient", "cycles")
    list_filter = ["trial"]

    def cycles(self, instance):
        return ", ".join("".join(period.treatment.blinded_title for period in cycle.periods.all()) for cycle in
                         instance.cycles.all())


class NofOneTrialAdmin(admin.ModelAdmin):
    inlines = [NofOneArmInlineAdmin]
    list_display = ["title", "registry"]


admin.site.register(NofOnePeriod, NofOnePeriodAdmin)
admin.site.register(NofOneCycle, NofOneCycleAdmin)
admin.site.register(NofOneArm, NofOneArmAdmin)
admin.site.register(NofOneTreatment, NofOneTreatmentAdmin)
admin.site.register(NofOneTrial, NofOneTrialAdmin)
