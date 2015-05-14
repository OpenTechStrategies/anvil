import dateutil, glob, os, re, subprocess, sys
from decimal import Decimal

from config import c
from transactions import Posting, Transaction, Transactions
from errs import ParseError
import util as u

class Account(Transactions):
    """This is, at heart, a transactions class: a list of txs that we can
    represent in a number of ways. The routines here are specific to
    loading those txs from Chase statements.

    self.statements is a date-sorted list of statement objects representing the monthly bank statements
    """
    def __init__(self, bank_name='', account_name=''):
        self.rename_pdfs()
        self.statements = []
        self.bank_name = bank_name
        self.name = account_name
        self.config = c['banks'][self.bank_name]['accounts'][self.name]
        Transactions.__init__(self)

    def rename_pdf(self, fname):
        """Take a pdf containing a monthly statement, find the end date of the statement and rename the PDF to YYYY_MM.pdf"""

        for line in subprocess.check_output("pdftotext -layout %s -" % u.shellquote(fname), shell=True).split("\n"):
            if "through" in line:
                rename =  '_'.join(str(dateutil.parser.parse(line.split("through")[1])).split('-')[0:2]) + ".pdf"
                break
        if len(rename) != 11:
            raise ParseError("Can't get date of Statement pdf file %s for rename (got %s)" % (fname, rename))
        os.rename(fname, rename)
        return rename

    def rename_pdfs(self):
        for fname in glob.glob("StatementPdf*.pdf"):
            self.rename_pdf(fname)

    def load_from_statements(self):
        """Pull all transactions from the PDF statements, sort them by date.
        """
        self.config['statements-dir'] = u.fix_path(self.config['statements-dir'], c['OTS-root'])
        sys.exit()
        for fname in sorted(glob.glob("20??_??.pdf")):
            statement = Statement(fname)
            statement.parse()
            self.extend(statement.get_txs())
            self.statements.append(statement)
        self.name = "Chase Bank account no. %s" % self.statements[0]['account_num']

        self.sort()

class Chase(list):
    """A bunch of accounts at Chase. We only have one, so support for multiples is rudimentary right now."""
    def __init__(self):
        list.__init__(self)
        self.name = "Chase Bank"
    def load_accounts(self):
        for account_name in c['banks'][self.name]['accounts']:
            self.append(Account(bank_name = self.name,
                                account_name = account_name))
            self[-1].load_from_statements()
