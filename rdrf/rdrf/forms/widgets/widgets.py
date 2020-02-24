import base64
import datetime
import inspect
import logging
import math
import re
import sys
from operator import attrgetter

import pycountry
from django.forms import HiddenInput, MultiWidget, Textarea, Widget, widgets
from django.forms.utils import flatatt
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import PatientConsent
from rdrf.forms.dynamic.validation import iso_8601_validator
from rdrf.helpers.cde_data_types import CDEDataTypes

logger = logging.getLogger(__name__)


class BadCustomFieldWidget(Textarea):

    """
    Widget to use instead if a custom widget is defined and fails on creation
    """


class TextAreaWidget(Textarea):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}


class OtherPleaseSpecifyWidget(MultiWidget):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}

    def __init__(self, main_choices, other_please_specify_value, unset_value, attrs=None):
        self.main_choices = main_choices
        self.other_please_specify_value = other_please_specify_value
        self.unset_value = unset_value

        _widgets = (
            widgets.Select(attrs=attrs, choices=self.main_choices),
            widgets.TextInput(attrs=attrs)
        )

        super(OtherPleaseSpecifyWidget, self).__init__(_widgets, attrs)

    def format_output(self, rendered_widgets):
        output = '<BR>'.join(rendered_widgets)
        return output

    def decompress(self, value):
        """
        :param value: value from db or None
        :return: values to be supplied to the select widget and text widget:
        If no value, we show unset for dropdown and nothing in text
        If a value is supplied outside of the dropdown range we provide it to the text box
        and set the select widget to the indicator for "Other please specify"
        otherwise we provide the selected value to the select box and an empty string to
        the textbox
        """
        if not value:
            return [self.unset_value, ""]

        if value not in [choice[0] for choice in self.main_choices]:
            return [self.other_please_specify_value, value]
        else:
            return [value, ""]

    def value_from_datadict(self, data, files, name):
        if name in data:
            return data[name]
        else:
            option_selected = data.get(name + "_0", self.unset_value)
            text_entered = data.get(name + "_1", "")

            if option_selected == self.other_please_specify_value:
                return text_entered
            else:
                return option_selected

    def render(self, name, value, attrs=None, renderer=None):
        select_id = "id_" + name + "_0"
        specified_value_textbox_id = "id_" + name + "_1"
        script = """
        <script>
            (function() {
                $("#%s").bind("change", function() {
                    if ($(this).val() == "%s") {
                        $("#%s").show();
                    }
                    else {
                        $("#%s").hide();
                    }
                });
            })();
            (function(){ $("#%s").change();})();

        </script>
        """ % (select_id, self.other_please_specify_value, specified_value_textbox_id, specified_value_textbox_id, select_id)

        return super(OtherPleaseSpecifyWidget, self).render(name, value, attrs) + script


class CalculatedFieldWidget(widgets.TextInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.CALCULATED}

    def __init__(self, script, attrs={}):
        attrs['readonly'] = 'readonly'
        self.script = script
        super(CalculatedFieldWidget, self).__init__(attrs=attrs)

    def render(self, name, value, attrs, renderer=None):
        # attrs['readonly'] = 'readonly'
        return super(CalculatedFieldWidget, self).render(name, value, attrs) + self.script


class LookupWidget(widgets.TextInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}

    def render(self, name, value, attrs, renderer=None):
        return """
            <input type="text" name="%s" id="id_%s" value="%s">
            <script type="text/javascript">
                $("#id_%s").keyup(function() {
                    lookup($(this), '%s');
                });
            </script>
        """ % (name, name, value or '', name, self.SOURCE_URL)


class DateWidget(widgets.TextInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.DATE}

    def render(self, name, value, attrs, renderer=None):
        def just_date(value):
            if value:
                if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                    return date_format(value)
                else:
                    return value
            else:
                return value
        return mark_safe("""
            <input type="text" name="%s" id="id_%s" value="%s" class="datepicker">
        """ % (name, name, just_date(value) or ''))


