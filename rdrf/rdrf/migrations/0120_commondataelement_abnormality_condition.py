# Generated by Django 2.2.9 on 2020-01-23 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0119_remove_ip_restrict_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='commondataelement',
            name='abnormality_condition',
            field=models.TextField(blank=True, help_text='Rules triggering a visual notification encouraging the user to process with further investigations', null=True),
        ),
    ]
