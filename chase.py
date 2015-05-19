"""Ideally, we wouldn't reference config here. Anything we need from
it would get passed in on object creation.

"""
import dateutil.parser, glob, os, re, subprocess, sys
from decimal import Decimal
from util import pp, pf

from config import config as c
from transactions import Posting, Transaction, Transactions
from errs import ParseError
import util as u

class Statement(dict):
    """This is a set of routines that represent a Chase bank statement. We
    might want to make a standard API for how we handle statements,
    but since we only have one kind (i.e. Chase) of statement
    available, this is it for now.

    """
    amount_pat = re.compile("\$? ?-? ?[.,\d]+$")

    def __init__(self, fname, ledger_account):
        dict.__init__(self)
        self.fname = fname
        self.ledger_account = ledger_account
        self.fname_text = os.path.splitext(fname)[0]+".txt"
        #self.fname_ledger = os.path.splitext(fname)[0]+".ledger"
        #if os.path.exists(self.fname_ledger):
        #    self.load_from_ledger():
        if os.path.exists(self.fname_text):
            self.load_from_text()
        else:
            self.load_from_pdf()
    def load_from_text(self):
        self.text = u.slurp(self.fname_text)
    def load_from_pdf(self):
        subprocess.call("pdftotext -layout %s" % self.fname, shell=True)
        self.load_from_text()
        
    def parse_date(self):
        line = self.text[0]
        if "through" in line:
            (fore, aft) = line.split("through")
            self['start_date'] = dateutil.parser.parse(fore)
            self['end_date'] = dateutil.parser.parse(aft)
        else:
            raise ParseError("Couldn't find statement date for %s" % self.fname)

    def parse_account_num(self):
        for line in self.text:
            if "Account Number" in line:
                self['account_num'] = Decimal(line.split("Account Number:")[1].strip())
                return

    def get_date(self, field="end_date"):
        try:
            return field.strftime("%Y/%m/%d")
        except AttributeError:
            return self[field].strftime("%Y/%m/%d")
    def get_end_date(self):
        return self.get_date("end_date")
    def get_start_date(self):
        return self.get_date("start_date")

    def parse_checking_summary(self, line_no, undef):
        while line_no <= len(self.text) and not self.text[line_no].startswith(" CHECKING SUMMARY"):
            line_no += 1
        fields = ["Beginning Balance", "Ending Balance", "Checks Paid", 
                  "Deposits and Additions", "ATM & Debit Card Withdrawals", 
                  "Electronic Withdrawals", "Fees and Other Withdrawals"]
        if not 'summary' in self:
            self['summary'] = {}
        for field in fields:
            for line in self.text[line_no:]:
                if line.startswith(" " + field):
                    amt = Decimal(re.findall(self.amount_pat, line)[0].replace(",","").replace("$", "").replace(" ",""))
                    self['summary'][field.lower()] = amt
                if not field.lower() in self['summary']:
                    self['summary'][field.lower()] = 0
                if line.startswith(" Ending Balance"): 
                    last_line = self.text[line_no:].index(line)
                    break
        return last_line+line_no+1


    def parse_daily_balance(self, line_no, field):
        self[field] = []
        for line in self.text[line_no+1:]:
            if line in '\x0c\n':
                break

            (date, amt) = line.rsplit(" ",1)
            if self.amount_pat.match(amt):
                self[field].append({self.complete_date(date):Decimal(amt.replace(",","").replace("$","").replace(" ",""))}) # date:amt

    def complete_date(self, date):
        """Given a month/year in \d\d/\d\d format, use the statement start and
        end dates to figure out the year. Return it as a parsed date.
        This is mostly to handle stuff that comes late in Dec for a
        Dec to Jan statement. I imagine this will only ever apply to
        events on the the 31st of Dec.

        """
        year = self['end_date'].year
        if (self['start_date'].year != self['end_date'].year
            and int(date.split('/')[0]) == 12):
            year = self['start_date'].year
        return dateutil.parser.parse(str(year)+"/"+ date)

    def parse_entries_neg(self, line_no, field):
        self.parse_entries(line_no, field, neg=True)
        
    def parse_entries(self, line_no, field, neg=False):
        if neg:
            neg = -1
        else:
            neg = 1

        # This should take care of a repeated section
        if not field in self:
            self[field] = Transactions()

        entry_pat = re.compile("^(\d\d/\d\d) *(.*?)(\$?) ?([-.,\d]+)$")
        for line in self.text[line_no+1:]:
            if self.unknown_section(line): break
            m = entry_pat.match(line)
            if m:
                parts = m.groups()
                descrip = parts[1].strip()
                amt = Decimal(parts[3].replace(",","").replace("$","")) * neg
                m = re.search("Purchase *(\d\d/\d\d)", descrip)
                if m:
                    aux_date = self.complete_date(m.groups()[0])
                    descrip = descrip.split(m.groups()[0],1)[1].strip()
                else:
                    aux_date = None

                tx = Transaction(**{'date':self.complete_date(parts[0]),
                                    'aux_date':aux_date,
                                    'payee':descrip,
                                    'file':self.fname,
                                    #'tags':{'section':field}
                                })
                tx['postings'] = [Posting(**{'commodity':'$',
                                             'amount':amt,
                                             'account_name':self.ledger_account + ':' +field,
                                             'tx':tx}),
                                  Posting(**{'commodity':'$',
                                             'amount':amt*-1,
                                             'account_name':'Liabilities:'+field,
                                             'tx':tx}),
                              ]
                self[field].append(tx)
    def parse_checks_paid(self, line_no, field):
        self[field] = Transactions()
        check_pat = re.compile("^(\d+) *(\^?) *(.*?) *(\d\d/\d\d) *(\$?) *([-,.\d]+)")
        date_amount_pat = re.compile("(\d\d/\d\d) *(\$?) *([-,.\d]+)$")
        for line in self.text[line_no+1:]:
            if line in '\x0c\n':
                break
            m = check_pat.match(line)
            if m:
                parts = m.groups()
                n = date_amount_pat.search(line)
                if n:
                    da_parts = n.groups()
                    amt = Decimal(da_parts[2].replace(",",""))
                tx = Transaction(**{
                    'code':parts[0],
                    'payee':"Check for $%s" % u.moneyfmt(amt),
                    'note':parts[2].strip(),
                    'date':self.complete_date(da_parts[0]),
                    })
                tx['postings']=[Posting(**{'commodity':da_parts[1] if da_parts[1] else "$",
                                           'account_name':'Income:'+field,
                                           'amount':amt,
                                           'tx':tx,
                                       }),
                                Posting(**{'commodity':da_parts[1] if da_parts[1] else "$",
                                           'account_name':self.ledger_account + ':' +field,
                                           'amount':amt * -1,
                                           'tx':tx,
                                       }),
                            ]

                self[field].append(tx)

    def unknown_section(self, line):
            if (not line
                or line == '\x0c'
                or (line.upper() != line)
            ):
                return False
            try:
                if dateutil.parser.parse(line.split(" ")[0]):
                    return False
            except TypeError:
                pass
            for txt in ["CUSTOMER SERVICE", "BROOKLYN", "TRANSACTIONS FOR SERVICE FEE CALCULATION", "SERVICE CHARGE SUMMARY"
                        , "WHAT YOU NEED TO KNOW ABOUT OVERDRAFTS"
                        ,"SERVICE CHARGE DETAIL" # Pretty sure service fees are assessed in next statement, so we can ignore in this one
                        , "SERVICE FEE CALCULATION" # Pretty sure service fees are assessed in next statement, so we can ignore in this one
            ]:
                if txt in line:
                    return False
            for regex in ["\d", "DESCRIPTION", "^[ \t\n]*$", "^[ \d]+$", "INSTANCES *AMOUNT", "DATE *AMOUNT"]:
                if re.search(regex, line):
                    return False
            return True

    def get_txs(self):
        txs = Transactions()
        for field in self.section_names:
            field = field.lower()
            if field in self:                
                txs.extend(self[field])
        return txs
    def parse(self):

        self.parse_date()
        self.parse_account_num()
        sections = {" CHECKING SUMMARY":self.parse_checking_summary,
                    "DAILY ENDING BALANCE":self.parse_daily_balance}
        
        # These result in ledger entries, as they affect the account balance
        ledger_sections = {
            "DEPOSITS AND ADDITIONS":self.parse_entries,
            "ELECTRONIC WITHDRAWALS":self.parse_entries_neg,
            "FEES AND OTHER WITHDRAWALS":self.parse_entries_neg,
            "ATM & DEBIT CARD WITHDRAWALS":self.parse_entries_neg,
            "CHECKS PAID":self.parse_checks_paid,
        }
        self.section_names = ledger_sections.keys()
        sections.update(ledger_sections)

        line_no = 0
        for line in self.text:
            found = False
            for k,v in sections.items():
                if line.startswith(k): 
                    v(line_no, k.lower().strip())
                    found = True
                    break
            if not found and self.unknown_section(line):
                raise ParseError("Found what might be an unrecognized section heading in %s: %s" % (self.fname, line))
                # TODO: maybe look at the next line to see if it looks like a tx
            line_no += 1

        # Make sure the sums are sane. Complain about parse errors it they're not
        sum = self['summary']['beginning balance']
        for field in self.section_names:
            field = field.lower()
            if field in self:                
                s = self[field].sum(self.ledger_account)
                if not field in self['summary']:
                    raise ParseError("Statement %s has a section that isn't in the summary: %s" % (self.fname, field))
                if s != self['summary'][field]:
                    raise ParseError("Sum of transactions of (%s) in %s's \"%s\" section doesn't match summary at top of statment (%s)." % 
                                     (s, self.fname, field, self['summary'][field]))
                sum += s
        if sum != self['summary']['ending balance']:
            raise ParseError("Sum of transactions doesn't yield ending balance in %s (%s vs %s)" % (self.fname, sum, self['summary']['ending balance']))

    def __str__(self):
        return str(dict(self))

