# Generated by Django 2.2.24 on 2022-01-14 15:30

import logging
import re

from django.db import migrations, models

import rdrf.helpers.utils

logger = logging.getLogger(__name__)

def get_valid_default_abbreviated_name(src_string):
    return "".join([c for c in src_string if re.match(r'^[A-Za-z0-9\s-]+$', c)])[0:100]

def set_abbreviated_name_on_cfg(apps, schema_editor):
    ContextFormGroup = apps.get_model('rdrf', 'ContextFormGroup')
    cfgs = ContextFormGroup.objects.all()
    logger.info(f'Setting abbreviated_name for {cfgs.count()} ContextFormGroup records.')
    for cfg in cfgs:
        cfg.abbreviated_name = get_valid_default_abbreviated_name(cfg.name)
        cfg.save()

def set_abbreviated_name_on_form(apps, schema_editor):
    RegistryForm = apps.get_model('rdrf', 'RegistryForm')
    forms = RegistryForm.objects.all()
    logger.info(f'Setting abbreviated_name for {forms.count()} RegistryForm records.')
    for f in forms:
        f.abbreviated_name = get_valid_default_abbreviated_name(f.name)
        f.save()

def set_abbreviated_name_on_section(apps, schema_editor):
    Section = apps.get_model('rdrf', 'Section')
    sections = Section.objects.all()
    logger.info(f'Setting abbreviated_name for {sections.count()} Section records.')
    for s in sections:
        s.abbreviated_name = get_valid_default_abbreviated_name(s.display_name)
        s.save()

def set_abbreviated_name_on_cde(apps, schema_editor):
    CommonDataElement = apps.get_model('rdrf', 'CommonDataElement')
    cdes = CommonDataElement.objects.all()
    logger.info(f'Setting abbreviated_name for {cdes.count()} CDE records.')
    for cde in cdes:
        cde.abbreviated_name = get_valid_default_abbreviated_name(cde.name)
        cde.save()

def run_set_abbreviations_on_clinical_data_parts(apps, schema_editor):
    set_abbreviated_name_on_cfg(apps, schema_editor)
    set_abbreviated_name_on_form(apps, schema_editor)
    set_abbreviated_name_on_section(apps, schema_editor)
    set_abbreviated_name_on_cde(apps, schema_editor)

class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0139_language_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='commondataelement',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of this CDE in other contexts (e.g. reports)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='contextformgroup',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of CFG in other contexts (e.g. reports)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='registryform',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of this RegistryForm in other contexts (e.g. reports)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='section',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of this Section in other contexts (e.g. reports)', max_length=100, null=True),
        ),
        migrations.RunPython(
            run_set_abbreviations_on_clinical_data_parts,
            migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='contextformgroup',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of CFG in other contexts (e.g. reports)', max_length=100, validators=[rdrf.helpers.utils.validate_abbreviated_name]),
        ),
        migrations.AlterField(
            model_name='registryform',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of this RegistryForm in other contexts (e.g. reports)', max_length=100, validators=[rdrf.helpers.utils.validate_abbreviated_name]),
        ),
        migrations.AlterField(
            model_name='section',
            name='abbreviated_name',
            field=models.CharField(help_text='Abbreviated name for identification of this Section in other contexts (e.g. reports)', max_length=100, validators=[rdrf.helpers.utils.validate_abbreviated_name]),
        ),
        migrations.AlterField(
            model_name='commondataelement',
            name='abbreviated_name',
            field=models.CharField(
                help_text='Abbreviated name for identification of this CDE in other contexts (e.g. reports)',
                max_length=100, validators=[rdrf.helpers.utils.validate_abbreviated_name]),
        ),
    ]