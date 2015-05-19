import dateutil, random, re, sys
from decimal import Decimal, ROUND_HALF_UP
from operator import itemgetter, attrgetter, methodcaller
from errs import ParseError
import util as u

# we use this for handling state flags on the payee line or for a posting
state_flags = {"":"", "cleared":"*", "pending":"!"}

class Posting(dict):
    """A posting for a transaction

     * account_name is a string. It starts out blank but eventually
       needs the name of the account (Assets:Checking, or whatever)

     * account_ref is in the xml and is presumably unique to the
       account, even if the account name differs slightly?

     * state is blank, "cleared" (matches *) or "pending" (matches !)
       See
       http://www.ledger-cli.org/3.0/doc/ledger3.html#Transaction-state

     * note is a note about the transaction. See
       http://www.ledger-cli.org/3.0/doc/ledger3.html#Transaction-notes

     * commodity is the currency or commodity. ledger uses the term commodity

     * amount is an amount instance or None

     * commodity_flags are a string, but I don't know what they mean. They're in the xml

     * tx is the parent transaction, if there is one and it is known
    """

    def __init__(self, **initial_vals):
        dict.__init__(self)
        self.update({
            'aux_date':None,
            'account_ref':'',
            'account_name':None,
            'amount':None, 
            'commodity':'', # usually will be $
            'commodity_flags':'',
            'note':"",
            'state':"",
            'tx':None,
        })
        self.amount_width = None #gets set by self.__unicode__()
        self.update(initial_vals)
    def amtstr(self):
        return (" " if self['amount'] >= 0 else "") + u.moneyfmt(self['amount'])
    def __str__(self): return unicode(self).encode('utf-8')
    def __unicode__(self):
        state = state_flags[self['state']]
        if state: state += " "
        account = "    " + state + self['account_name'] 
        if self.amount_width == None:
            if self['tx']:
                amount_width = max([len(posting.amtstr()) for posting in self['tx']['postings']])                
                for posting in self['tx']['postings']:
                    posting.amount_width = amount_width
            else:
                self.amount_width=0
        amount = self.amtstr()
        amt = " %s%s%s" % (self['commodity'],(" " * (self.amount_width-len(amount))), amount)
        note = ""
        if self['note'] != '': note = "  ;" + self['note']
        width = 90
        if [debit for debit in ["assets", "expenses", "debits", "losses", "dividends"] if self['account_name'].lower().startswith(debit)]:
            width = 75
        return account + (" " * (width-len(account+amt))) + amt + note + "\n"
    def get_date(self, field="aux_date", no_parent=False):
        try:
            return self[field].strftime("%Y/%m/%d")
        except AttributeError:
            if no_parent:
                return None
            return self['tx'].get_date("aux_date")

class Transaction(dict):
    """
    date is a datetime object with the date of the transaction, when it was posted or the receipt date

    aux_date is a second date associated with the transaction. See http://www.ledger-cli.org/3.0/doc/ledger3.html#Auxiliary-dates

    payee is the payee part

    postings is a list of Posting objects for this transaction

    amount is the amount of the transaction

    file is the filename of ledger file where this tx lives

    code - usually a check or invoice # or blank. See http://www.ledger-cli.org/3.0/doc/ledger3.html#Codes

    state is blank, "cleared" (matches *) or "pending" (matches !) See http://www.ledger-cli.org/3.0/doc/ledger3.html#Transaction-state

    note is a note about the transaction. See http://www.ledger-cli.org/3.0/doc/ledger3.html#Transaction-notes

    tags is a dict of key, value pairs.
        some useful tags: owner=uid, cc
    """

    def __init__(self, **initial_vals):
        dict.__init__(self)
        self.update({
            'date':None,
            'aux_date':None,
            'payee':"PAYEE UNKNOWN",
            'postings':[],
            'amount':0,
            'file':"", 
            'code':"",
            'state':"",
            'note':"",
            'tags':{},
        })
        if not 'id' in self['tags']:
            self['tags']['id'] = random.randint(0,10000000)
        self.update(initial_vals)

    def get_date(self, field="date"):
        try:
            return self[field].strftime("%Y/%m/%d")
        except AttributeError:
            return self['date'].strftime("%Y/%m/%d")

    def make_match_date_amounts(self, day_range=3):
        """Make a list of dates associated with a tx. Make a list of amounts
        associated with a check or expense in the tx. Make a list of
        all the combinations of the two, though if a date is
        associated with a specific posting, only associate it with
        that amount. Store those combinations in self['match_date_amounts'].

        """
        def plus_or_minus(date, day_range=3):
            return [ date + dateutil.relativedelta.relativedelta(days=d) for d in range(day_range*-1, day_range+1)]

        date_pat = re.compile("(\[\=[\d/]\])")

        total_checking = 0
        for posting in self['postings']:
            if "Assets:Checking".lower() in posting['account_name'].lower():
                total_checking += posting['amount']
        self['match_amounts'] = set([total_checking])
        mda = {}
        for posting in self['postings']:
            if "Assets:Checking".lower() in posting['account_name'].lower():
                self['match_amounts'].add(abs(posting['amount']))
                m = date_pat.search(posting.setdefault('note',''))
                if m: # there's a date in there in the right format
                    da = [dateutil.dateparser.parse(m.groups()[0]), abs(posting['amount'])]
                    mda[str(da)] = da
                else:
                    date = plus_or_minus(self['date'])
                    if self.setdefault('aux_date', ''): 
                        date.extend(plus_or_minus(self['aux_date']))
                    amount = [abs(posting['amount']), total_checking]
                    for day in date:
                        for amt in amount:
                            da=[day, amt]
                            mda[str(da)] = da
        self['match_date_amounts'] = mda.values()
    def __str__(self): return unicode(self).encode('utf-8')
    def __unicode__(tx):
        note = ''
        if tx['note']:
            note = "\n    ;" + tx['note'].replace("\n", "\n    ;")
        date = tx.get_date()
        if 'aux_date' in tx and tx['aux_date'] != None:
            date += "="+tx.get_date('aux_date')
        code = ""
        if 'code' in tx and tx['code'] != "":
            code = "(" + tx['code'] + ") "
        state = ''
        if 'state' in tx and tx['state'] != "":
            state = state_flags[tx['state']] +" " 
        s = date + " " + state + code + tx['payee'] + note + "\n"

        # Print tags
        for tag, val in tx['tags'].items():
            if not val:
                if not ":%s:" % tag.lower() in tx['note'].lower():
                    s += "    ; :%s:\n" % tag
            else:
                if not tag.lower() in [line.split(":",1)[0].strip().lower() for line in tx['note'].split("\n") if ':' in line]:
                    s += "    ; %s: %s\n" % (tag, val)

        if 'postings' in tx:
            for posting in tx['postings']:
                s += unicode(posting)
                
        return s

