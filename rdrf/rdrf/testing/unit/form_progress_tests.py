from rdrf.forms.progress.form_progress import FormProgressCalculator
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ClinicalData
from rdrf.views.form_view import FormView

from .tests import FormFiller, FormTestCase


import logging
logger = logging.getLogger(__name__)


class FormProgressTestCase(FormTestCase):

    def create_sections(self):
        super().create_sections()
        self.sectionD = self.create_section(
            "sectionD", "Section D", ["DM1Fatigue", "DM1FatigueSittingReading", "CDEfhDrugs"], False)
        self.sectionE = self.create_section(
            "sectionE", "Section E", ["DM1ChronicInfection", "DM1Cholesterol", "DateOfAssessment"], False)

    def create_forms(self):
        super().create_forms()
        self.new_form = self.create_form(
            "NewForm", [self.sectionA, self.sectionB, self.sectionD, self.sectionE]
        )
        self.other_form = self.create_form(
            "OtherForm", [self.sectionA, self.sectionB, self.sectionD, self.sectionE]
        )

    def _set_form_data(self, form, form_filler):
        request = self._create_request(form, form_filler.data)
        view = FormView()
        view.request = request
        request.session = {}
        view.post(
            request,
            form.registry.code,
            form.pk,
            self.patient.pk,
            self.default_context.pk)

    def _get_clinical_data(self):
        collection = ClinicalData.objects.collection(self.registry.code, "cdes")
        context_id = self.patient.default_context(self.registry).id
        return collection.find(self.patient, context_id).data().first()

    def _compute_progress(self, form, progress_cdes_map):
        fpc = FormProgressCalculator(form.registry, form, self._get_clinical_data(), progress_cdes_map)
        fpc.calculate_progress()
        return fpc.progress_as_dict()

    def test_form_progress_simple_condition(self):
        self.new_form.conditional_rendering_rules = '''
        DM1Fatigue visible if CDEAge >= 10
        '''
        cde_name = CommonDataElement.objects.get(code='CDEName')
        cde_fatigue = CommonDataElement.objects.get(code='DM1Fatigue')
        self.new_form.complete_form_cdes.add(cde_name)
        self.new_form.complete_form_cdes.add(cde_fatigue)
        self.new_form.save()

        ff = FormFiller(self.new_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionA.CDEAge = 5

        self._set_form_data(self.new_form, ff)

        progress_cdes_map = {}
        progress_cdes_map[self.new_form.name] = set(
            cde_model.code for cde_model in self.new_form.complete_form_cdes.all()
        )

        result = self._compute_progress(self.new_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 100)

        ff = FormFiller(self.new_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionA.CDEAge = 20

        self._set_form_data(self.new_form, ff)
        result = self._compute_progress(self.new_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 50)

    def test_form_progress_section_condition(self):
        self.other_form.conditional_rendering_rules = '''
        section sectionD visible if DateOfAssessment >= "10-01-2000"
        '''

        cde_name = CommonDataElement.objects.get(code='CDEName')
        cde_fatigue = CommonDataElement.objects.get(code='DM1Fatigue')
        cde_fatigue_reading = CommonDataElement.objects.get(code='DM1FatigueSittingReading')
        cde_drugs = CommonDataElement.objects.get(code='CDEfhDrugs')
        self.other_form.complete_form_cdes.add(cde_name)
        self.other_form.complete_form_cdes.add(cde_fatigue)
        self.other_form.complete_form_cdes.add(cde_fatigue_reading)
        self.other_form.complete_form_cdes.add(cde_drugs)
        self.other_form.save()

        ff = FormFiller(self.other_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionE.DateOfAssessment = "10-01-1999"
        ff.sectionD.DM1Fatigue = 'DM1FatigueNo'

        self._set_form_data(self.other_form, ff)

        progress_cdes_map = {}
        progress_cdes_map[self.other_form.name] = set(
            cde_model.code for cde_model in self.other_form.complete_form_cdes.all()
        )

        result = self._compute_progress(self.other_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 100)

        ff = FormFiller(self.other_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionE.DateOfAssessment = "10-01-2003"
        ff.sectionD.DM1Fatigue = 'DM1FatigueNo'

        self._set_form_data(self.other_form, ff)
        result = self._compute_progress(self.other_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 50)

    def test_form_progress_multi_condition(self):
        self.new_form.conditional_rendering_rules = '''
        DM1Fatigue visible if CDEAge >= 10 and DateOfAssessment >= "10-01-2000"
        CDEfhDrugs visible if CDEAge >=15 or DateOfAssessment >= "11-01-2000"
        '''
        cde_fatigue = CommonDataElement.objects.get(code='DM1Fatigue')
        cde_drugs = CommonDataElement.objects.get(code='CDEfhDrugs')
        self.new_form.complete_form_cdes.add(cde_fatigue)
        self.new_form.complete_form_cdes.add(cde_drugs)
        self.new_form.save()

        ff = FormFiller(self.new_form)
        ff.sectionA.CDEAge = 5
        ff.sectionE.DateOfAssessment = "10-01-2000"
        ff.sectionD.DM1Fatigue = 'DM1FatigueNo'
        ff.sectionD.CDEfhDrugs = 'PVfhDrugsEzetimibe'

        self._set_form_data(self.new_form, ff)

        progress_cdes_map = {}
        progress_cdes_map[self.new_form.name] = set(
            cde_model.code for cde_model in self.new_form.complete_form_cdes.all()
        )

        result = self._compute_progress(self.new_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 0)

        ff = FormFiller(self.new_form)
        ff.sectionA.CDEAge = 5
        ff.sectionE.DateOfAssessment = "11-01-2000"
        ff.sectionD.DM1Fatigue = 'DM1FatigueNo'
        ff.sectionD.CDEfhDrugs = 'PVfhDrugsEzetimibe'

        self._set_form_data(self.new_form, ff)
        result = self._compute_progress(self.new_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 100)

        ff = FormFiller(self.new_form)
        ff.sectionA.CDEAge = 20
        ff.sectionE.DateOfAssessment = "11-01-2000"
        ff.sectionD.DM1Fatigue = 'DM1FatigueNo'
        ff.sectionD.CDEfhDrugs = 'PVfhDrugsEzetimibe'

        self._set_form_data(self.new_form, ff)
        result = self._compute_progress(self.new_form, progress_cdes_map)
        self.assertEqual(result['progress']['percentage'], 100)
