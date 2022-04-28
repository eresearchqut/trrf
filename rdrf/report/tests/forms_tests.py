from django.contrib.auth.models import Group
from django.forms import model_to_dict
from django.test import TestCase

from rdrf.models.definition.models import Registry, RegistryForm, CommonDataElement, Section, ConsentQuestion, \
    ConsentSection
from registry.groups import GROUPS as RDRF_GROUPS
from registry.groups.models import WorkingGroup
from report.forms import get_demographic_field_value, get_demographic_field_choices, get_clinical_data_field_value, \
    get_cde_choices, get_section_choices, get_working_group_field_value, get_working_group_choices, \
    get_filter_consent_field_value, get_filter_consent_choices, ReportDesignerForm
from report.models import ReportCdeHeadingFormat, ReportDesign


class FormHelpersTestCase(TestCase):

    maxDiff = None

    def test_get_demographic_field_value(self):
        self.assertEqual('{"model": "patient", "field": "dateOfBirth"}',  get_demographic_field_value('patient', 'dateOfBirth') )
        self.assertEqual('{"model": "patientaddressSet", "field": "addressType { type }"}',  get_demographic_field_value('patientaddressSet', 'addressType { type }') )

    def test_get_demographic_field_choices(self):
        demographic_model = {
            'patient': {
                'label': 'Patient',
                'fields': {
                    'consent': 'Consent',
                }
            },
            'address': {
                'label': 'Patient Address',
                'fields': {
                    'street': 'Street',
                    'suburb': 'Suburb'
                }
            }
        }

        self.assertEqual([('Patient', [('{"model": "patient", "field": "consent"}', "Consent")]),
                          ('Patient Address', [('{"model": "address", "field": "street"}', "Street"),
                                               ('{"model": "address", "field": "suburb"}', "Suburb")])],
                         get_demographic_field_choices(demographic_model))

    def test_get_clinical_data_field_value(self):
        reg1 = Registry.objects.create(code="test1")
        reg2 = Registry.objects.create(code="test2")

        self.assertEqual('{"registry": "test1", "cde_key": "Form1__Section1__CDE1"}', get_clinical_data_field_value(reg1, "Form1__Section1__CDE1"))
        self.assertEqual('{"registry": "test2", "cde_key": "Sleep__SleepDiary__Time_To_Sleep"}', get_clinical_data_field_value(reg2, "Sleep__SleepDiary__Time_To_Sleep"))

    def test_get_cde_choices(self):
        reg1 = Registry.objects.create(code='reg1')

        CommonDataElement.objects.create(code='TimeToBed', name='Time to bed')
        CommonDataElement.objects.create(code='TimeToWake', name='Time Awoke')

        Section.objects.create(code='SleepDiary', display_name='Sleep Diary', elements='TimeToBed,TimeToWake')

        RegistryForm.objects.create(registry=reg1, name='SleepBehaviour', sections='SleepDiary', abbreviated_name='SleepBehaviour')

        self.assertEqual([('SleepBehaviour - Sleep Diary', [('{"registry": "reg1", "cde_key": "SleepBehaviour____SleepDiary____TimeToBed"}', 'Time to bed'),
                                                            ('{"registry": "reg1", "cde_key": "SleepBehaviour____SleepDiary____TimeToWake"}', 'Time Awoke')])],
                         get_cde_choices())

    def test_get_section_choices(self):
        reg1 = Registry.objects.create(code='reg1')
        Section.objects.create(code='Section1', display_name='Section A')
        Section.objects.create(code='Section2', display_name='Section B')
        Section.objects.create(code='Section3', display_name='Section C')
        Section.objects.create(code='Section4', display_name='Section D')
        RegistryForm.objects.create(registry=reg1, name='Form1', sections='Section1,Section2', abbreviated_name='1', position=1)
        RegistryForm.objects.create(registry=reg1, name='Form2', sections='Section3,Section4', abbreviated_name='2', position=2)

        self.assertEqual([("", "Show all Clinical Data Fields"),
                          ("Form1", [('{"registry": "reg1", "form": "Form1", "section": "Section A"}', 'Section A'),
                                     ('{"registry": "reg1", "form": "Form1", "section": "Section B"}', 'Section B')]),
                          ("Form2", [('{"registry": "reg1", "form": "Form2", "section": "Section C"}', 'Section C'),
                                     ('{"registry": "reg1", "form": "Form2", "section": "Section D"}', 'Section D')])],
                         get_section_choices())


