from particle import Particle


class SmokeEmitter:
    def __init__(self, color=(210, 214, 225), rate=18.0, lifetime=1.8):
        self.particles = []
        self.color = color
        self.rate = rate
        self.lifetime = lifetime
        self._accumulator = 0.0

    def emit(self, x, y, count=1):
        for _ in range(count):
            self.particles.append(
                Particle(x, y, self.color, self.lifetime))

    def update(self, dt, x, y, wind=0.0, rate=None):
        self._accumulator += (self.rate if rate is None else rate) * dt
        while self._accumulator >= 1.0:
            self.emit(x, y)
            self._accumulator -= 1.0

        for p in self.particles:
            p.update(dt, wind)
        self.particles = [p for p in self.particles if not p.dead]

    def draw(self, screen, ox=0, oy=0):
        for p in self.particles:
            p.draw(screen, ox, oy)