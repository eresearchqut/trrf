# Generated by Django 3.2.15 on 2022-10-24 10:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0145_optional_splash_screen'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registry',
            name='patient_splash_screen',
        ),
    ]
