from django.db import models

from rdrf.models.definition.models import Registry
from registry.patients.models import Patient


class Intervention(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True


class NofOneTreatment(Intervention):
    blinded_title = models.CharField(max_length=20)

    class Meta:
        verbose_name = "N-of-1 Treatment"
        verbose_name_plural = "N-of-1 Treatments"

    def __str__(self):
        return f"{self.blinded_title} ({self.title})"


class NofOneTrial(models.Model):
    title = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE, related_name="nofone_trials")

    class Meta:
        verbose_name = "N-of-1 Trial"
        verbose_name_plural = "N-of-1 Trials"

    def __str__(self):
        return f"{self.title} ({self.registry.code})"


class NofOneArm(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, blank=True, null=True)
    trial = models.ForeignKey(NofOneTrial, on_delete=models.PROTECT, related_name="arms")

    class Meta:
        verbose_name = "N-of-1 Arm"
        verbose_name_plural = "N-of-1 Arms"

    @property
    def ordered_periods(self):
        return self.cycles.select_related("periods").all().order_by("start")

    def __str__(self):
        return f"{self.patient} - {self.trial}"


class NofOneCycle(models.Model):
    arm = models.ForeignKey(NofOneArm, on_delete=models.PROTECT, related_name="cycles")

    class Meta:
        verbose_name = "N-of-1 Cycle"
        verbose_name_plural = "N-of-1 Cycles"

    def __str__(self):
        periods = self.ordered_periods
        cycle_treatments = "".join(period.treatment.blinded_title for period in periods)
        return f"{cycle_treatments} - ({periods.first().start} -> {periods.last().end})"

    @property
    def ordered_periods(self):
        return self.periods.all().order_by("start")


class NofOnePeriod(models.Model):
    cycle = models.ForeignKey(NofOneCycle, on_delete=models.PROTECT, related_name="periods")
    treatment = models.ForeignKey(NofOneTreatment, on_delete=models.PROTECT, related_name="periods")

    start = models.DateTimeField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)

    class Meta:
        verbose_name = "N-of-1 Period"
        verbose_name_plural = "N-of-1 Periods"

    def __str__(self):
        return f"{self.treatment}: {self.start} -> {self.end}"

    @property
    def end(self):
        return self.start + self.duration if self.start else None
