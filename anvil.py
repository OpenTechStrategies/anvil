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

from config import c
from chase import Chase
from errs import ConfigError
import util as u

def parse_args():
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description="""A helper for ledger.\n\ncommands:
  audit                 run all available tests on the ledger file
  monthly-bal           check ending balances of monthly statements against ledger""")
    parser.add_argument('command', type=str, nargs='?', default='audit',
                        help='a command for anvil to run')
    parser.add_argument('args', type=str, nargs='*', default=[],
                        help='arguments to the command')
    parser.add_argument('-f', '--file', nargs='?', type=str,
                        default=None,
                        help='the ledger file to parse')

    args = vars(parser.parse_args())

    # Handle file argument
    if args['file']:
        c['ledger-file'] = args['file']
    del args['file']

    # Munge and validate command
    args['command'] = args['command'].replace('-','_')
    valid_commands = [m[0].replace('_','-') for m in inspect.getmembers(Dispatch(), predicate=inspect.ismethod)]
    if not args['command'] in valid_commands:
        parser.print_help()
        print "\nUnknown command (%s).  Please try one of these: %s" % (args['command'], " ".join(valid_commands))
        sys.exit()
    return args

class Dispatch():
    """This class is a little bit magic. Any method defined here becomes
    a valid command and dispatch to the method is automatic from main.
    """
    def audit(self, **kwargs):
        """Look for problems in the ledger file."""

        chase = Chase()
        chase.load_accounts()
        print c
        sys.exit()
        print "audit"
        print kwargs
    def monthly_bal(self, **kwargs):
        pass
def dispatch(command, args):
    """Call the method of Dispatch that has the same name as
    `command`. Pass args as kwargs in the call.

    """
    getattr(Dispatch(), args['command'])(**args)

def main():
    args = parse_args()
    c['ledger-file'] = u.fix_path(c['ledger-file'], c['OTS-root'])
    dispatch(args['command'], args)

if __name__ == "__main__":
    main()
