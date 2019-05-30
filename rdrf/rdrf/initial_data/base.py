"""The minimal data needed for proper functioning.

This dataset is always installed when init is used, so add only required
datasets to it."""

import os

from django.contrib.sites.models import Site


def load_data(**kwargs):
    set_up_site()


def set_up_site():
    if not 'TRRF_SITE_DOMAIN' in os.environ:
        return

    domain = os.environ['TRRF_SITE_DOMAIN']
    name = os.environ.get('TRRF_SITE_NAME', os.environ.get('PROJECT_TITLE', domain))

    site = Site.objects.get_current()
    site.domain = domain
    site.name = name
    site.save()
