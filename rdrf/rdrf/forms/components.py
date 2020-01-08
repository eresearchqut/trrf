import logging
from collections import defaultdict, deque

from django.contrib.contenttypes.models import ContentType
from django.template import Context, loader
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from rdrf.forms.form_title_helper import FormTitleHelper
from rdrf.forms.progress.form_progress import FormProgress
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.helpers.utils import (consent_status_for_patient, get_form_links,
                                is_generated_form)
from rdrf.models.definition.models import (ContextFormGroup, RDRFContext,
                                           RegistryType)
from rdrf.security.security_checks import user_is_patient_type

logger = logging.getLogger("registry_log")


class Link:
    def __init__(self, url, text, current):
        self.url = url
        self.text = text
        self.current = current


class LauncherError(Exception):
    pass


class _Form:

    def __init__(self, url, text, current=False, add_link_url=None, add_link_text=None):
        self.id = None
        self.url = url
        self.text = text
        self.current = current
        self.add_link_url = add_link_url
        self.add_link_text = add_link_text
        self.heading = ""
        self.existing_links = []  # for multiple contexts
        self.list_link = ""

    def __str__(self):
        return "Form %s %s %s" % (self.text, self.url, self.current)


class _FormGroup:

    def __init__(self, name):
        self.name = name
        self.forms = []


class RDRFComponent:
    TEMPLATE = ""

    @property
    def html(self):
        return self._fill_template()

    def _fill_template(self):
        if not self.TEMPLATE:
            raise NotImplementedError("need to supply template")
        else:
            template = loader.get_template(self.TEMPLATE)
            data = self._get_template_data()
            context = Context(data)
            return template.render(context.flatten())

    def _get_template_data(self):
        # subclass should build dictionary for template
        return {}


class RDRFPatientInfoComponent(RDRFComponent):
    TEMPLATE = "rdrf_cdes/patient_info_component.html"

    @property
    def html(self):
        if user_is_patient_type(self.viewing_user):
            return ''
        return self._fill_template()

    def __init__(self, registry_model, patient_model, viewing_user):
        self.patient_model = patient_model
        self.registry_model = registry_model
        self.viewing_user = viewing_user

    def _get_template_data(self):
        patient_type = self._get_patient_type()
        return {
            "patient_type": patient_type,
            "patient_information": self.patient_model.patient_info
        }

    def _get_patient_type(self):
        patient_type = self.patient_model.patient_type
        if patient_type:
            metadata = self.registry_model.metadata
            type_dict = metadata.get("patient_types", {})
            info_dict = type_dict.get(patient_type, {})
            return info_dict.get("name", patient_type)
        return ""


