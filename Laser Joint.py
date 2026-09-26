# Assuming you have not changed the general structure of the template no modification is needed in this file.
# from . import commands
# from .lib import fusionAddInUtils as futil
import adsk.core
import logging
from . import sane
from . import laser_finger_feature

logger = logging.getLogger(__name__)
sane.configure_logger(logger)
app = adsk.core.Application.get()

def run(context):
    with sane.report_all_exceptions():
        logger.info("-- Laser Joint Add-In Starting --")

        global _feature
        _feature = laser_finger_feature.LaserFingerFeature()


def stop(context):
    with sane.report_all_exceptions():
        global _feature
        _feature = None
