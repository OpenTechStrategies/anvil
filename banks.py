import sys
from config import config as c
from errs import ConfigError
from chase import Chase

class Banks(dict):
    """A dict of Bank instances. Names are hashed to a list of bank
    accounts presented as a Bank object. See, e.g. the Chase class in
    chase.py

    """
    def load_bank(self, name):
        bank = c['banks'][name]
        for account_name, account in bank['accounts'].items():
            if name == "Chase Bank":
                self[name] = Chase(name=name, **account) 
                self[name].load_accounts()
            else:
                raise ConfigError("Unknown bank: %s" % name)
