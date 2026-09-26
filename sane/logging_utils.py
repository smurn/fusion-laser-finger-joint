"""
Logging support.
"""

import logging
import contextlib
import adsk.core

logger = logging.getLogger(__name__)
app = adsk.core.Application.get()
ui = app.userInterface

class FusionLogHandler(logging.Handler):
    """
    Log Handler that calls Fusion's logging API.
    """
    def __init__(self, log_type: adsk.core.LogTypes):
        super().__init__()
        self._log_type = log_type

    def emit(self, record: logging.LogRecord):
        message = self.format(record)

        level = record.levelno
        if level <= logging.INFO:
            fusion_level = adsk.core.LogLevels.InfoLogLevel
        elif level <= logging.WARN:
            fusion_level = adsk.core.LogLevels.WarningLogLevel
        else:
            fusion_level = adsk.core.LogLevels.ErrorLogLevel

        app.log(message, fusion_level, self._log_type)


class MessageBoxLogHandler(logging.Handler):
    """
    Log Handler that opens a message box.
    """
    def emit(self, record: logging.LogRecord):
        message = self.format(record)

        level = record.levelno
    
        if level <= logging.INFO:
            icon = adsk.core.MessageBoxIconTypes.InformationIconType
        elif level <= logging.WARN:
            icon = adsk.core.MessageBoxIconTypes.WarningIconType
        else:
            icon = adsk.core.MessageBoxIconTypes.CriticalIconType

        ui.messageBox(message, record.levelname, icon = icon)

def configure_logger(logger: logging.Logger):
    """
    Configures the given logger to 
    * LOg errors to Fusion's log file
    * Log everything to Fusion's console
    * Log everything to stderr
    * Open a dialog box for critical errors.
    """

    # Reset the logger. 
    # Fusion's way of reloading modules otherwise causes duplicated handlers
    for handler in list(logger.handlers):  # Iterate over a copy to avoid issues during removal
        logger.removeHandler(handler)
        handler.close()  # Close handlers, especially important for file handlers
    logger.setLevel(logging.NOTSET)
    logger.propagate = True

    formatter = logging.Formatter('%(levelname)s: %(message)s')

    # Log errors to the application's log file
    file_handler = FusionLogHandler(adsk.core.LogTypes.FileLogType)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Log everything to the application's console
    console_handler = FusionLogHandler(adsk.core.LogTypes.ConsoleLogType)
    console_handler.setLevel(logging.NOTSET)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Log everything to stderr
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.NOTSET)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    # Show a message box for critical messages
    messagebox_handler = MessageBoxLogHandler()
    messagebox_handler.setLevel(logging.CRITICAL)
    logger.addHandler(messagebox_handler)



@contextlib.contextmanager
def report_all_exceptions(message: str = "Unexpected Error"):
    """
    Helper that catches all exceptions and logs them.
    Does not forward the exceptions.
    """
    try:
        yield
    except:
        logger.exception(message)