class CountryWidget(widgets.Select):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}

    def render(self, name, value, attrs, renderer=None):
        final_attrs = self.build_attrs(attrs, {
            "name": name,
            "class": "form-control",
            "onchange": "select_country(this)",
        })
        output = [format_html("<select{}>", flatatt(final_attrs))]
        empty_option = "<option value=''>---------</option>"
        output.append(empty_option)
        for country in sorted(pycountry.countries, key=attrgetter('name')):

            if value == country.alpha_2:
                output.append("<option value='%s' selected>%s</option>" %
                              (country.alpha_2, country.name))
            else:
                output.append("<option value='%s'>%s</option>" % (country.alpha_2, country.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class StateWidget(widgets.Select):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}

    def render(self, name, value, attrs, renderer=None):
        try:
            state = pycountry.subdivisions.get(code=value)
        except KeyError:
            state = None

        if state is not None:
            country_states = pycountry.subdivisions.get(country_code=state.country.alpha_2)
        else:
            country_states = []

        final_attrs = self.build_attrs(attrs, {
            "name": name,
            "class": "form-control",
        })
        output = [format_html("<select{}>", flatatt(final_attrs))]
        empty_option = "<option value=''>---------</option>"
        output.append(empty_option)
        for state in country_states:
            if value == state.code:
                output.append("<option value='%s' selected>%s</option>" %
                              (state.code, state.name))
            else:
                output.append("<option value='%s'>%s</option>" % (state.code, state.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class ParameterisedSelectWidget(widgets.Select):
    """
    A dropdown that can retrieve values dynamically from the registry that "owns" the form containing the widget.
    This is an abstract class which must be subclassed.
    NB. The field factory is responsible for supplying the registry model to the widget instance  at
    form creation creation time.
    """

    def __init__(self, *args, **kwargs):
        self._widget_parameter = kwargs['widget_parameter']
        del kwargs['widget_parameter']
        self._widget_context = kwargs['widget_context']
        del kwargs['widget_context']
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs, renderer=None):
        if not value:
            value = self.attrs.get('default', '')

        # final_attrs = dict(self.attrs, name=name)

        final_attrs = self.build_attrs(attrs, {
            "name": name,
            "class": "form-control",
        })
        output = [format_html("<select{}>", flatatt(final_attrs))]
        output.append("<option value='---'>---------</option>")
        for code, display in self._get_items():
            if value == code:
                output.append("<option value='%s' selected>%s</option>" % (code, display))
            else:
                output.append("<option value='%s'>%s</option>" % (code, display))
        output.append("</select>")
        return mark_safe('\n'.join(output))

    def _get_items(self):
        raise NotImplementedError(
            "subclass responsibility - it should return a list of pairs: [(code, display), ...]")


class StateListWidget(ParameterisedSelectWidget):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}

    def render(self, name, value, attrs, renderer=None):
        country_states = pycountry.subdivisions.get(
            country_code=self._widget_context['questionnaire_context'].upper())
        output = ["<select class='form-control' id='%s' name='%s'>" % (name, name)]
        empty_option = "<option value='---'>---------</option>"
        output.append(empty_option)
        for state in country_states:
            if value == state.code:
                output.append("<option value='%s' selected>%s</option>" %
                              (state.code, state.name))
            else:
                output.append("<option value='%s'>%s</option>" % (state.code, state.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class DataSourceSelect(ParameterisedSelectWidget):
    """
    A parametrised select that retrieves values from a data source specified in the parameter
    """

    def _get_items(self):
        """
        :return: [(code, value), ... ] pairs from the metadata json from the registry context
        """
        from rdrf.forms.widgets import datasources
        if hasattr(datasources, self._widget_parameter):
            datasource_class = getattr(datasources, self._widget_parameter)
            datasource = datasource_class(self._widget_context)
            return list(datasource.values())


class PositiveIntegerInput(widgets.TextInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.INTEGER}

    def render(self, name, value, attrs, renderer=None):
        min_value, max_value = self._get_value_range(name)

        return """
            <input type="number" name="%s" id="id_%s" value="%s" min="%s" max="%s">
        """ % (name, name, value, min_value, max_value)

    def _get_value_range(self, cde_name):
        cde_code = cde_name.split("____")[2]
        cde = CommonDataElement.objects.get(code=cde_code)
        max_value = cde.max_value if cde.max_value else 2147483647
        min_value = cde.min_value if cde.min_value else 0
        return min_value, max_value


class RadioSelect(widgets.RadioSelect):
    template_name = "rdrf_cdes/radio_select.html"

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.RANGE}

    def _get_column_width(self):
        no_of_choices = len(self.choices)
        longest_choice_text = max(len(choice[1]) for choice in self.choices)
        has_long_text = longest_choice_text > 50
        has_short_texts_only = longest_choice_text < 5

        cols_per_row = 3
        if has_long_text:
            cols_per_row = 4
        elif has_short_texts_only and no_of_choices <= 3:
            cols_per_row = 2

        return f"col-xs-12 col-sm-{math.ceil((cols_per_row + 2) / 2) * 2} col-md-{cols_per_row}"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        force_vertical = self.attrs.pop("force_vertical") if "force_vertical" in self.attrs else False
        context["column_width"] = "col-sm-12" if force_vertical else self._get_column_width()
        return context


class ReadOnlySelect(widgets.Select):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.RANGE}

    def render(self, name, value, attrs=None, renderer=None):
        html = super(ReadOnlySelect, self).render(name, value, attrs)
        return self._make_label(html) + self._make_hidden_field(name, value, attrs)

    def _make_hidden_field(self, name, value, attrs):
        return """<input type="hidden" id="%s" name="%s" value="%s"/>""" % (
            attrs['id'], name, value)

    def _make_label(self, html):
        import re
        html = html.replace("\n", "")
        pattern = re.compile(r'.*selected=\"selected\">(.*?)</option>.*')
        m = pattern.match(html)
        if m:
            option_display_text = m.groups(1)[0]
            return """<span class="label label-default">%s</span>""" % option_display_text
        else:
            return html


class MultipleFileInput(Widget):
    """
    This widget combines multiple file inputs.
    The files are taken and returned as a list.

    It relies on javascript in form.js, which uses styling from
    rdrf.css.
    """

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.FILE}

    @staticmethod
    def input_name(base_name, i):
        return "%s_%s" % (base_name, i)

    number_pat = re.compile(r"_(\d+)$")

    @classmethod
    def input_index(cls, name, field_name, suffix=""):
        "Cuts the index part out of an form input name"
        if field_name.startswith(name) and field_name.endswith(suffix):
            chop = -len(suffix) if suffix else None
            m = cls.number_pat.match(field_name[len(name):chop])
            if m:
                return int(m.group(1))
        return None

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        items = self._render_each(name, value, attrs)

        elements = ("<div class=\"col-xs-12 multi-file\">%s</div>" % item for item in items)
        return """
            <div class="row multi-file-widget" id="%s_id">
              %s
            </div>
        """ % (name, "\n".join(elements))

    class TemplateFile(object):
        url = ""

        def __str__(self):
            return ""

    def _render_base(self, name, value, attrs, index):
        input_name = self.input_name(name, index)
        base = widgets.ClearableFileInput().render(input_name, value, attrs)
        hidden = HiddenInput().render(input_name + "-index", index, {})
        return "%s\n%s" % (base, hidden)

    def _render_each(self, name, value, attrs):
        return [self._render_base(name, self.TemplateFile(), attrs, "???")] + [
            self._render_base(name, val, attrs, i)
            for (i, val) in enumerate(value or [])
        ]

    def value_from_datadict(self, data, files, name):
        """
        Gets file input value from each sub-fileinput.
        """
        base_widget = widgets.ClearableFileInput()

        indices = (self.input_index(name, n, "-index") for n in data)
        clears = (self.input_index(name, n, "-clear") for n in data)
        uploads = (self.input_index(name, n) for n in files)

        nums = sorted(set(indices).union(clears).union(uploads) - set([None]))

        return [base_widget.value_from_datadict(data, files, self.input_name(name, i))
                for i in nums]