class RDRFContextLauncherComponent(RDRFComponent):
    TEMPLATE = "rdrf_cdes/rdrfcontext_launcher.html"

    def __init__(self,
                 user,
                 registry_model,
                 patient_model,
                 current_form_name="Demographics",
                 current_rdrf_context_model=None,
                 registry_form=None):
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.current_form_name = current_form_name
        self.content_type = ContentType.objects.get(model='patient')
        # below only used when navigating to form in a context
        # associated with a multiple context form group
        self.current_rdrf_context_model = current_rdrf_context_model
        self.consent_locked = self._is_consent_locked()
        self.registry_form = registry_form
        self.form_titles = FormTitleHelper(self.registry_model, current_form_name).all_titles_for_user(self.user)

    @property
    def form_name_for_template(self):
        # registry form may not be set
        if self.registry_form and self.registry_form.display_name:
            return self.registry_form.display_name
        else:
            return self.current_form_name

    def _get_template_data(self):
        def sort_by_name(form_group):
            fg_type, form_group = form_group
            if fg_type == 'fixed':
                return form_group.name
            else:
                return form_group.text

        existing_data_link = self._get_existing_data_link()

        fixed_contexts = self._get_fixed_contexts()
        multiple_contexts = self._get_multiple_contexts()
        sort_order = sorted(set(list(fixed_contexts.keys()) + list(multiple_contexts.keys())))

        context_form_groups = []
        for position in sort_order:
            form_groups = [('fixed', form_group) for form_group in fixed_contexts.get(position, ())]
            form_groups += [('multiple', form_group) for form_group in multiple_contexts.get(position, ())]
            form_groups = sorted(form_groups, key=sort_by_name)
            context_form_groups += form_groups

        logger.debug(context_form_groups)

        data = {
            "current_form_name": self.form_name_for_template,
            "form_titles": self.form_titles,
            "patient_listing_link": existing_data_link,
            "actions": self._get_actions(),
            "context_form_groups": context_form_groups,
            "current_multiple_context": self._get_current_multiple_context(),
            "demographics_link": self._get_demographics_link(),
            "consents_link": self._get_consents_link(),
            "family_linkage_link": self._get_family_linkage_link(),
            "consent_locked": self.consent_locked,
            "clinician_form_link": self._get_clinician_form_link(),
            "proms_link": self._get_proms_link(),
            "can_add_proms": not self._proms_adding_disabled(),
        }
        return data

    def _proms_adding_disabled(self):
        return self.registry_model.has_feature(RegistryFeatures.PROMS_ADDING_DISABLED)

    def _get_proms_link(self):
        if not self.registry_model.has_feature(RegistryFeatures.PROMS_CLINICAL):
            return None
        return reverse("proms_clinical_view",
                       args=[self.registry_model.code,
                             self.patient_model.pk])

    def _get_clinician_form_link(self):
        if not self.registry_model.has_feature(RegistryFeatures.CLINICIAN_FORM):
            return None

        return reverse(
            "clinician_form_view",
            args=[
                self.registry_model.code,
                self.patient_model.pk])

    def _is_consent_locked(self):
        has_config = hasattr(self.registry_model, 'consent_configuration')
        if has_config and self.registry_model.consent_configuration.consent_locked:
            return not consent_status_for_patient(self.registry_model.code,
                                                  self.patient_model)
        else:
            return False

    def _get_consents_link(self):
        return reverse(
            "consent_form_view",
            args=[
                self.registry_model.code,
                self.patient_model.pk])

    def _get_demographics_link(self):
        return reverse("patient_edit", args=[self.registry_model.code, self.patient_model.pk])

    def _get_family_linkage_link(self):
        pk = None
        if self.registry_model.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            if self.patient_model.is_index:
                pk = self.patient_model.pk
            elif self.patient_model.my_index:
                pk = self.patient_model.my_index.pk

        if pk is not None:
            return reverse('family_linkage', args=(self.registry_model.code, pk))
        else:
            return None

    def _get_existing_data_link(self):
        if self.registry_model.registry_type == RegistryType.NORMAL:
            # No need
            return None
        return self.patient_model.get_contexts_url(self.registry_model)

    def _get_actions(self):
        from rdrf.forms.navigation.context_menu import PatientContextMenu
        patient_context_menu = PatientContextMenu(self.user,
                                                  self.registry_model,
                                                  None,
                                                  self.patient_model)

        return patient_context_menu.actions

    def _get_multiple_contexts(self):
        if not self.registry_model.has_feature(RegistryFeatures.CONTEXTS):
            return {}

        # provide links to filtered view of the existing data
        # reuses the patient/context listing
        patients_listing_url = reverse("patientslisting")

        def _form(context_form_group):
            name = _("All " + context_form_group.direct_name)
            filter_url = patients_listing_url + "?registry_code=%s&patient_id=%s&context_form_group_id=%s" % (
                self.registry_model.code, self.patient_model.pk, context_form_group.pk)

            link_pair = context_form_group.get_add_action(self.patient_model)
            if link_pair:
                add_link_url, add_link_text = link_pair
                form = _Form(filter_url,
                             name,
                             add_link_url=add_link_url,
                             add_link_text=add_link_text)

                form.heading = _(context_form_group.direct_name)

                form.id = context_form_group.pk
                form.existing_links, form.existing_links_index, form.existing_links_len = \
                    self._get_existing_links(context_form_group)
                form.list_link = self._get_form_list_link(form)
                return form

        cfg_qs = ContextFormGroup.objects.filter(
            registry=self.registry_model,
            context_type="M"
        ).order_by("sort_order", "name")

        form_links = defaultdict(list)
        for cfg in cfg_qs:
            form = _form(cfg)
            if form:
                form_links[cfg.sort_order].append(form)

        return form_links

    def _get_form_list_link(self, form):
        return reverse("registry_form_list", args=[
            self.registry_model.code,
            form.id,
            self.patient_model.pk,
        ])

    def _get_existing_links(self, context_form_group, slice_len=5):
        """
        Create a subset of context form links of slice_len length, where the
        currently-selected context form (if one is selected) is as central as
        possible:

          01234.6789 (slice_len=5)
        = 34.67

          01234.6 (slice_len=4)
        = 34.6

          0123456 (slice_len=3)
        = 012

        :return: links, current_index, total_forms
        """
        links = deque(maxlen=slice_len)
        current_index = 0
        index_found = False
        current_context_id = self.current_rdrf_context_model.pk if self.current_rdrf_context_model else None

        forms = self.patient_model.get_forms_by_group(context_form_group)
        total_forms = len(forms)
        if not current_context_id:
            forms = forms[0:slice_len]

        for index, (context_id, url, text) in enumerate(forms):
            is_current = context_id == current_context_id
            if is_current:
                current_index = index
                index_found = True

            if (index - current_index) > (slice_len / 2) and len(links) == slice_len and index_found:
                break

            if not text:
                text = "Not set"
            link_obj = Link(url, text, is_current)
            links.append(link_obj)

        return list(links), current_index if index_found else -1, total_forms

    def _get_current_multiple_context(self):
        # def get_form_links(user, patient_id, registry_model, context_model=None, current_form_name=""):
        # provide links to other forms in this current context
        # used when landing on a form in multiple context
        registry_type = self.registry_model.registry_type
        fg = None
        if registry_type == RegistryType.HAS_CONTEXT_GROUPS:
            if self.current_rdrf_context_model and self.current_rdrf_context_model.context_form_group:
                cfg = self.current_rdrf_context_model.context_form_group
                if cfg.context_type == "M":
                    fg = _FormGroup(self.current_rdrf_context_model.display_name)
                    for form_link in get_form_links(self.user,
                                                    self.patient_model.pk,
                                                    self.registry_model,
                                                    self.current_rdrf_context_model,
                                                    self.current_form_name):
                        form = _Form(form_link.url,
                                     form_link.text,
                                     current=form_link.selected)
                        fg.forms.append(form)
        return fg

    def _get_fixed_contexts(self):
        # We can provide direct links to forms in these contexts as they
        # will be created on patient creation
        fixed_contexts = defaultdict(list)
        registry_type = self.registry_model.registry_type
        if registry_type == RegistryType.NORMAL:
            # just show all the forms
            fg = _FormGroup("Modules")
            for form_link in self._get_normal_form_links():
                form = _Form(form_link.url, form_link.text, current=form_link.selected)
                fg.forms.append(form)
            fixed_contexts[0].append(fg)
            return fixed_contexts
        elif registry_type == RegistryType.HAS_CONTEXTS:
            # nothing to show here
            return fixed_contexts
        else:
            # has context form groups , display form links for each "fixed" context
            for fixed_context_group in self._get_fixed_context_form_groups():
                rdrf_context = self._get_context_for_group(fixed_context_group)
                fg = _FormGroup(fixed_context_group.name)
                for form_link in self._get_visible_form_links(
                        fixed_context_group, rdrf_context):
                    form = _Form(form_link.url, form_link.text, current=form_link.selected)
                    fg.forms.append(form)
                fixed_contexts[fixed_context_group.sort_order].append(fg)
            return fixed_contexts

    def _get_normal_form_links(self):
        default_context = self.patient_model.default_context(self.registry_model)
        if default_context is None:
            raise LauncherError("Expected a default context for patient")
        else:
            return get_form_links(self.user,
                                  self.patient_model.id,
                                  self.registry_model,
                                  default_context,
                                  self.current_form_name)

    def _get_visible_form_links(self, fixed_context_group, rdrf_context):
        return get_form_links(self.user,
                              self.patient_model.id,
                              self.registry_model,
                              rdrf_context,
                              self.current_form_name)

    def _get_fixed_context_form_groups(self):
        return ContextFormGroup.objects.filter(registry=self.registry_model,
                                               context_type="F").order_by("sort_order")

    def _get_context_for_group(self, fixed_context_form_group):
        try:
            rdrf_context = RDRFContext.objects.get(registry=self.registry_model,
                                                   context_form_group=fixed_context_form_group,
                                                   object_id=self.patient_model.pk,
                                                   content_type=self.content_type)
            return rdrf_context
        except RDRFContext.DoesNotExist:
            return None


