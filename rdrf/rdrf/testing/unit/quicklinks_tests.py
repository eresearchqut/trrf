import logging

from django.test import override_settings
from registry.groups.models import WorkingGroup, CustomUser
from rdrf.models.definition.models import Registry
from rdrf.system_role import SystemRoles

from rdrf.forms.navigation.quick_links import QuickLinks, PromsLinks, RegularLinks

from .tests import RDRFTestCase

logger = logging.getLogger(__name__)


class QuickLinksTests(RDRFTestCase):

    def setUp(self):
        super(QuickLinksTests, self).setUp()
        self.registry = Registry.objects.get(code='fh')
        self.wg, created = WorkingGroup.objects.get_or_create(name="testgroup",
                                                              registry=self.registry)

        if created:
            self.wg.save()

        self.user = CustomUser.objects.get(username="curator")
        self.user.registry.set([self.registry])
        self.user.working_groups.add(self.wg)
        super().setUp()

    def contains_all_values(self, values_dict, container):
        for value in values_dict.values():
            self.assertIn(value, container)

    def does_not_contains_values(self, values_dict, container):
        for value in values_dict.values():
            self.assertIn(value, container)

    @override_settings(SYSTEM_ROLE=SystemRoles.CIC_PROMS)
    def test_cic_proms_menus(self):
        ql = QuickLinks([self.registry])
        ml = ql.menu_links(["Working Group Curators"])
        self.assertEqual(len(ml), 0)
        sl = ql.settings_links()
        self.assertEqual(len(sl), 0)
        al = ql.admin_page_links()
        self.contains_all_values(PromsLinks.CIC, al)

    @override_settings(SYSTEM_ROLE=SystemRoles.CIC_PROMS)
    @override_settings(DESIGN_MODE=True)
    def test_cic_proms_menus_design_mode(self):
        ql = QuickLinks([self.registry])
        al = ql.admin_page_links()
        self.contains_all_values(PromsLinks.CIC, al)
        self.contains_all_values(PromsLinks.REGISTRY_DESIGN, al)

    @override_settings(SYSTEM_ROLE=SystemRoles.NORMAL)
    def test_regular_menus(self):
        ql = QuickLinks([self.registry])
        ml = ql.menu_links(["Working Group Curators"])
        self.assertNotEqual(len(ml), 0)
        self.contains_all_values(RegularLinks.DATA_ENTRY, ml)
        sl = ql.settings_links()
        self.assertNotEqual(len(sl), 0)
        self.contains_all_values(RegularLinks.AUDITING, sl)
        al = ql.admin_page_links()
        self.does_not_contains_values(PromsLinks.CIC, al)
        self.contains_all_values(RegularLinks.EMAIL, al)

    @override_settings(SYSTEM_ROLE=SystemRoles.NORMAL)
    @override_settings(DESIGN_MODE=True)
    def test_regular_menus_design_mode(self):
        ql = QuickLinks([self.registry])
        al = ql.admin_page_links()
        self.does_not_contains_values(PromsLinks.CIC, al)
        self.contains_all_values(PromsLinks.REGISTRY_DESIGN, al)
        self.contains_all_values(RegularLinks.EMAIL, al)

    @override_settings(SYSTEM_ROLE=SystemRoles.CIC_DEV)
    def test_cic_non_proms_menus(self):
        ql = QuickLinks([self.registry])
        ml = ql.menu_links(["Working Group Curators"])
        self.assertNotEqual(len(ml), 0)
        self.contains_all_values(RegularLinks.DATA_ENTRY, ml)
        sl = ql.settings_links()
        self.assertNotEqual(len(sl), 0)
        self.contains_all_values(RegularLinks.AUDITING, sl)
        al = ql.admin_page_links()
        self.contains_all_values(RegularLinks.CIC, al)
        self.contains_all_values(RegularLinks.EMAIL, al)