class Transactions(list):
    def __init__(self, loaded=False):
        list.__init__(self)
        self.loaded=loaded
        self.index = {}

    def make_index_postings(self, name, predicate, key_func):
        """Takes every posting of every tx for which predicate(tx, posting) is
        true and indexes it under self.index[key_func(tx, posting)]

        If predicate = True, we'll index all the postings.

        """
        self.index[name] = {}
        for tx in self:
            for posting in tx:
                if predicate or predicate(tx, posting):
                    key = key_funct(tx, posting)
                    if not key in self.index[name]:
                        self.index[name].setdefault(key, []).append(posting)

    def make_index(self, name, predicate=None, key_func=None):
        """Takes every tx for which predicate(tx) is true and indexes it under
        key_func(tx).

        If predicate = True, we'll index all the transactions.
        """
        self.index[name] = {}
        for tx in self:
            if predicate or predicate(tx):
                key = key_func(tx)
                if not key in self.index[name]:
                    self.index[name].setdefault(key, []).append(tx)

    def sum(self, account):
        """Add up all the amounts in accounts that start with account."""
        ret = 0
        for tx in self:
            for posting in tx['postings']:
                if posting['account_name'].lower().startswith(account.lower()):
                    ret += posting['amount']
        return ret
    def load_from_statements(self, *args, **kwargs):
        """Pull transactions from some version of a bank statement, either PDF, XML, CVS or whatever.

        Set self.loaded when done. If it's already set when we enter,
        reload from statements as something might have chanced.

        Inherit from this class and override this method.

        """
        raise ParseError("load_from_statement method should be overridden")
    def get_cc_by_person(self, person):
        """Return transactions that are the cc transactions of the specified person.

        If self.loaded is False, load from the statements.

        Inherit from this class and override this method."""
        raise ParseError("get_cc_by_person method should be overridden")

    def sort(self):
        list.sort(self, key=itemgetter('date', 'amount'))

    def make_match_date_amounts(self):
        for tx in self:
            tx.make_match_date_amounts()
    def make_unmatched(self):
        self.unmatched = Transactions()
        for tx in self:
            if (len(tx['match_tx']) == 0 
                and not 0 in tx['match_amounts']
                and not tx.setdefault('match_ignore', False)
            ):
         #    if tx['match_undated']:
                tx['tags']['possible_match_dates'] = [otx.get_date() for otx in tx['match_undated']]
                self.unmatched.append(tx)
            elif tx['match_tx']:
                tx['tags']['possible_match_dates'] = [otx.get_date() for otx in tx['match_tx']]
    def write(self, fname):
        with open(fname, 'w') as OUTF:
            OUTF.write(self.__unicode__().encode('utf8'))
    def __unicode__(self):
        ret = ''
        for tx in self:
            ret += unicode(tx) + "\n"
        return ret
    def __str__(self): return unicode(self).encode('utf-8')
