import sys
from logger import logger
log = logger.get_logger()
class GenericException(Exception):
    def __init__(self, message):
        self.message = message
        
        log.error(str(message) + "\n")

class ConfigError(GenericException):
    pass

class ParseError(GenericException):
    pass

