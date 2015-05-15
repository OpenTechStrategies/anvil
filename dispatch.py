import inspect
class Dispatch(object):
    """This class is a little bit magic. Any method defined here becomes a
    valid command and dispatch to the method is automatic from
    main. Likewise, if it's not defined here, our command line parser
    will reject it as a command.

    For each method, we get the command line args in kwargs. Let's
    make a rule that we do not pass those args through wholesale. No
    passing all the kwargs to our implementation classes. Take what
    you need and set the right class parameters. This might help with
    separating interface and implementation.

    Method doc strings are magic too. Line one gets automatically snarfed
    into the help description for the command. The whole message gets
    displayed if the user requests detailed help on the command.

    Also this doc string stuff means that you'll want to put the
    user-facing documentation in the first doc string and the dev
    documentation in a separate doc string immediately after the first.

    It would be neat if parse_args pulled the valid commands from here
    not just for the valid_commands list but also for
    parser.add_arguments.

    _valid_commands(fix_underscore) is a method that returns a list of the names of
    the methods to this class. It filters out any method whose name
    starts with an underscore. It takes a parameter, fix_underscores,
    which defaults to True. It replaces '_' with '-' in the output
    list of names. This is because command line args might use '-' for
    word separation.

    _help(command) returns the documentation for the specified
    command. Basically, it grabs the doc string from the method so we
    can display it to the user.

    _describe(command, lower) returns the short documentation for the
    specified command. Basically, it grabs the first line from the
    doc string, lowercases the first char if lower is true (the
    default), and returns it for display to the user.

    Add a command to _undocumented to indicate that it should be
    somewhat hidden from the user.

"""
    _undocumented = []

    def _valid_commands(self, fix_underscores=True):
        cmds = [m[0] for m in inspect.getmembers(self, predicate=inspect.ismethod) if not m[0].startswith("_")]
        if fix_underscores: return [c.replace('_','-') for c in cmds]
        return cmds

    def _help(self, cmd):
        "Returns the documentation for the specified command method."
        if '-' in cmd:
            cmd = cmd.replace('-','_')
        lines = inspect.getdoc(getattr(self, cmd)).split("\n")
        return "\n".join(lines).strip()

    def _describe(self, cmd, lower=True):
        if '-' in cmd:
            cmd = cmd.replace('-','_')
        lines = inspect.getdoc(getattr(self, cmd)).split("\n")
        if lower: lines[0] = lines[0][0].lower() + lines[0][1:]
        return "  {0:<20}  {1}\n".format(cmd, lines[0])

