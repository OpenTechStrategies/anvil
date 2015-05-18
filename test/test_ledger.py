import pytest, os, sys
import dateutil
sys.path.insert(0, os.path.split(os.path.dirname(os.path.realpath(__file__)))[0])

from ledger import Ledger
import anvil

from config import config as c

@pytest.fixture
def loaded_ledger():
    ledger = Ledger("aux-date.ledger")
    ledger.load()
    return ledger

def test_posting_aux_date(loaded_ledger):
    ledger = loaded_ledger
    assert 'aux_date' in ledger[0]['postings'][0]
    assert ledger[0]['date'] != ledger[0]['postings'][0]['aux_date']

def test_tx_aux_date(loaded_ledger):
    ledger = loaded_ledger
    assert 'aux_date' in ledger[1]['postings'][0]
    assert ledger[1]['postings'][0]['aux_date'] == None
    assert ledger[1]['date'] != ledger[1]['aux_date']

def test_tx_posting_aux_date(loaded_ledger):
    ledger = loaded_ledger
    assert 'aux_date' in ledger[2]['postings'][0]
    assert ledger[2]['postings'][0]['aux_date'] != ledger[1]['aux_date']
    assert ledger[2]['date'] != ledger[1]['aux_date']

def test_posting_get_date(loaded_ledger):
    ledger = loaded_ledger
    assert ledger[0]['postings'][0]['aux_date'] == dateutil.parser.parse(ledger[0]['postings'][0].get_date())
    assert ledger[1]['aux_date'] == dateutil.parser.parse(ledger[1]['postings'][0].get_date())
    assert ledger[3]['date'] == dateutil.parser.parse(ledger[3]['postings'][0].get_date())

def test_posting_get_date_no_parent(loaded_ledger):
    "The no_parent flag should prevent get us None instead of the parent tx's date"
    ledger = loaded_ledger
    assert ledger[0]['postings'][1].get_date(no_parent=True) == None
    assert ledger[0].get_date() == ledger[0]['postings'][1].get_date(no_parent=False)
    assert ledger[0].get_date() == ledger[0]['postings'][1].get_date()
