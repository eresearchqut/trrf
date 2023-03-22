from enum import unique, Enum

from django.contrib.auth.models import Group
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import ConsentQuestion, Registry, ContextFormGroup
from registry.groups.models import WorkingGroup


class ReportDesignManager(models.Manager):

    def reports_for_user(self, user):
        if user.is_superuser:
            return super().get_queryset()
        if not user.has_perm('report.can_run_reports'):
            return self.none()

        registries = user.get_registries()
        if user.is_clinician and not user.ethically_cleared:
            # Registries that do NOT require ethical clearance
            registries = [
                r for r in registries if not r.has_feature(RegistryFeatures.CLINICIAN_ETHICAL_CLEARANCE)
            ]

        return super().get_queryset().filter(registry__in=registries, access_groups__in=user.get_groups())


@unique
class ReportCdeHeadingFormat(Enum):
    LABEL = 'LABEL'
    ABBR_NAME = 'ABBR_NAME'
    CODE = 'CODE'


class ReportDesign(models.Model):

    CDE_HEADING_FORMATS = (
        (ReportCdeHeadingFormat.LABEL.value, _('Use full labels')),
        (ReportCdeHeadingFormat.ABBR_NAME.value, _('Use abbreviated name')),
        (ReportCdeHeadingFormat.CODE.value, _('Use unique codes')))

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    access_groups = models.ManyToManyField(Group, blank=True)
    filter_working_groups = models.ManyToManyField(WorkingGroup, related_name='filter_working_groups', blank=True)
    filter_consents = models.ManyToManyField(ConsentQuestion, blank=True)
    cde_heading_format = models.CharField(max_length=30, choices=CDE_HEADING_FORMATS, default=ReportCdeHeadingFormat.LABEL.value)
    cde_include_form_timestamp = models.BooleanField(default=False)

    objects = ReportDesignManager()

    class Meta:
        permissions = (
            ('can_run_reports', 'Can run reports'),
        )
        ordering = ['registry', 'title']
        constraints = [
            UniqueConstraint(fields=['registry', 'title'], name='unique_report_title')
        ]


class ReportClinicalDataField(models.Model):
    report_design = models.ForeignKey(ReportDesign, on_delete=models.CASCADE)
    context_form_group = models.ForeignKey(ContextFormGroup, on_delete=models.CASCADE)

    cde_key = models.CharField(max_length=255)


class ReportDemographicField(models.Model):
    report_design = models.ForeignKey(ReportDesign, on_delete=models.CASCADE)

    model = models.CharField(max_length=255)
    field = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(null=False, blank=False)

    class Meta:
        ordering = ['sort_order']
