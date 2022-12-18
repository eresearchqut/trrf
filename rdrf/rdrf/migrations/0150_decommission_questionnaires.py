# Generated by Django 3.2.15 on 2022-12-14 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0149_applicability_condition_help_text'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cdepermittedvalue',
            name='questionnaire_value',
        ),
        migrations.RemoveField(
            model_name='commondataelement',
            name='questionnaire_text',
        ),
        migrations.RemoveField(
            model_name='consentquestion',
            name='questionnaire_label',
        ),
        migrations.RemoveField(
            model_name='registryform',
            name='is_questionnaire',
        ),
        migrations.RemoveField(
            model_name='registryform',
            name='is_questionnaire_login',
        ),
        migrations.RemoveField(
            model_name='registryform',
            name='questionnaire_display_name',
        ),
        migrations.RemoveField(
            model_name='registryform',
            name='questionnaire_questions',
        ),
        migrations.RemoveField(
            model_name='section',
            name='questionnaire_display_name',
        ),
        migrations.RemoveField(
            model_name='section',
            name='questionnaire_help',
        ),
        migrations.DeleteModel(
            name='QuestionnaireResponse',
        ),
    ]
