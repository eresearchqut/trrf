from django.test import override_settings

from rdrf.forms.navigation.quick_links import QuickLinks, RegularLinks
from registry.groups import GROUPS as RDRF_GROUPS

from .tests import RDRFTestCase


class ExtraAssertionsMixin:
    def assertIsEmpty(self, xs, msg='Should be empty'):
        assert len(xs) == 0, msg

    def assertNotEmpty(self, xs, msg='Should NOT be empty'):
        assert len(xs) != 0, msg

    def assertContainsAll(self, values_dict, container):
        for value in values_dict.values():
            assert value in container

    def assertContainsNoneOf(self, values_dict, container):
        for value in values_dict.values():
            assert value not in container, f'{value} found unexpectedly in {container}'


class NormalQuickLinksTests(ExtraAssertionsMixin, RDRFTestCase):

    @override_settings(DESIGN_MODE=False)
    def test_menus(self):
        ql = QuickLinks([])

        menu = ql.menu_links([RDRF_GROUPS.WORKING_GROUP_CURATOR])

        self.assertNotEmpty(menu)
        self.assertContainsAll(RegularLinks.DATA_ENTRY, menu)

        self.assertNotEmpty(ql.settings_links())
        self.assertContainsAll(RegularLinks.AUDITING, ql.settings_links())

        self.assertContainsAll(RegularLinks.EMAIL, ql.admin_page_links())

    @override_settings(DESIGN_MODE=True)
    def test_menus_design_mode(self):
        ql = QuickLinks([])

        self.assertContainsAll(RegularLinks.REGISTRY_DESIGN, ql.admin_page_links())
        self.assertContainsAll(RegularLinks.EMAIL, ql.admin_page_links())
