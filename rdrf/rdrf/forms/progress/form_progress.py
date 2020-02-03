import logging
import math

from django.urls import reverse
from django.templatetags.static import static

from rdrf.forms.dsl.code_evaluator import CodeEvaluator
from rdrf.helpers.utils import de_camelcase, parse_iso_datetime
from rdrf.models.definition.models import ClinicalData
from rdrf.helpers.registry_features import RegistryFeatures

from ..dynamic.value_fetcher import DynamicValueFetcher

logger = logging.getLogger(__name__)


class ProgressType:
    DIAGNOSIS = "diagnosis"


class ProgressMetric:
    PROGRESS = "progress"
    CURRENT = "current"
    HAS_DATA = "has_data"
    CDES_STATUS = "cdes_status"
    REQUIRED = "required"
    FILLED = "filled"
    PERCENTAGE = "percentage"

    @classmethod
    def valid_metric(cls, metric_name):
        return any(
            metric_name.endswith(metric) for metric in
            [cls.PROGRESS, cls.CURRENT, cls.HAS_DATA]
        )

    def __init__(self, metric):
        self.metric = metric
        if not self.valid_metric(metric):
            raise FormProgressError("Unknown metric: %s" % metric)

    def default_value(self):
        if self.metric.endswith(ProgressMetric.PROGRESS):
            return 0
        return False


class ModelTaggedMetric:

    ALLOWED_METRICS = [ProgressMetric.PROGRESS, ProgressMetric.CURRENT, ProgressMetric.CDES_STATUS]

    def __init__(self, form_model, metric_name):
        self.form_model = form_model
        self.metric_name = metric_name
        if metric_name not in ModelTaggedMetric.ALLOWED_METRICS:
            raise FormProgressError("Unknown metric: %s" % metric_name)

    def key_name(self):
        return f"{self.form_model.name}_form_{self.metric_name}"

    def default_value(self):
        if self.metric_name == ProgressMetric.PROGRESS:
            return {}
        elif self.metric_name == ProgressMetric.CURRENT:
            return False
        elif self.metric_name == ProgressMetric.CDES_STATUS:
            return {
                cde_model.name: False for cde_model in self.form_model.complete_form_cdes.all()
            }


class ProgressCalculationError(Exception):
    pass


def nice_name(name):
    try:
        return de_camelcase(name)
    except BaseException:
        return name


def percentage(a, b):
    if b > 0:
        return int(math.floor(100.00 * float(a) / float(b)))
    else:
        return 100


class FormProgressError(Exception):
    pass


