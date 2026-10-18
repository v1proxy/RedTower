"""Every MQTT topic the system uses, in one place.

The module contract is five endpoints under greenhouse/<module>/:
  enable   retained ON/OFF, owned by the supervisor. Write to enable/set to change it.
  status   retained JSON, owned by the supervisor: the one state the interface shows.
  health   JSON heartbeat written by the module itself. The broker writes the
           last-will version ({"alive": false}) if the module dies.
  config   retained JSON. Write to config/set to change it.
  cmd      JSON commands into the module.
"""
ROOT = "greenhouse"

LAYERS = ("core", "driver", "service", "agent")
AUTHORITY = ("off", "manual", "auto", "proposes", "autonomous")


def enable(m): return f"{ROOT}/{m}/enable"
def enable_set(m): return f"{ROOT}/{m}/enable/set"
def status(m): return f"{ROOT}/{m}/status"
def health(m): return f"{ROOT}/{m}/health"
def config(m): return f"{ROOT}/{m}/config"
def config_set(m): return f"{ROOT}/{m}/config/set"
def cmd(m): return f"{ROOT}/{m}/cmd"
def cycle(m): return f"{ROOT}/{m}/cycle"


AUTHORITY_STATE = f"{ROOT}/authority"
AUTHORITY_SET = f"{ROOT}/authority/set"
KILL_STATE = f"{ROOT}/kill"
KILL_SET = f"{ROOT}/kill/set"

# Safety governor. Nothing but the governor may publish under greenhouse/actuator/.
SAFETY_REQUEST = f"{ROOT}/safety/request"          # modules
SAFETY_REQUEST_UI = f"{ROOT}/safety/request/ui"    # the interface only (broker ACL)
STORE_CMD_UI = f"{ROOT}/store/cmd/ui"              # the interface only (broker ACL)
SAFETY_PENDING = f"{ROOT}/safety/pending"
def verdict(req_id): return f"{ROOT}/safety/verdict/{req_id}"
def actuator_set(a): return f"{ROOT}/actuator/{a}/set"
def proposal(pid): return f"{ROOT}/proposal/{pid}"
def proposal_decision(pid): return f"{ROOT}/proposal/{pid}/decision"
def interlock(name): return f"{ROOT}/interlock/{name}"

def plant(position): return f"{ROOT}/plant/{position}"
def log(kind): return f"{ROOT}/log/{kind}"

HA_STATUS = "homeassistant/status"

# Sensor values normalised by the ESPHome link (SI units, retained JSON {"v": value, "ts": time})
def sensor(key): return f"{ROOT}/sensor/{key}"
def photo(position): return f"{ROOT}/photo/{position}"        # latest JPEG, raw bytes, retained
def observation(position): return f"{ROOT}/observation/{position}"
def vision(position): return f"{ROOT}/vision/{position}"              # overview camera, per pot
PROPOSALS = f"{ROOT}/safety/proposals"                        # retained JSON list for the interface
HA_STATE = f"{ROOT}/ha"                                       # Home Assistant mqtt_statestream base
