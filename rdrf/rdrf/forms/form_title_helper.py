from rdrf.models.definition.models import FormTitle
from django.utils.translation import ugettext as _


class FormTitleHelper:

    def __init__(self, registry, default_title):
        self.registry = registry
        self.default_title = default_title

    def get_base_qs(self, user):
        return FormTitle.objects.filter(
            registry=self.registry,
            groups__in=user.groups.all(),
        )

    def title_for_user(self, user):
        entry = self.get_base_qs(user).filter(
            default_title=self.default_title
        ).order_by('order').first()
        return entry.custom_title if entry else self.default_title

    def title_dict_for_user(self, user):
        results = self.get_base_qs(user).order_by('default_title', 'order')
        mappings = {}
        for r in results:
            if r.default_title not in mappings:
                mappings[r.default_title] = _(r.custom_title)

        for default_title, custom_title in FormTitle.FORM_TITLE_CHOICES:
            if default_title not in mappings:
                mappings[default_title] = _(custom_title)
        return mappings
