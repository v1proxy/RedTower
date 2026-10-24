# Broker setup on Home Assistant (your step, about 3 minutes)

I do not create accounts or type passwords, so this part is yours.

1. Settings, Add-ons, Mosquitto broker, Configuration.
2. Under Logins add two entries. Choose your own passwords:

       - username: gh_core
         password: <choose one>
       - username: gh_module
         password: <choose another>

3. Save and restart the add-on.
4. On the machine that runs the stack, copy `jetson/.env.example` to `jetson/.env` and put the
   two passwords in it. The file stays on that machine and is never shared.

Optional, recommended before the arm is live: the access list in `jetson/mosquitto-acl.sample`.
It is what stops a module from writing actuator or approval topics directly. It needs the
Mosquitto add-on's "customize" folder. The sample has no entry for Home Assistant's own login:
add one before installing it, or Home Assistant loses MQTT. The bench check appends exactly
this (`homeassistant` is the user Home Assistant's MQTT integration logs in with on the add-on):

       user homeassistant
       topic readwrite #
 The list itself has been tested on a bench Mosquitto
(36 of 36). Once it is installed on the add-on, prove it there from the Jetson:

       python tools_acl_check.py

Every probe uses a name no live service acts on, so it can run with the stack up. If the list
is missing, two probes do get through, in the safe direction: the kill switch turns on and
the governor drops to authority off. Set both back in Home Assistant.
