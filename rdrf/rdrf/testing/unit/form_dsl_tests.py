import pytest
from django.core.exceptions import ValidationError

from .tests import FormTestCase


class FormDSLValidationTestCase(FormTestCase):
    def create_sections(self):
        super().create_sections()
        self.sectionD = self.create_section(
            "sectionD",
            "Section D",
            [
                "DM1Fatigue",
                "DM1FatigueSittingReading",
                "CDEfhDrugs",
                "CDEfhHistoryDrugIntolerance",
                "CDEfhIntolerantDrugs",
            ],
            False,
        )
        self.sectionE = self.create_section(
            "sectionE", "Section E", ["DM1AffectedStatus", "DM1Anxiety"], True
        )
        self.sectionF = self.create_section(
            "sectionF", "Section F", ["DM1Apathy", "DM1BestMotorLevel"], True
        )
        self.sectionG = self.create_section(
            "DM1Cholesterol",
            "Section G",
            [
                "DM1ChronicInfection",
                "DM1Cholesterol",
                "CardiacImplant",
                "CDEAge",
                "TestDuration",
            ],
            False,
        )

    def create_forms(self):
        super().create_forms()
        self.new_form = self.create_form(
            "NewForm",
            [
                self.sectionA,
                self.sectionB,
                self.sectionD,
                self.sectionE,
                self.sectionF,
                self.sectionG,
            ],
        )

    @staticmethod
    def get_exception_msgs(exc_info):
        return [
            err.message
            for err in exc_info.value.error_dict["conditional_rendering_rules"]
        ]

    def check_error_messages(
        self, exc_info, expected_count, expected_messages, eq_comparison=True
    ):
        error_messages = self.get_exception_msgs(exc_info)
        messages = error_messages
        if expected_count > 1:
            errors = error_messages[0].split("\n")
            messages = errors
            assert len(errors) == expected_count
        else:
            assert len(error_messages) == expected_count
        idx = 0
        for msg in messages:
            if not eq_comparison:
                assert msg.startswith(expected_messages[idx])
            else:
                assert msg == expected_messages[idx]
            idx += 1

    def test_simple_dsl(self):
        self.new_form.conditional_rendering_rules = """
        CDEName visible if CDEAge == 10
        """
        self.new_form.save()

    def test_simple_dsl_multiple_CDEs(self):
        self.new_form.conditional_rendering_rules = """
        CDEName DM1Fatigue visible if CDEAge == 10
        """
        self.new_form.save()

    def test_simple_dsl_multiple_sections(self):
        self.new_form.conditional_rendering_rules = """
        section sectionD sectionE sectionF hidden if CDEAge == 10
        """
        self.new_form.save()

    def test_invalid_cde(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEName1 visible if CDEAge == 10
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info, 1, ["Invalid CDEs specified on line 1 : CDEName1"]
        )

    def test_invalid_dsl(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEName visible CDEAge == 10
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info, 1, ["DSL parsing error:"], eq_comparison=False
        )

    def test_duplicate_condition(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEName visible if CDEAge == 10
            CDEName visible if CDEAge == 10
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info, 1, ["Duplicate condition on line 2: CDEAge == 10"]
        )

    def test_inverse_condition(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEName visible if CDEAge ==10
            CDEName visible if CDEAge != 10
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            ["Opposite condition with same target on line 2: CDEAge != 10"],
        )

    def test_overlap_with_section(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            section sectionA visible if CDEAge == 10
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            ["The target CDEs and conditions CDEs overlap on line 1"],
        )

    def test_multiple_errors(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEName1 visible if CDEAge == 10
            DM1Fatigue visible if DM1Fatigue == No
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            2,
            [
                "Invalid CDEs specified on line 1 : CDEName1",
                "The target CDEs and conditions CDEs overlap on line 2",
            ],
        )

    def test_invalid_cde_value(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            section sectionA visible if DM1Fatigue == abc
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info, 1, ["Invalid value:abc for CDE: DM1Fatigue on line 1"]
        )

    def test_valid_cde_value_text(self):
        self.new_form.conditional_rendering_rules = """
        CDEAge visible if DM1FatigueSittingReading == "Slight chance of dozing"
        """
        self.new_form.save()

    def test_valid_cde_value_code(self):
        self.new_form.conditional_rendering_rules = """
        CDEAge visible if DM1FatigueSittingReading != DM1FatigueDozingSlightChance
        """
        self.new_form.save()

    def test_contradicting_conditions(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEName visible if CDEAge == 10 and CDEAge == 11
            CDEName visible if CDEAge > 10 and CDEAge < 10
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            2,
            [
                "The conditions repeat or contradict on line 1",
                "The conditions repeat or contradict on line 2",
            ],
        )

    def test_multi_section_condition_and_targets_same_section(self):
        self.new_form.conditional_rendering_rules = """
        DM1BestMotorLevel visible if DM1Apathy == Yes
        """
        self.new_form.save()

    def test_multi_section_condition_and_targets_different_sections(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1AffectedStatus visible if DM1Apathy == Yes
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            [
                "The condition and target CDEs must be within the same section on line 1"
            ],
        )

    def test_cde_is_set(self):
        self.new_form.conditional_rendering_rules = """
        DM1BestMotorLevel visible if DM1Apathy is set
        """
        self.new_form.save()

    def test_cde_is_unset(self):
        self.new_form.conditional_rendering_rules = """
        DM1BestMotorLevel visible if DM1Apathy is unset
        """
        self.new_form.save()

    def test_cde_incompatible_set_unset(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1BestMotorLevel visible if DM1Apathy is set
            DM1BestMotorLevel visible if DM1Apathy is unset
            """
            self.new_form.save()

        self.check_error_messages(
            exc_info,
            1,
            [
                "Different condition with same target on line 2: DM1Apathy is unset"
            ],
        )

    def test_cde_includes_no_multiple_cde(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1BestMotorLevel visible if DM1Apathy includes "A, B"
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            [
                "The inclusion/exclusion operators require a CDE with multiple values on line 1"
            ],
        )

    def test_cde_does_not_include_no_multiple_cde(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1AffectedStatus visible if DM1Anxiety does not include A
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            [
                "The inclusion/exclusion operators require a CDE with multiple values on line 1"
            ],
        )

    def test_valid_cde_includes(self):
        self.new_form.conditional_rendering_rules = """
        DM1Fatigue visible if CDEfhDrugs includes Ezetimibe
        """
        self.new_form.save()

    def test_valid_overlapping_section_and_cde_name(self):
        self.new_form.conditional_rendering_rules = """
        DM1Cholesterol visible if DM1ChronicInfection == Yes
        """
        self.new_form.save()

    def test_invalid_overlapping_section_and_cde_name_with_qualifier(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            section DM1Cholesterol visible if DM1ChronicInfection == Yes
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            ["The target CDEs and conditions CDEs overlap on line 1"],
        )

    def test_single_or_condition(self):
        self.new_form.conditional_rendering_rules = """
        DM1Fatigue visible if DM1FatigueSittingReading == "Slight chance of dozing" or CDEfhDrugs == Ezetimibe
        """
        self.new_form.save()

    def test_three_or_conditions(self):
        self.new_form.conditional_rendering_rules = """
        DM1Fatigue visible if DM1FatigueSittingReading == "Slight chance of dozing" or CDEfhDrugs == Ezetimibe or CDEfhHistoryDrugIntolerance == Yes
        """
        self.new_form.save()

    def test_four_or_conditions(self):
        self.new_form.conditional_rendering_rules = """
        DM1Fatigue visible if DM1FatigueSittingReading == "Slight chance of dozing" or
         CDEfhDrugs == Ezetimibe or CDEfhHistoryDrugIntolerance == Yes or CDEfhIntolerantDrugs == Other
        """
        self.new_form.save()

    def test_contradicting_multiple_or_conditions(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1Fatigue visible if CDEfhDrugs == Ezetimibe or CDEfhDrugs == Statin or CDEfhDrugs != Ezetimibe
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info, 1, ["The conditions repeat or contradict on line 1"]
        )

    def test_simple_value_condition_containing_comma(self):
        self.new_form.conditional_rendering_rules = """
        DM1ChronicInfection visible if CardiacImplant == "Yes, not specified further"
        """
        self.new_form.save()

    def test_simple_condition_with_section_prefix_target(self):
        self.new_form.conditional_rendering_rules = """
        DM1Cholesterol:DM1ChronicInfection visible if CardiacImplant == "Yes, not specified further"
        """
        self.new_form.save()

    def test_simple_condition_with_section_prefix_different_sections(self):
        self.new_form.conditional_rendering_rules = """
        DM1Cholesterol:DM1ChronicInfection visible if sectionA:CDEAge == 18
        """
        self.new_form.save()

    def test_simple_condition_with_section_prefix_invalid_cde(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1Cholesterol:DM1ChronicInfection visible if sectionA:CDEAge2 == 18
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            ["Invalid condition cdes specified on line 1 : CDEAge2"],
        )

    def test_simple_condition_with_invalid_section_prefix(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1Cholesterol:DM1ChronicInfection visible if section:CDEAge == 18
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            [
                'Invalid condition cdes specified on line 1 : Invalid section "section" in section:CDEAge'
            ],
        )

    def test_simple_condition_with_section_prefix_invalid_section_prefix(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            DM1:DM1ChronicInfection visible if sectionA:CDEAge == 18
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            [
                'Invalid CDEs specified on line 1 : Invalid section "DM1" in DM1:DM1ChronicInfection'
            ],
        )

    def test_multi_section_condition_and_targets_same_section_with_section_prefix(
        self,
    ):
        self.new_form.conditional_rendering_rules = """
        sectionF:DM1BestMotorLevel visible if DM1Apathy == Yes
        """
        self.new_form.save()

    def test_with_condition_value_containing_colons_and_parantheses(self):
        self.new_form.conditional_rendering_rules = """
        DM1BestMotorLevel visible if CardiacImplant == "Test with ; on: 'and (this)' with quotes"
        """
        self.new_form.save()

    def test_with_multiple_quoted_conditions(self):
        self.new_form.conditional_rendering_rules = """
        DM1BestMotorLevel visible if CardiacImplant == "Test with ; on: 'and (this)' with quotes" or CardiacImplant == "Yes, not specified further"
        """
        self.new_form.save()

    def test_duration_valid_condition_value(self):
        self.new_form.conditional_rendering_rules = """
        CDEAge visible if TestDuration == "3 years, 2 months, 3 days and 16 hours"
        """
        self.new_form.save()

    def test_duration_invalid_condition_value(self):
        with pytest.raises(ValidationError) as exc_info:
            self.new_form.conditional_rendering_rules = """
            CDEAge visible if TestDuration == "3 years and"
            """
            self.new_form.save()
        self.check_error_messages(
            exc_info,
            1,
            ['Invalid value:"3 years and" for CDE: TestDuration on line 1'],
        )

    def test_other_please_specify_free_value(self):
        self.new_form.conditional_rendering_rules = """
        DM1BestMotorLevel visible if CardiacImplant == "my made up value"
        """
        self.new_form.save()
