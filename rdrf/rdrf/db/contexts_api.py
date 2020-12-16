from django.db.models import Prefetch

from rdrf.models.definition.models import Registry, ContextFormGroup, ContextFormGroupItem
from rdrf.models.definition.models import RDRFContext
from django.contrib.contenttypes.models import ContentType
from rdrf.helpers.registry_features import RegistryFeatures

import logging

from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class RDRFContextError(Exception):
    pass


def create_rdrf_default_contexts(patient, registry_ids):
    # invoked when patient is added to a registry
    for registry in Registry.objects.filter(pk__in=registry_ids):
        if not RDRFContext.objects.get_for_patient(patient, registry).exists():
            context_manager = RDRFContextManager(registry)
            return context_manager.get_or_create_default_context(patient)


class RDRFContextManager:

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.supports_contexts = self.registry_model.has_feature(RegistryFeatures.CONTEXTS)

    def get_or_create_default_context(self, patient_model, new_patient=False):
        if not self.supports_contexts:
            contexts = RDRFContext.objects.get_for_patient(patient_model, self.registry_model)
            if len(contexts) == 0:
                return self.create_context(patient_model, "default")
            elif len(contexts) == 1:
                return contexts[0]
            else:
                raise RDRFContextError("Patient %s in %s has more than 1 context" %
                                       (patient_model, self.registry_model))
        else:
            default_fixed_context = self.create_fixed_contexts_for_patient(patient_model)
            if default_fixed_context is None:
                return self.create_initial_context_for_new_patient(patient_model)
            else:
                return default_fixed_context

    def create_fixed_contexts_for_patient(self, patient_model):
        from rdrf.models.definition.models import ContextFormGroup
        if not self.supports_contexts:
            # nothing to do
            pass
        else:
            # create any "fixed" contexts as a side effect and return the default one:
            # if there are context groups defined, check for "fixed" ones
            # create one context for each (if it doesn't exist).
            # return the context associated with the fixed
            # group marked is_default ( if there is one)

            default_context = None
            content_type = ContentType.objects.get_for_model(patient_model)
            for context_form_group in ContextFormGroup.objects.filter(
                    registry=self.registry_model, context_type='F'):
                # fixed type so create one for the supplied patient
                fixed_context, created = RDRFContext.objects.get_or_create(registry=self.registry_model,
                                                                           content_type=content_type,
                                                                           object_id=patient_model.pk,
                                                                           context_form_group=context_form_group)
                if created:
                    fixed_context.display_name = context_form_group.get_default_name(
                        patient_model)
                    fixed_context.save()
                if context_form_group.is_default:
                    default_context = fixed_context
            return default_context

    def create_initial_context_for_new_patient(self, patient_model):
        context = RDRFContext.objects.get_for_patient(patient_model, self.registry_model).order_by("pk").first()
        return self.create_context(patient_model, "default") if not context else context

    def create_context(self, patient_model, display_name):
        rdrf_context = RDRFContext(registry=self.registry_model,
                                   content_object=patient_model, display_name=display_name)

        default_context_form_group = self.registry_model.default_context_form_group
        if default_context_form_group is not None:
            rdrf_context.context_form_group = default_context_form_group
            rdrf_context.display_name = default_context_form_group.get_default_name(
                patient_model)

        rdrf_context.save()
        return rdrf_context

    def get_context(self, context_id, patient_model):
        if context_id is None:
            return self.get_or_create_default_context(patient_model)

        content_type = ContentType.objects.get_for_model(patient_model)
        try:
            rdrf_context_model = RDRFContext.objects.get(pk=context_id,
                                                         registry=self.registry_model,
                                                         content_type=content_type,
                                                         object_id=patient_model.pk)
            return rdrf_context_model
        except RDRFContext.DoesNotExist:
            raise RDRFContextError("Context does not exist")

    def get_previous_contexts(self, context, patient_model):
        content_type = ContentType.objects.get_for_model(patient_model)
        return RDRFContext.objects.filter(
            created_at__lt=context.created_at, registry=self.registry_model,
            content_type=content_type, object_id=patient_model.pk,
            context_form_group__id=context.context_form_group_id
        ).order_by("-created_at")

    def get_patient_current_contexts(self, patient):
        return ContextFormGroup.objects\
            .filter(registry=self.registry_model)\
            .order_by("sort_order")\
            .prefetch_related(
                Prefetch(
                    lookup="rdrfcontext_set",
                    queryset=RDRFContext.objects.filter(
                        object_id=patient.pk,
                        content_type=ContentType.objects.get_for_model(Patient)
                    ),
                    to_attr="patient_contexts"
                ),
                Prefetch(
                    lookup="items",
                    queryset=ContextFormGroupItem.objects.filter(
                        registry_form__is_questionnaire=False
                    )
                )
            )
