from django.test import TestCase

from rdrf.models.definition.models import (
    CDEPermittedValueGroup,
    CommonDataElement,
)


class CommonDataElementModelDisplayValueTest(TestCase):
    def setUp(self):
        super(CommonDataElementModelDisplayValueTest, self).setUp()
        self.cde = CommonDataElement.objects.create()

    def test_cde_display_value_for_lookup(self):
        self.cde.widget_name = "lookup"
        self.assertEqual(self.cde.display_value("some_value"), "some_value")

        self.cde.allow_multiple = True
        self.assertEqual(self.cde.display_value("some_value"), ["some_value"])
        self.assertEqual(
            self.cde.display_value(["val1", "val2"]), ["val1", "val2"]
        )

    def test_cde_display_value_for_pvg_value(self):
        pvg = CDEPermittedValueGroup.objects.create(code="TEST-1")
        for values in (("V1", "Value One"), ("V2", "Value Two")):
            pvg.permitted_value_set.create(code=values[0], value=values[1])

        self.cde.pv_group = pvg

        self.assertEqual(self.cde.display_value("V1"), "Value One")

        self.cde.allow_multiple = True
        self.assertEqual(self.cde.display_value("V1"), ["Value One"])
        self.assertEqual(
            self.cde.display_value(["V2", "V1"]), ["Value Two", "Value One"]
        )

    def test_cde_display_value(self):
        self.assertEqual(self.cde.display_value("Raw Value"), "Raw Value")

        self.cde.allow_multiple = True
        self.assertEqual(self.cde.display_value("Raw Value"), ["Raw Value"])
        self.assertEqual(
            self.cde.display_value(["Apples", "Oranges"]), ["Apples", "Oranges"]
        )
