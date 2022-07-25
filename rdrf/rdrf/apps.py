import atexit
import logging

from aws_xray_sdk.core import xray_recorder
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RDRFConfig(AppConfig):
    name = 'rdrf'

    def ready(self):
        logger.info("running RDRFConfig.ready ... ")
        # migration wasn't being found - importing here fixed that
        import rdrf.checks.security  # noqa

        xray_recorder.begin_segment(self.name)
        atexit.register(lambda: xray_recorder.end_segment())
