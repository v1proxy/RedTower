# Commissioning the greenhouse software

The order to bring the stack up on the real hardware. Each step names the tool that proves it
and what a pass looks like. Do not skip ahead: every step leans on the ones before it.
Mechanical build and wiring are in the Herb Tower Design Basis; this covers the software.

## 1. Network and broker

1. pfSense, Services, DHCP Server, IOT: static mappings for the Jetson (192.168.10.20,
   hostname REDGrow), the four ESPHome nodes (.21 to .24) and the arm's Raspberry Pi (.25).
   See `pfsense/jetson-network-plan.md`.
2. Home Assistant, Mosquitto add-on: create the users `gh_core` and `gh_module`
   (`ha/mosquitto-setup.md`).
3. Install the access list (`jetson/mosquitto-acl.sample`) in the add-on's customize folder.

## 2. Jetson

1. Docker, plus `/etc/docker/daemon.json` with `{"dns": ["192.168.10.1"]}` (IoT DNS is pfSense only).
2. Clone this repository over HTTPS (SSH to the internet is blocked on IoT).
3. `cd greenhouse/jetson`, copy `.env.example` to `.env`, fill in the two broker passwords and
   the Claude API key.
4. `python tools_broker_check.py`. Pass: 6 of 6.
5. `python tools_acl_check.py`. Pass: 37 of 37. If the access list is missing, two probes get
   through in the safe direction (kill switch on, authority off): set them back.
6. `docker compose build`, then `docker compose up -d`. Every module starts on its simulated
   backend, so the stack runs before any hardware is plugged in.
   This is the first arm64 build: if `pyrealsense2` fails to install, report the error.

## 3. Home Assistant

1. Copy `ha/packages/greenhouse_jetson.yaml` next to the existing `greenhouse.yaml` package, and
   `ha/www/greenhouse/greenhouse-panel.js` to `/config/www/greenhouse/`.
2. Settings, Dashboards, Resources: add `/local/greenhouse/greenhouse-panel.js` (JavaScript module).
3. Add the view in `ha/dashboard_view.yaml` to the Red Tower dashboard, without `demo: true`.
4. Replace `notify.notify` in the package with your phone's notify service. Restart.
5. Pass: the Greenhouse view shows every module with its status; Supervisor reads Running.
   The same checks run against a bench Home Assistant with `tools_ha_check.py`.

## 4. ESPHome nodes

1. Flash the four nodes and adopt them (Design Basis, commissioning steps 4 to 6).
2. Pass: in the panel, ESPHome link reads Running and the door, E-stop and water interlocks
   read OK (open a door: door reads OPEN).

## 5. Water

1. Review `jetson/config/limits.yaml`. The values are starting values.
2. Authority Manual. Run each zone from the panel into a bucket. Wet each leak probe and lift
   the float: watering stops and the governor denies new runs.
3. Authority Auto. Irrigation waters by soil moisture from now on.

## 6. Gantry

1. FluidNC config on the Jackpot3: status reports in machine position (MPos), steppers kept
   enabled when idle, homing on, soft limits on, the door chain on the safety-door input.
2. `docker stop gh-gantry`, then `python tools_gantry_check.py /dev/serial/by-id/... --home`.
   Pass: the board answers, and one homing cycle completes.
3. Jog to each pot and write the carriage X per pot, Z per tier, the travel and the park
   position into `jetson/config/robot.yaml` (they are placeholders until then).
4. Gantry config: `backend: fluidnc`, `port:` the by-id path. Start gh-gantry.
5. Pass: from the panel, Home and then Photo now on one plant; the gantry homes first.

## 7. Arm

1. On the arm's Pi: pymycobot's socket server running at boot, on port 9000.
2. `python tools_arm_check.py 192.168.10.25`. Pass: connects, servo power on, joint angles read.
3. Teach `stow` (folded inside the 174 mm lane, clear of both rails) and `look` (the D405 about
   200 mm in front of the pot): `--release`, pose by hand, `--lock`, read the angles, write them
   into `jetson/config/arm.yaml`. Then `taught: true`. Until then the real arm never moves.
4. Arm config: `backend: mycobot`, `host: 192.168.10.25`.
5. Pass: the panel shows the arm Parked; the gantry refuses to move while the arm is out.

## 8. Cameras

1. `python tools_d405_check.py out` on a plant. Pass: candidates on the annotated image.
   Depth camera config: `backend: realsense`.
2. Hand-eye: fix a chessboard in the cabinet (20 mm squares halved the error of 10 mm ones in
   simulation; measure a printed square with calipers), then
   `python tools_handeye_calibrate.py capture calib --host 192.168.10.25` for 10 to 15 poses with
   the wrist tilted and rolled 40 degrees or more, and `... solve calib --square <mm>`. Pass:
   spread under 8 mm, ideally under 3.
3. Overview camera: `python tools_widecam_check.py <device> out`, draw a box round each pot on
   `widecam_frame.jpg` and write them into `jetson/config/widecam.yaml`. Overview camera config:
   `backend: v4l2`, `device:` the by-id path.
4. Pass: the daily photo route captures every living plant; the overview sensors update at
   11:00 and 19:00.

## 9. Agents

1. Set each plant's type in the panel (Replace plant). The tender reasons far better with them.
2. Authority Agent proposes. Watch a few days of the environment agent's output and the
   proposals before approving anything: the reasons matter more than the actions.
3. Cuts: every cut is a tend task the owner approves, in every mode. On the real arm, approach
   and cut stay refused until they are tuned on the hardware.
4. Authority Agent autonomous only after that. The kill switch stops every agent at once.
