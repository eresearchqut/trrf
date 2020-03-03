from collections import namedtuple
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
import re


def is_iterable(el):
    return isinstance(el, Iterable) and not isinstance(el, str)


def unquote(val):
    if val and len(val) >= 2:
        if val[0] == '"' and val[-1] == '"':
            return unquote(val[1:-1])
    return val


def make_key(section, cde):
    return f"{section}:{cde}"


class SectionHelper:

    def __init__(self, form):
        self.form = form
        self.section_codes = set(s.code for s in self.form.section_models)

    def is_section(self, code):
        return code in self.section_codes

    def get_section_codes(self):
        return self.section_codes

    def get_section_cdes(self, section_code):
        s = [s for s in self.form.section_models if s.code == section_code]
        if s and s[0]:
            return [make_key(s[0].code, m.code) for m in s[0].cde_models]
        return []

    def get_cde_to_section_dict(self):
        return {
            make_key(s.code, m.code): (s.code, s.allow_multiple)
            for s in self.form.section_models
            for m in s.cde_models
        }


CDEInfo = namedtuple('CDEInfo', 'name type allow_multiple is_multi_section formset_prefix')


class CDEHelper:

    def __init__(self, form):
        self.form = form
        self.cde_names_dict = self.get_cde_names_dict(form)
        self.section_names_dict = self.get_section_names_dict(form)
        self.cde_values_dict = self.get_cde_values_dict(form)
        self.section_dict = self.get_cde_sections_dict(form)

    @staticmethod
    def get_cde_sections_dict(form):
        return {
            m.code: s.code
            for s in form.section_models
            for m in s.cde_models
        }

    @staticmethod
    def get_section_names_dict(form):

        return {
            s.code: (
                CDEInfo(
                    name=s.code,
                    type='',
                    allow_multiple='',
                    is_multi_section=s.allow_multiple,
                    formset_prefix=f"formset_{s.code}" if s.allow_multiple else ''
                )
            )
            for s in form.section_models
        }

    @staticmethod
    def get_cde_names_dict(form):

        return {
            make_key(s.code, m.code): (
                CDEInfo(
                    name=f"{s.code}____{m.code}",
                    type=m.widget_name,
                    allow_multiple=m.allow_multiple,
                    is_multi_section=s.allow_multiple,
                    formset_prefix=f"formset_{s.code}" if s.allow_multiple else ''
                )
            )
            for s in form.section_models
            for m in s.cde_models
        }

    @staticmethod
    def get_cde_values_dict(form):
        return {
            m.code: {
                'type': m.datatype,
                'min_value': m.min_value,
                'max_value': m.max_value,
                'max_length': m.max_length,
                'values': {
                    el['value'].lower(): el['code'] for el in m.pv_group.as_dict()['values']
                } if m.pv_group else {},
                'codes': [
                    el['code'] for el in m.pv_group.as_dict()['values']
                ] if m.pv_group else []

            }
            for s in form.section_models
            for m in s.cde_models
        }

    def get_cde_section(self, cde):
        return self.section_dict.get(cde, None)

    def get_cdes_for_section(self, section_code):
        return [m.code for s in self.form.section_models for m in s.cde_models if s.code == section_code]

    def get_cde_info(self, cde):
        default_info = CDEInfo(cde, None, False, False, '')
        return self.cde_names_dict.get(cde, default_info)

    def get_section_info(self, section):
        default_info = CDEInfo(section, None, False, False, '')
        return self.section_names_dict.get(section, default_info)

    def get_actual_value(self, cde, value):
        stripped_val = unquote(value)
        return self.cde_values_dict.get(cde, {}).get('values', {}).get(stripped_val.lower(), stripped_val)

    def get_data_type(self, cde):
        return self.cde_values_dict.get(cde, {}).get('type', None)

    def is_valid_value(self, cde, value):

        def validate_date(v):
            try:
                datetime.strptime(v, '%d-%m-%Y')
            except ValueError:
                return False
            return True

        def validate_range(v, min_value, max_value):
            try:
                value = Decimal(v)
                is_valid = True
                if min_value:
                    is_valid = value >= min_value
                if max_value:
                    is_valid = valid and value <= max_value
            except ValueError:
                return False
            return is_valid

        def valid_code_or_value(v):
            return v.lower() in values_dict or v.strip() in codes_list

        def validate_humanised_duration(v):
            valid_intervals = {
                "years", "year", "months", "month", "week", "weeks",
                "days", "day", "hours", "hour", "minutes", "minute",
                "seconds", "second"
            }

            def valid_str(s):
                if "," in s:
                    return all(valid_str(v.strip()) for v in s.split(","))
                if "and" in s:
                    return all(valid_str(v.strip()) for v in s.split("and"))
                values = re.split(r"\s+", s)
                return (
                    len(values) % 2 == 0
                    and all(s.isdecimal() for s in values[::2])
                    and all(s.lower() in valid_intervals for s in values[1::2])
                )

            return valid_str(v)

        stripped_val = unquote(value)
        valid = True
        cde_dict = self.cde_values_dict.get(cde, {})
        values_dict = cde_dict.get('values', {})
        codes_list = cde_dict.get('codes', [])
        if not values_dict:
            if cde_dict.get('type') == 'date':
                return validate_date(stripped_val)
            elif cde_dict.get('type') == 'duration':
                return validate_humanised_duration(stripped_val)
            elif cde_dict.get('min_value') or cde_dict.get('max_value'):
                return validate_range(stripped_val, cde_dict.get('min_value'), cde_dict.get('max_value'))
            elif cde_dict.get('max_length'):
                return len(stripped_val) <= cde_dict.get('max_length')
            return valid
        else:
            valid = valid_code_or_value(stripped_val)
            return valid or all(valid_code_or_value(v) for v in stripped_val.split(","))


