import datetime
import time

from django.db import transaction, connections

from analytics.models import ClinicalDataViewRefreshLog


@transaction.atomic
def refresh_reports():
    start_time = time.monotonic()
    with connections['clinical'].cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_clinicaldataview')
    end_time = time.monotonic()
    ClinicalDataViewRefreshLog.objects.create(duration=datetime.timedelta(seconds=end_time - start_time))

