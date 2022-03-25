# Generated by Django 2.2.24 on 2022-01-21 09:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('groups', '0017_staff_help_text'),
        ('auth', '0011_update_proxy_permissions'),
        ('rdrf', '0137_split_new_patient_event_types_data_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportDesign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('cde_heading_format', models.CharField(choices=[('LABEL', 'Use full labels'), ('ABBR_NAME', 'Use abbreviated name'), ('CODE', 'Use unique codes')], default='LABEL', max_length=30)),
                ('access_groups', models.ManyToManyField(blank=True, to='auth.Group')),
                ('filter_consents', models.ManyToManyField(blank=True, to='rdrf.ConsentQuestion')),
                ('filter_working_groups', models.ManyToManyField(blank=True, related_name='filter_working_groups', to='groups.WorkingGroup')),
                ('registry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.Registry')),
            ],
            options={
                'ordering': ['registry', 'title'],
            },
        ),
        migrations.CreateModel(
            name='ReportDemographicField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(max_length=255)),
                ('field', models.CharField(max_length=255)),
                ('sort_order', models.PositiveIntegerField()),
                ('report_design', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='report.ReportDesign')),
            ],
            options={
                'ordering': ['sort_order'],
            },
        ),
        migrations.CreateModel(
            name='ReportClinicalDataField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cde_key', models.CharField(max_length=255)),
                ('report_design', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='report.ReportDesign')),
            ],
        ),
        migrations.AddConstraint(
            model_name='reportdesign',
            constraint=models.UniqueConstraint(fields=('registry', 'title'), name='unique_report_title'),
        ),
    ]