#!/usr/bin/env python
"""
anvil --help for options

Copyright 2015 James Vasile 
Available under the terms of the Affero GNU General Public License, version 3 or later.
"""
__author__ = "James Vasile <james@jamesvasile.com>"
__version__ = "0.2.1"
__license__ = "AGPLv3+"

import os, sys

from config import config as c
from banks import Banks
from ledger import Ledger
from errs import ConfigError
from accountant import Stacy 
import dispatch
import display, display_cl, display_csv
import util as u
from logger import logger
log = logger.get_logger()

from util import pp, pf

def parse_args():
    import argparse

    # Mine the Dispatch class for list of commands and documentations
    dispatch = Dispatch()
    help_str = {}
    description = ""
    for cmd in dispatch._valid_commands():
        help_str[cmd] = dispatch._help(cmd)
        if cmd in dispatch._undocumented: continue
        description += dispatch._describe(cmd)

    # Specify parameters for the command line interface
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, add_help=False, description=description)
    parser.add_argument('command', type=str, nargs='?', help='a command for anvil to run')
    parser.add_argument('args', type=str, nargs='*', default=[], help='arguments to the command')
    parser.add_argument('-b', '--begin-date', type=str, default=None, help='ignore transactions before this date')
    parser.add_argument('-f', '--file', type=str, default=None, help='the ledger file to parse')
    parser.add_argument('-o', '--output', type=str, default=None, help='redirect output to a file (not implemented)')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='be more verbose about status messages')
    parser.add_argument('-q', '--quiet', action='store_true', default=False, help='be quieter and print fewer status messages')
    parser.add_argument('--csv', action='store_true', default=False, help='output in csv format')
    parser.add_argument('-h', '--help', action='store_true', help='display this help message. Specify a command for detailed help on that command.')

    # Run the argument parser
    args = vars(parser.parse_args())

    # Detailed help for `anvil.py -h foo`
    if args['help']:
        if not args['command']:
            parser.print_help()
            print
            sys.exit()
            return
        if not args['command'] in dispatch._valid_commands():
            log.error(("Unknown command: %s\n" % args['command']))
        else:
            print "%s: %s" % (args['command'].upper(), help_str[args['command']])
        sys.exit()

    # If we specify this as the default in the parser.add_argument
    # line above, the detailed help breaks because it relies on
    # command being blank sometimes.
    if not args['command']: args['command'] = 'audit'

    # Handle logging arguments
    if args['verbose']:
        logger.set_level("debug")
    del args['verbose']
    if args['quiet']:
        logger.set_level("warn")
    del args['quiet']
    log.debug("args: %s" % args)

    # Handle file argument
    if args['file']:
        c['ledger-file'] = args['file']
    del args['file'] # ensure later funcs don't rely on the wrong source of the file name

    # Munge and validate command
    valid_commands = dispatch._valid_commands()
    if not args['command'] in valid_commands:
        parser.print_help()
        print
        log.error("Unknown command (%s).  Please try one of these: %s" % (args['command'], " ".join(valid_commands)))
        sys.exit()
    args['command'] = args['command'].replace('-','_')

    # Handle setting of output file. Some displays (cli and csv) will
    # respect this.  Here we're changing the display.Display class.
    # Later, we'll instantiate another class that inherits from
    # display.Display.  Our change will be inherited too.
    if args.setdefault('output', None):
        display.Display.output_file = args['output']

    return args

