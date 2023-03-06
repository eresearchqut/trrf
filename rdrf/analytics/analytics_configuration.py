from django.utils.translation import gettext as _
def get_demographic_fields():
    return {'date_of_birth': _('Date of Birth'),
            'date_of_death': _('Date of Death'),
            'place_of_birth': _('Place of Birth'),
            'country_of_birth': _('Country of Birth'),
            'ethnic_origin': _('Ethnic Origin'),
            'sex': _('Sex'),
            'living_status': _('Living Status'),}