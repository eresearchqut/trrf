# Generated by Django 3.2.18 on 2023-05-26 15:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0022_alter_workinggroup_options'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='workinggroup',
            unique_together={('registry', 'name')},
        ),
    ]
