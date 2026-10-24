# Module — arm, vision and the Jetson

*The arm and gantry chapters are written as part of the 0.2.0 work, when the
generators are driven by the solver. The Jetson bring-up below is complete and
tested on the reference build.*

## The tool: Herb Snip

The arm carries one printed tool, the Herb Snip: a servo-driven blade that cuts a stem and
holds what it cut in the same closing. A dead leaf rides in the folded jaws to Harvest
Rev B's dead-leaf tray in the base bay and is let go over it; leaves and veggies go out
through the right panel into its feeder at tier B. It goes on the 280's flange with four
LEGO pins, through its camera ring, and replaces the adaptive gripper: 95.9 g of tool and
58 g of D405, 96 g of the payload left. Everything about it, the booklet, the print files
and the BOM, is in
[`greenhouse/snip/`](../greenhouse/snip/HERB_SNIP.md), and its booklet can be read
[page by page](booklets/snip.md); commissioning is section 7b of
[`greenhouse/COMMISSIONING.md`](../greenhouse/COMMISSIONING.md).

## Jetson bring-up

Everything above the node firmware runs on one Jetson Orin Nano Super developer
kit: the four core services, the drivers, the services and the agents, each in
its own container. This is how to get one from the box to a running core layer,
including the two traps that will otherwise cost you an evening.

Tested with JetPack 7.2.1 (Jetson Linux r39.2.1, Ubuntu 24.04) in October 2026.

### What you need

- Jetson Orin Nano Super developer kit and its 19 V supply.
- An M.2 2280 NVMe SSD. It goes in the **2280 slot, PCIe Gen3 x4**, not the short
  2230 one. A Gen4 drive works and runs at Gen3 speed. Use a bare drive: the slot
  sits under the module and heatsinked drives may not fit.
- A USB stick of 16 GB or more. It will be erased.
- For the first boot only: a DisplayPort monitor (or HDMI through a DP adapter),
  a USB keyboard and a mouse. After that the Jetson runs headless.

You do not need an Ubuntu PC. JetPack 7.2 installs from a USB stick.

### 1. Check the firmware

With monitor and keyboard connected, power on and tap **Esc** at the NVIDIA logo.
The firmware version is at the top of the UEFI menu.

- **36.x or newer:** go on.
- **Older than 36.0:** follow NVIDIA's *JetPack 6.x Update Path* first. It needs a
  microSD card.

### 2. Make the installer stick

