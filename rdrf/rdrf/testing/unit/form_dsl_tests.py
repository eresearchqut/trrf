from django.core.exceptions import ValidationError
from .tests import FormTestCase


class FormDSLValidationTestCase(FormTestCase):
    def setUp(self):
        super().setUp()

    def create_sections(self):
        super().create_sections()
        self.sectionD = self.create_section(
            "sectionD", "Section D", ["DM1Fatigue", "DM1FatigueSittingReading"], False)
        self.sectionE = self.create_section(
            "sectionE", "Section E", ["DM1AffectedStatus", "DM1Anxiety"], True)
        self.sectionF = self.create_section(
            "sectionF", "Section F", ["DM1Apathy", "DM1BestMotorLevel"], True)

    def create_forms(self):
        super().create_forms()
        self.new_form = self.create_form("simple", [self.sectionA, self.sectionB, self.sectionD,
                                                    self.sectionE, self.sectionF])

    def test_simple_form(self):
        pass

    @staticmethod
    def get_exception_msgs(exc_info):
        return exc_info.exception.message_dict['conditional_rendering_rules']

    def test_simple_dsl(self):
        self.new_form.conditional_rendering_rules = '''
        CDEName visible if CDEAge == 10
        '''
        self.new_form.save()

    def test_simple_dsl_multiple_CDEs(self):
        self.new_form.conditional_rendering_rules = '''
        CDEName DM1Fatigue visible if CDEAge == 10
        '''
        self.new_form.save()

    def test_simple_dsl_multiple_sections(self):
        self.new_form.conditional_rendering_rules = '''
        section sectionD sectionE sectionF hidden if CDEAge == 10
        '''
        self.new_form.save()

    def test_invalid_cde(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            CDEName1 visible if CDEAge == 10
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'Invalid CDEs specified on line 1 : CDEName1')

    def test_invalid_dsl(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            CDEName visible CDEAge == 10
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertTrue(error_messages[0].startswith('DSL parsing error:'))

    def test_duplicate_condition(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            CDEName visible if CDEAge == 10
            CDEName visible if CDEAge == 10
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'Duplicate condition on line 2: CDEAge == 10')

    def test_inverse_condition(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            CDEName visible if CDEAge ==10
            CDEName visible if CDEAge != 10
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'Opposite condition with same target on line 2: CDEAge != 10')

    def test_overlap_with_section(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            section sectionA visible if CDEAge == 10
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'The target CDEs and conditions CDEs overlap on line 1')

    def test_multiple_errors(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            CDEName1 visible if CDEAge == 10
            DM1Fatigue visible if DM1Fatigue == No
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        results = error_messages[0].split("\n")
        self.assertEqual(results[0], 'Invalid CDEs specified on line 1 : CDEName1')
        self.assertEqual(results[1], 'The target CDEs and conditions CDEs overlap on line 2')

    def test_invalid_cde_value(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            section sectionA visible if DM1Fatigue == abc
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'Invalid value:abc for CDE: DM1Fatigue on line 1')

    def test_valid_cde_value_text(self):
        self.new_form.conditional_rendering_rules = '''
        CDEAge visible if DM1FatigueSittingReading == "Slight chance of dozing"
        '''
        self.new_form.save()

    def test_valid_cde_value_code(self):
        self.new_form.conditional_rendering_rules = '''
        CDEAge visible if DM1FatigueSittingReading != DM1FatigueDozingSlightChance
        '''
        self.new_form.save()

    def test_contradicting_conditions(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            CDEName visible if CDEAge == 10 and CDEAge == 11
            CDEName visible if CDEAge > 10 and CDEAge < 10
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        results = error_messages[0].split("\n")
        self.assertEqual(results[0], 'The conditions repeat or contradict on line 1')
        self.assertEqual(results[1], 'The conditions repeat or contradict on line 2')

    def test_multi_section_condition_and_targets_same_section(self):
        self.new_form.conditional_rendering_rules = '''
        DM1BestMotorLevel visible if DM1Apathy == Yes
        '''
        self.new_form.save()

    def test_multi_section_condition_and_targets_different_sections(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            DM1AffectedStatus visible if DM1Apathy == Yes
            '''
            self.new_form.save()
        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'The condition and target CDEs must be within the same section on line 1')

    def test_cde_is_set(self):
        self.new_form.conditional_rendering_rules = '''
        DM1BestMotorLevel visible if DM1Apathy is set
        '''
        self.new_form.save()

    def test_cde_is_unset(self):
        self.new_form.conditional_rendering_rules = '''
        DM1BestMotorLevel visible if DM1Apathy is unset
        '''
        self.new_form.save()

    def test_cde_incompatible_set_unset(self):
        with self.assertRaises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = '''
            DM1BestMotorLevel visible if DM1Apathy is set
            DM1BestMotorLevel visible if DM1Apathy is unset
            '''
            self.new_form.save()

        error_messages = self.get_exception_msgs(exc_info)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'Different condition with same target on line 2: DM1Apathy is unset')