class WorkingGroupTestCase(TestCase):
    def setUp(self):
        self.reg1 = Registry.objects.create(code='reg1')
        self.reg2 = Registry.objects.create(code='reg2')
        self.wg1 = WorkingGroup.objects.create(id=1, registry=self.reg1, name='Working Group 1')
        self.wg2 = WorkingGroup.objects.create(id=2, registry=self.reg2, name='Uncategorised')

    def test_get_working_group_field_value(self):
        self.assertEqual('{"registry": "reg1", "wg": 1}', get_working_group_field_value(self.wg1))
        self.assertEqual('{"registry": "reg2", "wg": 2}', get_working_group_field_value(self.wg2))

    def test_get_working_group_choices(self):
        self.assertEqual([('{"registry": "reg1", "wg": 1}', 'reg1 Working Group 1'),
                          ('{"registry": "reg2", "wg": 2}', 'reg2 Uncategorised')], get_working_group_choices())


class FilterConsentTestCase(TestCase):
    def setUp(self):
        self.reg1 = Registry.objects.create(code='abc')
        self.reg2 = Registry.objects.create(code='def')
        self.section1 = ConsentSection.objects.create(registry=self.reg1, code="s1", section_label="Section 1")
        self.section2 = ConsentSection.objects.create(registry=self.reg2, code="s2", section_label="Section 2")
        self.cq1 = ConsentQuestion.objects.create(code="q1", section=self.section1, question_label='Question 1')
        self.cq2 = ConsentQuestion.objects.create(code="q2", section=self.section2, question_label='Question 2')

    def test_get_filter_consent_field_value(self):
        self.assertEqual('{"registry": "abc", "consent_question": "q1"}', get_filter_consent_field_value(self.cq1))
        self.assertEqual('{"registry": "def", "consent_question": "q2"}', get_filter_consent_field_value(self.cq2))

    def test_get_filter_consent_choices(self):
        self.assertEqual([('{"registry": "abc", "consent_question": "q1"}', 'Question 1'),
                          ('{"registry": "def", "consent_question": "q2"}', 'Question 2')],
                         get_filter_consent_choices())

