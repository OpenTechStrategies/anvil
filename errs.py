import sys
class GenericException(Exception):
    def __init__(self, message):
        self.message = message
        
        sys.stdout.write("\nERROR: " + str(message) + "\n\n")

class ConfigError(GenericException):
    pass

class ParseError(GenericException):
    pass

