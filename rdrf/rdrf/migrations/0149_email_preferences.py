# Generated by Django 3.2.15 on 2022-11-18 08:55
import logging

from django.db import migrations, models

from rdrf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0148_add_cde_calculation_query'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotification',
            name='subscribable',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='emailnotification',
            name='public_description',
            field=models.CharField(blank=True, help_text='Displayed to users when managing their email preferences',
                                   max_length=200, null=True),
        ),
        migrations.CreateModel(
            name='EmailPreference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unsubscribe_all',
                 models.BooleanField(help_text='Unsubscribed from current and future system generated emails')),
                (
                'user', models.OneToOneField(on_delete=models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EmailNotificationPreference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_subscribed', models.BooleanField()),
                ('email_notification',
                 models.ForeignKey(limit_choices_to={'subscribable': True}, on_delete=models.deletion.CASCADE,
                                   to='rdrf.emailnotification')),
                ('user_email_preference',
                 models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='notification_preferences',
                                   to='rdrf.emailpreference')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='emailnotificationpreference',
            unique_together={('user_email_preference', 'email_notification')},
        ),
        migrations.AlterField(
            model_name='emailnotification',
            name='public_description',
            field=models.CharField(blank=True, help_text='Displayed to users when managing their email preferences', max_length=200, null=True),
        ),
    ]
