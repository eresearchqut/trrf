DSL_DEFINITION = '''
start: instruction+
instruction: (target~1 action~1 "if" condition (boolean_operator~1 condition)*)
condition.3: (VARIABLE OPERATOR ID_OR_CONSTANT)
VARIABLE: CDE
ID_OR_CONSTANT: "unset" | "set" | /\\w+/ | /"[()\\w\\s,-]+"/
FORM_OR_SECTION: "form\\s" | "section\\s"
CDE:SECTION_PREFIX? /\\w+/
SECTION_PREFIX:/\\w+/":"
target.2: FORM_OR_SECTION? CDE+
boolean_operator.4: BOOLEAN_OPERATOR~1
BOOLEAN_OPERATOR: "and" | "or"
OPERATOR: ">="| "<=" | "==" | "!=" | "<" | ">" | "is" | "includes" | "does not include"
action.1: ACTION~1
ACTION: "visible" | "hidden" | "enabled" | "disabled"
%import common.WS
%ignore WS
'''

# Examples
# '''
# ANG1 ANG2 ANG3 visible if ANGBMImetric >= 28
# ANGObesityAge disabled if ANGBMImetric < 25 and ANGAge > 18
# section Test hidden if ANGTest == 2
# form Form1 enabled if ANGTest == PV23
# '''

ENABLED = 'enabled'
DISABLED = 'disabled'
VISIBLE = 'visible'
HIDDEN = 'hidden'

INVERSE_ACTION_MAP = {
    DISABLED: ENABLED,
    VISIBLE: HIDDEN,
    ENABLED: DISABLED,
    HIDDEN: VISIBLE
}

QUALIFIERS = ["section", "form"]

PREDEFINED_VALUES = ["set", "unset"]

INCLUDE_OPERATORS = ["includes", "does not include"]
