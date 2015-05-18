"""
Code related to parsing or representing ledger files.
"""

import dateutil, os, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
import xml.etree.ElementTree as ET

from util import pp, pf

from transactions import ParseError, Transaction, Transactions, Posting
import util as u
from config import config as c

from logger import logger
log = logger.get_logger()

def strip(a,b,c):
    return ''.join(c).strip()

def call_ledger(cmd, fname="", stdin="", start_date=""):
    """This calls ledger and returns the result. If ledger writes to
    stderr, we complain and raise ParseError

    """
    if start_date: start_date = "-b " + start_date
    cmd = "ledger {1} {0}".format(cmd, start_date)
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = proc.communicate(stdin)
    if stderr and not stdout:
        log.debug("Ledger error: {0}".format(stderr))
        if not fname:
            fname = "the ledger file"
        raise ParseError("Ledger could not parse {0} with cmd {1}. Please correct the file.".format(fname, cmd))
    return stdout            

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

        Also remember the name of file it came from."""

        def set_if_found(tx, t, field, default=None, force_default=False, rename_field=None):
            temp = tx.find(field)
            if temp != None:
                if rename_field:
                    t[rename_field] = temp.text
                else:
                    t[field] = temp.text
            elif default or force_default:
                if rename_field:
                    t[rename_field] = default
                else:
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
                p['tx'] = t # point back at parent
                set_if_found(posting, p, 'aux-date', rename_field="aux_date")
                if 'aux_date' in p:
                    p['aux_date'] = dateutil.parser.parse(p['aux_date'])
                t['postings'].append(Posting(**p))
            self.append(t)

    def load(self, search=None, opts=None):
        """Use ledger's xml function to get transactions.

        search will add terms to the commandline ledger call so you can grab a subset of entries

        We don't just ask ledger to parse everything wholesale because
        it will hide the metadata about which files transactions
        belong in. So we load each file into memory, remove the
        directives to load adjunct ledger files, then load those files
        ourselves.

        """
        def load_file(fname, files_to_load):
            log.debug("Loading " + fname)
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
            return call_ledger("-f - {0} xml {1}".format(ledger_opts, search), fname, ledger)

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

    def run(self):
        """Run the balance command from ledger and grab the results
        """
        cmd_line = "-f " + self.fname + " " + self.opts + " balance " + self.search
        self.bal_lines = call_ledger(cmd_line, self.fname).split("\n")

        if self.bal_lines == ['']:
            self.balance = 0
            return

        for line in self.bal_lines:
            if self.search in line:
                line = line.split(self.search,1)[0].strip()
                self.balance = Decimal( line.replace(",","").replace("$","") )
