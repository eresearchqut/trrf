from lark import Lark, Transformer

from .constants import QUALIFIERS, INVERSE_ACTION_MAP, DSL_DEFINITION, PREDEFINED_VALUES
from .parse_utils import EnrichedCDE


class Target:

    def __init__(self, values, cde_helper, section_helper):
        self.cde_helper = cde_helper
        self.section_helper = section_helper
        self.has_qualifier = values[0].strip() in QUALIFIERS
        input_cdes = values[1:] if self.has_qualifier else values
        self.target_cdes = [EnrichedCDE(cde, self.cde_helper, self.has_qualifier) for cde in input_cdes]

    def invalid_cdes(self):
        if self.has_qualifier:
            sections = set(s.cde for s in self.target_cdes)
            valid_sections = set(s.cde for s in self.target_cdes if s.cde in self.section_helper.get_section_codes())
            return sections - valid_sections

        cdes = set(target.cde for target in self.target_cdes)
        valid_cdes = set(target.cde for target in self.target_cdes if target.cde in self.cde_helper.cde_names_dict)
        return set(cdes) - valid_cdes

    def __eq__(self, other):
        if isinstance(other, Target):
            my_cdes = set(cde.cde for cde in self.target_cdes)
            other_cdes = set(cde.cde for cde in other.target_cdes)
            return len(my_cdes - other_cdes) == 0
        return False

    def __hash__(self):
        cde_tuples = tuple(cde.cde for cde in self.target_cdes)
        return hash(cde_tuples)


class Action:

    def __init__(self, value):
        self.action = value
        self.inverse_action = INVERSE_ACTION_MAP[value]

    def __eq__(self, other):
        if isinstance(other, Action):
            return self.action == other.action
        return False

    def __hash__(self):
        return hash((self.action, ))


class Condition:

    def __init__(self, value, cde_helper):
        self.cde_helper = cde_helper
        cde, self.operator, self.value = value
        self.cde = EnrichedCDE(cde, cde_helper)
        self.actual_value = self.cde.actual_cde_value(self.value)

    @classmethod
    def from_values(cls, cde, operator, value, cde_helper):
        return cls((cde, operator, value), cde_helper)

    def simple_condition_text(self):
        return f'''test_cde_value_simple("{self.cde.element_name()}", "{self.operator}", "{self.actual_value}")'''

    def invalid_cdes(self):
        cde = self.cde.cde
        cdes = {cde}
        valid_cdes = {cde} if cde in self.cde_helper.cde_names_dict else set()
        return cdes - valid_cdes

    def is_valid_value(self):
        return self.value in PREDEFINED_VALUES or self.cde_helper.is_valid_value(self.cde.cde, self.value)

    def as_string(self):
        return f"{self.cde.cde} {self.operator} {self.value}"

    def __eq__(self, other):
        if isinstance(other, Condition):
            return self.cde.cde == other.cde.cde and self.operator == other.operator and self.value == other.value
        return False

    def __hash__(self):
        return hash((self.cde.cde, self.operator, self.value))


class BooleanOp:

    def __init__(self, value):
        self.operator = value

    def to_js(self):
        return "&&" if self.operator == "and" else "||"

    def as_string(self):
        return self.operator

    def inverse(self):
        return "and" if self.operator == "or" else "or"

    def __eq__(self, other):
        if isinstance(other, BooleanOp):
            return self.operator == other.operator
        return False

    def __hash__(self):
        return hash((self.operator, ))


class TreeTransformer(Transformer):

    def __init__(self, cde_helper, section_helper):
        self.cde_helper = cde_helper
        self.section_helper = section_helper

    def target(self, input):
        return Target([x.value for x in input], self.cde_helper, self.section_helper)

    def action(self, input):
        return Action(input[0].value)

    def condition(self, input):
        return Condition([x.value for x in input], self.cde_helper)

    def boolean_operator(self, input):
        return BooleanOp(input[0].value)


def parse_dsl(dsl):
    p = Lark(DSL_DEFINITION, parser='earley', debug=False)
    return p.parse(dsl)


def transform_tree(parse_tree, cde_helper, section_helper):
    return TreeTransformer(cde_helper, section_helper).transform(parse_tree)
