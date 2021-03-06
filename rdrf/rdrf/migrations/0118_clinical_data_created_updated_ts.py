# Generated by Django 2.1.12 on 2019-11-20 02:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0117_rdrfcontext_updated_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicaldata',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='clinicaldata',
            name='last_updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='clinicaldata',
            name='last_updated_by',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
    ]