class Account(Transactions):
    """This is, at heart, a Transactions class: a list of txs that we can
    represent in a number of ways. The routines here are specific to
    loading those txs from Chase statements, but I've tried to do this
    in a fairly general way. If we have more banks at some point, this
    code should be generalizable. Toward that end, let's try to treat
    the way it talks to the world as our future API.

    * self.statements is a date-sorted list of statement objects
      representing the monthly bank statements

    * self.bank_name is the name of the bank, e.g. 'Chase Bank'. It
      should match the name used in config.json.

    * self.account_num is the account number

    * self.name is the account_name, which might or might not be the account number
    """

    def __init__(self, **kwargs):
        self.rename_pdfs()
        self.statements = []
        self.statements_dir = kwargs['statements-dir']
        self.bank_name = kwargs['bank-name']
        self.name = kwargs['name']
        self.ledger_account = kwargs['ledger-account']
        self.account_num = None
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
        """Pull all transactions from the PDF statements, sort them by
        date.

        """
        for fname in sorted(glob.glob(os.path.join(self.statements_dir, "20??_??.pdf"))):
            statement = Statement(fname, self.ledger_account)
            statement.parse()
            self.extend(statement.get_txs())
            self.statements.append(statement)
        self.account_num = self.statements[0]['account_num']

        self.sort()

        # save a copy of this bank statement as a ledger file
        #self.write(os.path.join(os.path.split(c['ledger-file'])[0], (self.bank_name + "-" + self.name).replace(' ','_')+".ledger"))

class Chase(dict):
    """A dict of accounts at Chase. Name of account hashes to the account object. We only have one, so support for multiples is rudimentary right now."""
    def __init__(self, **kwargs):
        dict.__init__(self)
        for key, val in kwargs.items():
            setattr(self, key, val)
    def load_accounts(self):
        for account_name, account in c['banks'][self.name]['accounts'].items():
            account['name'] = account_name
            account['bank-name'] = self.name
            self[account_name] = (Account(**account))
            self[account_name].load_from_statements()
    def __str__(self):
        return self.name
        
