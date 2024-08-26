import json

from django.forms import Widget
from django.forms.renderers import get_default_renderer
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from .widgets import TimeWidget


class JSONWidgetSettings(Widget):
    def get_allowed_fields(self):
        raise NotImplementedError()

    def generate_inputs(self):
        raise NotImplementedError()

    def set_extra_js(self, javascript):
        self.javascript = javascript

    def parse_value(self, value):
        self.parsed = {}
        try:
            self.parsed = json.loads(value)
            self.parsed = {
                k: v
                for k, v in self.parsed.items()
                if k in self.get_allowed_fields()
            }
        except Exception:
            pass

    def _update_input(self, name, title, info=None, onchange=None):
        value = self.parsed.get(name, "")
        self.parsed[name] = {
            "name": name,
            "value": value,
            "title": title,
            "info": info,
            "onchange": onchange or "saveJSON()",
        }

    def generate_text_input(self, name, title, **kwargs):
        self._update_input(
            name, title, kwargs.get("info"), kwargs.get("onchange")
        )
        self.parsed[name]["input_type"] = "text"

    def generate_checkbox_input(self, name, title, **kwargs):
        self._update_input(
            name, title, kwargs.get("info"), kwargs.get("onchange")
        )
        self.parsed[name]["input_type"] = "checkbox"
        self.parsed[name]["checked"] = kwargs.get("checked")

    def generate_select_input(self, name, title, **kwargs):
        self._update_input(
            name, title, kwargs.get("info"), kwargs.get("onchange")
        )
        self.parsed[name]["input_type"] = "select"
        self.parsed[name]["options"] = kwargs.get("options", [])

    def render(self, name, value, attrs=None, renderer=None):
        self.parse_value(value)
        self.generate_inputs()
        if not renderer:
            renderer = get_default_renderer()
        context = {
            "settings": self.parsed,
            "name": name,
            "value": value,
        }
        if hasattr(self, "javascript"):
            context.update({"extra_js": mark_safe(self.javascript)})

        return renderer.render("widgets/widget_settings.html", context)


class SliderWidgetSettings(JSONWidgetSettings):
    def get_allowed_fields(self):
        return {"min", "max", "left_label", "right_label", "step"}

    def generate_inputs(self):
        (
            self.generate_text_input(
                "min",
                _("Min value"),
                info=_("leave empty if you want to use the CDE's min value"),
            ),
        )
        self.generate_text_input(
            "max",
            _("Max value"),
            info=_("leave empty if you want to use the CDE's max value"),
        )
        (self.generate_text_input("left_label", _("Left label")),)
        (self.generate_text_input("right_label", _("Right label")),)
        (self.generate_text_input("step", _("Step")),)


class TimeWidgetSettings(JSONWidgetSettings):
    def get_allowed_fields(self):
        return {"format"}

    def generate_input(self, name, title, info=None):
        value = self.parsed.get(name, "")
        selected_12hour = "selected" if value == TimeWidget.AMPM else ""
        selected_24hour = "selected" if value == TimeWidget.FULL else ""
        if not selected_12hour and not selected_24hour:
            selected_12hour = "selected"
        self.generate_select_input(
            name,
            title,
            info=info,
            options=[
                {
                    "value": TimeWidget.AMPM,
                    "selected": selected_12hour,
                    "text": "12-hour-format",
                },
                {
                    "value": TimeWidget.FULL,
                    "selected": selected_24hour,
                    "text": "24-hour-format",
                },
            ],
        )

    def generate_inputs(self):
        (
            self.generate_input(
                "format", _("Format"), _("Format of time: 12-hour or 24-hour")
            ),
        )


class RadioSelectSettings(JSONWidgetSettings):
    def get_allowed_fields(self):
        return {"force_vertical"}

    def generate_input(self, name, title, info=None):
        value = self.parsed.get(name, False)
        checked = "checked" if value else ""
        self.generate_checkbox_input(name, title, info=info, checked=checked)

    def generate_inputs(self):
        self.generate_input(
            "force_vertical",
            _("Force vertical layout"),
            info=_("Always display each radio button on its own separate row"),
        )


class DurationWidgetSettings(JSONWidgetSettings):
    def get_allowed_fields(self):
        return {
            "years",
            "months",
            "days",
            "hours",
            "minutes",
            "seconds",
            "weeks_only",
        }

    def generate_input(self, name, title, info=None, default_value=False):
        value = self.parsed.get(name, default_value)
        on_change = (
            "update_weeks_only()"
            if name != "weeks_only"
            else "update_other_checkboxes()"
        )
        checked = "checked" if value else ""
        self.generate_checkbox_input(
            name, title, info=info, checked=checked, onchange=on_change
        )

    def generate_inputs(self):
        is_empty = len(self.parsed) == 0
        (
            self.generate_input(
                "years",
                _("Display years input"),
                info=None,
                default_value=is_empty,
            ),
        )
        (
            self.generate_input(
                "months",
                _("Display months input"),
                info=None,
                default_value=is_empty,
            ),
        )
        (
            self.generate_input(
                "days",
                _("Display days input"),
                info=None,
                default_value=is_empty,
            ),
        )
        (
            self.generate_input(
                "hours",
                _("Display hours input"),
                info=None,
                default_value=is_empty,
            ),
        )
        (
            self.generate_input(
                "minutes",
                _("Display minutes input"),
                info=None,
                default_value=is_empty,
            ),
        )
        (
            self.generate_input(
                "seconds",
                _("Display seconds input"),
                info=None,
                default_value=is_empty,
            ),
        )
        (self.generate_input("weeks_only", _("Display only weeks input")),)

    def render(self, name, value, attrs=None, renderer=None):
        javascript = """
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
        """ % (name, name)
        self.set_extra_js(javascript)
        return super().render(name, value, attrs, renderer)
