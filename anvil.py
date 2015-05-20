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
from accountant import Monthly_Balancer, Reconciler 
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
    valid_commands = [c for c in dispatch._valid_commands() if not c in dispatch._undocumented]
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
        accountant = Monthly_Balancer()
        for name, account in kwargs['accounts'].items():
            accountant.monthly_bal(account, self.display.Monthly_Bal())

    def reconcile(self, **kwargs):
        """Match transactions in the ledger and bank statements.

        This might be useful: 

         * ledger -f Chase_Bank-Preferred_Business_Checking.ledger --sort 'date' print
         * ledger -f main.ledger --sort 'date' print

        """


        # If a set of accounts hasn't been provided, load them here.
        if not kwargs.setdefault('accounts', None):
            self._load_banks()
            for name, bank in self.banks.items():
                kwargs['accounts'] = bank
                self.reconcile(**kwargs)
            return

        begin_date = ""
        if 'begin_date' in kwargs and kwargs['begin_date']: begin_date = " -b " + kwargs['begin_date']

        for name, account in kwargs['accounts'].items():
            log.info( "Loading ledger." )
            ledger = Ledger(search=account.ledger_account, opts = "--related-all" + begin_date)
            ledger.load()
            reconciler = Reconciler(ledger, account)
            reconciler.reconcile()

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
