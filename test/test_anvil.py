import pytest, os, sys
sys.path.insert(0, os.path.split(os.path.dirname(os.path.realpath(__file__)))[0])
#os.chdir(os.path.split(os.path.dirname(os.path.realpath(__file__)))[0])

import anvil

from config import config as c

def test_fix_paths():
    p = c['ledger-file']
    anvil.fix_paths()
    assert ( c['ledger-file'] == os.path.join(c['OTS-root'], c['ledger-file']) )
