import logging
logger = logging.getLogger(__name__)


class DataSource(object):

    def __init__(self, context):
        self.context = context

    def values(self):
        return []


class PatientCentres(DataSource):

    """
    centres = working groups
    We default to working groups if metadata on the registry doesn't have override
    context is a string like au or nz ( ophg wanted different centre dropdowns for DM1 in au vs nz for example)
    """

    def values(self):
        registry_model = self.context["registry_model"]
        if "patientCentres" in registry_model.metadata:
            context = 'au'
            return registry_model.metadata["patientCentres"][context]
        else:
            from registry.groups.models import WorkingGroup
            items = []
            for working_group in WorkingGroup.objects.filter(
                    registry=registry_model).order_by('name'):
                items.append((working_group.name, working_group.name))

            return items
