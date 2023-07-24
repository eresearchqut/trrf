from django import template
from rdrf.models.definition.models import EmailNotification

register = template.Library()


# check whether the registry the user belongs to has subscribable email notifications.
@register.filter()
def has_subscribable_email(user):
    if user.num_registries == 0:
        return False
    registries = user.registry.all()
    for registry in registries:
        email_notification_data = EmailNotification.objects.filter(registry=registry).values()
        for data in email_notification_data:
            if data['subscribable']:
                return True
            pass

    return False
