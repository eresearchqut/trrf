from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class RDRFConfig(AppConfig):
    name = 'rdrf'

    def ready(self):
        logger.info("running RDRFConfig.ready ... ")
        import rdrf.account_handling.backends
        import rdrf.models.definition.models
        # migration wasn't being found - importing here fixed that
        import rdrf.models.verification.models
        import rdrf.models.proms.models  # noqa
        import rdrf.models.definition.review_models  # oqa
        import rdrf.models.definition.verification_models  # noqa
