import random
import string

from django.test import TestCase
from registry.groups.models import CustomUser

from rdrf.models.definition.models import (
    EmailNotification,
    EmailPreference,
    Registry,
)


class EmailPreferenceTest(TestCase):
    def setUp(self):
        self.registry = Registry.objects.create(code="test")

    def _make_users(self, size):
        return [
            CustomUser.objects.create(
                username="".join(random.choices(string.ascii_uppercase, k=10))
            )
            for i in range(size)
        ]

    def _make_email_notifications(self, size):
        return [
            EmailNotification.objects.create(
                registry=self.registry, subscribable=True
            )
            for i in range(size)
        ]

    def test_is_email_allowed(self):
        user1, user2 = self._make_users(2)
        email1, email2, email3 = self._make_email_notifications(3)

        user1_pref = EmailPreference.objects.create(
            user=user1, unsubscribe_all=True
        )
        user2_pref = EmailPreference.objects.create(
            user=user2, unsubscribe_all=False
        )

        user2_pref.notification_preferences.create(
            email_notification=email1, is_subscribed=False
        )
        user2_pref.notification_preferences.create(
            email_notification=email2, is_subscribed=True
        )

        self.assertFalse(user1_pref.is_email_allowed(email1))
        self.assertFalse(user1_pref.is_email_allowed(email2))
        self.assertFalse(user1_pref.is_email_allowed(email3))

        self.assertFalse(user2_pref.is_email_allowed(email1))
        self.assertTrue(user2_pref.is_email_allowed(email2))
        self.assertTrue(
            user2_pref.is_email_allowed(email3)
        )  # Allows email if preference doesn't exist

    def test_filter_unsubscribed(self):
        user1, user2, user3, user4 = self._make_users(4)
        email1, email2, email3 = self._make_email_notifications(3)

        self.assertEqual(
            [], list(EmailPreference.objects.filter_by_unsubscribed(email1))
        )

        user1_pref = EmailPreference.objects.create(
            user=user1, unsubscribe_all=False
        )
        user2_pref = EmailPreference.objects.create(
            user=user2, unsubscribe_all=True
        )
        user3_pref = EmailPreference.objects.create(
            user=user3, unsubscribe_all=False
        )
        user4_pref = EmailPreference.objects.create(
            user=user4, unsubscribe_all=False
        )

        user1_pref.notification_preferences.create(
            email_notification=email2, is_subscribed=False
        )
        user3_pref.notification_preferences.create(
            email_notification=email1, is_subscribed=False
        )
        user3_pref.notification_preferences.create(
            email_notification=email3, is_subscribed=False
        )
        user4_pref.notification_preferences.create(
            email_notification=email1, is_subscribed=True
        )
        user4_pref.notification_preferences.create(
            email_notification=email2, is_subscribed=True
        )

        self.assertEqual(
            {user2_pref, user3_pref},
            set(EmailPreference.objects.filter_by_unsubscribed(email1)),
        )
        self.assertEqual(
            {user1_pref, user2_pref},
            set(EmailPreference.objects.filter_by_unsubscribed(email2)),
        )
        self.assertEqual(
            {user2_pref, user3_pref},
            set(EmailPreference.objects.filter_by_unsubscribed(email3)),
        )

        users = CustomUser.objects.filter(
            id__in=EmailPreference.objects.filter_by_unsubscribed(
                email1
            ).values_list("user__id", flat=True)
        )
        self.assertEqual({user2, user3}, set(users.all()))
