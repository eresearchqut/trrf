import logging

from registry.groups.models import WorkingGroup, CustomUser
from rdrf.models.definition.models import Registry
from rdrf.system_role import SystemRoles

from django.conf import settings

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

    def test_cic_proms_menus(self):
        settings.SYSTEM_ROLE = SystemRoles.CIC_PROMS
        from rdrf.forms.navigation.quick_links import QuickLinks, PromsLinks

        ql = QuickLinks([self.registry])
        ml = ql.menu_links(["Working Group Curators"])
        self.assertEqual(len(ml), 0)
        sl = ql.settings_links()
        self.assertEqual(len(sl), 0)
        al = ql.admin_page_links()
        for value in PromsLinks.CIC.values():
            self.assertIn(value, al)

    def test_cic_proms_menus_design_mode(self):
        settings.SYSTEM_ROLE = SystemRoles.CIC_PROMS
        settings.DESIGN_MODE = True
        from rdrf.forms.navigation.quick_links import QuickLinks, PromsLinks

        ql = QuickLinks([self.registry])
        al = ql.admin_page_links()
        for value in PromsLinks.CIC.values():
            self.assertIn(value, al)
        for value in PromsLinks.REGISTRY_DESIGN.values():
            self.assertIn(value, al)

    def test_regular_menus(self):
        settings.SYSTEM_ROLE = SystemRoles.NORMAL
        from rdrf.forms.navigation.quick_links import QuickLinks, PromsLinks, RegularLinks

        ql = QuickLinks([self.registry])
        ml = ql.menu_links(["Working Group Curators"])
        self.assertNotEqual(len(ml), 0)
        for value in RegularLinks.DATA_ENTRY.values():
            self.assertIn(value, ml)
        sl = ql.settings_links()
        self.assertNotEqual(len(sl), 0)
        for value in RegularLinks.AUDITING.values():
            self.assertIn(value, sl)
        al = ql.admin_page_links()
        for value in PromsLinks.CIC.values():
            self.assertNotIn(value, al)
        for value in RegularLinks.EMAIL.values():
            self.assertIn(value, al)

    def test_regular_menus_design_mode(self):
        settings.SYSTEM_ROLE = SystemRoles.NORMAL
        settings.DESIGN_MODE = True
        from rdrf.forms.navigation.quick_links import QuickLinks, PromsLinks, RegularLinks

        ql = QuickLinks([self.registry])
        al = ql.admin_page_links()
        for value in PromsLinks.CIC.values():
            self.assertNotIn(value, al)
        for value in PromsLinks.REGISTRY_DESIGN.values():
            self.assertIn(value, al)
        for value in RegularLinks.EMAIL.values():
            self.assertIn(value, al)

    def test_cic_non_proms_menus(self):
        settings.SYSTEM_ROLE = SystemRoles.CIC_DEV
        from rdrf.forms.navigation.quick_links import QuickLinks, PromsLinks, RegularLinks

        ql = QuickLinks([self.registry])
        ml = ql.menu_links(["Working Group Curators"])
        self.assertNotEqual(len(ml), 0)
        for value in RegularLinks.DATA_ENTRY.values():
            self.assertIn(value, ml)
        sl = ql.settings_links()
        self.assertNotEqual(len(sl), 0)
        for value in RegularLinks.AUDITING.values():
            self.assertIn(value, sl)
        al = ql.admin_page_links()
        for value in PromsLinks.CIC.values():
            self.assertIn(value, al)
        for value in RegularLinks.EMAIL.values():
            self.assertIn(value, al)
