# Generated by Django 3.2.16 on 2023-02-08 10:06
from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0151_alter_cdefile_patient'),
    ]

    operations = [
        UnaccentExtension()
    ]