class EnrichedCDE:

    def __init__(self, cde, cde_helper, has_qualifier=False):
        parts = cde.split(":")
        self.section = None
        if len(parts) == 2:
            self.section, self.cde = parts
        else:
            self.cde = cde
        self.cde_helper = cde_helper
        self.has_qualifier = has_qualifier

    def __repr__(self):
        return f"EnrichedCDE: section={self.section}, cde={self.cde}, qualifier={self.has_qualifier}"

    def get_key(self, input_section=None):
        if self.section:
            return make_key(self.section, self.cde)
        section = input_section or self.cde_helper.section_dict.get(self.cde)
        return make_key(section, self.cde)

    def get_cde_info(self):
        return self.cde_helper.get_cde_info(self.get_key())

    def get_section_info(self):
        return self.cde_helper.get_section_info(self.cde)

    def get_section(self):
        return self.cde_helper.get_cde_section(self.cde)

    def get_data_type(self):
        return self.cde_helper.get_data_type(self.cde)

    def actual_cde_value(self, value):
        parts = value.split(", ")
        if parts and len(parts) > 1:
            values = []
            for part in parts:
                values.append(self.cde_helper.get_actual_value(self.cde, part.strip()))
            ret_val = ", ".join(values)
            if unquote(ret_val) != unquote(value):
                return ret_val
        return self.cde_helper.get_actual_value(self.cde, value)

    def element_name(self):
        return self.cde if self.has_qualifier else self.get_cde_info().name

    def is_multi_section(self):
        return self.get_cde_info().is_multi_section

    def has_valid_section(self):
        if self.section:
            return self.section in self.cde_helper.section_names_dict
        return True

    def is_valid_cde(self):
        return self.get_key() in self.cde_helper.cde_names_dict

    def __eq__(self, other):
        if isinstance(other, EnrichedCDE):
            return (
                self.cde == other.cde and self.section == other.section and self.has_qualifier == other.has_qualifier
            )
        return False

    def __hash__(self):
        return hash((self.cde, self.section, self.has_qualifier))
