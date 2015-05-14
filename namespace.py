"""namespace module

James adjusted this code so it works with Python 2.x. He's not sure if
that means it *won't* work with python 3.x, but the original version
is available at the url below.

https://code.activestate.com/recipes/577887-a-simple-namespace-class/
says this is licensed under the MIT license, but does not provide a
copy of the license to reproduce. A generic version of the license
doesn't quite suit because it doesn't have the copyright year or
copyright holders. Still, the webpage says Eric Snow "created" the
code in 2011, so:

The MIT License (MIT)

Copyright (c) 2011, Eric Snow

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

__all__ = ("Namespace", "as_namespace")

from collections import Mapping, Sequence

class _Dummy: "..."
CLASS_ATTRS = dir(_Dummy)
del _Dummy


class Namespace(dict):
    """A dict subclass that exposes its items as attributes.

    Warning: Namespace instances do not have direct access to the
    dict methods.

    """

    def __init__(self, obj={}):
        dict.__init__(self, obj)

    def __dir__(self):
        return tuple(self)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict.__repr__(self))

    def __getattribute__(self, name):
        try:
            return self[name]
        except KeyError:
            msg = "'%s' object has no attribute '%s'"
            raise AttributeError(msg % (type(self).__name__, name))

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    #------------------------
    # "copy constructors"

    @classmethod
    def from_object(cls, obj, names=None):
        if names is None:
            names = dir(obj)
        ns = {name:getattr(obj, name) for name in names}
        return cls(ns)

    @classmethod
    def from_mapping(cls, ns, names=None):
        if names:
            ns = {name:ns[name] for name in names}
        return cls(ns)

    @classmethod
    def from_sequence(cls, seq, names=None):
        if names:
            seq = {name:val for name, val in seq if name in names}
        return cls(seq)

    #------------------------
    # static methods

    @staticmethod
    def hasattr(ns, name):
        try:
            object.__getattribute__(ns, name)
        except AttributeError:
            return False
        return True

    @staticmethod
    def getattr(ns, name):
        return object.__getattribute__(ns, name)

    @staticmethod
    def setattr(ns, name, value):
        return object.__setattr__(ns, name, value)

    @staticmethod
    def delattr(ns, name):
        return object.__delattr__(ns, name)


def as_namespace(obj, names=None):

    # functions
    if isinstance(obj, type(as_namespace)):
        obj = obj()

    # special cases
    if isinstance(obj, type):
        names = (name for name in dir(obj) if name not in CLASS_ATTRS)
        return Namespace.from_object(obj, names)
    if isinstance(obj, Mapping):
        return Namespace.from_mapping(obj, names)
    if isinstance(obj, Sequence):
        return Namespace.from_sequence(obj, names)
    
    # default
    return Namespace.from_object(obj, names)
