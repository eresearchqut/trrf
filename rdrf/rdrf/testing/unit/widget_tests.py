from django.test import TestCase

from rdrf.forms.widgets.widgets import XnatWidget


class WidgetTest(TestCase):
    def test_xnat_extract_lookup_values(self):
        self.assertEqual(XnatWidget.extract_lookup_values('PROJ1;SUBJ-Y'), ['PROJ1', 'SUBJ-Y'])
        self.assertEqual(XnatWidget.extract_lookup_values('Assessment ABC;Patient XYZ'), ['Assessment ABC', 'Patient XYZ'])
        self.assertEqual(XnatWidget.extract_lookup_values(';Subject'), ['', 'Subject'])
        self.assertEqual(XnatWidget.extract_lookup_values(';'), ['', ''])
        self.assertEqual(XnatWidget.extract_lookup_values(''), (None, None))

        with self.assertRaises(AssertionError):
            XnatWidget.extract_lookup_values('1;2;3'), (None, None)