class FormsButton(RDRFComponent):
    """
    A button/popover which pressed shows links to forms in a registry or a form group
    """
    TEMPLATE = "rdrf_cdes/forms_button.html"
    MULTIPLE_LIMIT = 10  # Only show the last <MULTIPLE_LIMIT> items for multiple context form groups

    class FormWrapper:

        def __init__(
                self,
                registry_model,
                patient_model,
                form_model,
                context_form_group,
                context_model=None):
            self.registry_model = registry_model
            self.context_form_group = context_form_group
            self.patient_model = patient_model
            self.form_model = form_model
            self.context_model = context_model
            self.progress = FormProgress(self.registry_model)
            # if no progress cdes defined on form, don't show any percentage
            self.has_progress = form_model.has_progress_indicator

        @property
        def link(self):
            return reverse('registry_form', args=(self.registry_model.code,
                                                  self.form_model.id,
                                                  self.patient_model.pk,
                                                  self.context_model.id))

        @property
        def title(self):
            if not self.context_form_group or self.context_form_group.context_type == "F":
                return self.form_model.nice_name
            else:
                # multiple group
                if self.context_form_group.supports_direct_linking:
                    value = self.context_form_group.get_name_from_cde(self.patient_model,
                                                                      self.context_model)
                    if not value:
                        return "Not set"
                    else:
                        return value
                else:
                    return self.context_form_group.name + " " + self.form_model.nice_name

        @property
        def progress_percentage(self):
            return self.progress.get_form_progress(
                self.form_model, self.patient_model, self.context_model)

        @property
        def is_current(self):
            return self.progress.get_form_currency(
                self.form_model, self.patient_model, self.context_model)

    def __init__(self,
                 registry_model,
                 user,
                 patient_model,
                 context_form_group,
                 form_models):
        self.registry_model = registry_model
        self.user = user
        self.patient_model = patient_model
        self.context_form_group = context_form_group
        self.forms = [f for f in form_models if self.user.can_view(
            f) and not is_generated_form(f)]

    def _get_template_data(self):
        # subclass should build dictionary for template
        if self.context_form_group:
            heading = self.context_form_group.direct_name
            if self.context_form_group.context_type == "M":
                heading = heading
        else:
            heading = "Modules"

        add_link, add_link_text = self._get_add_link()

        return {
            "heading": heading,
            "forms": self._get_form_link_wrappers(),
            "add_link": add_link,
            "add_link_text": add_link_text,
        }

    def _get_form_link_wrappers(self):
        if self.context_form_group is None:
            default_context = self.patient_model.default_context(self.registry_model)
            return [self.FormWrapper(self.registry_model,
                                     self.patient_model,
                                     form_model,
                                     self.context_form_group,
                                     default_context) for form_model in self.forms]
        elif self.context_form_group.context_type == "F":
            # there should only be one context
            contexts = list(
                RDRFContext.objects.filter(
                    registry=self.registry_model,
                    context_form_group=self.context_form_group,
                    object_id=self.patient_model.pk,
                    content_type__model="patient"))

            assert len(
                contexts) == 1, "There should only be one context in %s" % self.context_form_group

            context_model = contexts[0]
            return [self.FormWrapper(self.registry_model,
                                     self.patient_model,
                                     form_model,
                                     self.context_form_group,
                                     context_model) for form_model in self.forms]
        else:
            # multiple group
            # we may have more than one assessment etc
            # NB. We LIMIT the number of forms shown to the last 10

            context_models = self.patient_model.get_multiple_contexts(self.context_form_group)
            context_models = context_models[:self.MULTIPLE_LIMIT]

            return [
                self.FormWrapper(self.registry_model,
                                 self.patient_model,
                                 form_model,
                                 self.context_form_group,
                                 context_model) for form_model in self.forms
                for context_model in context_models]

    @property
    def id(self):
        if self.context_form_group is None:
            return 0
        else:
            return self.context_form_group.pk

    def _get_add_link(self):
        if self.context_form_group and self.context_form_group.context_type == "M":
            link_url, link_text = self.context_form_group.get_add_action(self.patient_model)
            return link_url, link_text
        return None, None

    @property
    def button_caption(self):
        if self.context_form_group is None:
            return "Modules"
        else:
            if self.context_form_group.supports_direct_linking:
                # we know there is one form
                return self.context_form_group.forms[0].nice_name
            else:
                return self.context_form_group.name


