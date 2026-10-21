"""The myCobot 280 Pi, reached over TCP: the arm runs its own Raspberry Pi, and pymycobot's
socket server on it relays commands to the servos.

connect() returns an object with pymycobot's method names. SimCobot has the same names and
moves on the module clock, so the simulated arm and the real one run the same driver code."""
import socket

JOINTS = 6


def connect(host, port, timeout_s=3.0):
    try:
        from pymycobot import MyCobot280Socket as Socket       # pymycobot 3.x and 4.x
    except ImportError:
        from pymycobot import MyCobotSocket as Socket           # older releases
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout_s)       # its constructor connects with no timeout of its own:
    try:                                      # a powered-off Pi would hang the driver for minutes
        mc = Socket(host, port)
    finally:
        socket.setdefaulttimeout(old)
    sock = getattr(mc, "sock", None)
    if sock is not None:
        sock.settimeout(timeout_s)                              # a hung Pi must not hang the driver
    return mc


def valid_angles(angles):
    return (isinstance(angles, (list, tuple)) and len(angles) == JOINTS and
            all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in angles))


class SimCobot:
    """pymycobot's interface, simulated. A move takes move_s whatever its size."""

    def __init__(self, clock, move_s=2.0, start=(0.0,) * JOINTS):
        self.clock, self.move_s = clock, move_s
        self.angles, self.goal, self.until, self.powered = list(start), None, 0.0, True
        self.pwm = []                       # (pin, hz, duty) sent to the end connector, in order

    def _settle(self):
        if self.goal is not None and self.clock() >= self.until:
            self.angles, self.goal = list(self.goal), None

    def power_on(self):
        self.powered = True

    def is_power_on(self):
        return 1 if self.powered else 0

    def send_angles(self, angles, speed):
        if self.powered:
            self._settle()
            self.goal, self.until = list(angles), self.clock() + self.move_s

    def get_angles(self):
        self._settle()
        return list(self.angles)

    def is_moving(self):
        self._settle()
        return 1 if self.goal is not None else 0

    def set_pwm_output(self, channel, frequency, pin_val):
        if self.powered:                    # the end connector is dead with the arm unpowered
            self.pwm.append((channel, frequency, pin_val))

    def stop(self):
        self.goal = None                    # stays where it was: a stop mid-move is not a pose

    def close(self):
        pass
