import inspect
import rdrf.forms.widgets.widgets as w

FILTERED_WIDGET_NAMES = ['Widget', 'HiddenInput']


def get_widgets_for_data_type(data_type):
    def is_widget(obj):
        return issubclass(obj, w.Widget)

    def has_valid_type(obj, name):
        if hasattr(obj, 'get_allowed_fields'):
            return False
        if hasattr(obj, 'usable_for_types'):
            return data_type in obj.usable_for_types()
        return False

    def has_valid_name(name):
        return name not in FILTERED_WIDGET_NAMES

    def is_valid_obj(name, obj):
        return (
            inspect.isclass(obj) and is_widget(obj) and has_valid_name(name) and has_valid_type(obj, name)
        )

    return [{
        'name': name,
        'value': name
    } for name, obj in inspect.getmembers(w) if is_valid_obj(name, obj)]
