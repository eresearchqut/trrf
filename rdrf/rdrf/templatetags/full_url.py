from django import template

from rdrf.helpers.utils import get_base_url


register = template.Library()


@register.tag
def full_url(parser, token):
    url_node = template.defaulttags.url(parser, token)
    return WrapperNode(url_node)


class WrapperNode(template.base.Node):
    def __init__(self, url_node):
        self.url_node = url_node

    def render(self, context):
        url = self.url_node.render(context)
        return get_base_url() + url