class ReportDesignFormTestCase(TestCase):
    def setUp(self):
        self.reg1 = Registry.objects.create(code='reg1')
        self.reg2 = Registry.objects.create(code='reg2')

        self.required_attrs = {"title": "title",
                               "registry": self.reg1.code,
                               "cde_heading_format": ReportCdeHeadingFormat.LABEL.value,
                               "demographic_fields": ['{"model": "patient", "field": "givenNames"}']}

    def test_duplicate_report_title_validation(self):
        def make_valid_form(registry, title):
            valid_form = ReportDesignerForm(data={"title": title,
                                                  "registry": registry.code,
                                                  "cde_heading_format": ReportCdeHeadingFormat.LABEL.value,
                                                  "demographic_fields": ['{"model": "patient", "field": "givenNames"}',
                                                                         '{"model": "patient", "field": "dateOfBirth"}']})
            return valid_form

        ReportDesign.objects.create(title='Sleep Report', registry=self.reg1)
        ReportDesign.objects.create(title='Infancy Behaviours Report', registry=self.reg1)

        # Unique title is valid
        form = make_valid_form(self.reg1, 'New Report Title')
        self.assertEqual(True, form.is_valid())

        # Duplicate title is invalid
        form_dup_title = make_valid_form(self.reg1, 'Sleep Report')
        self.assertEqual(False, form_dup_title.is_valid())
        self.assertEqual(['A report in this registry with the title "Sleep Report" already exists.'], form_dup_title.errors['title'])

        # Same title is valid in a registry where it hasn't been used
        form_different_reg = make_valid_form(self.reg2, 'Sleep Report')
        self.assertEqual(True, form_different_reg.is_valid())

    def test_clean_filter_working_groups(self):
        wg1 = WorkingGroup.objects.create(id=1, registry=self.reg1)
        wg2 = WorkingGroup.objects.create(id=2, registry=self.reg2)
        wg3 = WorkingGroup.objects.create(id=3, registry=self.reg2)

        form1 = ReportDesignerForm(data=(dict(self.required_attrs,
                                              **{"filter_working_groups": ['{"registry": "reg1", "wg": 1}', '{"registry": "reg2", "wg": 2}']})))
        form2 = ReportDesignerForm(data=(dict(self.required_attrs,
                                              **{"filter_working_groups": ['{"registry": "reg2", "wg": 3}']})))
        form1.is_valid()
        form2.is_valid()

        # Assert that the json representation of working groups have been converted to model objects
        self.assertEqual([wg1, wg2], form1.cleaned_data['filter_working_groups'])
        self.assertEqual([wg3], form2.cleaned_data['filter_working_groups'])

    def test_clean_filter_consents(self):
        s1 = ConsentSection.objects.create(registry=self.reg1, section_label="Section 1", code="S1")
        s2 = ConsentSection.objects.create(registry=self.reg2, section_label="Section 2", code="S2")

        cq1 = ConsentQuestion.objects.create(section=s1, code='cq1')
        cq2 = ConsentQuestion.objects.create(section=s1, code='cq2')
        cq3 = ConsentQuestion.objects.create(section=s2, code='cq3')

        form1 = ReportDesignerForm(data=(dict(self.required_attrs,
                                              **{"filter_consents": ['{"registry": "reg1", "consent_question": "cq1"}',
                                                                     '{"registry": "reg1", "consent_question": "cq2"}']})))
        form2 = ReportDesignerForm(data=(dict(self.required_attrs,
                                              **{"filter_consents": ['{"registry": "reg2", "consent_question": "cq3"}']})))

        form1.is_valid()
        form2.is_valid()

        # Assert that the json representation of consents have been converted to model objects
        self.assertEqual([cq1, cq2], form1.cleaned_data['filter_consents'])
        self.assertEqual([cq3], form2.cleaned_data['filter_consents'])

        # Test when filter_consents contains invalid data
        form3 = ReportDesignerForm(data=(dict(self.required_attrs,
                                              **{"filter_consents": ['{"registry": "reg2", "consent_question": "NonExistent"}']})))
        form3.is_valid()
        self.assertNotIn('filter_consents', form3.cleaned_data)

    def test_save_to_model(self):
        # Given
        group_curator = Group.objects.create(name=RDRF_GROUPS.WORKING_GROUP_CURATOR)
        group_clinician = Group.objects.create(name=RDRF_GROUPS.CLINICAL)
        group_patient = Group.objects.create(name=RDRF_GROUPS.PATIENT)
        group_parent = Group.objects.create(name=RDRF_GROUPS.PARENT)

        reg_mnd = Registry.objects.create(code='mnd')
        reg_ang = Registry.objects.create(code='ang')

        wg1_ang = WorkingGroup.objects.create(registry=reg_ang)
        wg2_ang = WorkingGroup.objects.create(registry=reg_ang)
        wg1_mnd = WorkingGroup.objects.create(registry=reg_mnd)
        wg2_mnd = WorkingGroup.objects.create(registry=reg_mnd)

        cs1 = ConsentSection.objects.create(registry=reg_ang, section_label="Section 1", code="S1")
        cs2 = ConsentSection.objects.create(registry=reg_ang, section_label="Section 2", code="S2")

        cq1 = ConsentQuestion.objects.create(section=cs1, code='cq1')
        cq2 = ConsentQuestion.objects.create(section=cs1, code='cq2')
        cq3 = ConsentQuestion.objects.create(section=cs2, code='cq3')

        CommonDataElement.objects.create(code='DayOfWeek')
        CommonDataElement.objects.create(code='TimeToBed')
        CommonDataElement.objects.create(code='TimeToSleep')
        CommonDataElement.objects.create(code='NumTimesWoke')
        CommonDataElement.objects.create(code='LongestTimeAwake')
        Section.objects.create(code='SleepDiary', elements='DayOfWeek,TimeToBed,TimeToSleep,NumTimesWoke,LongestTimeAwake')
        RegistryForm.objects.create(name='SleepBehaviour', sections='SleepDiary', registry=reg_ang, abbreviated_name='SleepBehaviour')

        # When
        form = ReportDesignerForm(data={"title": "Sleep Tracking Report",
                                        "description": "Reporting on general sleep trends",
                                        "registry": "ang",
                                        "access_groups": [group_clinician.pk, group_curator.pk],
                                        "filter_by_working_groups": True,
                                        "filter_working_groups": [f'{{"registry": "ang", "wg": {wg2_ang.pk}}}'],
                                        "filter_by_consents": True,
                                        "filter_consents": ['{"registry": "ang", "consent_question": "cq2"}', '{"registry": "ang", "consent_question": "cq3"}'],
                                        "demographic_fields": ['{"model": "patient", "field": "givenNames"}', '{"model": "patient", "field": "familyName"}'],
                                        "cde_heading_format": ReportCdeHeadingFormat.ABBR_NAME.value,
                                        "cde_fields": ['{"registry": "ang", "cde_key": "SleepBehaviour____SleepDiary____DayOfWeek"}',
                                                       '{"registry": "ang", "cde_key": "SleepBehaviour____SleepDiary____TimeToBed"}',
                                                       '{"registry": "ang", "cde_key": "SleepBehaviour____SleepDiary____TimeToSleep"}']
                                        })

        self.assertIsNone(form.instance.id)
        valid = form.is_valid()
        self.assertTrue(valid)

        form.save_to_model()

        report_design = form.instance
        self.assertIsNotNone(report_design.id)
        self.assertEqual('Sleep Tracking Report', report_design.title)
        self.assertEqual('Reporting on general sleep trends', report_design.description)
        self.assertEqual(reg_ang, report_design.registry)
        self.assertEqual([group_curator, group_clinician], list(report_design.access_groups.all()))
        self.assertEqual([wg2_ang], list(report_design.filter_working_groups.all()))
        self.assertEqual([cq2, cq3], list(report_design.filter_consents.all()))
        self.assertEqual(ReportCdeHeadingFormat.ABBR_NAME.value, report_design.cde_heading_format)

        demographic_fields = report_design.reportdemographicfield_set.all()
        cde_fields = report_design.reportclinicaldatafield_set.all().order_by('cde_key')

        self.assertEqual(2, len(demographic_fields))
        self.assertEqual(3, len(cde_fields))

        self.assertEqual({'model': 'patient', 'field': 'givenNames', 'sort_order': 0},
                         model_to_dict(demographic_fields[0], fields=('model', 'field', 'sort_order')))
        self.assertEqual({'model': 'patient', 'field': 'familyName', 'sort_order': 1},
                         model_to_dict(demographic_fields[1], fields=('model', 'field', 'sort_order')))

        self.assertEqual({'cde_key': 'SleepBehaviour____SleepDiary____DayOfWeek'}, model_to_dict(cde_fields[0], fields=('cde_key',)))
        self.assertEqual({'cde_key': 'SleepBehaviour____SleepDiary____TimeToBed'}, model_to_dict(cde_fields[1], fields=('cde_key',)))
        self.assertEqual({'cde_key': 'SleepBehaviour____SleepDiary____TimeToSleep'}, model_to_dict(cde_fields[2], fields=('cde_key',)))