class FormProgressCalculator:

    def __init__(self, registry_model, form_model, dynamic_data, progress_cdes_map):
        self.registry_model = registry_model
        self.form_model = form_model
        self.dynamic_data = dynamic_data
        self.progress_cdes_map = progress_cdes_map
        self.form_progress_dict = {}
        self.form_currency = False
        self.form_has_data = False
        self.form_cdes_status = {}

    def _get_form_by_name(self):
        model_name = self.form_model.name
        forms_by_name = [
            form_model for form_model in self.registry_model.forms
            if not form_model.is_questionnaire and form_model.name == model_name
        ]
        return forms_by_name[0] if forms_by_name else None

    def _get_hidden_cdes(self, form_model):
        if form_model and form_model.conditional_rendering_rules:
            code_eval = CodeEvaluator(form_model, self.dynamic_data)
            return code_eval.determine_hidden_cdes()
        return set()

    def _get_progress_cdes(self):
        cdes_required = self.progress_cdes_map[self.form_model.name]
        form_model = self._get_form_by_name()
        if form_model:
            hidden_cdes = self._get_hidden_cdes(form_model)
            cdes_required = set(cdes_required) - hidden_cdes

            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    if cde_model.code in cdes_required:
                        yield section_model, cde_model

    def _get_num_items(self, section_model):
        if not section_model.allow_multiple:
            return 1
        if self.dynamic_data is None:
            return 0
        if "forms" not in self.dynamic_data:
            return 0
        for form_dict in self.dynamic_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                # for multisections the cdes field contains a list
                # of items, each of which is a list of cde dicts
                # containing the values for each item
                cdes = [
                    section_dict["cdes"] for section_dict in form_dict["sections"]
                    if section_dict["code"] == section_model.code
                ]
                return len(cdes[0]) if cdes else 0
        return 0

    def _calculate_form_progress(self):
        result = {
            ProgressMetric.REQUIRED: 0,
            ProgressMetric.FILLED: 0,
            ProgressMetric.PERCENTAGE: 0
        }

        value_fetcher = DynamicValueFetcher(self.dynamic_data)

        for section_model, cde_model in self._get_progress_cdes():
            result[ProgressMetric.REQUIRED] += self._get_num_items(section_model)

            try:
                values = value_fetcher.find_cde_values(self.form_model.name, section_model.code, cde_model.code)
                result[ProgressMetric.FILLED] += len([value for value in values if value])
            except Exception as ex:
                logger.error(
                    "Error getting value for %s %s: %s" %
                    (section_model.code, cde_model.code, ex))

        if result[ProgressMetric.REQUIRED] > 0:
            result[ProgressMetric.PERCENTAGE] = int(
                100.00 * (float(result[ProgressMetric.FILLED]) / float(result[ProgressMetric.REQUIRED])))
        else:
            result[ProgressMetric.PERCENTAGE] = 0

        return result

    def _calculate_form_currency(self):
        from datetime import timedelta, datetime
        form_timestamp_key = "%s_timestamp" % self.form_model.name
        one_year_ago = datetime.now() - timedelta(weeks=52)

        if self.dynamic_data is None:
            return False

        if form_timestamp_key in self.dynamic_data:
            timestamp = parse_iso_datetime(self.dynamic_data[form_timestamp_key])
            if timestamp >= one_year_ago:
                return True

        return False

    def _form_section_traversal(self):
        if self.dynamic_data is None:
            yield {}
        else:
            for form_dict in self.dynamic_data['forms']:
                if form_dict["name"] == self.form_model.name:
                    for section_dict in form_dict["sections"]:
                        if not section_dict["allow_multiple"]:
                            for cde_dict in section_dict["cdes"]:
                                yield cde_dict
                        else:
                            for item in section_dict["cdes"]:
                                for cde_dict in item:
                                    yield cde_dict

    def _calculate_form_has_data(self):
        for cde_dict in self._form_section_traversal():
            if not cde_dict:
                return False
            if cde_dict["value"]:
                return True

    def _calculate_form_cdes_status(self):
        if self.dynamic_data is None:
            return {}

        required_cdes = self.progress_cdes_map[self.form_model.name]
        form_model = self._get_form_by_name()
        if form_model:
            hidden_cdes = self._get_hidden_cdes(form_model)
            required_cdes = set(required_cdes) - hidden_cdes

        cdes_status = {code: False for code in required_cdes}

        code_values_dict = {}
        for cde_dict in self._form_section_traversal():
            if cde_dict and "code" in cde_dict:
                code_values_dict[cde_dict["code"]] = True
        cdes_status.update(code_values_dict)
        return cdes_status

    def calculate_progress(self):
        self.form_progress_dict = self._calculate_form_progress()
        self.form_currency = self._calculate_form_currency()
        self.form_has_data = self._calculate_form_has_data()
        self.form_cdes_status = self._calculate_form_cdes_status()

    def progress_as_dict(self):
        return {
            ProgressMetric.PROGRESS: self.form_progress_dict,
            ProgressMetric.CURRENT: self.form_currency,
            ProgressMetric.HAS_DATA: self.form_has_data,
            ProgressMetric.CDES_STATUS: self.form_cdes_status
        }


