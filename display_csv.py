"""Command line display objects"""

import sys
from namespace import Namespace
import display
import csv
import cStringIO as StringIO

class Monthly_Bal(display.Monthly_Bal):
    def done(self, first_continuous):
        """This method is called when all the statement periods have been
        compared to the ledger. On the command line, we can now
        display the results as we've held off until now. For other
        interfaces, maybe you display as soon as you get the results
        and this method doesn't really do anything.

        first_continuous is the first month that, going backwards from the
        last month, forms an unbroken string of unbalanced months. We
        want to know this because gaps in the series of unbalanced
        months usually indicate correct entries that got recorded in
        our ledger in a different month than they do in our bank
        statements. Usually this is because they happened near the
        boundaries of the statement period. We can generally ignore
        them, as they aren't errors that affect the final totals.

        We output csv in excel format.
        """
        csvfile = StringIO.StringIO()
        csvwriter = csv.writer(csvfile, dialect=csv.excel)
        csvwriter.writerow(["As of", "Statement Bal", "Ledger Bal", "Monthly Delta", "Cumu Delta"])

        first = False
        last = 0
        for m in self.months:
            if not first:
                if m.end_date != first_continuous:
                    continue
            first = True
            cumu = m.statement_bal - m.ledger_bal
            monthly = cumu - last
            csvwriter.writerow([m.end_date, "$%s" % m.statement_bal, "$%s" % m.ledger_bal, "$%s" % monthly, "$%s" % cumu])
            last = cumu

        if self.output_file == "-":
            print csvfile.getvalue()
        else:
            with open(self.output_file, 'w') as OUTF:
                OUTF.write(csvfile.getvalue())
        csvfile.close()

