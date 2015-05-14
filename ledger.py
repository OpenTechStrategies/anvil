"""
Code related to parsing or representing ledger files.
"""

import dateutil, os, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
import xml.etree.ElementTree as ET

from transactions import ParseError, Transaction, Transactions, Posting
import util as u
from config import config as c

def strip(a,b,c):
    return ''.join(c).strip()


class Ledger(Transactions):
    search = ''

    def __init__(self, fname=None, search="", opts=""):
        Transactions.__init__(self)
        if not fname: fname = c['ledger-file']
        self.search = search
        self.opts = opts
        self.fname = fname
        self.name = self.fname

    def get_pre_and_post_amble(self, fname=None):
        if not fname:
            fname = self.fname
        lines = u.slurp(fname)
        self.preamble = ""
        self.postamble = []
        now = dateutil.parser.parse("")
        for line in lines:
            try:
                stub = line.split(" ",1)[0]
                if '=' in stub: stub = stub.split("=",1)[0]
                if dateutil.parser.parse(stub) != now:
                    break
            except TypeError:
                pass
            self.preamble += line + "\n"

        for line in reversed(lines): 
            try:
                if dateutil.parser.parse(line.split(" ",1)[0]) != now:
                    break
            except TypeError:
                pass
            self.postamble.insert(0,line)
        
        for line in self.postamble:
            if not line: break
            if line[0] in " \t\n":
                self.postamble = self.postamble[1:]
        self.postamble = "\n".join(self.postamble)
        return (self.preamble, self.postamble)
    def export_file(self, fname, orig_fname=None):
        """Write ledger file to fname. Try to pull transactions out of the
        original file. If no original file specified, try to pull
        it from the file we're writing to.
        
        """
        if not orig_fname:
            orig_fname = fname
        if os.path.exists(orig_fname):
            self.get_pre_and_post_amble(orig_fname)
        else:
            self.preamble = ""
            self.postambe = ""
        with open(fname, 'w') as OUTF:
            OUTF.write(self.preamble)
            OUTF.write(self.__unicode__().encode('utf8'))
            OUTF.write(self.postamble)
    def export(self, fname=None):
        """If you don't specify a file, we'll write out to the files where entries come from.
        New entries that don't have an original file associated will go to a random file.

        If you do specify an fname, we'll combine all the entries into
        one file and not bother with pre and postamble
        """


        # fname specified
        if fname:
            with open(fname, 'w') as OUTF:
                OUTF.write(self.__unicode__().encode('utf8'))
                return
        
        # no fname
        seen = list(set([tx['fname'] for tx in self if 'fname' in tx]))

        for name in seen:
            temp = Ledger()
            for tx in self:
                if tx['fname'] == name:
                    temp.append(tx)
            temp.export_file(name)

        temp = Ledger()
        for tx in self:
            if not 'fname' in tx:
                temp.append(tx)
        if len(temp) > 0:
            if len(seen) > 0:
                temp.export_file(name, seen[0])

    def parse_xml(self, xml, fname=None):
        """Take output from Ledger's xml command and parse it.

        Also save the file it came from."""
        def set_if_found(tx, t, field, default=None):
            temp = tx.find(field)
            if temp != None:
                t[field] = temp.text
            elif default:
                t[field] = default

        for tx in ET.fromstring(xml).find('transactions'):
            t = Transaction()
            t['fname'] = fname
            t['state'] = tx.attrib.setdefault('state', '')
            t['date'] = dateutil.parser.parse(tx.find('date').text)
            if tx.find('aux-date') != None: t['aux_date'] = dateutil.parser.parse(tx.find('aux-date').text)
            set_if_found(tx, t, 'code', '')
            set_if_found(tx, t, 'payee', 'PAYEE UNKNOWN')
            set_if_found(tx, t, 'note', '')

            # parse tags
            metadata = tx.find('metadata')
            if metadata != None:
                for tag in metadata.findall('tag'):
                    t['tags'][tag.text] = None
                for tag in metadata.findall('value'):
                    t['tags'][tag.attrib["key"]] = tag.find("string").text

            for posting in tx.find('postings'):
                p = {}
                p['account_name'] = posting.find('account').find('name').text
                p['account_ref'] = posting.find('account').attrib['ref']
                amt = posting.find('post-amount').find('amount')
                p['commodity'] = amt.find('commodity').find('symbol').text
                p['commodity_flags'] = amt.find('commodity').attrib['flags']
                p['amount'] = Decimal(amt.find('quantity').text)
                p['state'] = posting.attrib.setdefault('state', '')
                set_if_found(posting, p, 'note', '')
                p['tx'] = t
                t['postings'].append(Posting(**p))
            self.append(t)

    def load(self, search=None, opts=None):
        """
        Use ledger's xml function to get transactions.

        search will add terms to the commandline ledger call so you can grab a subset of entries
        """
        def load_file(fname, files_to_load):
            print "Loading " + fname
            lines = u.slurp(fname)
            ledger = ""
            
            for line in lines:
                if line.startswith("include "):
                    new_fname = line.split("include ",1)[1]
                    if not new_fname.startswith("/"):
                        dirs = os.path.split(fname)[:-1]
                        new_fname = os.path.join(os.path.join(*dirs), new_fname)
                    files_to_load.append(new_fname)
                else:
                    ledger += line + "\n"

            proc = subprocess.Popen("ledger -f - %s xml %s" % (ledger_opts, search), shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            (stdout, stderr) = proc.communicate(ledger)
            return stdout

        if search == None:
            search = self.search
        if opts == None:
            opts = self.opts

        date_format = "%Y/%m/%d"
        ledger_opts = "--date-format %s %s" % (date_format, opts)

        files_to_load=[self.fname] 
        for fname in files_to_load:
            xml = load_file(fname, files_to_load) # note: this appends to files_to_load
            self.parse_xml(xml, fname)

class Balance(dict):
    """Run a balance command and represent the results."""
    def __init__(self, search="", opts="", fname=None):
        dict.__init__(self)
        if not fname: fname = c['ledger-file']
        self.search = search
        self.opts = opts
        self.fname = fname
        self.account = {}
        self.run()

    def parse_line(self, col, line_no, parent_name=""):
        line = self.bal_lines[line_no]
        if not col:
            col = len(line.split("Assets")[0])
        if parent_name:
            parent_name += ":"
        account = parent_name + line[col:]
        print account
        if line_no < len(self.bal_lines):
            self.parse_line(col, line_no+1, account)

    def run(self):
        "Run the balance command from ledger and grab the results"
        lines = subprocess.check_output("ledger -f " + self.fname + " " + self.opts + " balance " + self.search, shell=True).split("\n")
        depth = 0
        col = len(lines[0].split("Assets")[0])
        
        for line in lines:
            account = line[col:]
            depth = (len(account) - len(account.lstrip()))/2
            if account == "": break
            #print account, depth

        self.balance = Decimal( lines[-2].replace(",","").replace("$","") )
        self.bal_lines = lines
            
