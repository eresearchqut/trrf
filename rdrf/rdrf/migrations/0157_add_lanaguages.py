# Generated by Django 3.2.19 on 2023-06-06 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0156_alter_emailnotification_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(choices=[('en', 'English'), ('af', 'Afrikaans'), ('ar', 'العربية'), ('cs', 'Čeština'), ('de', 'Deutsch'), ('es', 'Español'), ('fr', 'Français'), ('he', 'עִבְרִית'), ('hi', 'हिन्दी'), ('hu', 'Magyar'), ('id', 'Bahasa Indonesia'), ('it', 'Italiano'), ('ms', 'Bahasa Melayu'), ('pl', 'Język polski'), ('pt', 'Português'), ('ro', 'Română'), ('ru', 'Русский'), ('sv', 'Svenska'), ('tr', 'Türkçe'), ('ur', 'اردو'), ('vi', 'Tiếng Việt'), ('zh-CN', '汉语'), ('zh-TW', '漢語')], max_length=6),
        ),
    ]