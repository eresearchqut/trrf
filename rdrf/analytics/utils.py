import datetime
import time

from django.db import transaction, connections

from analytics.models import ClinicalDataViewRefreshLog


@transaction.atomic
def refresh_reports():
    #  TODO register as a cron or other type of scheduled job: https://gutsytechster.wordpress.com/2019/06/24/how-to-setup-a-cron-job-in-django/
    start_time = time.monotonic()
    with connections['clinical'].cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_clinicaldataview')
    end_time = time.monotonic()
    ClinicalDataViewRefreshLog.objects.create(duration=datetime.timedelta(seconds=end_time - start_time))

