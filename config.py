import util as u
import simplejson as json
c = json.loads(u.slurp("etc/config.json", split=False))
