# Generated by Django 3.2.15 on 2022-11-14 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0146_remove_patient_splash_screen'),
    ]

    operations = [
        migrations.AddField(
            model_name='section',
            name='header',
            field=models.TextField(blank=True),
        ),
    ]