class ValueWrapper:
    def __init__(self, value):
        self.value = value
        self.url = value.url
        # capture the original uploaded filename here
        self.filename = None

    def __str__(self):
        return self.filename


class ConsentFileInput(widgets.ClearableFileInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.FILE}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)

        def wrap(value):
            """
            Wrap the incoming value so we can display
            the original filename properly
            """
            try:
                if hasattr(value, 'url'):
                    patient_consent = PatientConsent.objects.get(form=value)
                    filename = patient_consent.filename
                    vw = ValueWrapper(value)
                    vw.filename = filename
                    return vw
                else:
                    return ''
            except ValueError:
                # was getting this on the Clear operation
                # if we catch here, the clearing still works ...
                return ''

        context['widget'].update({
            'checkbox_name': checkbox_name,
            'checkbox_id': checkbox_id,
            'is_initial': self.is_initial(value),
            'input_text': self.input_text,
            'value': wrap(value),
            'initial_text': self.initial_text,
            'clear_checkbox_label': self.clear_checkbox_label,
        })

        return context


class SliderWidget(widgets.TextInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.INTEGER, CDEDataTypes.FLOAT}

    def render(self, name, value, attrs=None, renderer=None):
        if not (value and isinstance(value, float) or isinstance(value, int)):
            value = 0

        left_label = self.attrs.pop("left_label") if "left_label" in self.attrs else ''
        right_label = self.attrs.pop("right_label") if "right_label" in self.attrs else ''

        if self.attrs:
            widget_attrs = ",\n".join("\"{}\":{}".format(k, v) for k, v in self.attrs.items()) + ","
        else:
            widget_attrs = ''

        context = f"""
             <div>
                <div style="float:left; margin-right:20px;"><b>{left_label}</b></div>
                <div style="float:left">
                    <input type="hidden" id="{attrs['id']}" name="{name}" value="{value}"/>
                </div>
                <div style="float:left;margin-left:20px;"><b>{right_label}</b></div>
             </div>
             <br/>
             <script>
                 $(function() {{
                     $( "#{attrs['id']}" ).bootstrapSlider({{
                         tooltip: 'always',
                         value: '{value}',
                         {widget_attrs}
                         slide: function( event, ui ) {{
                             $( "#{attrs['id']}" ).val( ui.value );
                         }}
                     }});
                     // Set z-index to 0 for slider tooltip so it's not displayed through
                     // form headers
                     $(".slider .tooltip").css("z-index","0");
                 }});
             </script>
            """

        return context


