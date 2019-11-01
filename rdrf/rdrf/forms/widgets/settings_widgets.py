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