"""First contact with the myCobot 280 Pi, and pose teaching (commissioning step 10).
Stop gh-arm first. Needs pymycobot's socket server running on the arm's Pi.

  python tools_arm_check.py 192.168.10.25              read only: power, joint angles, coordinates
  python tools_arm_check.py 192.168.10.25 --release    servos off, so the arm can be posed by hand
  python tools_arm_check.py 192.168.10.25 --lock       servos on again, holding where they are
  python tools_arm_check.py 192.168.10.25 --stow       move to the stow pose in arm.yaml (needs taught: true)

To teach a pose: --release, hold the arm and move it into the pose, --lock, then run with no
option and copy the joint angles into config/arm.yaml. --release lets the arm fall: support it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh.mods.arm import load_spec                          # noqa: E402
from gh.mods.mycobot import connect, valid_angles          # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    host, opts = sys.argv[1], sys.argv[2:]
    try:
        mc = connect(host, 9000)
    except Exception as exc:
        sys.exit(f"FAIL  cannot reach {host}:9000 ({exc}): is the arm powered and its socket server running?")
    print("PASS  connected")
    if "--release" in opts:
        mc.release_all_servos()
        print("servos released: the arm can be moved by hand")
    if "--lock" in opts:
        mc.power_on()
        print("servos on")
    angles = mc.get_angles()
    print("      servo power", "on" if mc.is_power_on() == 1 else "off")
    print("      joint angles", [round(a, 1) for a in angles] if valid_angles(angles) else f"unreadable ({angles!r})")
    print("      coordinates ", mc.get_coords())
    if "--stow" in opts:
        spec = load_spec(Path(__file__).resolve().parent / "config" / "arm.yaml")
        if not spec.get("taught"):
            sys.exit("arm.yaml is not marked taught: teach the poses first")
        mc.send_angles(spec["poses"]["stow"], spec["speed"])
        print("moving to stow at speed", spec["speed"])


if __name__ == "__main__":
    main()
