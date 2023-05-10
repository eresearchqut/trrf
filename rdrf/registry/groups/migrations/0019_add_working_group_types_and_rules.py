# Generated by Django 3.2.18 on 2023-05-10 15:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('groups', '0019_auto_20230508_1321'), ('groups', '0020_alter_workinggrouptyperule_type')]

    dependencies = [
        ('groups', '0018_alter_customuser_managers'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkingGroupType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='workinggroup',
            name='type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='working_groups', to='groups.workinggrouptype'),
        ),
        migrations.CreateModel(
            name='WorkingGroupTypeRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('has_default_access', models.BooleanField(default=False, help_text='Indicates whether the user group automatically has access to the working groups in this working group type')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='groups.workinggrouptype')),
                ('user_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
            ],
        ),
    ]
