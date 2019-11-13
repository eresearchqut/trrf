from rdrf.models.definition.models import FormTitle


class FormTitleHelper:

    def __init__(self, registry, default_name):
        self.registry = registry
        self.default_name = default_name

    def title_for_user(self, user):
        entry = FormTitle.objects.filter(
            registry=self.registry,
            group__in=user.groups.all(),
            default_name=self.default_name
        ).order_by('order').first()
        return entry.custom_name if entry else self.default_name

    def title_dict_for_user(self, user):
        results = FormTitle.objects.filter(
            registry=self.registry,
            group__in=user.groups.all(),
        ).order_by('default_name', 'order')
        mappings = {}
        for r in results:
            if r.default_name not in mappings:
                mappings[r.default_name] = r.custom_name

        for default_name, custom_name in FormTitle.FORM_TITLE_CHOICES:
            if default_name not in mappings:
                mappings[default_name] = custom_name
        return mappings
