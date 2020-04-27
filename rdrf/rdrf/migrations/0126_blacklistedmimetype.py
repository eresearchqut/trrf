# Generated by Django 2.2.10 on 2020-04-23 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0125_cde_file_user_and_patient_fks'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlacklistedMimeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mime_type', models.CharField(max_length=256, unique=True)),
                ('description', models.TextField()),
            ],
            options={
                'verbose_name': 'Disallowed mime type',
            },
        ),
    ]