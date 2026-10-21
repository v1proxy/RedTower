"""The Herb Snip from the Jetson, through the arm's end connector (Herb Snip booklet, step 12).
Stop gh-arm first. Needs the arm powered, pymycobot's socket server on its Pi, and the servo's
signal and ground on the end connector's G22 and GND (booklet, wiring page).

  python tools_snip_check.py 192.168.10.25              read only: the snip block and its duty steps
  python tools_snip_check.py 192.168.10.25 pulse 1500   one pulse width in microseconds: finding the ends
  python tools_snip_check.py 192.168.10.25 close        arm.yaml's closed_us
  python tools_snip_check.py 192.168.10.25 open         arm.yaml's open_us
  python tools_snip_check.py 192.168.10.25 pwm          open and close three times: the pulses reach the servo
  python tools_snip_check.py 192.168.10.25 cut          close, hold 2 s, open: a stem in the jaws is cut and held
  python tools_snip_check.py 192.168.10.25 limp         no pulses: the jaw can be pushed open by hand
  python tools_snip_check.py stem --empty               the D405 with the jaws empty: saves the reference
  python tools_snip_check.py stem                       is anything in the jaws? compared with the reference

Finding the two pulses (calibrated: false until then; the real arm sends none in service):
  1. pulse 1500, then pulse 2400. If the horn turned clockwise seen from the horn side, the closed
     end is the long pulse; if anticlockwise, it is the short one (600). Fit the crank there (step 6).
  2. Step the closed pulse toward the anvil, 78 us at a time, until the blade just reaches it, then
     one step more so the servo presses: that is closed_us.
  3. open_us is about 1700 us from it on the other side: the jaw at 55 degrees, the crank short of
     the body. If the servo runs out of travel first, take its end: the jaw opens a little less.
  4. Write both into config/arm.yaml, then calibrated: true.
One duty step is 78 us, about 7 degrees of servo: that is the finest the end connector can do.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gh.mods import snip as S                              # noqa: E402
from gh.mods.arm import load_spec                          # noqa: E402

REF = HERE / "snip_empty_depth.npy"


def spec():
    return (load_spec(HERE / "config" / "arm.yaml").get("snip") or {})


def show(sp):
    for line in S.check_spec(sp):
        print("FAIL ", line)
    hz = sp.get("hz", 50)
    for key in ("closed_us", "open_us"):
        if isinstance(sp.get(key), (int, float)):
            try:
                d = S.duty(sp[key], hz)
                print(f"      {key} {sp[key]} -> duty {d} of 256 at {hz} Hz = {S.pulse_us(d, hz):.0f} us")
            except ValueError as exc:
                print("FAIL ", exc)
    print("      calibrated", bool(sp.get("calibrated")))


def stem(opts):
    import numpy as np
    from gh.mods.d405 import RealSense
    sp = spec()
    cam = RealSense()
    _, depth, intr = cam.grab()
    cam.close()
    roi = S.jaw_roi(intr, sp["stem_view"])
    print("      jaw box in the image", roi)
    if "--empty" in opts:
        np.save(REF, depth)
        print(f"PASS  reference saved to {REF.name}: jaws empty, nothing in front of them")
        return
    if not REF.exists():
        sys.exit("FAIL  no reference yet: run 'stem --empty' with the jaws empty first")
    present, n = S.stem_present(depth, np.load(REF), roi, sp["stem_view"])
    print(("      something in the jaws" if present else "      jaws empty"), f"({n} pixels nearer than empty)")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "stem":
        return stem(args[1:])
    host, opts = args[0], args[1:]
    sp = spec()
    show(sp)
    if not opts:
        return
    from gh.mods.mycobot import connect
    try:
        mc = connect(host, 9000)
    except Exception as exc:
        sys.exit(f"FAIL  cannot reach {host}:9000 ({exc}): is the arm powered and its socket server running?")
    if mc.is_power_on() != 1:
        mc.power_on()
    print("PASS  connected, arm power on")
    pin, hz = int(sp.get("pin", 22)), int(sp.get("hz", 50))

    def send(us, why=""):
        d = S.duty(us, hz)
        mc.set_pwm_output(pin, hz, d)
        print(f"      G{pin}: {S.pulse_us(d, hz):.0f} us (duty {d}) {why}".rstrip())

    op = opts[0]
    if op == "pulse":
        send(float(opts[1]))
    elif op in ("open", "close"):
        send(sp["open_us" if op == "open" else "closed_us"], op)
    elif op == "pwm":
        for _ in range(3):
            send(sp["open_us"], "open"); time.sleep(1.0)
            send(sp["closed_us"], "closed"); time.sleep(1.0)
        print("PASS  if the jaw opened and closed three times")
    elif op == "cut":
        send(sp["open_us"], "open"); time.sleep(1.2)
        input("      stem between the jaws, then Enter ")
        send(sp["closed_us"], "closed: cut and hold"); time.sleep(2.0)
        input("      is the cut piece held in the pads? Enter to open ")
        send(sp["open_us"], "open")
    elif op == "limp":
        mc.set_pwm_output(pin, hz, 0)
        print(f"      G{pin}: no pulses, the servo is limp")
    else:
        sys.exit(f"unknown option {op!r}\n\n{__doc__}")


if __name__ == "__main__":
    main()
