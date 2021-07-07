from django.db import models

from rdrf.models.definition.models import Registry
from registry.patients.models import Patient


class NofOneTrial(models.Model):
    title = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE, related_name="nofone_trials")

    class Meta:
        verbose_name = "N-of-1 Trial"
        verbose_name_plural = "N-of-1 Trials"

    def __str__(self):
        return f"{self.title} ({self.registry.code})"


class NofOneTreatment(models.Model):
    title = models.CharField(max_length=100)
    blinded_title = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    trial = models.ForeignKey(NofOneTrial, on_delete=models.CASCADE, related_name="trials")

    class Meta:
        verbose_name = "N-of-1 Treatment"
        verbose_name_plural = "N-of-1 Treatments"

    def __str__(self):
        return f"{self.blinded_title} ({self.title})"


class NofOneArm(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.PROTECT, blank=True, null=True, related_name="n_of_1_arm")
    trial = models.ForeignKey(NofOneTrial, on_delete=models.CASCADE, related_name="arms")

    sequence_index = models.IntegerField()

    class Meta:
        verbose_name = "N-of-1 Arm"
        verbose_name_plural = "N-of-1 Arms"

    def __str__(self):
        return f"{self.patient} - {self.trial}"

    @property
    def formatted_treatments(self):
        cycles = self.cycles.order_by("sequence_index").prefetch_related("periods__treatment").all()
        return ", ".join(cycle.formatted_treatments for cycle in cycles)

    @property
    def ordered_periods(self):
        return NofOnePeriod.objects.filter(cycle__in=self.cycles.all()).order_by("cycle__sequence_index", "sequence_index")


class NofOneCycle(models.Model):
    arm = models.ForeignKey(NofOneArm, on_delete=models.CASCADE, related_name="cycles")

    sequence_index = models.IntegerField()

    class Meta:
        verbose_name = "N-of-1 Cycle"
        verbose_name_plural = "N-of-1 Cycles"

    def __str__(self):
        return f"{self.formatted_treatments} - ({self.start} -> {self.end})"

    @property
    def start(self):
        return self.ordered_periods.first().start

    @property
    def end(self):
        return self.ordered_periods.last().end

    @property
    def ordered_periods(self):
        return self.periods.all().order_by("sequence_index")

    @property
    def formatted_treatments(self):
        return "".join(period.treatment.blinded_title for period in self.ordered_periods.all())


class NofOnePeriod(models.Model):
    cycle = models.ForeignKey(NofOneCycle, on_delete=models.CASCADE, related_name="periods")
    treatment = models.ForeignKey(NofOneTreatment, on_delete=models.CASCADE, related_name="periods")

    sequence_index = models.IntegerField()

    start = models.DateTimeField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    washout = models.DurationField(blank=True, null=True)

    class Meta:
        verbose_name = "N-of-1 Period"
        verbose_name_plural = "N-of-1 Periods"

    def __str__(self):
        return f"{self.treatment}: {self.start} -> {self.end}"

    @property
    def end(self):
        return self.start + self.duration if self.start else None
