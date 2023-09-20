# Generated by Django 3.2.20 on 2023-09-20 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0165_update_chinese_language_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(choices=[('en', 'English'), ('af', 'Afrikaans'), ('ar-AR', 'العربية'), ('cs', 'Čeština'), ('de', 'Deutsch'), ('es', 'Español'), ('fr', 'Français'), ('he', 'עִבְרִית'), ('hi', 'हिन्दी'), ('hu', 'Magyar'), ('id', 'Bahasa Indonesia'), ('it', 'Italiano'), ('ms', 'Bahasa Melayu'), ('pl', 'Język polski'), ('pt', 'Português'), ('pt-br', 'Português (Brasil)'), ('ro', 'Română'), ('ru', 'Русский'), ('sv', 'Svenska'), ('tr', 'Türkçe'), ('ur', 'اردو'), ('vi', 'Tiếng Việt'), ('zh-CN', '简体中文'), ('zh-TW', '繁體中文')], max_length=6),
        ),
    ]