class Dispatch(dispatch.Dispatch):
    """See dispatch.Dispatch for method documentation."""
    _undocumented=["nop"]
    banks = None
    def __init__(self, kwargs={}):

        # Pick our display module but don't instantiate our display
        # class yet. We'll do that in the actual command methods
        # below.
        self.display = display_cl # cli is the default display
        if kwargs.setdefault('csv', None):
            self.display = display_csv # but the user can choose csv

    def _load_banks(self):
        log.info( "Loading bank statements" )
        if not self.banks:
            self.banks = Banks()
            for bank_name, bank in c['banks'].items():
                self.banks.load_bank(bank_name)

    def audit(self, **kwargs):
        """Look for problems in the ledger file."""

        self._load_banks()

        for name, bank in self.banks.items():
            self.monthly_bal(accounts = bank)

    def monthly_bal(self, **kwargs):
        "check ending balances of statements against the ledger."

        """kwargs['accounts'] is a bank object (or just a list of
        accounts, I guess)

        """

        # If a set of accounts hasn't been provided, load them here.
        if not kwargs.setdefault('accounts', None):
            self._load_banks()
            for name, bank in self.banks.items():
                self.monthly_bal(accounts = bank)
            return

        # do the monthly balance thing for all the accounts
        accountant = Stacy()
        for name, account in kwargs['accounts'].items():
            accountant.monthly_bal(account, self.display.Monthly_Bal())

    def reconcile(self, **kwargs):
        """Match transactions in the ledger and bank statements."""

        # If a set of accounts hasn't been provided, load them here.
        if not kwargs.setdefault('accounts', None):
            self._load_banks()
            for name, bank in self.banks.items():
                kwargs['accounts'] = bank
                self.reconcile(**kwargs)
            return

        begin_date = ""
        if 'begin_date' in kwargs and kwargs['begin_date']: begin_date = " -b " + kwargs['begin_date']

        accountant = Stacy()
        for name, account in kwargs['accounts'].items():
            log.info( "Loading ledger." )
            ledger = Ledger(search=account.ledger_account, opts = "--related-all" + begin_date)
            ledger.load()

            # collect the entries that aren't for our checking account
            non_ac_ledger = Ledger(search=r"\(liabilities or expenses\) and not " + account.ledger_account, opts = "--related-all" + begin_date)
            non_ac_ledger.load() # These are the txs that can easily be mistakes

            log.info( "Matching up the ledger and the statements." )

            # Store our two transactions objects. These hold lists of all
            # our transactions and we're going to reconcile one against
            # the other.
            TXS = { 'ledger':ledger, 'bank':account, 'non_ac':non_ac_ledger }

            
            # This section does a few things:
            #
            #  * Make lists of the checking account postings except for
            #    transactions where the postings zero each other out.  
            #
            #  * Make amts dict that hashes amounts to a posting of that amount
            #  * Make multi_amts dict that hashes amounts to postings that sum to that amount
            #  * Make dates dict that hashes dates to postings and txs that sum to that amount

            class Index(object):
                """
                An index into the universe of postings.
                """
                def __init__(self):
                    self.solo = {'ledger': {}, 'bank': {}} # hash to single posting 
                    self.multi = {'ledger': {}, 'bank': {}} # has to list of postings
                    self.combined = {'ledger': {}, 'bank': {}}
                def combine(self):
                    "make a combined lookup for both multi and solo."
                    for act in ['ledger', 'bank']:
                        for key, val in self.solo[act].items():
                            self.combined[act].setdefault(key, []).append(val)
                            for multi in self.multi[act].setdefault(key, []):
                                self.combined[act].setdefault(key, []).append(multi)

            amts = Index()
            dates = Index()
            for act in ['ledger','bank']:
                TXS[act].make_index("date", 
                                    lambda tx: [posting for posting in tx['postings'] if posting['account_name'].lower().startswith(account.ledger_account.lower())],
                                    lambda tx: tx.get_date())
                #TXS[act].make_index("amount", True, lambda tx: tx.get_date())
                for tx in TXS[act]:
                    tx.pac = []
                    postings = [posting for posting in tx['postings'] if posting['account_name'].lower().startswith(account.ledger_account.lower())]
                    total = sum([posting['amount'] for posting in postings]) # total of the checking account postings
                    if total != 0: # check if checking account postings don't cancel out
                        if len(postings) > 1:
                            # Add postings to list of all groups of postings with the same amount as the total of this posting
                            amts.multi[act].setdefault(total, []).append(postings)
                            dates.multi[act].setdefault(tx.get_date(), []).append(postings)
                        for posting in postings:
                            tx.pac.append(posting)
                            posting.same_amount = []

                            amts.solo[act].setdefault(posting['amount'], []).append(posting)
                            dates.solo[act].setdefault(posting.get_date(), []).append(posting)
            amts.combine()
            dates.combine()

            for tx in TXS['ledger']:
                for posting in tx.pac:
                    pp (posting)
                    #TXS['bank'].index['date']
                    #posting.amount
            sys.exit()
            # hash non-checking account posting amounts to the non-checking-account txs that contain them
            non_ac_amts = {}
            for tx in non_ac_ledger:
                for amt in list(set([abs(p['amount']) for p in tx['postings']])):
                    non_ac_amts.setdefault(amt, []).append(tx)
                
            # We now have all the postings for any given amount for
            # both the ledger and the bank, hashed by amount. We have
            # non-checking account txs from the ledger, hashed by
            # amount. We've also hashed total tx checking account
            # amounts to txs that have multiple checking account
            # postings.

            
            # For every posting or group of postings in the ledger, we
            # want to match it to one in the statements. First, we
            # check the posting date and see if that narrows it down
            # to only one option. Second, we check the note and see if
            # that narrows it further. If not, we make a list of all
            # possible options.

            # Identify each posting's candidate matche(s)
            from transactions import Transactions
            no_candidates = Transactions()
            for act in ['ledger','bank']: 
                other = 'ledger' if act == 'bank' else 'bank'
                for tx in TXS[act]: # step through every tx in ledger, then bank
                    for posting in tx.pac: # go through the checking account postings
                        if not posting['amount'] in amts.solo[other] and not posting['amount'] in amts.multi[other]:
                            if not tx in no_candidates:
                                no_candidates.append(tx)

                        pdate = posting.get_date(no_parent=True)
                        if pdate:
                            if not pdate in dates.solo[other]:
                                print [d for d in dates.solo[other].keys()]
                                log.warn("Posting specifies a date of {1} but I couldn't find a paired bank statement entry.\n{0}".format(tx, pdate))

                            if pdate in dates.solo[other]:
                                print posting['amount'], [p['amount'] for p in dates.solo[other][pdate]]

                            elif pdate in dates.multi[other]:
                                print [p.get_date() for p in dates.multi[other][pdate]]


                        continue
                        for atx in amts.combined[other].setdefault(posting['amount'], []):

                            # atx is now a transaction w/ postings that match tx individually or in sum

                            # skip matches to self
                            try:
                                if atx['tx'] == tx: continue # some of atx are of type posting
                            except TypeError:
                                if atx[0]['tx'] == tx: continue # some of atx are lists of posting instances


                        #same_amount = [atx['tx']['tags']['id'] for atx in amts.solo[other].setdefault(posting['amount'], []) if atx['tx'] != tx]

                        # same_amount is a list of transaction ids
                        #pp (same_amount)

            #if len(no_candidates) > 0:
            #    print "Transaction for which we found no possible matches:"
            #    print "Clean those up before continuing."
            #    sys.exit()

            return
            for act in ['ledger','bank']:
                for amt in amts.solo[act]:
                    print ( "{0}: {1}".format(amt, pf([p['tx'].get_date() for p in amts.solo[act][amt]])) )
                for amt, postings in amts.multi[act].items():
                    print ( "{0}: {1}".format(amt, pf([p[0]['tx'].get_date() for p in postings])) )
                 #   print amt, multi_amts[act]
#                            print posting['amount'], [p['tx'].get_date() for p in amts[act][posting['amount']]]

            return

    def nop(self, **kwargs):
        """Do nothing. Used for tests. Limits execution to main.

        We need a way to test main, and this command helps us do
        that. You can safely ignore it. I mostly do.

        """
        pass

def dispatch(command, args):
    """Call the method of Dispatch that has the same name as
    `command`. Pass args as kwargs in the call.

    """
    getattr(Dispatch(args), command)(**args)

def fix_paths():
    """Change all the paths in config.json to abs paths because we don't
    know if they point local, relative to root or relative to the root
    of the OTS repo.
    """
    c['ledger-file'] = u.fix_path(c['ledger-file'], c['OTS-root'])
  
    for bank_name, bank in c['banks'].items():
        for account_name, account in bank['accounts'].items():
            account['statements-dir'] = u.fix_path(account['statements-dir'], c['OTS-root'])

def main():
    fix_paths()
    args = parse_args()
    dispatch(args['command'], args)

if __name__ == "__main__":
    main()
