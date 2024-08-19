# Generated by Django 4.2.14 on 2024-08-15 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0170_consentsection_information_media'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(choices=[('en', 'English'), ('af', 'Afrikaans'), ('ar-AR', 'العربية'), ('bg', 'български език'), ('cs', 'Čeština'), ('de', 'Deutsch'), ('es', 'Español'), ('el', 'Ελληνικά'), ('fr', 'Français'), ('he', 'עִבְרִית'), ('hi', 'हिन्दी'), ('hu', 'Magyar'), ('id', 'Bahasa Indonesia'), ('it', 'Italiano'), ('ms', 'Bahasa Melayu'), ('pl', 'Język polski'), ('pt', 'Português'), ('pt-BR', 'Português (Brasil)'), ('ro', 'Română'), ('ru', 'русский язык'), ('sv', 'Svenska'), ('tr', 'Türkçe'), ('ur', 'اردو'), ('vi', 'Tiếng Việt'), ('zh-CN', '简体中文'), ('zh-TW', '繁體中文')], max_length=6),
        ),
    ]