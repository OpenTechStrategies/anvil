import util as u
import simplejson as json
config = json.loads(u.slurp("etc/config.json", split=False))
