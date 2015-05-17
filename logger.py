"""This is a module that lets us have consistent logging across the
whole program. It includes a custom formatter so log.info sends useful
info to the user without the usual logging formatting cruft. AT the
same time, log.debug will include the cruft because it might be useful
to a dev.

 * Use log.debug for status messages to the dev.

 * Use log.info for status messages to the user.

 * Use log.warning and log.error for elevated messages to the user.

 * Use log.critical for elevated messages that might interest a dev.
"""
import inspect
import logging

class LogFormatter(logging.Formatter):
    def format(self, record):
        import dateutil
        import subprocess
        now = dateutil.parser.parse(subprocess.check_output("date", shell=True))
        if record.levelno <= 10:
            # debug
            return "{0} {2} {1}: {3}".format(now.strftime("%Y-%m-%d %H:%M:%S"), record.levelname, record.name, record.getMessage())
        elif record.levelno <= 20:
            # info (20)
            return record.getMessage()
        elif record.levelno <= 40:
            # warning (30), error (40)
            return "{0}: {1}".format(record.levelname, record.getMessage())
            # critical
        return "{0} {2} {1}: {3}".format(now.strftime("%Y-%m-%d %H:%M:%S"), record.levelname, record.name, record.getMessage())

class Logger(object):
    """This class is designed to be a singleton. Use the instance below,
    as it will handle setting the level for you.

    """

    loggers = []
    _default_level = logging.INFO # do not twiddle this directly. Use the accessor below.

    def set_level(self, level, name=None):
        """We can adjust logging just for a module by setting the name parameter"""
        if level.lower() == "debug":
            level = logging.DEBUG
        elif level.lower() == "info":
            level = logging.INFO
        elif level.lower() == "warn":
            level = logging.WARN
        for log in self.loggers:
            if name and log.name != name:
                continue
            log.setLevel(level)

    def get_logger(self):
        """Return a logger for the given context (the caller's module
        name). Create the logger if needed.

        Note that if the logger exists, it might not have the defaults
        anymore. E.g., its logging level might have been adjusted.

        """
        frame = inspect.stack()[1]
        mod = inspect.getmodule(frame[0])
        for log in self.loggers:
            if mod == log.name:
                return log

        # create logger
        log = logging.getLogger(mod.__name__)
        log.setLevel(self._default_level)
        ch = logging.StreamHandler()
        formatter = LogFormatter()
        ch.setFormatter(formatter)
        log.addHandler(ch)

        self.loggers.append(log)
        return log

logger = Logger()
