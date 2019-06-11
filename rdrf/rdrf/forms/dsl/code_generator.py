import logging

from .parse_utils import CDEHelper, SectionHelper
from .parse_operations import parse_dsl, transform_tree, Condition, BooleanOp


logger = logging.getLogger(__name__)


class CDE:

    def __init__(self, enriched_cde):
        self.cde = enriched_cde

    @staticmethod
    def multi_section_handler(cde_info):
        return f'''
            for (idx = 0; idx < total_forms_count("{cde_info.formset_prefix}"); idx ++) {{
                add_change_handler(get_cde_name("{cde_info.name}", idx));
            }}
        '''

    def simple_change_handler(self):
        return f'add_change_handler(get_cde_name("{self.cde.element_name()}", 0));'

    def change_handler(self):
        cde_info = self.cde.get_cde_info()
        return (
            self.multi_section_handler(cde_info) if cde_info.is_multi_section else self.simple_change_handler()
        )


class ConditionGenerator:

    @staticmethod
    def generate_simple_condition(condition, action_assignments, inverse_action_assignments):
        return f'''
            if ({condition}) {{
                {action_assignments}
            }} else {{
                {inverse_action_assignments}
            }}'''

    @staticmethod
    def generate_multi_section_condition(condition, action_assignments, inverse_action_assignments):
        cde_info = condition.cde.get_cde_info()
        return f'''
            for (var idx = 0; idx < total_forms_count("{cde_info.formset_prefix}"); idx ++) {{
                var name = get_cde_name("{cde_info.name}", idx);
                if (test_cde_value(name, '{cde_info.name}', '{condition.operator}', '{condition.actual_value}')) {{
                    {action_assignments}
                }} else {{
                    {inverse_action_assignments}
                }}
            }}'''


class Instruction:

    def __init__(self, inst_list, cde_helper):
        self.target, self.action, *self.conditions = inst_list
        self.multiple_conditions = len(self.conditions) > 1
        self.cde_helper = cde_helper

    def generate_visibility_assignments(self, is_multi_section):

        def visibility_map_entry(cde_info, action, is_inverse=False, condition_is_multiple=False):
            final_action = action.action if not is_inverse else action.inverse_action
            if cde_info.is_multi_section and condition_is_multiple:
                return f'visibility_map[get_cde_name("{cde_info.name}", idx)] = "{final_action}";'

            return f'visibility_map_update(visibility_map, "{cde_info.name}", "{final_action}");'

        actions = [
            visibility_map_entry(target.get_cde_info(), self.action, False, is_multi_section)
            for target in self.target.target_cdes
        ]
        inverse_actions = [
            visibility_map_entry(target.get_cde_info(), self.action, True, is_multi_section)
            for target in self.target.target_cdes
        ]
        return "\n".join(actions), "\n".join(inverse_actions)

    def single_condition_assignments(self):
        condition = self.conditions[0]
        cde_info = condition.cde.get_cde_info()

        action_assignments, inverse_action_assignments = self.generate_visibility_assignments(cde_info.is_multi_section)

        if cde_info.is_multi_section:
            return ConditionGenerator.generate_multi_section_condition(
                condition, action_assignments, inverse_action_assignments
            )
        else:
            return ConditionGenerator.generate_simple_condition(
                condition.simple_condition_text(), action_assignments, inverse_action_assignments
            )

    def multiple_condition_assignments(self):

        def multi_section_handler(cond, action_assignments, inverse_action_assignments):
            conditions = [c for c in cond if isinstance(c, Condition)]
            boolean_ops = ['"' + op.to_js() + '"' for op in cond if isinstance(op, BooleanOp)]
            computation = []
            for c in conditions:
                cde = c.cde
                computation.append(
                    f'results.push(test_cde_value(get_cde_name("{cde.element_name()}", idx), "{cde.element_name()}", "{c.operator}", "{c.actual_value}"));'
                )

            computations = "\n".join(computation)
            return f'''
                var results = [];
                var boolean_ops =[{",".join(boolean_ops)}];
                {computations}
                if (test_conditions(results, boolean_ops)) {{
                    {action_assignments}
                }} else {{
                    {inverse_action_assignments}
                }}
            '''

        has_multi_section = any(
            [c for c in self.conditions if isinstance(c, Condition) and c.cde.is_multi_section]
        )

        action_assignments, inverse_action_assignments = self.generate_visibility_assignments(has_multi_section)

        if has_multi_section:
            cde_infos = [c.cde.get_cde_info() for c in self.conditions if isinstance(c, Condition)]
            multi_cde_info = [c for c in cde_infos if c.is_multi_section][0]
            return f'''
                var result = true;
                for (var idx = 0; idx < total_forms_count("{multi_cde_info.formset_prefix}"); idx ++) {{
                    {multi_section_handler(self.conditions, action_assignments, inverse_action_assignments)}
                }}'''
        else:
            cond_str_list = [
                c.simple_condition_text() if isinstance(c, Condition) else c.to_js() for c in self.conditions
            ]
            condition = " ".join(cond_str_list)
            return ConditionGenerator.generate_simple_condition(condition, action_assignments, inverse_action_assignments)

    def conditional_visibility_assignments(self):
        return (
            self.multiple_condition_assignments() if self.multiple_conditions
            else self.single_condition_assignments()
        )

    def generate_change_handler(self):
        if not self.multiple_conditions:
            condition_cdes = [CDE(c.cde) for c in self.conditions if isinstance(c, Condition)]
            return "\n".join([cde.change_handler() for cde in condition_cdes])
        else:
            event_handler_cdes = [CDE(c.cde) for c in self.conditions if isinstance(c, Condition)]
            return "\n".join([cde.change_handler() for cde in event_handler_cdes])

    @staticmethod
    def change_handler_element(cde_info):
        return f'''
            if (change_handler.hasOwnProperty("{cde_info.formset_prefix}")) {{
                change_handler["{cde_info.formset_prefix}"].push("{cde_info.name}");
            }} else {{
                change_handler["{cde_info.formset_prefix}"] = ["{cde_info.name}"];
            }}
        '''

    def get_multi_section_targets(self):
        if not self.multiple_conditions:
            condition = self.conditions[0]
            cde_info = condition.cde.get_cde_info()
            if cde_info.is_multi_section:
                return self.change_handler_element(cde_info)
            else:
                return ''
        else:
            event_handler_cdes = [c.cde for c in self.conditions if isinstance(c, Condition)]
            filtered_cde_infos = [cde.get_cde_info() for cde in event_handler_cdes if cde.get_cde_info().is_multi_section]
            return "\n".join([self.change_handler_element(cde_info) for cde_info in filtered_cde_infos])


