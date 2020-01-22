import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import caches
from django.db import transaction, connection
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.generic import View

from rdrf.events.events import EventType
from rdrf.forms.admin.registry_registration import RegistrationAdminForm
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry, EmailNotification
from rdrf.views.admin.registration_notifications import DEFAULT_NOTIFICATIONS

logger = logging.getLogger(__name__)


class SetupRegistrationView(View):
    notifications = DEFAULT_NOTIFICATIONS

    @staticmethod
    def missing_cache_table():
        for cache_alias in settings.CACHES:
            cache = caches[cache_alias]
            if hasattr(cache, '_table') and cache._table not in connection.introspection.table_names():
                return cache._table

    def get(self, request, registry_code):
        registry = Registry.objects.get(code=registry_code)

        missing_table = self.missing_cache_table()
        if missing_table:
            messages.error(request, _(f"Cache table '{missing_table}' is missing. Run django-admin createcachetable"))

        form = RegistrationAdminForm(self.notifications)

        context = {
            'existing_notifications': EmailNotification.objects.filter(
                registry=registry,
                description__in=EventType.REGISTRATION_TYPES),
            'form': form,
            'registry': registry,
        }

        return TemplateResponse(request, 'admin/registration_setup.html', context)

    def post(self, request, registry_code):
        registry = Registry.objects.get(code=registry_code)
        form = RegistrationAdminForm(self.notifications, request.POST)

        if form.is_valid():
            with transaction.atomic():
                if form.cleaned_data['enable_registration']:
                    registry.add_feature(RegistryFeatures.REGISTRATION)
                    messages.success(request, _("Registration enabled"))
                else:
                    registry.remove_feature(RegistryFeatures.REGISTRATION)
                    messages.success(request, _("Registration disabled"))
                registry.save()

                if form.cleaned_data['new_notification']:
                    for notification_data in DEFAULT_NOTIFICATIONS:
                        name = notification_data.name

                        notification = EmailNotification(
                            description=EventType.NEW_PATIENT,
                            registry=registry,
                            email_from=form.cleaned_data[f'{name}_from_address'],
                            recipient="{{ patient.user.email }}"
                        )
                        notification.save()

                        for template in notification_data.templates:
                            language = template.language

                            notification.email_templates.create(
                                language=form.cleaned_data[f'{name}_{language}_language'],
                                description=form.cleaned_data[f'{name}_{language}_description'],
                                subject=form.cleaned_data[f'{name}_{language}_subject'],
                                body=form.cleaned_data[f'{name}_{language}_body'],
                            )
            return HttpResponseRedirect(reverse("admin:rdrf_registry_changelist"))
