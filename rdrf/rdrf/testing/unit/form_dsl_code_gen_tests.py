import pytest

from rdrf.forms.dsl.code_generator import CodeGenerator

from .tests import FormTestCase


class CodeGenTestCase(FormTestCase):

    def create_sections(self):
        super().create_sections()
        self.sectionD = self.create_section(
            "sectionD", "Section D",
            ["DM1Fatigue", "DM1FatigueSittingReading", "CDEfhDrugs", "CDEfhHistoryDrugIntolerance", "CDEfhIntolerantDrugs"],
            False
        )
        self.sectionE = self.create_section(
            "sectionE", "Section E", ["DM1AffectedStatus", "DM1Anxiety"], True)
        self.sectionF = self.create_section(
            "sectionF", "Section F", ["DM1Apathy", "DM1BestMotorLevel"], True)
        self.sectionG = self.create_section(
            "DM1Cholesterol", "Section G", ["DM1ChronicInfection", "DM1Cholesterol", "CardiacImplant", "CDEAge", "TestDuration"], False)

    def create_forms(self):
        super().create_forms()
        self.new_form = self.create_form("new_form", [self.sectionA, self.sectionB, self.sectionD,
                                                      self.sectionE, self.sectionF, self.sectionG])

    def code_gen(self, form, dsl=None):
        return CodeGenerator(dsl or form.conditional_rendering_rules, form)

    def basic_generated_code_validation(self, generated_js):
        assert 'render_changes(visibility_handler())' in generated_js

    def change_handler_validation(self, content, generated_js):
        assert f'add_change_handler({content})' in generated_js

    def visibility_handler_basic_validation(self, visibility_handler_output):
        assert 'function visibility_handler()' in visibility_handler_output
        assert 'visibility_map_update(visibility_map, ' in visibility_handler_output

    def visibility_handler_simple_test(self, visibility_handler_output, name, op, value):
        assert f'test_cde_value_simple("{name}", "{op}", "{value}")'  in visibility_handler_output

    def change_targets_assertions(self, change_targets_output):
        assert 'function change_handler_targets()' in change_targets_output

    def test_code_gen_with_bad_dsl(self):
        generated_js = self.code_gen(self.new_form, 'BAD DSL!').generate_code()
        assert generated_js is None

    def test_code_gen_with_simple_dls(self):
        self.new_form.conditional_rendering_rules = '''
        CDEName visible if CDEAge == 10
        '''
        self.new_form.save()
        code_gen = self.code_gen(self.new_form)
        generated_js = code_gen.generate_code()
        self.basic_generated_code_validation(generated_js)
        self.change_handler_validation('get_cde_name("DM1Cholesterol____CDEAge", 0)', generated_js)
        vho = code_gen.generate_visibility_handler()
        self.visibility_handler_basic_validation(vho)
        self.visibility_handler_simple_test(vho, "DM1Cholesterol____CDEAge", "==", "10")
        change_targets_output = code_gen.generate_change_targets()
        self.change_targets_assertions(change_targets_output)

    def test_three_or_conditions(self):
        self.new_form.conditional_rendering_rules = '''
        DM1Fatigue visible if DM1FatigueSittingReading == "Slight chance of dozing" or CDEfhDrugs == Ezetimibe or CDEfhHistoryDrugIntolerance == Yes
        '''
        self.new_form.save()
        code_gen = self.code_gen(self.new_form)
        generated_js = code_gen.generate_code()
        self.basic_generated_code_validation(generated_js)
        self.change_handler_validation('get_cde_name("sectionD____DM1FatigueSittingReading", 0)', generated_js)
        self.change_handler_validation('get_cde_name("sectionD____CDEfhDrugs", 0)', generated_js)
        self.change_handler_validation('get_cde_name("sectionD____CDEfhHistoryDrugIntolerance", 0)', generated_js)

        vho = code_gen.generate_visibility_handler()
        self.visibility_handler_basic_validation(vho)
        self.visibility_handler_simple_test(vho, "sectionD____DM1FatigueSittingReading", "==", "DM1FatigueDozingSlightChance")
        self.visibility_handler_simple_test(vho, "sectionD____CDEfhDrugs", "==", "PVfhDrugsEzetimibe")
        self.visibility_handler_simple_test(vho, "sectionD____CDEfhHistoryDrugIntolerance", "==", "y")

        change_targets_output = code_gen.generate_change_targets()
        self.change_targets_assertions(change_targets_output)

    def test_multi_section_condition_and_targets_same_section_with_section_prefix(self):
        self.new_form.conditional_rendering_rules = '''
        sectionF:DM1BestMotorLevel visible if DM1Apathy == Yes
        '''
        self.new_form.save()
        code_gen = self.code_gen(self.new_form)
        generated_js = code_gen.generate_code()
        self.basic_generated_code_validation(generated_js)
        code_chunk = '''
            for (idx = 0; idx < total_forms_count("formset_sectionF"); idx ++) {
                add_change_handler(get_cde_name("sectionF____DM1Apathy", idx));
            }
        '''
        assert code_chunk in generated_js
        vho = code_gen.generate_visibility_handler()
        assert 'var name = get_cde_name("sectionF____DM1Apathy", idx);' in vho
        assert "test_cde_value(name, 'sectionF____DM1Apathy', '==', 'Yes')" in vho
        change_targets_output = code_gen.generate_change_targets()
        assert 'change_handler.hasOwnProperty("formset_sectionF")' in change_targets_output
        assert 'change_handler["formset_sectionF"].push("sectionF____DM1Apathy")' in change_targets_output
        assert 'change_handler["formset_sectionF"] = ["sectionF____DM1Apathy"]' in change_targets_output
