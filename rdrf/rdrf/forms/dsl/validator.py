import logging
from collections import defaultdict
from enum import Enum

from django.core.exceptions import ValidationError

from .constants import INCLUDE_OPERATORS
from .parse_utils import CDEHelper, SectionHelper, is_iterable
from .parse_operations import parse_dsl, transform_tree, Condition, BooleanOp

logger = logging.getLogger(__name__)


class ConditionCheckResult(Enum):
    OK = 1
    DUPLICATE_CONDITION = 2
    DIFFERENT_CONDITION_SAME_TARGET = 3
    OPPOSITE_CONDITION_SAME_ACTION = 4
    TARGET_AND_CONDITION_OVERLAP = 5
    INVALID_CONDITION = 6
    MULTI_SECTION_CDE_FAILURE = 7
    MULTI_VALUE_REQUIRED_INCLUDES_EXCLUDES = 8


class ConditionChecker:

    EQUAL = '=='
    NOT_EQUAL = '!='
    GT = '>'
    LT = '<'
    GTE = '>='
    LTE = '<='
    IS = "is"

    AND = "and"
    OR = "or"

    INVERSE_CONDITION_DICT = {
        EQUAL: (NOT_EQUAL,),
        GT: (LT, LTE),
        GTE: (LT,),
        LTE: (GT,),
        LT: (GT, GTE),
        NOT_EQUAL: (EQUAL, ),
    }

    INVERSE_BOOLEAN_OP_DICT = {
        AND: OR,
        OR: AND
    }

    def __init__(self, section_helper):
        self.condition_dict = {}
        self.reverse_condition_dict = {}
        self.section_helper = section_helper
        self.cde_dict = {}

    def inverse_conditions(self, c):
        """"
        Returns the inverse condition for a given condition
        Ex: Condition("a",">","b") -> [Condition("a",  "<=",  "b"), Condition("a",  "<", "b")]
        """
        inverse_ops = self.INVERSE_CONDITION_DICT.get(c.operator, [])
        return [Condition.from_values(c.cde.cde, inverse, c.value, c.cde_helper) for inverse in inverse_ops]

    # TODO: Refactor to meet cyclomatic complexity requirements
    def inverse_multiple_conditions(self, condition):  # noqa: C901
        """"
        Returns a list of inverse conditions for a given multiple condition
        Ex: [Condition("a > b"), BooleanOp("and"), Condition("d > e")] =>
            [[Condition("a > b"), BooleanOp("or"), Condition("d > e")],
             [Condition("a < b"), BooleanOp("and"), Conditionn("d < e")],
             [Condition("a <=b"), BooleanOp("and"), Condition("d <=e")]]
        """

        cloned = [x for x in condition]

        def next_operator():
            return cloned.pop(0)

        def next_condition():
            cond = cloned.pop(0)
            inverse = self.inverse_conditions(cond)
            return cond, inverse

        def add_result(first_inverse_list, second_inverse_list, op):
            for f in first_inverse_list:
                for s in second_inverse_list:
                    result.append([f, op, s])

        result = []
        op_next = False
        prev_conditions = []
        while cloned:
            if op_next:
                op = next_operator()
            first_cond, first_inverse = next_condition()
            op_next = True
            if cloned:
                prev_conditions.append((first_cond, first_inverse))
                if op_next:
                    op = next_operator()
                second_cond, second_inverse = next_condition()
                prev_conditions.append((second_cond, second_inverse))
                result.append([first_cond, BooleanOp(op.inverse()), second_cond])
                add_result(first_inverse, second_inverse, op)
            else:
                for cond, inverse in prev_conditions:
                    result.append([first_cond, BooleanOp(op.inverse()), cond])
                    add_result(first_inverse, inverse, op)

        return result

    # TODO: Refactor to meet cyclomatic complexity requirements
    def check_condition_values(self, condition, multiple_conditions):  # noqa: C901
        """
        Check if conditions do not repeat/contradict in case of multiple conditions
        """
        if multiple_conditions:
            operation_dict = defaultdict(list)
            idx = 0
            cond_len = len(condition)
            current_boolean_op = None
            while idx < cond_len:
                c = condition[idx]
                if idx + 2 < cond_len:
                    boolean_op = condition[idx + 1]
                    operation_dict[boolean_op].append(c)
                elif current_boolean_op:
                    operation_dict[current_boolean_op].append(c)
                idx += 2
                current_boolean_op = boolean_op

            for key, values in operation_dict.items():
                cde_dict = {}
                for el in values:
                    if el.cde.cde in cde_dict:
                        existing_op, existing_value = cde_dict[el.cde.cde]
                        if key.operator == self.AND:
                            if existing_op == el.operator and existing_value != el.value:
                                return False
                            if existing_op != el.operator and existing_value == el.value:
                                return False
                        if key.operator == self.OR and existing_value == el.value:
                            return False
                    else:
                        cde_dict[el.cde.cde] = (el.operator, el.value)

        return True

    def expand_cdes(self, filtered_cdes):
        """
        If the cdes in filtered_cdes refer to a section expands them
        to all the cdes contained in that section
        """
        expanded_cdes = []
        for cde in filtered_cdes:
            if self.section_helper.is_section(cde.cde):
                expanded_cdes.extend(self.section_helper.get_section_cdes(cde.cde))
            else:
                expanded_cdes.append(cde.cde)
        return tuple(expanded_cdes)

    def check_includes_cde(self, condition):
        return condition.cde.get_cde_info().allow_multiple

    # TODO: Refactor to meet cyclomatic complexity requirements
    def check_condition(self, conditions, action, target):  # noqa: C901
        expanded_cdes = self.expand_cdes(target.target_cdes) if target.has_qualifier else \
            tuple([cde.cde for cde in target.target_cdes])
        multiple_conditions = any([c for c in conditions if isinstance(c, BooleanOp)])
        condition_cdes = [c.cde.cde for c in conditions if isinstance(c, Condition)]

        overlap_condition = any([c for c in condition_cdes if c in expanded_cdes])

        if overlap_condition:
            return ConditionCheckResult.TARGET_AND_CONDITION_OVERLAP

        condition_key = tuple(conditions)
        condition_target = (action, expanded_cdes)

        if condition_key in self.condition_dict:
            return ConditionCheckResult.DUPLICATE_CONDITION

        inverse_cond_list = (
            self.inverse_multiple_conditions(conditions) if multiple_conditions
            else self.inverse_conditions(conditions[0])
        )
        for cond_key in inverse_cond_list:
            key = tuple(cond_key) if is_iterable(cond_key) else tuple([cond_key])
            if self.condition_dict.get(key) == condition_target:
                return ConditionCheckResult.OPPOSITE_CONDITION_SAME_ACTION

        if condition_target in self.reverse_condition_dict:
            return ConditionCheckResult.DIFFERENT_CONDITION_SAME_TARGET

        if not self.check_condition_values(conditions, multiple_conditions):
            return ConditionCheckResult.INVALID_CONDITION

        cde_section_dict = self.section_helper.get_cde_to_section_dict()
        condition_entries = {cde: cde_section_dict.get(cde) for cde in condition_cdes}
        target_entries = {cde.cde: cde_section_dict.get(cde.cde) for cde in target.target_cdes}
        for _, cond_value in condition_entries.items():
            for target_key, target_value in target_entries.items():
                if cond_value and target_value:
                    both_cdes_in_allow_multiple_section = cond_value[1] and cond_value[1] == target_value[1]
                    in_different_sections = cond_value[0] != target_value[0]
                    if both_cdes_in_allow_multiple_section and in_different_sections:
                        return ConditionCheckResult.MULTI_SECTION_CDE_FAILURE

        conditions_with_inclusion_operators = [
            c for c in conditions if isinstance(c, Condition) and c.operator in INCLUDE_OPERATORS
        ]
        if conditions_with_inclusion_operators:
            valid_inclusion_conditions = all([self.check_includes_cde(c) for c in conditions_with_inclusion_operators])
            if not valid_inclusion_conditions:
                return ConditionCheckResult.MULTI_VALUE_REQUIRED_INCLUDES_EXCLUDES

        self.condition_dict[condition_key] = condition_target
        self.reverse_condition_dict[condition_target] = condition_key
        return ConditionCheckResult.OK


