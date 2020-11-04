from itertools import chain
import logging
import operator

from ..dynamic.value_fetcher import DynamicValueFetcher
from .constants import VISIBLE, HIDDEN
from .parse_operations import BooleanOp, Condition, parse_dsl, transform_tree
from .parse_utils import CDEHelper, SectionHelper
from .utils import DATE_TYPE, INTEGER_TYPE, parse_date, parse_int, as_type


logger = logging.getLogger(__name__)


class ConditionEvaluator:

    def __init__(self, op, value, existing_value, data_type):
        self.operator = op
        self.value = value
        self.existing_value = existing_value
        self.data_type = data_type
        self.eval_dict = {
            "==": operator.eq,
            "!=": operator.ne,
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            "is": lambda existing, current: bool(existing) if current == "set" else not bool(existing),
            "includes": lambda existing, current: existing in [as_type(self.data_type, el) for el in current.split(",")],
            "does not include": lambda existing, current: existing not in [as_type(self.data_type, el) for el in current.split(",")]
        }

    @staticmethod
    def default_comparison(existing, current):
        return False

    def evaluate(self):
        value = self.value
        existing_value = self.existing_value
        if self.data_type:
            if self.data_type.lower() == INTEGER_TYPE:
                value = parse_int(self.value) if self.value not in ["set", "unset"] else None
                existing_value = parse_int(self.existing_value) if self.existing_value else None
            elif self.data_type.lower() == DATE_TYPE:
                value = parse_date(self.value) if self.value not in ["set", "unset"] else None
                existing_value = parse_date(self.existing_value) if self.existing_value else None
            if not all([value, existing_value]):
                # If one of the values is None fail the evaluation
                return False
        return self.eval_dict.get(self.operator, self.default_comparison)(existing_value, value)


# This should be used only on previously validated from DSLs
class CodeEvaluator:
    """
    This is used in form progress indicator to not include in the
    progress computation the elements which are hidden due to form
    conditional rendering rules
    """

    def __init__(self, form, dynamic_data):
        self.dsl = form.conditional_rendering_rules
        self.form = form
        self.cde_helper = CDEHelper(form)
        self.section_helper = SectionHelper(form)
        self.dynamic_data = dynamic_data

    def check_condition(self, condition):
        cde, operator, value = condition.cde.cde, condition.operator, condition.actual_value
        value_fetcher = DynamicValueFetcher(self.dynamic_data)
        existing_value = value_fetcher.get_value_from_dynamic_data(
            self.form.name, condition.cde.get_section(), cde
        )
        final_value = existing_value[0] if existing_value and isinstance(existing_value, list) else existing_value
        evaluator = ConditionEvaluator(operator, value, final_value, condition.cde.get_data_type())
        return evaluator.evaluate()

    def hidden_cdes(self, target, action, check_result):
        result = []
        if (action == HIDDEN and check_result) or (action == VISIBLE and not check_result):
            if target.has_qualifier:
                section_cdes = [self.cde_helper.get_cdes_for_section(s.cde) for s in target.target_cdes]
                result = list(chain(*section_cdes))
            else:
                result = [t.cde for t in target.target_cdes]
        return result

    def hidden_cdes_for_conditions(self, target, action, conditions):
        # Fetch actual values for CDEs which appear in condition, evaluate condition and determine if the
        # target CDEs are hidden or not
        if len(conditions) > 1:
            conditions_only = [c for c in conditions if isinstance(c, Condition)]
            boolean_ops = [op.operator for op in conditions if isinstance(op, BooleanOp)]
            condition_checks = [self.check_condition(c) for c in conditions_only]
            check_result = condition_checks.pop(0)
            for op in boolean_ops:
                next_check = condition_checks.pop(0)
                if op == "and":
                    check_result = check_result and next_check
                else:
                    check_result = check_result or next_check
        else:
            check_result = self.check_condition(conditions[0])

        return self.hidden_cdes(target, action.action, check_result)

    def handle_instruction(self, inst):
        target, action, *conditions = inst.children
        cde_validation = target.invalid_cdes()
        if cde_validation:
            logger.error(f'Invalid CDEs specified: {" ".join(cde_validation)}')
            return []

        return self.hidden_cdes_for_conditions(target, action, conditions)

    def determine_hidden_cdes(self):
        result = []
        try:
            parse_tree = parse_dsl(self.dsl)
            transformed_tree = transform_tree(parse_tree, self.cde_helper, self.section_helper)
        except Exception:
            logger.exception("Exception while parsing dsl")
            return result

        for inst in transformed_tree.children:
            result.extend(self.handle_instruction(inst))

        return set(result)
