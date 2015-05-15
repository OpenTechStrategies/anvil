"""Command line display objects"""

import sys
from namespace import Namespace
import display

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

        TODO: there's gotta be a pretty table printer class out
        there. What the heck am I doing calculating column widths and
        such?

        """
        out = ""
        padding=2
        widths = [0,0,0,0,0]
        cols = ["As of", "Statement Bal", "Ledger Bal", "Monthly Delta", "Cumu Delta"]
        first = False
        last = 0
        for m in self.months:
            if not first:
                if m.end_date != first_continuous:
                    continue
            first = True
            cumu = m.statement_bal - m.ledger_bal
            monthly = cumu - last
            widths[0] = max(widths[0], len(cols[0]) + padding, len(str(m.end_date)))
            widths[1] = max(widths[1], len(cols[1]) + padding, len(str(m.statement_bal)))
            widths[2] = max(widths[2], len(cols[2]) + padding, len(str(m.ledger_bal)))
            widths[3] = max(widths[3], len(cols[3]) + padding, len(str(monthly)))
            widths[4] = max(widths[4], len(cols[4]) + padding, len(str(cumu)))
            last = cumu
        for idx in range(0,5):
            heading = cols[idx]
            width = widths[idx]
            fmtstr = "|{0:^%d}" % width
            out += fmtstr.format(heading)
        out += "|\n"
        first = False
        last = 0
        for m in self.months:
            if not first:
                if m.end_date != first_continuous:
                    continue
            first = True
            fmtstr = "|"
            for idx in range(0,5):
                width = widths[idx]
                fmtstr += "{%d:>%d}|" % (idx, width)
            cumu = m.statement_bal - m.ledger_bal
            monthly = cumu - last
            out += fmtstr.format(m.end_date, m.statement_bal, m.ledger_bal, monthly, cumu) + "\n"
            last = cumu
        if self.output_file == "-":
            print out
        else:
            with open(self.output_file, 'w') as OUTF:
                OUTF.write(out)