class DSLValidator:

    def __init__(self, dsl, form):
        self.dsl = dsl
        self.form = form
        self.cde_helper = CDEHelper(form)
        self.section_helper = SectionHelper(form)

    @staticmethod
    def validate_condition_cdes(cond, idx):
        cond_validation = cond.invalid_cdes()
        if cond_validation:
            return [f'Invalid condition specified on line {idx} : {" ".join(cond_validation)}']
        return []

    @staticmethod
    def validate_condition_values(cond, idx):
        if not cond.is_valid_value():
            return [f'Invalid value:{cond.value} for CDE: {cond.cde.cde} on line {idx}']
        return []

    @staticmethod
    def check_condition(checker, condition_list, action, target, idx):
        condition_str = " ".join([c.as_string() for c in condition_list])
        errors = []

        result_handlers = {
            ConditionCheckResult.DUPLICATE_CONDITION:
                lambda: f"Duplicate condition on line {idx}: {condition_str}",
            ConditionCheckResult.DIFFERENT_CONDITION_SAME_TARGET:
                lambda: f"Different condition with same target on line {idx}: {condition_str}",
            ConditionCheckResult.OPPOSITE_CONDITION_SAME_ACTION:
                lambda: f"Opposite condition with same target on line {idx}: {condition_str}",
            ConditionCheckResult.TARGET_AND_CONDITION_OVERLAP:
                lambda: f"The target CDEs and conditions CDEs overlap on line {idx}",
            ConditionCheckResult.INVALID_CONDITION:
                lambda: f"The conditions repeat or contradict on line {idx}",
            ConditionCheckResult.MULTI_SECTION_CDE_FAILURE:
                lambda: f"The condition and target CDEs must be within the same section on line {idx}",
            ConditionCheckResult.MULTI_VALUE_REQUIRED_INCLUDES_EXCLUDES:
                lambda: f"The inclusion/exclusion operators require a CDE with multiple values on line {idx}"
        }

        check_result = checker.check_condition(condition_list, action, target)
        handler = result_handlers.get(check_result, None)
        if handler:
            errors.append(handler())

        return errors

    def handle_instruction(self, inst, idx, checker):
        errors = []
        target, action, *conditions = inst.children
        multiple_conditions = len(conditions) > 1
        cde_validation = target.invalid_cdes()
        if cde_validation:
            errors.append(f'Invalid CDEs specified on line {idx} : {" ".join(cde_validation)}')
            return errors

        if not multiple_conditions:
            errors.extend(self.validate_condition_cdes(conditions[0], idx))
            errors.extend(self.validate_condition_values(conditions[0], idx))
            errors.extend(self.check_condition(checker, conditions, action, target, idx))
        else:
            only_conditions = [c for c in conditions if isinstance(c, Condition)]
            for c in only_conditions:
                errors.extend(self.validate_condition_cdes(c, idx))
                errors.extend(self.validate_condition_values(c, idx))

            errors.extend(self.check_condition(checker, conditions, action, target, idx))

        return errors

    def check_rules(self):

        errors = []
        checker = ConditionChecker(SectionHelper(self.form))

        try:
            parse_tree = parse_dsl(self.dsl)
            transformed_tree = transform_tree(parse_tree, self.cde_helper, self.section_helper)
        except Exception as e:
            logger.exception("Exception while parsing dsl")
            raise ValidationError({
                "conditional_rendering_rules": f"DSL parsing error: {e}"
            })

        for idx, inst in enumerate(transformed_tree.children):
            errors.extend(self.handle_instruction(inst, idx + 1, checker))

        if errors:
            logger.info(f'DSL validation errors: {", ".join(errors)}')
            raise ValidationError({
                "conditional_rendering_rules": "\n".join(errors)
            })
