from django.db import models
from django.db.models import Q


class ClinicalDataViewManager(models.Manager):
    def filter_non_empty(self):
        return self\
            .exclude(cde_value__exact='')\
            .exclude(cde_value__isnull=True)\
            .exclude(cde_value__exact='null')


class ClinicalDataView(models.Model):

    objects = ClinicalDataViewManager()

    id = models.IntegerField(primary_key=True)
    patient_id = models.IntegerField()
    form_name = models.CharField(max_length=80)
    form_entry_num = models.IntegerField()
    section_code = models.CharField(max_length=100)
    cde_entry_num = models.IntegerField()
    cde_code = models.CharField(max_length=30)
    cde_value = models.TextField()

    class Meta:
        managed = False
        db_table = 'analytics_clinicaldataview'


class ClinicalDataViewRefreshLog(models.Model):
    created_at = models.DateTimeField()