class FormProgress:

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.progress_data = {}
        self.progress_collection = self._get_progress_collection()
        self.progress_cdes_map = self._build_progress_map()
        self.loaded_data = None
        self.current_patient = None
        self.context_model = None
        # if the following is true, the "type" of patient affects what forms
        # are applicable/presented/counted:
        self.uses_patient_types = self.registry_model.has_feature(RegistryFeatures.PATIENT_TYPES)
        if self.uses_patient_types:
            self.patient_type_form_map = self.registry_model.metadata["patient_types"]
        else:
            self.patient_type_form_map = None

    def _set_current(self, patient_model):
        if self.current_patient is None:
            self.current_patient = patient_model
            self.reset()
        else:
            if self.current_patient.pk != patient_model.pk:
                self.current_patient = patient_model
                self.reset()

    def _get_progress_collection(self):
        return ClinicalData.objects.collection(self.registry_model.code, ProgressMetric.PROGRESS)

    def _get_progress_metadata(self):
        try:
            metadata = self.registry_model.metadata
            if ProgressMetric.PROGRESS in metadata:
                pm = metadata[ProgressMetric.PROGRESS]
            else:
                # default behaviour - this is the old behaviour
                groups_dict = {ProgressType.DIAGNOSIS: []}
                for form_model in self.registry_model.forms:
                    groups_dict[ProgressType.DIAGNOSIS].append(form_model.name)
                pm = groups_dict

            # if the registry uses patient types , we need to prefilter the list
            if self.uses_patient_types:
                return self._get_applicable_form_progress_dict(pm)
            else:
                return pm

        except Exception as ex:
            logger.error(
                "Error getting progress metadata for registry %s: %s" %
                (self.registry_model.code, ex))
            return {}

    def _build_progress_map(self):
        # maps form names to sets of required cde codes
        result = {}
        for form_model in self.registry_model.forms:
            if not form_model.is_questionnaire:
                result[form_model.name] = set([cde_model.code for cde_model in
                                               form_model.complete_form_cdes.all()])
        return result

    def _get_applicable_form_progress_dict(self, unfiltered_dict):
        filtered_dict = {}
        if not self.current_patient:
            return unfiltered_dict
        else:
            patient_type = self.current_patient.patient_type
            if not patient_type:
                patient_type = "default"

            applicable_forms = self.registry_model.metadata["patient_types"][patient_type]["forms"]
            for group_name in unfiltered_dict:
                filtered_dict[group_name] = [form_name for form_name in unfiltered_dict[group_name]
                                             if form_name in applicable_forms]
            return filtered_dict

    def _applicable(self, form_model):
        if self.patient_type_form_map:
            if self.current_patient:
                if not self.current_patient.patient_type:
                    applicable_forms = self.patient_type_form_map["default"]["forms"]
                else:
                    applicable_forms = self.patient_type_form_map[self.current_patient.patient_type]["forms"]
                applicable_to_form = form_model.applicable_to(self.current_patient)
                return form_model.name in applicable_forms and applicable_to_form
        else:
            if self.current_patient:
                return form_model.applicable_to(self.current_patient)
        return True

    def _calculate(self, dynamic_data, patient_model=None):

        logger.info("calculating progress")
        if patient_model is not None:
            self.current_patient = patient_model

        progress_metadata = self._get_progress_metadata()
        if not progress_metadata:
            return

        groups_progress = {}
        forms_progress = {}

        existing_patient_data = patient_model.get_dynamic_data(self.registry_model) if patient_model else {}
        existing_form_dyn_data = {
            el['name']: {"forms": [el]} for el in existing_patient_data['forms']
        } if existing_patient_data else {}

        forms = dynamic_data.get("forms", [])
        current_form_name = forms[0]["name"] if forms else ""

        for form_model in self.registry_model.forms:
            if form_model.is_questionnaire or not self._applicable(form_model):
                continue
            form_name = form_model.name
            if form_name != current_form_name and form_name in existing_form_dyn_data:
                # Load existing data from previously saved forms because dynamic_data
                # contains data only for the currently submitted form. As progress is cummulative
                # we need existing data to properly compute it
                form_dynamic_data = existing_form_dyn_data[form_name]
            else:
                form_dynamic_data = dynamic_data
            fpc = FormProgressCalculator(self.registry_model, form_model, form_dynamic_data, self.progress_cdes_map)
            fpc.calculate_progress()
            forms_progress[form_model.name] = fpc.progress_as_dict()

            for progress_group in progress_metadata:
                if form_model.name in progress_metadata[progress_group]:

                    if progress_group not in groups_progress:
                        groups_progress[progress_group] = {
                            ProgressMetric.REQUIRED: 0,
                            ProgressMetric.FILLED: 0,
                            ProgressMetric.PERCENTAGE: 0,
                            ProgressMetric.CURRENT: True,
                            ProgressMetric.HAS_DATA: False
                        }

                    groups_progress[progress_group][ProgressMetric.REQUIRED] += (
                        fpc.form_progress_dict[ProgressMetric.REQUIRED]
                    )
                    groups_progress[progress_group][ProgressMetric.FILLED] += (
                        fpc.form_progress_dict[ProgressMetric.FILLED]
                    )
                    groups_progress[progress_group][ProgressMetric.CURRENT] = groups_progress[
                        progress_group][ProgressMetric.CURRENT] or fpc.form_currency
                    groups_progress[progress_group][ProgressMetric.HAS_DATA] = groups_progress[
                        progress_group][ProgressMetric.HAS_DATA] or fpc.form_has_data

        for group_name in groups_progress:
            groups_progress[group_name][ProgressMetric.PERCENTAGE] = percentage(
                groups_progress[group_name][ProgressMetric.FILLED],
                groups_progress[group_name][ProgressMetric.REQUIRED]
            )

        # now save the metric in form expected by _get_metric
        result = {}
        for form_name in forms_progress:
            result[form_name + "_form_progress"] = forms_progress[form_name][ProgressMetric.PROGRESS]
            result[form_name + "_form_current"] = forms_progress[form_name][ProgressMetric.CURRENT]
            result[form_name + "_form_has_data"] = forms_progress[form_name][ProgressMetric.HAS_DATA]
            result[form_name + "_form_cdes_status"] = forms_progress[form_name][ProgressMetric.CDES_STATUS]

        for groups_name in groups_progress:
            result[groups_name + "_group_progress"] = groups_progress[groups_name][ProgressMetric.PERCENTAGE]

            result[groups_name + "_group_current"] = groups_progress[groups_name][ProgressMetric.CURRENT]
            result[groups_name + "_group_has_data"] = groups_progress[groups_name][ProgressMetric.HAS_DATA]

        self.progress_data = result

    def _get_query(self, patient_model, context_model):
        return self.progress_collection.find(
            patient_model, context_id=context_model.id if context_model else None)

    def _load(self, patient_model, context_model=None):
        self.loaded_data = self._get_query(patient_model, context_model).data().first() or {}
        return self.loaded_data

    def _get_metric_helper(self, patient_model, context_model=None):
        # if new model passed in this causes progress data reload
        self._set_current(patient_model)
        self.context_model = context_model
        if self.loaded_data is None:
            self._load(patient_model, context_model)

    def _get_model_tagged_metric(self, mtm, patient_model, context_model=None):
        self._get_metric_helper(patient_model, context_model)
        return self.loaded_data.get(mtm.key_name(), mtm.default_value())

    def _get_metric(self, metric, patient_model, context_model=None):
        self._get_metric_helper(patient_model, context_model)
        pm = ProgressMetric(metric)
        return self.loaded_data.get(metric, pm.default_value())

    def _get_viewable_forms(self, user):
        form_container_model = self._get_form_container_model()

        return [f for f in form_container_model.forms if not f.is_questionnaire and user.can_view(f)]

        # return [f for f in RegistryForm.objects.filter(registry=self.registry_model).order_by(
        #    'position') if not f.is_questionnaire and user.can_view(f)]

    def _get_form_container_model(self):
        if self.context_model is not None:
            if self.context_model.context_form_group:
                return self.context_model.context_form_group
        return self.registry_model

    # Public API
    def reset(self):
        self.loaded_data = None

    def get_form_progress_dict(self, form_model, patient_model, context_model=None):
        # returns a dict of required filled percentage numbers
        return self._get_model_tagged_metric(
            ModelTaggedMetric(form_model, ProgressMetric.PROGRESS), patient_model, context_model
        )

    def get_form_progress(self, form_model, patient_model, context_model=None):
        d = self.get_form_progress_dict(form_model, patient_model, context_model)
        return d.get(ProgressMetric.PERCENTAGE, 0)

    def get_form_currency(self, form_model, patient_model, context_model=None):
        return self._get_model_tagged_metric(
            ModelTaggedMetric(form_model, ProgressMetric.CURRENT), patient_model, context_model
        )

    def get_form_cdes_status(self, form_model, patient_model, context_model=None):
        return self._get_model_tagged_metric(
            ModelTaggedMetric(form_model, ProgressMetric.CDES_STATUS), patient_model, context_model
        )

    def get_group_progress(self, group_name, patient_model, context_model=None):
        metric_name = "%s_group_progress" % group_name
        return self._get_metric(metric_name, patient_model, context_model)

    def get_group_currency(self, group_name, patient_model, context_model=None):
        metric_name = "%s_group_current" % group_name
        return self._get_metric(metric_name, patient_model, context_model)

    def get_group_has_data(self, group_name, patient_model, context_model=None):
        metric_name = "%s_group_has_data" % group_name
        return self._get_metric(metric_name, patient_model, context_model)

    def get_data_modules(self, user, patient_model, context_model):
        self._set_current(patient_model)
        viewable_forms = self._get_viewable_forms(user)
        content = ""
        if not viewable_forms:
            content = "No modules available"
        else:
            for form in viewable_forms:
                is_current = self.get_form_currency(form, patient_model, context_model)
                flag = "images/%s.png" % ("tick" if is_current else "cross")
                url = reverse('registry_form', args=(self.registry_model.code,
                                                     form.id, patient_model.pk,
                                                     context_model.pk))
                link = "<a href=%s>%s</a>" % (url, form.nice_name)
                label = form.nice_name
                to_form = link
                if user.is_working_group_staff:
                    to_form = label

                if form.has_progress_indicator:
                    src = static(flag)
                    percentage = self.get_form_progress(form, patient_model, context_model)
                    content += "<img src=%s> <strong>%d%%</strong> %s</br>" % (
                        src, percentage, to_form)
                else:
                    content += "<img src=%s> %s</br>" % (static(flag), to_form)

        html = "<button type='button' class='btn btn-primary btn-xs' " + \
               "data-toggle='popover' data-content='%s' id='data-modules-btn'>Show</button>" % content
        return html

    #########################################################################################
    # save progress
    def save_progress(self, patient_model, dynamic_data, context_model=None):
        if not dynamic_data:
            return self.progress_data
        self._calculate(dynamic_data, patient_model)
        record = self._get_query(patient_model, context_model).first()
        if not record:
            ctx = dict(context_id=context_model.id if context_model else None)
            context_id = context_model.id if context_model else None
            record = ClinicalData.create(patient_model, collection="progress",
                                         registry_code=self.registry_model.code,
                                         context_id=context_id,
                                         data=ctx)
        record.data.update(self.progress_data)
        record.save()
        return self.progress_data

    # a convenience method
    def save_for_patient(self, patient_model, context_model=None):
        self.reset()
        from rdrf.db.dynamic_data import DynamicDataWrapper
        if context_model is None:
            wrapper = DynamicDataWrapper(patient_model)
        else:
            wrapper = DynamicDataWrapper(patient_model, rdrf_context_id=context_model.pk)
        dynamic_data = wrapper.load_dynamic_data(
            self.registry_model.code, "cdes", flattened=False)
        return self.save_progress(patient_model, dynamic_data, context_model)
