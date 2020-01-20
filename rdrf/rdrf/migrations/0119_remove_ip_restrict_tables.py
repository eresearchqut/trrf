# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0118_clinical_data_created_updated_ts'),
    ]

    operations = [
        migrations.RunSQL('''
            drop table if exists iprestrict_ipgroup cascade;
            drop table if exists iprestrict_iplocation;
            drop table if exists iprestrict_iprange;
            drop table if exists iprestrict_reloadrulesrequest;
            drop table if exists iprestrict_rule;
            delete from auth_permission where content_type_id in (select id from django_content_type where app_label = 'iprestrict');
            delete from django_admin_log where content_type_id in (select id from django_content_type where app_label = 'iprestrict');
            delete from reversion_version where content_type_id in (select id from django_content_type where app_label = 'iprestrict');
            delete from django_content_type where app_label = 'iprestrict';
            delete from django_migrations where app='iprestrict';
        ''')
    ]