class SignatureWidget(widgets.TextInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.STRING}

    def render(self, name, value, attrs=None, renderer=None):

        has_value = value and value != 'None'
        encoded_default_value = base64.b64encode('{"width":1, "data":[]}'.encode('utf-8')).decode('utf-8')
        set_value = f"set_value('{value}');" if has_value else f"set_value('{encoded_default_value}');"
        # We're hiding the "Undo last stroke" button, because it looks strange when showing an already signed form
        hide_undo_btn = "$sigdiv.find('input[type=\"button\"][value=\"Undo last stroke\"]').hide()" if has_value else ""
        clear_signature_text = _('Clear signature')
        html_value = value if has_value else encoded_default_value

        html = f"""
            <div id="signature" style="border: 1px solid black">
            </div>
            <input type="hidden" name="{name}" value='{html_value}'/>
            <div class="pull-right">
                <a class="btn btn-default" onclick="reset_signature();">
                    <span class="glyphicon glyphicon-remove"></span> """ + clear_signature_text + """
                </a>
            </div>
        """

        javascript = """
                var $sigdiv = $("#signature").jSignature({'UndoButton':true});
                var disabled = false;
                $sigdiv.change(function(e) {
                    var isModified =  $sigdiv.jSignature('isModified');
                    if (isModified) {
                        var has_signature = $sigdiv.jSignature('getSettings').data.length > 0;
                        var value = has_signature ? $sigdiv.jSignature('getData', 'native') : [];
                        var obj = {
                            width:$("#signature").width(),
                            data:value
                        }
                        $("input[name='""" + name + """']").val(btoa(JSON.stringify(obj)));
                    }
                    if (disabled) {
                        set_disabled_background();
                        $sigdiv.find('input[type="button"][value="Undo last stroke"]').hide();
                    }

                });

                function set_disabled_background() {
                    $("#signature div").css('background-color','lightgray');
                    $(".jSignature").css('background-color','lightgray');
                    $("#signature").css('background-color', 'lightgray');
                }

                function disable_signature() {
                    disabled = true;
                    $sigdiv.jSignature('disable', true);
                    set_disabled_background();
                }

                function reset_signature() {
                    $sigdiv.jSignature('reset');
                    $("input[name='""" + name + """']").val('""" + encoded_default_value + """');
                    return false;
                }

                // function taken from: https://github.com/brinley/jSignature/blob/master/src/jSignature.js#L658
                function scale_data(data, scale){
                    var newData = [];
                    var o, i, l, j, m, stroke;
                    for ( i = 0, l = data.length; i < l; i++) {
                        stroke = data[i];

                        o = {'x':[],'y':[]};

                        for ( j = 0, m = stroke.x.length; j < m; j++) {
                            o.x.push(stroke.x[j] * scale);
                            o.y.push(stroke.y[j] * scale);
                        }

                        newData.push(o);
                    }
                    return newData;
                }

                function set_value(input) {
                    decoded = atob(input);
                    var obj = JSON.parse(decoded);
                    var current_width = $("#signature").width();
                    var scale = current_width * 1.0 / obj.width;
                    var data = scale_data(obj.data, scale);
                    $sigdiv.jSignature('setData', data, 'native');
                }
        """

        return mark_safe(f"""
            {html}
            <script>
                {javascript}
                {set_value}
                {hide_undo_btn}
            </script>
         """)


class AllConsentWidget(widgets.CheckboxInput):

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.BOOL}

    def render(self, name, value, attrs=None, renderer=None):

        base = super().render(name, value, attrs, renderer)
        javascript = """
                $("[name='""" + name + """']").change(function(e) {
                    if (this.checked) {
                        $("[name^='customconsent']").prop("checked", this.checked);
                    }
                })
        """
        return mark_safe(f"""
            {base}
            <script>
                {javascript}
            </script>
         """)


