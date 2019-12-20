# Provide a lookup for group names of the form rdrf.registry.groups.GROUPS.GENETIC_STAFF
# The tuple values are used to match against group names in the db (explicitly case insensitive or using .lower())
# GROUPS.SUPER_USER is a sentinel used to trigger membership to all groups for superuser
from collections import namedtuple


GROUP_ATTR_NAMES = (
    'PATIENT',
    'PARENT',
    'CLINICAL',
    'WORKING_GROUP_STAFF',
    'WORKING_GROUP_CURATOR',
    'SUPER_USER',
    'CARRIER',
)


GroupLookup = namedtuple('GroupLookup', GROUP_ATTR_NAMES)
GROUPS = GroupLookup('patients',
                     'parents',
                     'clinical staff',
                     'working group staff',
                     'working group curators',
                     '__super_user__',
                     'carriers')


def reverse_lookup(group_name):
    try:
        return GROUP_ATTR_NAMES[GROUPS.index(group_name.lower())]
    except ValueError:
        return None
