from django import template

register = template.Library()


@register.filter
def has_usable_password(user):
    return user.has_usable_password()
