from django import template

register = template.Library()


@register.filter
def has_unusable_password(user):
    return user.has_unusable_password()
