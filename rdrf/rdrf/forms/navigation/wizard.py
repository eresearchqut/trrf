import logging
from collections import defaultdict

from django.urls import reverse

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import RDRFContext

logger = logging.getLogger(__name__)


class NavigationError(Exception):
    pass


class NavigationFormType:
    DEMOGRAPHICS = 1
    CONSENTS = 2
    CLINICAL = 3
    CLINICIAN = 4  # other clinician


class NavigationWizard(object):
    def __init__(
        self,
        user,
        registry_model,
        patient_model,
        form_type,
        context_id,
        current_form_model=None,
    ):
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.form_type = form_type
        self.context_id = context_id
        self.on_create_form_view = context_id == "add"
        self.current_form_model = current_form_model
        self.links = []
        self.current_index = None  # set by method below
        self.has_clinician_form = self.registry_model.has_feature(
            RegistryFeatures.CLINICIAN_FORM
        )

        self._construct_links()

    def _construct_links(self):
        # aim is to construct a web ring of links:
        # --> demographics --> consents --> fixed group 1 form 1 --> fixed group 1 form 2 --> ... --> --> multiple group 1 assessment 1 form 1 ---> ..
        # ^<---  free form n <---  free form n -1 <--                                                                                    <--^
        demographics_link = self._construct_demographics_link()
        self.links.append(demographics_link)
        consents_link = self._construct_consents_link()
        self.links.append(consents_link)

        if self.has_clinician_form:
            clinician_form_link = self._construct_clinican_form_link()
            self.links.append(clinician_form_link)

        form_groups_dict = defaultdict(list)

        # there is one context per fixed group (always)
        for fixed_form_group in self._fixed_form_groups():
            context_models = list(
                RDRFContext.objects.filter(
                    context_form_group=fixed_form_group,
                    object_id=self.patient_model.pk,
                    content_type__model="patient",
                )
            )

            num_contexts = len(context_models)
            assert num_contexts == 1, (
                "There should only be one context model for this fixed context there are: %s"
                % num_contexts
            )

            context_model = context_models[0]
            for form_model in fixed_form_group.forms:
                if self.user.can_view(form_model):
                    form_groups_dict[fixed_form_group.sort_order].append(
                        self._construct_fixed_form_link(
                            context_model, form_model
                        )
                    )

        # for each multiple group, link through each assessment created for that group
        # in form order
        for multiple_form_group in self._multiple_form_groups():
            for context_model in self.patient_model.get_multiple_contexts(
                multiple_form_group
            ):
                for form_model in multiple_form_group.forms:
                    if self.user.can_view(form_model):
                        form_groups_dict[multiple_form_group.sort_order].append(
                            self._form_link(form_model, context_model)
                        )

        for _, links in sorted(form_groups_dict.items()):
            self.links.extend(links)

        # if form models have not been partitioned into form groups, they are "free"
        # most registries just have free forms because they don't define form groups
        for form_model in self._free_forms():
            if self.user.can_view(form_model):
                self.links.append(self._construct_free_form_link(form_model))

        if not self.on_create_form_view:
            self.current_index = self._determine_current_index()

    def _construct_free_form_link(self, form_model):
        # get default context model from patient
        context_model = self.patient_model.default_context(self.registry_model)
        return self._form_link(form_model, context_model)

    def _form_link(self, form_model, context_model):
        link = reverse(
            "registry_form",
            args=(
                self.registry_model.code,
                form_model.id,
                self.patient_model.pk,
                context_model.id,
            ),
        )
        return "clinical", form_model.pk, link

    def _fixed_form_groups(self):
        return [cfg for cfg in self.registry_model.fixed_form_groups]

    def _multiple_form_groups(self):
        return [cfg for cfg in self.registry_model.multiple_form_groups]

    def _construct_demographics_link(self):
        return (
            "demographic",
            None,
            reverse(
                "patient_edit",
                args=[self.registry_model.code, self.patient_model.pk],
            ),
        )

    def _construct_consents_link(self):
        return (
            "consents",
            None,
            reverse(
                "consent_form_view",
                args=[self.registry_model.code, self.patient_model.pk],
            ),
        )

    def _construct_clinican_form_link(self):
        return (
            "clinician",
            None,
            reverse(
                "clinician_form_view",
                args=[self.registry_model.code, self.patient_model.pk],
            ),
        )

    def _construct_fixed_form_link(self, context_model, form_model):
        return self._form_link(form_model, context_model)

    def _free_forms(self):
        if self.registry_model.is_normal:
            return [
                f
                for f in self.registry_model.forms
                if f.applicable_to(self.patient_model)
            ]
        else:
            return []

    def _determine_current_index(self):
        # where are we in the link ring?
        if self.form_type == NavigationFormType.DEMOGRAPHICS:
            return 0  # because demographics is always added first
        elif self.form_type == NavigationFormType.CONSENTS:
            return 1
        elif self.form_type == NavigationFormType.CLINICIAN:
            return 2
        else:
            # we're on some form
            if self.has_clinician_form:
                special_names = ["demographic", "consents", "clinician"]
            else:
                special_names = ["demographic", "consents"]

            for index, (name, form_id, link) in enumerate(self.links):
                if name in special_names:
                    continue
                # form link so get the models
                link_parts = link.split("/")
                context_id = int(link_parts[-1])
                if form_id == self.current_form_model.pk and context_id == int(
                    self.context_id
                ):
                    return index

        # shouldn't get here ...
        raise Exception("could not determine current index!")

    @property
    def previous_link(self):
        if self.on_create_form_view:
            # unsure what to do here
            return self.links[0]

        num_links = len(self.links)
        next_index = (self.current_index - 1) % num_links
        return self.links[next_index][-1]

    @property
    def next_link(self):
        if self.on_create_form_view:
            # unsure what to do here
            return self.links[0]
        num_links = len(self.links)
        next_index = (self.current_index + 1) % num_links
        return self.links[next_index][-1]