class CodeGenerator:

    def __init__(self, dsl, form):
        self.dsl = dsl
        self.cde_helper = CDEHelper(form)
        self.section_helper = SectionHelper(form)
        self.multi_section_targets = []
        self.condition_handlers = []
        self.form = form

    def generate_visibility_handler(self):
        visibility_assignments = "\n".join(self.condition_handlers)
        return f'''
        function visibility_handler() {{
            var visibility_map = {{}};
            {visibility_assignments}
            return visibility_map;
        }}'''

    @staticmethod
    def get_initializer():
        return "\trender_changes(visibility_handler());"

    def generate_code(self):
        if not self.dsl:
            return None

        try:
            parse_tree = parse_dsl(self.dsl)
            transformed_tree = transform_tree(parse_tree, self.cde_helper, self.section_helper)

            change_handlers = []
            for idx, inst in enumerate(transformed_tree.children):
                instruction_obj = Instruction(inst.children, self.cde_helper)
                self.condition_handlers.append(instruction_obj.conditional_visibility_assignments())
                change_handlers.append(instruction_obj.generate_change_handler())
                self.multi_section_targets.append(instruction_obj.get_multi_section_targets())

            event_handlers = "\n".join(change_handlers)
            ret_val = f'''
                \t{event_handlers}
                \t{self.get_initializer()}'''

            logger.info(f"Generated code:\n{ret_val}")
            return ret_val
        except Exception:
            logger.exception("Exception while parsing dsl")
            return None

    def generate_change_targets(self):
        elements = "\n".join(self.multi_section_targets)
        return f'''
            function change_handler_targets() {{
                var change_handler = {{}};
                {elements}
                return change_handler;
            }}
        '''

    def generate_declarations(self):

        def cde_mapping(cde_info):
            multiple = 'true' if cde_info.allow_multiple else 'false'
            return f'''
                "{cde_info.name}":{{ type: "{cde_info.type}", allow_multiple: {multiple}, formset: "{cde_info.formset_prefix}"}}
            '''

        entries = ",".join([
            cde_mapping(cde_info) for cde_info in self.cde_helper.get_cde_names_dict(self.form).values()
        ])
        return f'''
            var cdeNamePrefix = "{self.form.name}____";
            var cdeNameMapping = {{
                {entries}
            }}
        '''
