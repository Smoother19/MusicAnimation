import math, random
from grammar_engine import generate
from shapes import Wheel
import config as C
import grammar as G


class TrainView:
    """Enveloppe le resultat de la grammaire et reprend l'animation de ton
    ancienne classe Train : vitesse, inertie, tangage, rotation des roues."""

    BOB_AMPLITUDE = 1.2
    MAX_SPEED = 220.0
    LEAN_DAMPING = 1.0
    LEAN_MAX = 500.0
    LEAN_STRENGTH = 1.0

    def __init__(self, seed=None, x=0, y=0):
        self._base_x, self._base_y = x, y
        self.x, self.y = x, y
        self._lean = 0.0
        self._time = 0.0
        self.speed = 0.0
        self.target_speed = 0.0
        self.distance = 0.0
        self.regenerate(seed)

    def regenerate(self, seed=None):
        self.seed = random.randrange(10 ** 6) if seed is None else seed
        ctx = G.context(self.seed)
        self.shapes, self.root, self.length = generate(
            "Train", self.seed, x=C.MARGIN, bottom=C.RAIL_Y, height=C.BAND_H,
            world=G.world(self.seed), on_missing=G.missing, ctx=ctx)
        self.wheels = [s for s in self.shapes if isinstance(s, Wheel)]
        self.smoke_anchor = ctx["_hooks"].get("smoke")
        return self

    def set_speed(self, value, instant=False):
        self.target_speed = max(0.0, value)
        if instant:
            self.speed = self.target_speed
        return self

    def accelerate(self, delta): return self.set_speed(self.target_speed + delta)
    def stop(self, instant=False): return self.set_speed(0.0, instant)

    def update(self, dt, speed=None):
        if speed is not None:
            self.set_speed(speed)
        diff = self.target_speed - self.speed
        step = self.MAX_SPEED * dt
        temp = max(-step, min(step, diff))
        accel = temp / dt if dt else 0.0
        self.speed += temp
        self.distance += self.speed * dt

        self._lean -= accel * self.LEAN_STRENGTH * dt
        self._lean *= (1 - self.LEAN_DAMPING * dt)
        self._lean = min(self.LEAN_MAX, max(-self.LEAN_MAX, self._lean))
        self.x = self._base_x + self._lean

        for wheel in self.wheels:
            wheel.angle -= self.speed * dt / max(1, wheel.radius)

        self._time += dt * (0.4 + self.speed / 160.0)
        amp = self.BOB_AMPLITUDE * min(1.0, self.speed / 90.0)
        self.y = self._base_y + math.sin(self._time * 7.0) * amp

    def smoke_position(self, ox=0, oy=0):
        """Position monde de la cheminee, ou None (loco diesel)."""
        if not self.smoke_anchor:
            return None
        return (self.x + ox + self.smoke_anchor[0],
                self.y + oy + self.smoke_anchor[1])

    def draw(self, screen, ox=0, oy=0):
        for s in self.shapes:
            s.draw(screen, self.x + ox, self.y + oy)