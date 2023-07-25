from django import template
from rdrf.models.definition.models import EmailNotification

register = template.Library()


@register.filter()
def has_subscribable_email(user):
    registries = user.registry.all()
    if EmailNotification.objects.filter(registry__in=registries, subscribable=True).exists():
        return True

    return False
