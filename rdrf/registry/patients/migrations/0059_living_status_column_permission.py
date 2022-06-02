# Generated by Django 2.2.28 on 2022-06-02 20:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0058_nextofkin_relationship_unique'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='patient',
            options={'ordering': ['family_name', 'given_names', 'date_of_birth'], 'permissions': (('can_see_full_name', 'Can see Full Name column'), ('can_see_dob', 'Can see Date of Birth column'), ('can_see_working_groups', 'Can see Working Groups column'), ('can_see_diagnosis_progress', 'Can see Diagnosis Progress column'), ('can_see_diagnosis_currency', 'Can see Diagnosis Currency column'), ('can_see_data_modules', 'Can see Data Modules column'), ('can_see_code_field', 'Can see Code Field column'), ('can_see_living_status', 'Can see Living Status column')), 'verbose_name_plural': 'Patient List'},
        ),
    ]
