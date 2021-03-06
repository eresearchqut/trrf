# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-23 12:21
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0089_auto_20181120_1604'),
        ('patients', '0030_auto_20181121_1502'),
    ]

    operations = [
        migrations.CreateModel(
            name='Speciality',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('registry', models.ForeignKey(on_delete=models.CASCADE,
                                                to='rdrf.Registry')),
            ],
        ),
        migrations.AddField(
            model_name='clinicianother',
            name='speciality',
            field=models.ForeignKey(null=True,
                                    on_delete=models.SET_NULL,
                                    to='patients.Speciality'),
        ),
    ]
