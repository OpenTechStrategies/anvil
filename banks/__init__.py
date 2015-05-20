"""These are some foundational parts for this directory. The Bank
class is the base class from which banks should inherit. The Banks
class is a dict of banks. It handles loading the bank modules in a way
that lets us find the right class later.

"""
import os, sys
from config import config as c
from errs import ConfigError

class Bank(dict):
    anvil_type = 'bank' # magic string that lets us identify bank classes below
    def __init__(self, *kwargs):
        dict.__init__(self)

class Banks(dict):
    """A dict of Bank instances. Names are hashed to a list of bank
    accounts presented as a Bank object. See, e.g. the Chase class in
    chase.py

    """
    def __init__(self):
        dict.__init__(self)

        self.classes = {} # where we'll put the classes for the banks

        # load_bank_modules
        banks_dir = os.path.split(__file__)[0]
        sys.path.insert(0, banks_dir)
        for module in os.listdir(banks_dir):
            if (not module.endswith(".py")
                or module == "__init__.py"):
                continue

            name = os.path.splitext(module)[0]
            __import__(name)
            module = sys.modules[name]
            import inspect
            for cl in inspect.getmembers(module, inspect.isclass):
                if cl[0]=="Bank" or not name == os.path.splitext(os.path.split(inspect.getfile(cl[1]))[1])[0]:
                    continue
        
                try:
                    if cl[1].anvil_type == "bank":
                        self.classes[cl[1].name] = getattr(module, cl[0])
                except AttributeError:
                    continue

    def load_bank(self, name):
        bank = c['banks'][name]
        for account_name, account in bank['accounts'].items():
            if not name in self.classes:
                raise ConfigError("Unknown bank: %s" % name)

            self[name] = self.classes[name].__new__(self.classes[name], **account)
            self[name].load_accounts()
