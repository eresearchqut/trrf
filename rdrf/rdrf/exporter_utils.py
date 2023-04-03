import io
import logging
import zipfile
from datetime import datetime
from functools import reduce

from django.http import HttpResponse

from rdrf.services.io.defs.exporter import Exporter, ExportType

logger = logging.getLogger(__name__)


def partial_descriptor_str(export_type):
    return '_partial' if export_type == ExportType.PARTIAL else ''


def write_export_single_file(yaml_data, registry, export_type):
    if yaml_data is None:
        return

    export_time = str(datetime.now())

    yaml_export_filename = f"export_{export_time}_{registry.name}{partial_descriptor_str(export_type)}.yaml"

    response = HttpResponse(yaml_data, content_type='text/yaml')
    response['Content-Disposition'] = 'attachment; filename="%s"' % yaml_export_filename

    return response


def write_export_zip(exports, export_type):
    registries = []

    zip_stream = io.BytesIO()

    with zipfile.ZipFile(zip_stream, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
        for export_data, registry in exports:
            registries.append(registry)
            archive.writestr(f'{registry.code}{partial_descriptor_str(export_type)}.yaml', export_data)

    response = HttpResponse(zip_stream.getvalue(), content_type='application/zip')
    export_time = str(datetime.now())
    name = "export_" + export_time + "_" + reduce(lambda x, y: x + '_and_' + y, [r.code for r in registries]) + ".zip"
    response['Content-Disposition'] = 'attachment; filename="%s"' % name

    return response


def write_response(exports, export_type):
    if len(exports) == 1:
        export_data, registry = exports[0]
        return write_export_single_file(export_data, registry, export_type)
    else:
        return write_export_zip(exports, export_type)


def export_registries(registries):
    exports = []

    export_type = ExportType.REGISTRY_PLUS_CDES

    for registry in registries:
        exporter = Exporter(registry_model=registry)
        export_data, errors = exporter.export_yaml(export_type=export_type)

        if errors:
            return errors, registry.name
        else:
            logger.info("Exported YAML Data for %s OK" % registry.name)
            exports.append((export_data, registry))

    return write_response(exports, export_type)


def _group_objs_by_registry(objs):
    registry_groups = {}

    for item in objs:
        registry_groups.setdefault(item.registry, []).append(item)

    return registry_groups.items()


def _export_cascading_form_definition(registry, context_form_groups=None, forms=None, sections=None, cdes=None):
    non_null_args = [arg for arg in [context_form_groups, forms, sections, cdes] if arg]
    assert len(non_null_args) == 1, f'Expected 1 form definition part to be provided, got {len(non_null_args)}'

    export_definition = {}

    if context_form_groups:
        export_definition['context_form_groups'] = context_form_groups
        forms = set(form
                    for cfg in context_form_groups
                    for form in cfg.forms)

    if forms:
        export_definition['forms'] = forms
        sections = set(section
                       for form in forms
                       for section in form.section_models)

    if sections:
        export_definition['sections'] = sections
        cdes = set(cde
                   for section in sections
                   for cde in section.cde_models)

    if cdes:
        export_definition['cdes'] = cdes

    return Exporter(registry_model=registry).partial_export(export_definition)


def export_context_form_groups(context_form_groups):
    exports = []

    for registry, context_form_groups in _group_objs_by_registry(context_form_groups):
        export_data = _export_cascading_form_definition(registry, context_form_groups=context_form_groups)
        exports.append((export_data, registry))

    return write_response(exports, ExportType.PARTIAL)


def export_forms(forms):
    exports = []

    for registry, forms in _group_objs_by_registry(forms):
        export_data = _export_cascading_form_definition(registry, forms=forms)
        exports.append((export_data, registry))

    return write_response(exports, ExportType.PARTIAL)


def export_registry_dashboards(dashboards):
    exports = []

    for registry, dashboards in _group_objs_by_registry(dashboards):
        export_data = Exporter(registry_model=registry).partial_export({'registry_dashboards': dashboards})
        exports.append((export_data, registry))

    return write_response(exports, ExportType.PARTIAL)
