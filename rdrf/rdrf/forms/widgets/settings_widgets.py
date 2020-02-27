import json

from django.forms import Widget
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from .widgets import TimeWidget


class SliderWidgetSettings(Widget):

    @staticmethod
    def get_allowed_fields():
        return {'min', 'max', 'left_label', 'right_label', 'step'}

    @staticmethod
    def generate_input(name, title, parsed, info=None):
        value = parsed.get(name, '')
        input_str = f'<input type="text" name="{name}" id="{name}" value="{value}" onchange="saveJSON()">'
        help_text = f'<div class="help">{info}</div>' if info else ''
        return f"""
            <div>
                <label for="{name}">{title}</label>
                {input_str}
                {help_text}
            </div>"""

    def generate_inputs(self, parsed):
        rows = [
            self.generate_input('min', _('Min value'), parsed, _("leave empty if you want to use the CDE's min value")),
            self.generate_input('max', _('Max value'), parsed, _("leave empty if you want to use the CDE's max value")),
            self.generate_input('left_label', _('Left label'), parsed),
            self.generate_input('right_label', _('Right label'), parsed),
            self.generate_input('step', _('Step'), parsed),
        ]
        return "<br/>".join(rows)

    def render(self, name, value, attrs=None, renderer=None):
        parsed = {}
        try:
            parsed = json.loads(value)
        except Exception:
            pass

        html = """
             <div style="display:inline-grid" id="id_{name}">
                {inputs}
                <input type="hidden" name="{name}" value='{value}'/>
             </div>""".format(inputs=self.generate_inputs(parsed), name=name, value=value)
        javascript = """
            function saveJSON() {
                var inputs = $('#id_%s input[type!=hidden]');
                var obj = {};
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].value !='' && inputs[i].value.trim() != '') {
                        obj[inputs[i].name] = inputs[i].value;
                    }
                }
                $("input[name='%s']").val(JSON.stringify(obj));
            }
            saveJSON();
        """ % (name, name)
        return mark_safe(f"""
            {html}
            <script>
                {javascript}
            </script>""")


class TimeWidgetSettings(Widget):

    @staticmethod
    def get_allowed_fields():
        return {'format'}

    def generate_input(self, name, title, parsed, info=None):
        value = parsed.get(name, '')
        selected_12hour = 'selected' if value == TimeWidget.AMPM else ''
        selected_24hour = 'selected' if value == TimeWidget.FULL else ''
        if not selected_12hour and not selected_24hour:
            selected_12hour = 'selected'

        input_str = f'''
            <select name="{name}" id="{name}" onchange="saveJSON()">
                <option value="{TimeWidget.AMPM}" {selected_12hour}> 12-hour format </option>
                <option value="{TimeWidget.FULL}" {selected_24hour}> 24-hour format </option>
            </select>'''
        help_text = f'<div class="help">{info}</div>' if info else ''
        return f"""
            <div>
                <label for="{name}">{title}</label>
                {input_str}
                {help_text}
            </div>"""

    def generate_inputs(self, parsed):
        rows = [
            self.generate_input('format', _('Format'), parsed, _("Format of time: 12-hour or 24-hour")),
        ]
        return "<br/>".join(rows)

    def render(self, name, value, attrs=None, renderer=None):
        parsed = {}
        try:
            parsed = json.loads(value)
        except Exception:
            pass

        html = """
             <div style="display:inline-grid" id="id_{name}">
                {inputs}
                <input type="hidden" name="{name}" value='{value}'/>
             </div>""".format(inputs=self.generate_inputs(parsed), name=name, value=value)
        javascript = """
            function saveJSON() {
                var value = $('#id_%s option:selected').val();
                var obj = { format: value };
                $("input[name='%s']").val(JSON.stringify(obj));
            }
            saveJSON();
        """ % (name, name)
        return mark_safe(f"""
            {html}
            <script>
                {javascript}
            </script>""")


