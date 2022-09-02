from django.test import TestCase

from rdrf.templatetags.join_if_list import join_if_list


class StandardFilterTests(TestCase):
    def test_join_if_list(self):
        self.assertEqual(join_if_list([], ','), 'None')
        self.assertEqual(join_if_list(None, ','), 'None')
        self.assertEqual(join_if_list(None, ',', 'Not defined'), 'Not defined')
        self.assertEqual(join_if_list(['A', 'B', 'C']), 'A, B, C')
        self.assertEqual(join_if_list(['A', 'B', 'C'], '; '), 'A; B; C')
        self.assertEqual(join_if_list(['A']), 'A')
        self.assertEqual(join_if_list('String value'), 'String value')
        self.assertEqual(join_if_list([1, 2, 3]), '1, 2, 3')
        self.assertEqual(join_if_list(1), 1)
