# Generated by Django 3.2.19 on 2023-06-26 13:40

from django.db import migrations, models


def create_default_whitelist(apps, schema_editor):
    WhitelistedFileExtension = apps.get_model('rdrf', 'WhitelistedFileExtension')
    WhitelistedFileExtension.objects.bulk_create([
        WhitelistedFileExtension(file_extension='.csv'),
        WhitelistedFileExtension(file_extension='.txt'),
        WhitelistedFileExtension(file_extension='.doc'),
        WhitelistedFileExtension(file_extension='.docx'),
        WhitelistedFileExtension(file_extension='.pdf'),
        WhitelistedFileExtension(file_extension='.rtf'),
        WhitelistedFileExtension(file_extension='.msg'),
        WhitelistedFileExtension(file_extension='.gz'),
        WhitelistedFileExtension(file_extension='.zip'),
        WhitelistedFileExtension(file_extension='.jfif'),
        WhitelistedFileExtension(file_extension='.jpeg'),
        WhitelistedFileExtension(file_extension='.jpg'),
        WhitelistedFileExtension(file_extension='.tif'),
        WhitelistedFileExtension(file_extension='.png'),
        WhitelistedFileExtension(file_extension='.heic'),
        WhitelistedFileExtension(file_extension='.mov'),
        WhitelistedFileExtension(file_extension='.apng'),
        WhitelistedFileExtension(file_extension='.avif'),
        WhitelistedFileExtension(file_extension='.gif'),
        WhitelistedFileExtension(file_extension='.webp'),
        WhitelistedFileExtension(file_extension='.3gp'),
        WhitelistedFileExtension(file_extension='.aac'),
        WhitelistedFileExtension(file_extension='.flac'),
        WhitelistedFileExtension(file_extension='.mpg'),
        WhitelistedFileExtension(file_extension='.mpeg'),
        WhitelistedFileExtension(file_extension='.mp3'),
        WhitelistedFileExtension(file_extension='.mp4'),
        WhitelistedFileExtension(file_extension='.m4a'),
        WhitelistedFileExtension(file_extension='.m4p'),
        WhitelistedFileExtension(file_extension='.ogv'),
        WhitelistedFileExtension(file_extension='.ogg'),
        WhitelistedFileExtension(file_extension='.wav'),
        WhitelistedFileExtension(file_extension='.webm'),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0158_update_arabic'),
    ]

    operations = [
        migrations.CreateModel(
            name='WhitelistedFileExtension',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_extension', models.CharField(max_length=256, unique=True)),
            ],
        ),
        migrations.RunPython(create_default_whitelist, migrations.RunPython.noop)
    ]