class RadioSelectSettings(Widget):
    @staticmethod
    def get_allowed_fields():
        return {'force_vertical'}

    def generate_input(self, name, title, parsed, info=None):
        value = parsed.get(name, False)

        input_str = f'''
            <input type="checkbox" name="{name}" id="{name}" onchange="saveJSON()" {"checked" if value else ""}>
            '''
        help_text = f'<div class="help">{info}</div>' if info else ''
        return f"""
            <div>
                <label for="{name}">{title}</label>
                {input_str}
                {help_text}
            </div>"""

    def generate_inputs(self, parsed):
        rows = [
            self.generate_input(
                'force_vertical', _('Force vertical layout'), parsed,
                info=_('Always display each radio button on its own separate row')),
        ]
        return "<br/>".join(rows)

    def render(self, name, value, attrs=None, renderer=None):
        parsed = {}
        try:
            parsed = json.loads(value)
        except Exception:
            pass

        html = """
             <div style="display:inline-grid" id="id_{name}">
                {inputs}
                <input type="hidden" name="{name}" value='{value}'/>
             </div>""".format(inputs=self.generate_inputs(parsed), name=name, value=value)
        javascript = """
            function saveJSON() {
                var value = $('#id_%s input').prop("checked");
                var obj = { force_vertical: value };
                $("input[name='%s']").val(JSON.stringify(obj));
            }
            saveJSON();
        """ % (name, name)
        return mark_safe(f"""
            {html}
            <script>
                {javascript}
            </script>""")


class DurationWidgetSettings(Widget):

    @staticmethod
    def get_allowed_fields():
        return {'years', 'months', 'days', 'hours', 'minutes', 'seconds', 'weeks_only'}

    def generate_input(self, name, title, parsed, info=None, default_value=False):
        value = parsed.get(name, default_value)
        on_change = "update_weeks_only()" if name != "weeks_only" else "update_other_checkboxes()"
        checked = "checked" if value else ""
        input_str = f'''
            <input type="checkbox" name="{name}" id="{name}" {checked} onchange="{on_change}"/>
        '''
        help_text = f'<div class="help">{info}</div>' if info else ''
        return f"""
            <div>
                <label for="{name}" style="width:175px">{title}</label>
                {input_str}
                {help_text}
            </div>"""

    def generate_inputs(self, parsed):
        is_empty = len(parsed) == 0
        rows = [
            self.generate_input('years', _("Display years input"), parsed, info=None, default_value=is_empty),
            self.generate_input('months', _("Display months input"), parsed, info=None, default_value=is_empty),
            self.generate_input('days', _("Display days input"), parsed, info=None, default_value=is_empty),
            self.generate_input('hours', _("Display hours input"), parsed, info=None, default_value=is_empty),
            self.generate_input('minutes', _("Display minutes input"), parsed, info=None, default_value=is_empty),
            self.generate_input('seconds', _("Display seconds input"), parsed, info=None, default_value=is_empty),
            '<span style="margin-bottom:5px;height:10px;border-bottom:1px solid #ccc"></span>',
            self.generate_input('weeks_only', _("Display only weeks input"), parsed),
        ]
        return "<br/>".join(rows)

    def render(self, name, value, attrs=None, renderer=None):
        parsed = {}
        try:
            parsed = json.loads(value)
        except Exception:
            pass

        html = """
             <div style="display:inline-grid" id="id_{name}">
                {inputs}
                <input type="hidden" name="{name}" value='{value}'/>
             </div>""".format(inputs=self.generate_inputs(parsed), name=name, value=value)
        javascript = """
            function saveJSON() {
                var inputs = $('#id_%s input[type=checkbox]');
                var obj = {};
                for (var i = 0; i < inputs.length; i++) {
                    obj[inputs[i].name] = inputs[i].checked;
                }
                $("input[name='%s']").val(JSON.stringify(obj));
            }

            function update_weeks_only() {
                var value = $('#id_%s input[type=checkbox][name!="weeks_only"]').filter(function(idx, el) { return el.checked;});
                if (value.length) {
                    $("#weeks_only").prop("checked", false);
                }
                saveJSON();
            }


            function update_other_checkboxes() {
                var value = $("#weeks_only").prop("checked");
                if (value) {
                    $('#id_%s input[type=checkbox][name!="weeks_only"]').prop("checked", !value);
                }
                saveJSON();
            }

            saveJSON();
        """ % (name, name, name, name)
        return mark_safe(f"""
            {html}
            <script>
                {javascript}
            </script>""")