Download the Jetson ISO for the current JetPack from NVIDIA's
[JetPack downloads](https://developer.nvidia.com/embedded/jetpack/downloads)
and write it to the USB stick with [balenaEtcher](https://etcher.balena.io).
You do not need to format the stick first; Etcher overwrites it. Copying the ISO
onto the stick as a file does not work.

When Windows offers to format the stick afterwards, click **Cancel**. It cannot
read the Linux partitions, and formatting would destroy the installer.

The NVMe does not need preparing either. The installer repartitions it.

### 3. Install, and press Y

Put the SSD in, plug in the stick, power on, tap **Esc**, choose **Boot Manager**,
then the USB stick.

> **Trap one.** Before the install menu, the installer asks to update the QSPI
> firmware, with a 30 second countdown. **Press Y.** If the countdown runs out,
> the install still completes, but the first boot hangs on a black screen with a
> blinking cursor and the board reboots itself in a loop. The firmware will still
> read 36.x in the UEFI menu. Nothing is broken: run the installer again and press
> Y this time.

The update runs in two passes and reboots in between. Then choose
**Install Jetson ISO**, pick the NVMe, confirm, and reboot when told to.

The installer itself does not ask for a user name. That happens on the first
boot of the installed system: accept the licence, set language and time zone,
join your network, and create the user. Name the computer `greenhouse`. Skip
Ubuntu Pro.

Do not pick MAXN SUPER. This workload is light and the board lives in a closed
cabinet; set 15 W below.

### 4. Get SSH working

> **Trap two.** On a fresh install the SSH server can refuse every connection
> (`kex_exchange_identification: read: Connection reset`). The host keys were
> never generated: NVIDIA's first-boot key service skips itself whenever the
> cloud-init package is installed, even though cloud-init is disabled. On the
> Jetson, open a terminal (Ctrl+Alt+T) and run once:
>
> ```bash
> sudo ssh-keygen -A; sudo systemctl reset-failed; sudo systemctl restart ssh.socket ssh
> ```
>
> The keys are permanent after that.

Then install your key from your PC (`ssh-copy-id`, or append it to
`~/.ssh/authorized_keys`), and unplug the monitor, keyboard and mouse.

### 5. Base settings

```bash
sudo apt update && sudo apt full-upgrade -y     # reboot when it finishes
sudo nvpmodel -m 0                               # 15 W
sudo usermod -aG docker $USER                    # log out and in again
sudo apt install -y docker-compose-v2
```

JetPack 7.2.1 already ships Docker and the NVIDIA container toolkit. Check that
containers see the GPU:

```bash
docker run --rm --runtime nvidia ubuntu:24.04 ls /usr/lib/aarch64-linux-gnu/nvidia
```

Headless, the case power button does nothing useful by default. This makes a
short press a clean shutdown (takes effect after the next reboot):

```bash
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandlePowerKey=poweroff\nPowerKeyIgnoreInhibited=yes\n' |
  sudo tee /etc/systemd/logind.conf.d/50-greenhouse-power-button.conf
```

### 6. RealSense D405

Install the SDK from the RealSense apt repository. The repository is now signed
with a new key; the old `librealsense.pgp` fails with `NO_PUBKEY
FB0B24895113F120`, so use `librealsenseai.asc`:

```bash
sudo mkdir -p /etc/apt/keyrings
curl -sSf https://librealsense.realsenseai.com/Debian/librealsenseai.asc |
  gpg --dearmor | sudo tee /etc/apt/keyrings/librealsenseai.gpg >/dev/null
echo "deb [signed-by=/etc/apt/keyrings/librealsenseai.gpg] https://librealsense.realsenseai.com/Debian/apt-repo $(lsb_release -cs) main" |
  sudo tee /etc/apt/sources.list.d/librealsense.list
sudo apt update && sudo apt install -y librealsense2-utils librealsense2-udev-rules
rs-enumerate-devices -s
```

For Python, the `pyrealsense2` wheel on PyPI has an aarch64 build for Python
3.12. Keep it in a venv:

```bash
python3 -m venv /opt/greenhouse/venv
/opt/greenhouse/venv/bin/pip install pyrealsense2 opencv-python-headless numpy
```

Plug the camera into a USB 3 port (the blue ones). Then, from
`greenhouse/jetson/prototype/`:

- `d405_fps.py` should report a true 30 fps at 848x480 with depth aligned to
  colour. (`d405_check.py` reports about 20; that is its own start-up time.)
- `d405_leaf.py` measures depth quality on a real plant in the arm's working
  band. On the reference build, under ordinary room light: 94 % fill and
  0.8 mm frame-to-frame noise at 225 to 333 mm; 97 % and 2.3 mm at 340 to 525 mm.

A plain wall returns no depth at all. The D405 has no IR projector and needs
texture. Inside the cabinet that is a feature: the back panel drops out and the
plants stand out.

### 7. The broker

The message broker is the Mosquitto app on Home Assistant, not on the Jetson,
so Home Assistant still sees the Jetson die if it does.

1. In Home Assistant, **Settings → Apps → Install app → Mosquitto broker**.
   Install it, turn on **Start on boot** and **Watchdog**, start it, and accept
   the MQTT integration Home Assistant then offers.
2. Copy `greenhouse/jetson/` to the Jetson (here `/opt/greenhouse/stack`) and
   create its `.env` with two long random passwords. Never commit `.env`.

   ```bash
   cd /opt/greenhouse/stack
   umask 077
   sed -e "s|^GH_CORE_PASSWORD=.*|GH_CORE_PASSWORD=$(openssl rand -hex 24)|" \
       -e "s|^GH_MODULE_PASSWORD=.*|GH_MODULE_PASSWORD=$(openssl rand -hex 24)|" \
       .env.example > .env
   ```

3. Give the broker the same two logins. In the Mosquitto app, **Configuration →
   ⋮ → Edit in YAML**, and set `logins` to:

   ```yaml
   logins:
     - username: gh_core
       password: "<GH_CORE_PASSWORD from .env>"
     - username: gh_module
       password: "<GH_MODULE_PASSWORD from .env>"
   ```

   Save, then restart the app.

`mosquitto-acl.sample` restricts what each of the two users may write. It is not
applied yet; until it is, both users can write every topic.

### 8. Start the core layer

```bash
cd /opt/greenhouse/stack
docker compose build supervisor
docker compose run --rm --no-deps -v "$PWD:/src:ro" -w /src supervisor python tools_broker_check.py
docker compose up -d supervisor safety store bridge
```

The broker check should pass all six checks. Start **only** the four core
services: the supervisor starts and stops the other modules, but only containers
compose has already created, so drivers and agents stay off until you bring up
the hardware they drive.

Within a minute Home Assistant shows a device called **Greenhouse** with about
220 entities. The four core services read *running*; the rest read *offline*,
*degraded*, *paused* or *disabled*, which is the honest state of a greenhouse
with no hardware yet. The services restart on their own after a reboot or power
cut, and are back in Home Assistant about 40 seconds after boot.

The unit tests run inside the same image:

```bash
docker compose run --rm --no-deps -v "$PWD:/src:ro" -w /src -e PYTHONDONTWRITEBYTECODE=1 supervisor \
  sh -c "pip install -q -r requirements-test.txt pytest && python -m pytest -q -p no:cacheprovider tests"
```
