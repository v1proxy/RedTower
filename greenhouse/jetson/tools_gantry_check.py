"""First contact with the FluidNC controller (commissioning step 9). Stop gh-gantry first:
only one program may hold the serial port.

  python tools_gantry_check.py /dev/ttyUSB0            read only: version, state, position, inputs
  python tools_gantry_check.py /dev/ttyUSB0 --home     also run one homing cycle

--home moves the gantry outside the safety governor. Close the doors, park the arm and keep a
hand on the E-stop. The door chain and the E-stop still cut motor power through the relay.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh.mods.fluidnc import FluidNC, SerialLink           # noqa: E402


def pump(ctl, seconds, until=lambda: False):
    end = time.time() + seconds
    while time.time() < end and not until():
        ctl.poll()
        time.sleep(0.2)
    return until()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    link = SerialLink(sys.argv[1])
    raw = []
    read = link.read
    link.read = lambda: raw.append(read()) or raw[-1]          # keep a copy of everything the board says
    ctl = FluidNC(link, time.time)
    ok = pump(ctl, 5, lambda: ctl.last_report is not None and not ctl.pending)
    text = b"".join(raw).decode("ascii", "replace")
    for line in text.splitlines():
        if line.startswith(("[VER", "[OPT", "Grbl", "[MSG")):
            print(line)
    if not ok:
        link.close()
        sys.exit("FAIL  no answer to $I or to a status request: wrong port, wrong baud, or the board is booting")
    last = [l for l in text.splitlines() if l.startswith("<")][-1]
    print("PASS  controller answers")
    print("      status", last)
    print("      state", ctl.state, "position X Z", ctl.mpos)
    if "Pn:" in last:
        print("      inputs active now:", last.split("Pn:")[1].split("|")[0].rstrip(">"),
              "(X, Z limit switches; D door; when nothing is pressed this should be empty)")
    if "--home" in sys.argv:
        print("homing, up to 90 s ...")
        ctl.home()
        done = pump(ctl, 90, lambda: not ctl.homing)
        if done and ctl.homed:
            print("PASS  homed, machine position X Z", ctl.mpos)
        else:
            print("FAIL  homing:", ctl.alarm or ctl.error or "timed out")
            ctl.stop()
            pump(ctl, 2)
    link.close()


if __name__ == "__main__":
    main()