class FormGroupButton(RDRFComponent):
    """
    A button which when clicked, loads a patient's forms
    via Ajax.
    """

    TEMPLATE = "rdrf_cdes/form_group_button_component.html"

    def __init__(self, registry_model, user, patient_model, context_form_group):
        self.registry_model = registry_model
        self.user = user
        self.patient_model = patient_model
        self.context_form_group = context_form_group

    def _get_template_data(self):
        if self.context_form_group is None:
            form_group_id = None
            registry_type = "normal"
        else:
            form_group_id = self.context_form_group.id
            registry_type = "has_groups"

        return {"button_caption": self.button_caption,
                "patient_id": self.patient_model.id,
                "form_group_id": form_group_id,
                "registry_type": registry_type}

    @property
    def button_caption(self):
        if self.context_form_group is None:
            return "Modules"
        else:
            if self.context_form_group.supports_direct_linking:
                # we know there is one form
                return self.context_form_group.forms[0].nice_name
            else:
                return self.context_form_group.name


class FamilyLinkagePanel(RDRFComponent):
    TEMPLATE = "rdrf_cdes/family_linkage_panel.html"

    def __init__(self, user, registry_model, patient_model):
        self.registry_model = registry_model
        fth = FormTitleHelper(self.registry_model, "Family linkage")
        self.form_titles = fth.all_titles_for_user(user)
        if not registry_model.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            self.patient_model = None
            self.link_allowed = self.is_index = None
            self.index_working_groups = None
            return

        self.user = user
        self.link_allowed = True
        self.patient_model = patient_model
        self.is_index = patient_model.is_index
        if not self.is_index:
            # if we can't see the link to the index
            # we want to know the working groups of the index at least
            self.link_allowed = user.can_view_patient_link(patient_model.my_index)

            self.index_working_groups = ",".join(
                sorted([wg.name for wg in self.patient_model.my_index.working_groups.all()]))
        else:
            self.index_working_groups = None

    def _get_template_data(self):
        data = {
            "patient": self.patient_model,
            "link_allowed": self.link_allowed,
            "is_index": self.is_index,
            "registry_code": self.registry_model.code,
            "index_working_groups": self.index_working_groups,
            "form_titles": self.form_titles
        }

        return data
