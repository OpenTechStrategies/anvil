#from errs import UnimplementedError
from namespace import Namespace

class Display():
    """Display callbacks that get passed in to the implementation to handle display.

    TODO: define the API for Display objects. Or maybe each object has
    its own API to a degree.

    """

    # These values get inherited by the display classes. If you change
    # these values, change them *before* you instantiate your display
    # class. Otherwise the changes won't be inherited.

    output_file = "-" # stdout. Set to something else for something else.

class Monthly_Bal(Display):
    months = []
    def add(self, end_date, statement_bal, ledger_bal, last_month):
        self.months.append(Namespace({'end_date':end_date, 'statement_bal':statement_bal, 'ledger_bal':ledger_bal, 'last_month':last_month}))


    def done(self, first_continuous):
        """This method is called when all the statement periods have been
        compared to the ledger. 

        On the command line, we can now display the results as we've
        held off until now. For other interfaces, maybe you display as
        soon as you get the results and this method doesn't really do
        anything.

        first_continuous is the first month that, going backwards from the
        last month, forms an unbroken string of unbalanced months. We
        want to know this because gaps in the series of unbalanced
        months usually indicate correct entries that got recorded in
        our ledger in a different month than they do in our bank
        statements. Usually this is because they happened near the
        boundaries of the statement period. We can generally ignore
        them, as they aren't errors that affect the final totals.
        """
        raise NotImplementedError, "Monthly_Bal not implemented for this interface."""
