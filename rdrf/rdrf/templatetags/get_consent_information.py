from django import template
from rdrf.models.definition.models import ConsentSection
register = template.Library()


@register.filter()
def get_consent_information(fields):
    #  ['customconsent_15_13_21', 'customconsent_15_13_22']
    if len(fields) > 0:
        consent_field = fields[0]
        if not consent_field.startswith("customconsent_"):
            return

        consent_section_model_pk = consent_field.split("_")[2]
        try:
            consent_section_model = ConsentSection.objects.get(pk=consent_section_model_pk)
            return {
                "link": consent_section_model.information_link,
                "text": consent_section_model.information_text,
                "media": consent_section_model.information_media
            }
        except BaseException:
            return None
