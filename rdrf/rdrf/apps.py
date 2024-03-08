import atexit
import logging

from aws_xray_sdk.core import xray_recorder
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RDRFConfig(AppConfig):
    name = 'rdrf'

    def ready(self):
        logger.info("running RDRFConfig.ready ... ")
        import rdrf.account_handling.backends
        import rdrf.models.definition.models
        # migration wasn't being found - importing here fixed that
        import rdrf.checks.security  # noqa
        import rdrf.checks.import_export_logic_updates

        xray_recorder.begin_segment(self.name)
        atexit.register(lambda: xray_recorder.end_segment())
