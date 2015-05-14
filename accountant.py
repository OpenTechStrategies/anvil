"""I imagine our accounting firm as a three-person team. Danielle is
the big picture person. She's client-facing and we can ask her broad
questions. Nick is task focused and can pull up all our accounts for
any individual bank. Stacy works under Nick and gets into the books
for any specific account.

We can go to Stacy directly with account-related questions, but as
clients maybe it's best if we mostly talk to Danielle.

Casting this module as an accounting firm with three roles personified
by fake people is a bit of a conceit that works for James because he
knows Danielle, Nick and Stacy in the default world. If might or might
not help us keep straight how it works. If it proves a hindrance, we
should dump it. James isn't the one to eval that, though because it
will work for him long after it stops working for others.

"""
import sys
from Ledger import Balance
class Account_Accountant():
    """Stacy is our bookkeeper. She can answer questions about an
    individual account.

    """
    def monthly_bal(self, account, display):
        errs = []
        for month in account.statements:
            print account
            sys.exit()

            bal = Balance(search="Assets:Checking", opts="--effective -e " + month.get_date(month['end_date'] + dateutil.relativedelta.relativedelta(days=1)))
            if bal.balance != month['summary']['ending balance']:
                errs.append("As of %s: Statement balance of %s != Ledger balance of %s. Off by %s." % (month.get_date(), month['summary']['ending balance'], bal.balance, month['summary']['ending balance'] - bal.balance))
            else:
                # unbalanced months followed by balanced months are
                # month-boundary dating errors
                errs = []
        print "\n".join(errs)
Stacy = Account_Accountant
    

class Bank_Accountant():
    """Nick is our accountant that handles bank-level stuff. He can answer
    questions about groups of accounts, which usually means all our
    accounts at a specific bank.

    """
    pass

class Accountant():
    """Our accountant is the person who actually tries to figure out
    what's going on with the books. Let's call her Danielle. We can
    ask her to do things like reconcile the accounts and check monthly
    balances against the statements.

    Danielle knows about our books and also about our bank
    statements. Tasks that require matching up those two sets of
    information should generally be referred to her.

    The accountant is not our graphic designer. She doesn't do display
    stuff. She is a numbers and data wonk. If you want her to display
    things, make a function (usually a method in the Display class in
    anvil.py) available to her as a callback. Without a Display
    method, Danielle will just return data.

    Danielle has the overview of the banks. She mostly delegates work
    to other accountants that handle lower-level stuff.

    """
    def __init__(self):
        pass

    def monthly_bal(self, display=None):
        pass
