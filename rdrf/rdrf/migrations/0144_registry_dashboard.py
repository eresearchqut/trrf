# Generated by Django 2.2.28 on 2022-08-19 13:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0143_add_hindi_language'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistryDashboard',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registry', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='rdrf.Registry')),
            ],
        ),
        migrations.CreateModel(
            name='RegistryDashboardWidget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('widget_type', models.CharField(choices=[('demographics', 'Demographics'), ('clinical_data', 'Clinical Data'), ('consents', 'Consent'), ('module_progress', 'Module Progress')], max_length=50)),
                ('title', models.CharField(blank=True, max_length=100)),
                ('free_text', models.CharField(blank=True, max_length=255)),
                ('registry_dashboard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='widgets', to='rdrf.RegistryDashboard')),
            ],
            options={
                'unique_together': {('registry_dashboard', 'widget_type')},
            },
        ),
        migrations.CreateModel(
            name='RegistryDashboardFormLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField()),
                ('label', models.CharField(max_length=255)),
                ('context_form_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.ContextFormGroup')),
                ('registry_form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.RegistryForm')),
                ('widget', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='rdrf.RegistryDashboardWidget')),
            ],
            options={
                'ordering': ['sort_order'],
                'unique_together': {('widget', 'sort_order')},
            },
        ),
        migrations.CreateModel(
            name='RegistryDashboardDemographicData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField()),
                ('label', models.CharField(max_length=255)),
                ('model', models.CharField(max_length=255)),
                ('field', models.CharField(choices=[('patient', 'Patient')], max_length=255)),
                ('widget', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='demographics', to='rdrf.RegistryDashboardWidget')),
            ],
            options={
                'ordering': ['sort_order'],
                'unique_together': {('widget', 'sort_order')},
            },
        ),
        migrations.CreateModel(
            name='RegistryDashboardCDEData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField()),
                ('label', models.CharField(max_length=255)),
                ('cde', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.CommonDataElement')),
                ('context_form_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.ContextFormGroup')),
                ('registry_form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.RegistryForm')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rdrf.Section')),
                ('widget', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cdes', to='rdrf.RegistryDashboardWidget')),
            ],
            options={
                'ordering': ['sort_order'],
                'unique_together': {('widget', 'sort_order')},
            },
        ),
    ]
