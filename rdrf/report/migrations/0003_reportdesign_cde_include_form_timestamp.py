# Generated by Django 2.2.28 on 2022-07-29 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0002_reportclinicaldatafield_context_form_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportdesign',
            name='cde_include_form_timestamp',
            field=models.BooleanField(default=False),
        ),
    ]
