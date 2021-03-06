# Generated by Django 2.1.9 on 2019-06-21 19:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0035_demographic_audit_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatientStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('allowed_next_stages', models.ManyToManyField(blank=True, related_name='_patientstage_allowed_next_stages_+', to='patients.PatientStage')),
                ('allowed_prev_stages', models.ManyToManyField(blank=True, related_name='_patientstage_allowed_prev_stages_+', to='patients.PatientStage')),
            ],
            options={
                'ordering': ['pk'],
            },
        ),
        migrations.AddField(
            model_name='historicalpatient',
            name='stage',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='patients.PatientStage'),
        ),
        migrations.AddField(
            model_name='patient',
            name='stage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='patients.PatientStage'),
        ),
    ]
