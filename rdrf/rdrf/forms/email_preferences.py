import logging

from django.forms import ModelForm, MultipleChoiceField, CheckboxSelectMultiple, RadioSelect
from django.utils.translation import gettext_lazy as _

from rdrf.models.definition.models import EmailPreference, EmailNotification

logger = logging.getLogger(__name__)


def unsubscribe_all_choices():
    return [(True, _('I would like to unsubscribe from all emails')),
            (False, _('I would like to choose which emails to receive'))]


def email_notification_choices():
    return [(notification.id, notification.subscription_label)
            for notification in EmailNotification.objects.subscribable()]


class EmailPreferencesForm(ModelForm):
    email_notifications = MultipleChoiceField(required=False, widget=CheckboxSelectMultiple(attrs={'class': 'form-check-input'}))

    class Meta:
        model = EmailPreference
        fields = ('unsubscribe_all',)
        exclude = ('user',)
        widgets = {
            'unsubscribe_all': RadioSelect(choices=unsubscribe_all_choices(), attrs={'class': 'form-check-input'})
        }

    def setup_initials(self):
        if self.instance.id:
            self.fields['unsubscribe_all'].initial = self.instance.unsubscribe_all

            # All notifications will be preselected if user's current preference is to 'unsubscribe_all',
            # otherwise the user has specifically selected the emails they want to receive
            self.fields['email_notifications'].initial = [
                email_notification.id
                for email_notification in EmailNotification.objects.subscribable()
                if self.instance.unsubscribe_all or self.instance.is_email_allowed(email_notification)]
        else:
            # For users without any existing saved preferences,
            # select option to choose email subscriptions, with each notification selected by default.
            self.fields['unsubscribe_all'].initial = False
            self.fields['email_notifications'].initial = [
                email_notification.id
                for email_notification in EmailNotification.objects.subscribable()]

    def __init__(self, user, *args, **kwargs):
        super(EmailPreferencesForm, self).__init__(*args, **kwargs)

        # Initialise data-driven choices
        self.fields['email_notifications'].choices = email_notification_choices()

        # Initialise preferences based on user
        self.user = user
        self.instance = EmailPreference.objects.get_by_user(user) or self.instance

        # Initialise default field values
        self.setup_initials()

    def clean_email_notifications(self):
        return [EmailNotification.objects.get(id=id) for id in self.cleaned_data['email_notifications']]

    def save(self, commit=True):
        email_preference, created = EmailPreference.objects.update_or_create(
            id=self.instance.id,
            defaults={'user': self.user,
                      'unsubscribe_all': self.cleaned_data['unsubscribe_all']})

        if email_preference.unsubscribe_all:
            email_preference.notification_preferences.all().delete()
        else:
            selected_emails = self.cleaned_data['email_notifications']
            for email in EmailNotification.objects.subscribable():
                has_subscribed = email in selected_emails
                email_preference.notification_preferences.update_or_create(
                    email_notification=email,
                    defaults={'is_subscribed': has_subscribed}
                )

        return email_preference.save()