class TimeWidget(widgets.TextInput):
    AMPM = "12hour"
    FULL = "24hour"

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.TIME}

    def _parse_value(self, value, fmt):
        '''
        Parse the input time and transform it to the format
        the timepicki widget expects
        '''

        def validate(hr, min, fmt):
            try:
                max_hr = 12 if fmt == self.AMPM else 23
                return 0 <= int(hr) <= max_hr and 0 <= int(min) <= 59
            except ValueError:
                return False

        NO_VALUE = ('', [])
        if not value:
            return NO_VALUE

        m = re.match("(\\d{2}):(\\d{2})\\s*(AM|PM)?", value)
        if not m:
            return NO_VALUE
        parts = m.groups()
        hour, minute, meridian = parts
        if not validate(hour, minute, self.AMPM if meridian else self.FULL):
            return NO_VALUE
        hour, minute = int(hour), int(minute)

        if fmt == self.FULL:
            if meridian == 'PM':
                hour = 12 if hour == 12 else hour + 12
        else:
            if hour == 0:
                hour = 12
            elif hour > 12:
                hour = hour - 12
                meridian = 'PM'
            meridian = meridian or 'AM'

        formatted_time = f'{hour:02d}:{minute:02d}'
        start_time = [hour, minute]
        if fmt == self.AMPM:
            formatted_time += f' {meridian}'
            start_time.append(meridian)

        return formatted_time, start_time

    def render(self, name, value, attrs=None, renderer=None):
        fmt = self.attrs.pop("format") if "format" in self.attrs else self.AMPM
        value, start_time = self._parse_value(value, fmt)
        html = f'''
            <input id="id_{name}" type="text" name="{name}" value="{value}"/>
        '''
        set_time_str = f", start_time:{start_time}" if start_time else ""
        change_handler = '''
            on_change: function() { $("#main-form").trigger('change'); }
        '''

        if fmt == self.AMPM:
            attrs = f"{{ {change_handler}, $show_meridian:true, min_hour_value:1, max_hour_value:12 {set_time_str}}}"
        else:
            attrs = f"{{ {change_handler}, show_meridian:false, min_hour_value:0, max_hour_value:23 {set_time_str}}}"

        js = f'''
            $("#id_{name}").timepicki({attrs});
            $("#id_{name}").addClass("form-control");
            $(".meridian .mer_tx input").css("padding","0px"); // fix padding for meridian display
        '''
        return f'''
            {html}
            <script>
                {js}
            </script>
        '''


class DurationWidget(widgets.TextInput):
    """
    Time duration picker component used:
    https://digaev.github.io/jquery-time-duration-picker/
    """

    @staticmethod
    def usable_for_types():
        return {CDEDataTypes.DURATION}

    def render(self, name, value, attrs=None, renderer=None):
        if not value or not iso_8601_validator(value):
            value = "PT0S"  # default ISO-8601 duration

        return f'''
            <input id="id_{name}_text" type="text" value="{value}" readonly/>
            <input id="id_{name}_duration" type="hidden" name="{name}" value="{value}"/>
            <script>
                $("#id_{name}_text").timeDurationPicker({{
                    css: {{
                        "width":"200px"
                    }},
                    seconds: true,
                    defaultValue: function() {{
                        return $("#id_{name}_duration").val();
                    }},
                    onSelect: function(element, seconds, duration, text) {{
                        $("#id_{name}_duration").val(duration);
                        $("#id_{name}_text").val(text);
                        $("#main-form").trigger('change');
                        $("#id_{name}_duration").trigger('change');
                    }}
                }});
                $("#id_{name}_text").addClass("form-control");
            </script>
        '''


def _all_widgets():
    EXCLUDED_WIDGET_NAMES = ['Widget', 'HiddenInput']

    def is_widget(cls):
        return issubclass(cls, Widget)

    def is_name_ok(name):
        return name not in EXCLUDED_WIDGET_NAMES

    return ((name, cls) for name, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass) if is_widget(cls) and is_name_ok(name))


def get_all_widgets():
    return [name for name, _ in _all_widgets()]


def get_widgets_for_data_type(data_type):
    def has_valid_type(cls):
        if not hasattr(cls, 'usable_for_types'):
            return False
        return data_type in cls.usable_for_types()

    return [name for name, cls in _all_widgets() if has_valid_type(cls)]
