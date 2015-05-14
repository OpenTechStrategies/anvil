import sys
class ConfigError(Exception):
    def __init__(self, message):
        self.message = message
        
        sys.stdout.write("\nERROR: " + str(message) + "\n\n")
