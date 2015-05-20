import os, sys
import simplejson as json
import util as u
from errs import ConfigError

import __main__

path = None
for p in ["etc/config.json", 
          "/etc/config.json", 
          os.path.join(os.path.split(__main__.__file__)[0], "etc/config.json"),
          os.path.join(os.path.split(__file__)[0], "etc/config.json")]:
    if os.path.exists(p):
        path = p
    else:
        print p

if path:
    config = json.loads(u.slurp(path, split=False))
else:
    raise ConfigError("Can't find config.json anywhere!")

