import logging
import random

from django.db.models import Count

from django.utils.translation import gettext as _

from analytics.models import ClinicalDataView
from rdrf.models.definition.models import Registry, RegistryForm, Section, CommonDataElement
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


def chart_types():
    return {'line': _('Line'), 'bar': _('Bar')}


DATASOURCE_CDE = 'cde'
DATASOURCE_DEMOGRAPHIC = 'demographic'

DATASOURCE_CHOICES = {
    DATASOURCE_CDE: _("Form Element"),
    DATASOURCE_DEMOGRAPHIC: _("Demographic Field")
}

def process_chart_design(post):
    dataset_types = post.getlist('dataset_type')

    demographics = post.getlist('demographic_field')
    form = post.getlist('form')
    section = post.getlist('section')
    cde = post.getlist('cde')

    logger.info(demographics)
    logger.info(form)
    logger.info(section)
    logger.info(cde)

    datasets = []

    for i, dataset_type in enumerate(dataset_types):
        dataset = {'type': dataset_type}
        if dataset_type == DATASOURCE_CDE:
            dataset.update({'form': RegistryForm.objects.get(id=form[i]),
                            'section': Section.objects.get(id=section[i]),
                            'cde': CommonDataElement.objects.get(code=cde[i])})
        elif dataset_type == DATASOURCE_DEMOGRAPHIC:
            dataset.update({'demographic': demographics[i]})

        datasets.append(dataset)

    chart_design_opts = {
        'registry': Registry.objects.get(id=post.get('registry')),
        'title': post.get('chart_title'),
        'type': post.get('chart_type'),
        'datasets': datasets
    }

    return chart_design_opts
