"""A FluidNC stand-in on the far side of the serial link, for the gantry tests.

It speaks the Grbl line protocol the way the controller does: one "ok" or "error:N" per line,
in order, real-time bytes acted on at once, status reports on "?", ALARM:N lines, and the
start-up banner after a reset. Motion is interpolated on the test clock."""

BANNER = b"\r\nGrbl 3.7 [FluidNC v3.7.8 (noradio) '$' for help]\r\n"


class FakeFluidNC:
    def __init__(self, clock, speed_mm_s=50.0, homing_s=6.0, decel_s=0.4, x_max=1250.0, z_max=1300.0,
                 alarm_at_start=True):
        self.clock, self.speed, self.homing_s, self.decel_s = clock, speed_mm_s, homing_s, decel_s
        self.x_max, self.z_max = x_max, z_max
        self.out, self.inbuf, self.written = bytearray(), b"", bytearray()
        self.pos, self.state, self.sub = [0.0, 0.0], ("Alarm" if alarm_at_start else "Idle"), ""
        self.move = None                     # (start, goal, t0, duration)
        self.homing_until = None
        self.hold_until = None
        self.lines = []                      # every G-code line received
        self.plugged, self.mute = True, False
        self.fail_homing = False

    # ---- the link interface the gantry driver uses
    def write(self, data):
        self._check()
        self.written += data
        for b in data:
            ch = bytes([b])
            if ch == b"?":
                self._status()
            elif ch == b"!":
                self._hold()
            elif ch == b"~":
                self.state = "Run" if self.move else "Idle"
            elif ch == b"\x18":
                self._reset()
            else:
                self.inbuf += ch
        while b"\n" in self.inbuf:
            line, self.inbuf = self.inbuf.split(b"\n", 1)
            self._line(line.decode().strip())

    def read(self):
        self._check()
        self._advance()
        data, self.out = bytes(self.out), bytearray()
        return data

    def close(self):
        pass

    def _check(self):
        if not self.plugged:
            raise OSError("device disconnected")

    # ---- test controls
    def emit(self, text):
        self.out += text.encode() + b"\r\n"

    def hard_limit(self):
        self._advance()
        self.move, self.state = None, "Alarm"
        self.emit("ALARM:1")

    # ---- controller behaviour
    def _now_pos(self):
        if not self.move:
            return list(self.pos)
        start, goal, t0, dur = self.move
        f = 1.0 if dur <= 0 else min(1.0, (self.clock() - t0) / dur)
        return [start[i] + (goal[i] - start[i]) * f for i in range(2)]

    def _advance(self):
        now = self.clock()
        if self.homing_until is not None and now >= self.homing_until:
            self.homing_until = None
            if self.fail_homing:
                self.state = "Alarm"
                self.emit("ALARM:9")
                self.emit("ok")
            else:
                self.pos, self.state = [0.0, 0.0], "Idle"
                self.emit("ok")
        if self.state == "Run" and self.move and now >= self.move[2] + self.move[3]:
            self.pos, self.move, self.state = list(self.move[1]), None, "Idle"
        if self.state == "Hold" and self.sub == "1" and now >= self.hold_until:
            self.sub = "0"

    def _status(self):
        if self.mute:
            return
        self._advance()
        x, z = self._now_pos()
        state = f"{self.state}:{self.sub}" if self.state in ("Hold", "Door") else self.state
        self.out += f"<{state}|MPos:{x:.3f},0.000,{z:.3f}|FS:0,0>\r\n".encode()

    def _hold(self):
        self._advance()
        if self.state == "Run":
            self.pos, self.move = self._now_pos(), None          # frozen where the deceleration ends
            self.state, self.sub, self.hold_until = "Hold", "1", self.clock() + self.decel_s

    def _reset(self):
        self._advance()
        if self.state in ("Run", "Home") or (self.state == "Hold" and self.sub == "1"):
            self.pos, self.move, self.homing_until = self._now_pos(), None, None
            self.state = "Alarm"
            self.out += BANNER
            self.emit("ALARM:3")
            return
        self.move, self.state, self.sub = None, ("Alarm" if self.state == "Alarm" else "Idle"), ""
        self.out += BANNER

    def _line(self, line):
        if not line:
            return
        self.lines.append(line)
        if line == "$I":
            self.emit("[VER:3.7 FluidNC v3.7.8:]")
            return self.emit("ok")
        if line == "$X":
            self.state = "Idle"
            self.emit("[MSG:Caution: Unlocked]")
            return self.emit("ok")
        if line == "$H":
            self.state, self.homing_until = "Home", self.clock() + self.homing_s
            return                                           # "ok" when the cycle ends
        if line.startswith("G53 G1"):
            if self.state == "Alarm":
                return self.emit("error:9")                  # locked out until homed or unlocked
            words = {w[0]: float(w[1:]) for w in line.split()[2:]}
            goal = [words.get("X", self.pos[0]), words.get("Z", self.pos[1])]
            if not (0 <= goal[0] <= self.x_max and 0 <= goal[1] <= self.z_max):
                self.state = "Alarm"
                self.emit("ALARM:2")
                return self.emit("ok")
            dist = max(abs(goal[0] - self.pos[0]), abs(goal[1] - self.pos[1]))
            self.move, self.state = (list(self.pos), goal, self.clock(), dist / self.speed), "Run"
            return self.emit("ok")
        self.emit("error:20")                                # unsupported command
