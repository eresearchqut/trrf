from django.test import TestCase

from rdrf.forms.widgets.widgets import DurationWidgetHelper


class DurationWidgetTests(TestCase):

    def setUp(self):
        super().setUp()
        self.helper = DurationWidgetHelper({})
        self.is_compatible = self.helper.compatible_formats

    def test_duration_compatibile_formats(self):
        self.assertTrue(self.is_compatible("P0Y0M0D", "P0Y"))
        self.assertTrue(self.is_compatible("P0Y0M0D", "P0Y0D"))
        self.assertTrue(self.is_compatible("P0Y0M0D", "P0M0D"))
        self.assertTrue(self.is_compatible("P0Y0M0DT0H0M0S", "PT0S"))
        self.assertTrue(self.is_compatible("P0M0D", "P0D"))

    def test_duration_incompatible_formats(self):
        self.assertFalse(self.is_compatible("P0Y0M0D", "P0Y0M0DT0H0M0S"))
        self.assertFalse(self.is_compatible("P0Y0M0D", "P0Y0M0DT0M"))
        self.assertFalse(self.is_compatible("P0Y0M0D", "PT0M0H0S"))
        self.assertFalse(self.is_compatible("P0Y0M0DT0H0M", "PT0S"))
        self.assertFalse(self.is_compatible("P0M0D", "P0Y0D"))
        self.assertFalse(self.is_compatible("P0M0D", "PXTR"))
        self.assertFalse(self.is_compatible("ABCD", "XYZ"))

    def test_current_default_format(self):
        helper = DurationWidgetHelper({
            "years": True, "months": False, "days": True,
            "hours": False, "minutes": False, "seconds": False
        })
        self.assertEqual(helper.current_format_default(), "P0Y0D")

        helper = DurationWidgetHelper({
            "weeks_only": True
        })
        self.assertEqual(helper.current_format_default(), "P0W")

        helper = DurationWidgetHelper({
            "years": False, "months": False, "days": True,
            "hours": True, "minutes": True, "seconds": False
        })
        self.assertEqual(helper.current_format_default(), "P0DT0H0M")
