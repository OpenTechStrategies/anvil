#!/usr/bin/env python
"""
anvil --help for options

Copyright 2015 James Vasile 
Licensed to you under the terms of the Affero GNU General Public License, version 3 or later.
"""
__author__ = "James Vasile <james@jamesvasile.com>"
__version__ = "0.2.1"
__license__ = "AGPLv3+"

import inspect, os, sys

from config import config as c
from banks import Banks
from errs import ConfigError
from accountant import Accountant, Bank_Accountant, Stacy
import cl_display # command line display classes
import util as u

def parse_args():
    import argparse

    dispatch = Dispatch()
    help_str = {}
    description = ""
    for cmd in dispatch._valid_commands(fix_underscores=False):
        lines = inspect.getdoc(getattr(dispatch, cmd)).split("\n")
        help_str[cmd.replace('_','-')] = "\n".join(lines).strip()
        lines[0] = lines[0][0].lower() + lines[0][1:]
        description += "  {0:<20}  {1}\n".format(cmd, lines[0])

    # Specify parameters for the command line interface
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, add_help=False, description=description)
    parser.add_argument('command', type=str, nargs='?',
                        help='a command for anvil to run')
    parser.add_argument('args', type=str, nargs='*', default=[],
                        help='arguments to the command')
    parser.add_argument('-f', '--file', nargs='?', type=str,
                        default=None,
                        help='the ledger file to parse')
    parser.add_argument('-h', '--help', action='store_true', dest='help',
                        help='display this help message and exit')

    # Run the argument parser
    args = vars(parser.parse_args())

    # Detailed help for `anvil.py -h foo`
    if args['help']:
        if not args['command']:
            parser.print_help()
            sys.exit()
            return
        if not args['command'] in dispatch._valid_commands():
            sys.stderr.write("Unknown command: %s\n" % args['command'])
        else:
            print "%s: %s" % (args['command'].upper(), help_str[args['command']])
        sys.exit()

    if not args.command: args.command = 'audit'

    # Handle file argument
    if args['file']:
        c['ledger-file'] = args['file']
    del args['file'] # ensure later funcs don't rely on the wrong source of the file name

    # Munge and validate command
    valid_commands = dispatch._valid_commands()
    if not args['command'] in valid_commands:
        parser.print_help()
        print "\nUnknown command (%s).  Please try one of these: %s" % (args['command'], " ".join(valid_commands))
        sys.exit()
    args['command'] = args['command'].replace('-','_')
    return args

class Dispatch():
    """This class is a little bit magic. Any method defined here becomes a
    valid command and dispatch to the method is automatic from
    main. Likewise, if it's not defined here, our command line parser
    will reject it as a command.

    For each method, we get the command line args in kwargs. Let's
    make a rule that we do not pass those args through wholesale. No
    passing all the kwargs to our implementation classes. Take what
    you need and set the right class parameters. This might help with
    separating interface and implementation.

    Method comments are magic too. Line one gets automatically snarfed
    into the help description for the command. The whole message gets
    displayed if the user requests detailed help on the command.

    It would be neat if parse_args pulled the valid commands from here
    not just for the valid_commands list but also for
    parser.add_arguments.

    TODO: don't include methods that start with _ in parse.arg's valid_commands

    """

    banks = None

    def _valid_commands(self, fix_underscores=True):
        cmds = [m[0] for m in inspect.getmembers(self, predicate=inspect.ismethod) if not m[0].startswith("_")]
        if fix_underscores: return [c.replace('_','-') for c in cmds]
        return cmds

    def _load_banks(self):
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
            accountant.monthly_bal(account, cl_display.monthly_bal)

    def reconcile(self, **kwargs):
        """Match transactions in the ledger and bank statements."""
        pass

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
    getattr(Dispatch(), args['command'])(**args)

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
    args = parse_args()
    fix_paths()
    dispatch(args['command'], args)

if __name__ == "__main__":
    main()
