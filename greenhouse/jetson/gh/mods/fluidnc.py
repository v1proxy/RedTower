"""FluidNC on the V1 Engineering Jackpot3, over USB serial. Grbl line protocol.

Nothing here blocks: the gantry module calls poll() every tick, which asks for a status
report and reads whatever has arrived. Each G-code line gets an "ok" or "error:N" back, in
order. "?", "!" and Ctrl-X are real-time bytes that act at once, even mid-move.

Moves use G53 (machine coordinates), so no work offset can shift where a plant is.
"""
import re
from collections import deque

STATUS = re.compile(r"^<([A-Za-z]+)(?::(\d))?\|(.*)>$")
ALARMS = {1: "hard limit hit", 2: "target beyond soft limits", 3: "reset while moving, position lost",
          4: "probe fail", 5: "probe fail", 6: "homing reset", 7: "homing stopped by the door",
          8: "homing pull-off failed", 9: "homing switch not found"}
RESET = b"\x18"
HOLD_WAIT_S = 5        # a feed hold decelerates well inside this; reset anyway after it


class SerialLink:
    """pyserial, opened without toggling DTR or RTS: on an ESP32 board those reset the chip."""

    def __init__(self, port, baud=115200):
        import serial
        self.s = serial.Serial()
        self.s.port, self.s.baudrate, self.s.timeout, self.s.write_timeout = port, baud, 0, 1
        self.s.dtr = self.s.rts = False
        self.s.open()

    def write(self, data):
        self.s.write(data)

    def read(self):
        return self.s.read(self.s.in_waiting or 0)

    def close(self):
        self.s.close()


class FluidNC:
    """The controller's side of the gantry: homing, moves, stop, status."""

    def __init__(self, link, clock, feed_mm_min=3000):
        self.link, self.clock, self.feed = link, clock, feed_mm_min
        self.buf, self.pending = b"", deque()        # lines sent, waiting for ok or error
        self.state, self.sub, self.mpos, self.homed = "Unknown", "", None, False
        self.stopping = None
        self.alarm = self.error = ""
        self.last_report = None
        self.opened = clock()
        self.homing = False
        self.send("$I")                               # build info: proves the line protocol works

    # ---- outgoing
    def send(self, line):
        self.pending.append(line)
        self.link.write(line.encode() + b"\n")

    def home(self):
        self.homed, self.homing, self.alarm, self.error = False, True, "", ""
        self.send("$H")

    def move_to(self, x, z):
        self.error = ""
        self.send(f"G53 G1 X{x:.3f} Z{z:.3f} F{self.feed:.0f}")

    def stop(self):
        """Feed hold first, so the carriage decelerates under control; once the hold is complete
        poll() sends the reset that empties the planner. A reset while still moving would lose
        the position (alarm 3). Homing ignores a feed hold, so it is reset at once. Either way
        the position is no longer trusted and the next move needs a homing cycle."""
        if self.homing:
            self._reset()
        else:
            self.link.write(b"!")
            self.stopping = self.clock()
        self.homed = self.homing = False

    def _reset(self):
        self.link.write(RESET)
        self.pending.clear()                          # nothing in flight is answered after a reset
        self.stopping = None

    def unlock(self):
        self.send("$X")

    # ---- incoming
    def poll(self):
        self.link.write(b"?")
        self.buf += self.link.read()
        while b"\n" in self.buf:
            raw, self.buf = self.buf.split(b"\n", 1)
            line = raw.decode("ascii", "replace").strip()
            if line:
                self._line(line)
        if self.stopping is not None and (self.state in ("Idle", "Alarm") or (self.state, self.sub) == ("Hold", "0")
                                          or self.clock() - self.stopping > HOLD_WAIT_S):
            self._reset()

    def _line(self, line):
        m = STATUS.match(line)
        if m:
            self.state, self.sub, self.last_report = m.group(1), m.group(2) or "", self.clock()
            fields = dict(f.split(":", 1) for f in m.group(3).split("|") if ":" in f)
            pos = fields.get("MPos") or fields.get("WPos")
            if pos:
                x, _, z = (float(v) for v in pos.split(",")[:3])
                self.mpos = (x, z)
            if self.state == "Alarm":
                self.homed = False
            return
        if line == "ok" or line.startswith("error:"):
            sent = self.pending.popleft() if self.pending else ""
            if line.startswith("error:"):
                self.error = f"{sent!r} refused with {line}"
                if sent == "$H":
                    self.homing = False
            elif sent == "$H":
                self.homing, self.homed = False, not self.alarm      # an alarm during the cycle means it failed
            return
        if line.startswith("ALARM:"):
            code = int(line[6:]) if line[6:].isdigit() else 0
            self.alarm = f"alarm {code}: {ALARMS.get(code, 'see the FluidNC alarm list')}"
            self.homed = self.homing = False
            return
        if line.startswith("Grbl "):                  # start-up banner: the controller restarted
            self.pending.clear()
            self.homed = self.homing = False

    # ---- what the gantry module asks
    def idle_at(self, x, z, tol=0.05):
        return (self.state == "Idle" and not self.pending and self.stopping is None and self.mpos is not None and
                abs(self.mpos[0] - x) <= tol and abs(self.mpos[1] - z) <= tol)

    def silent_for(self):
        """Seconds since the last status report, or since the port opened if none came yet."""
        return self.clock() - (self.last_report if self.last_report is not None else self.opened)

    def close(self):
        self.link.close()
