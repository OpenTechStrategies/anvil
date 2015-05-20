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
import dateutil, sys
from ledger import Balance
from config import config as c
from transactions import Transactions
class Account_Accountant():
    """Stacy is our bookkeeper. She can answer questions about an
    individual account.

    """
    def monthly_bal(self, account, display):
        first_continuous = None
        last = 0
        for month in account.statements:
            bal = Balance(search=account.ledger_account, opts="--effective -e " + month.get_date(month['end_date'] + dateutil.relativedelta.relativedelta(days=1)))
            if bal.balance != month['summary']['ending balance']:
                if not first_continuous: 
                    last = 0
                display.add(month.get_date(), month['summary']['ending balance'], bal.balance, last)
                if not first_continuous: 
                    first_continuous = month.get_date()
                last = month['summary']['ending balance'] - bal.balance
            else:
                # unbalanced months followed by balanced months are
                # month-boundary dating errors
                first_continuous = None #month.get_date()
        display.done(first_continuous)
Stacy = Account_Accountant
    

class Bank_Accountant():
    """Nick is our accountant that handles bank-level stuff. He can answer
    questions about groups of accounts, which usually means all our
    accounts at a specific bank.

    """
    def monthly_bal(self):
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

class Reconciler(object):
    """Given a couple Transactions objects, this class has tools to help
    us reconcile them. We're assuming one of the objects is a ledger
    and the other is a bank account.

    """
    def __init__(self, ledger, account):
        self.ledger = ledger
        self.account = account
    def make_rows(self):
        import dateutil
        def get_increments(ledger, account):
            ld = ledger[ledger.idx].get_date(posting=ledger_account_name, return_string=False) if ledger.idx < len(ledger) else dateutil.parser.parse("2099/01/01")
            ad = account[account.idx].get_date(posting=ledger_account_name, return_string=False) if account.idx < len(account) else dateutil.parser.parse("2099/01/01")
                
            lbump = abump = False
            if ledger.idx == len(ledger):
                lbump = True
            if account.idx == len(account):
                abump = True
            if ledger.idx < len(ledger) and account.idx < len(account) and self.total(ledger[ledger.idx])==self.total(account[account.idx]):
                abump = lbump = True
            if ld <= ad:
                lbump = True
            if ld >= ad:
                abump = True
            ledger.bump = False
            if ledger.idx < len(ledger): ledger.bump = lbump
            account.bump = False
            if account.idx < len(account): account.bump = abump
        uncleared = Transactions()
        ret = ""
        ledger_account_name = c['banks'][self.account.bank_name]['accounts'][self.account.name]['ledger-account'].lower()
        while self.ledger.idx < len(self.ledger) or self.account.idx < len(self.account):
            if self.ledger.idx < len(self.ledger):
                if (self.ledger[self.ledger.idx]['state'] != "cleared" and 
                    not "cleared" in [p['state'] for p in self.ledger[self.ledger.idx]['postings'] if p['account_name'].lower().startswith(ledger_account_name)]):
                   uncleared.append(self.ledger[self.ledger.idx])
                   self.ledger.idx += 1
                   continue
            get_increments(self.ledger, self.account)

            if self.ledger.bump:
                self.ledger.total.append(self.ledger.total[-1] + self.total(self.ledger[self.ledger.idx]))
            if self.account.bump:
                self.account.total.append(self.account.total[-1] + self.total(self.account[self.account.idx]))

            if True:
                # make table row
                line = "<tr><td align='right'>"
                if self.ledger.bump: line += '{0}<br />'
                line += "</td><td>"
                if self.account.bump: line += '{1}<br />'
                line += "</td></tr>"
                ret += line.format(self.ledger[self.ledger.idx] if self.ledger.idx<len(self.ledger) else "", 
                                   self.account[self.account.idx] if self.account.idx < len(self.account) else "")
                if self.ledger.total[-1] == self.account.total[-1]:
                    ret += ("<tr><td align='right'><font color='green'>{0}</font><br /></td><td><font color='green'>{1}</font></td></tr>".
                            format(self.ledger.total[-1], self.account.total[-1]))
                else:
                    if self.ledger.bump == self.account.bump == True:
                        ret += ("<tr><td align='right'><font color='blue'>{0}</font><br /></td><td><font color='blue'>{1}</font></td></tr>".
                                format(self.ledger.total[-1], self.account.total[-1]))
                    else:
                        ret += "<tr><td align='right'>{0}<br /></td><td>{1}</td></tr>".format(self.ledger.total[-1], self.account.total[-1])

            if self.ledger.bump: self.ledger.idx += 1
            if self.account.bump: self.account.idx += 1

            #if len(self.ledger) >= self.ledger.idx and len(self.account) >= self.account.idx:
            #    if len(uncleared) > 0:
            #        for tx in uncleared:
            #            print "<tr><td align='right'>{0}</td></tr>".format(tx)
        return ret

    def total(self, tx):
        return sum([p['amount'] for p in tx['postings'] if p['account_name'].lower().startswith("assets:checking")])

    def reconcile(self):
        def sorter(tx):
            return (tx.get_date(posting=c['banks'][self.account.bank_name]['accounts'][self.account.name]['ledger-account'],
                                return_string=False),
                                abs(self.total(tx)))

        ledger = self.ledger
        account = self.account
        account.sort(key=sorter)
        ledger.sort(key=sorter)
        self.ledger.idx = self.account.idx = 0
        self.ledger.total = [0]
        self.account.total = [0]

        ret = "<html><body><table border='1'>"
        ret += self.make_rows()
        ret += "</table></body></html>"
        ret = ret.replace("\n", "<br />\n")
        import re
        ret = re.sub(r"(Assets:Checking.*)<", "<font color='red'>\\1</font><", ret)
        print ret

