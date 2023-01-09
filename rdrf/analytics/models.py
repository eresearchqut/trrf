from django.db import models


class ClinicalDataView(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    duration = models.DurationField()


