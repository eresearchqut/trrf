from django.utils.translation import ugettext as _

from rdrf.models.definition.models import FormTitle


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

    def all_titles_for_user(self, user):
        default_titles = {x[0]: _(x[1]) for x in FormTitle.FORM_TITLE_CHOICES}
        custom_titles = dict(
            self.get_base_qs(user)
                .order_by('default_title', '-order')
                .values_list('default_title', 'custom_title')
        )

        return {**default_titles, **custom_titles}
