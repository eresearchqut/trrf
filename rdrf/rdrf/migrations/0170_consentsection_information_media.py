# Generated by Django 4.2.14 on 2024-07-12 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0169_greek'),
    ]

    operations = [
        migrations.AddField(
            model_name='consentsection',
            name='information_media',
            field=models.TextField(blank=True, null=True),
        ),
    ]
