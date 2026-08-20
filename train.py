import math
import random
from shapes import *
import pygame as ui
class Wheel(TriangularShape):
    def __init__(self, x, y, radius, color, spoke_color, spokes=6):
        super().__init__(x, y, radius * 2, radius * 2, color)
        self.radius = radius
        self.spoke_color = spoke_color
        self.spokes = spokes
        self.angle = 0.0

    def list_triangles(self):
        tris = []
        # jante
        n = 12
        for i in range(n):
            a1 = 2 * math.pi * i / n
            a2 = 2 * math.pi * (i + 1) / n
            tris.append([(self.x, self.y),
                         (self.x + self.radius * math.cos(a1), self.y + self.radius * math.sin(a1)),
                         (self.x + self.radius * math.cos(a2), self.y + self.radius * math.sin(a2))])
        return tris

    def spoke_triangles(self):
        tris = []
        w = 0.13
        r = self.radius * 0.82
        for i in range(self.spokes):
            a = self.angle + 2 * math.pi * i / self.spokes
            tris.append([(self.x, self.y),
                         (self.x + r * math.cos(a - w), self.y + r * math.sin(a - w)),
                         (self.x + r * math.cos(a + w), self.y + r * math.sin(a + w))])
        return tris

    def hub_triangles(self):
        n, r = 6, self.radius * 0.30
        return [[(self.x, self.y),
                 (self.x + r * math.cos(2 * math.pi * i / n),
                  self.y + r * math.sin(2 * math.pi * i / n)),
                 (self.x + r * math.cos(2 * math.pi * (i + 1) / n),
                  self.y + r * math.sin(2 * math.pi * (i + 1) / n))]
                for i in range(n)]

    def draw(self, screen, ox=0, oy=0, angle=0, pivot = None):
        for group, color in ((self.list_triangles(), self.color),
                             (self.spoke_triangles(), self.spoke_color),
                             (self.hub_triangles(), self.color)):
            STATS["triangles"] += len(group)
            for i, t in enumerate(group):
                pts=[(px + ox, py + oy) for px, py in t]
                if angle !=0 and pivot is not None:
                    pts = [self._rotate_point(p, pivot, angle) for p in pts]
                ui.draw.polygon(screen, facet(color, i), pts)


class Train(Group):

    WHEEL_R = 9
    CHASSIS_H = 7
    GAP = 14            # espace entre deux vehicules
    BOB_AMPLITUDE = 1.2  # oscillation verticale de la caisse
    MAX_SPEED = 220.0
    LEAN_DAMPING = 1.0
    LEAN_MAX = 500.0
    LEAN_STRENGTH = 1.0

    def __init__(self, seed=None, n_wagons=None, x=0, y=0):
        super().__init__(x, y)
        self.seed = random.randrange(10 ** 6) if seed is None else seed
        self.rng = random.Random(self.seed)
        self.pal = make_palette(self.rng)
        self.wheels = []
        self.length = 0
        self._base_x = x
        self._base_y = y
        self._lean = 0.0
        self._time = 0.0
        self.speed = 0.0
        self.target_speed = 0.0
        self.distance = 0.0
        self._build(n_wagons)

    def set_speed(self, value, instant=False):
        '''speed in pixels/second
        Attribute:
            value (float): new target speed
            instant (bool): if True, sets the speed immediately
        '''
        self.target_speed = max(0.0, value)
        if instant:
            self.speed = self.target_speed
        return self
    
    def accelerate(self, delta):
        '''Add delta to the target speed, and return self.'''
        return self.set_speed(self.target_speed + delta)
    
    def stop(self, instant=False):
        return self.set_speed(0.0, instant)      

    # generation train + wagon
    def _build(self, n_wagons):
        cursor = 0
        loco, L = self._locomotive()
        loco.x = cursor
        self.add(loco)
        cursor += L + self.GAP

        builders = [self._passenger, self._boxcar, self._tank,
                    self._hopper, self._flatcar]
        weights = [3, 3, 2, 2, 2]

        n = self.rng.randint(4, 7) if n_wagons is None else n_wagons
        previous = None
        for _ in range(n):
            # grammaire minimale : jamais deux fois le meme type d'affilee
            build = self.rng.choices(builders, weights)[0]
            while build is previous:
                build = self.rng.choices(builders, weights)[0]
            previous = build

            wagon, L = build()
            wagon.x = cursor
            self.add(wagon)
            cursor += L + self.GAP

        self.length = cursor - self.GAP

    def regenerate(self, seed=None, n_wagons=None):
        self.children.clear()
        self.wheels.clear()
        self.seed = random.randrange(10 ** 6) if seed is None else seed
        self.rng = random.Random(self.seed)
        self.pal = make_palette(self.rng)
        self._build(n_wagons)
        return self

    # animation

    def update(self, dt, speed=None, k=LEAN_DAMPING):
        if speed is not None:
            self.set_speed(speed)

        # acceleration bornee
        diff = self.target_speed - self.speed
        step = self.MAX_SPEED * dt
        temp = max(-step, min(step, diff))
        accel = temp / dt
        self.speed += temp
        self.distance += self.speed * dt

        self._lean -= accel * self.LEAN_STRENGTH * dt
        self._lean *= (1 - self.LEAN_DAMPING * dt)
        self._lean = min(self.LEAN_MAX, max(-self.LEAN_MAX, self._lean))
        self.x = self._base_x + self._lean

        for wheel in self.wheels:
            wheel.angle -= self.speed * dt / max(1, wheel.radius)

        # l'oscillation suit la vitesse
        self._time += dt * (0.4 + self.speed / 160.0)
        amplitude = self.BOB_AMPLITUDE * min(1.0, self.speed / 90.0)
        self.y = self._base_y + math.sin(self._time * 7.0) * amplitude

    def smoke_position(self, ox=0, oy=0):
        loco = self.children[0]
        ax, ay = self.smoke_anchor
        return (ox + self.x + loco.x + ax,
                oy + self.y + loco.y + ay)

    # briques communes

    def _chassis(self, g, length, wheel_r=None):
        wheel_r = wheel_r or self.WHEEL_R
        top = -(2 * wheel_r)
        g.add(Rectangle(length / 2, top - self.CHASSIS_H / 2, length,
                        self.CHASSIS_H, self.pal["chassis"]))
        return top - self.CHASSIS_H

    def _wheel(self, g, cx, r, spokes=6, hub=None):
        w = Wheel(cx, -r, r, self.pal["hub"], hub or self.pal["wheel"], spokes)
        g.add(w)
        self.wheels.append(w)
        return w

    def _wheels(self, g, length, wheel_r=None, bogies=True):
        r = wheel_r or self.WHEEL_R
        xs = ([length * 0.15, length * 0.30, length * 0.70, length * 0.85]
              if bogies else [length * 0.22, length * 0.78])
        for cx in xs:
            self._wheel(g, cx, r)

    def _couplers(self, g, length, wheel_r=None):
        r = wheel_r or self.WHEEL_R
        y = -(2 * r) - self.CHASSIS_H / 2
        for cx in (-self.GAP / 4, length + self.GAP / 4):
            g.add(Rectangle(cx, y, self.GAP / 2 + 2, 4, self.pal["metal"]))

    def _windows(self, g, x0, x1, y_center, h, min_gap=26):
        span = x1 - x0
        n = max(1, int(span // min_gap))
        step = span / n
        w = min(16, step * 0.62)
        for i in range(n):
            g.add(Rectangle(x0 + step * (i + 0.5), y_center, w, h, self.pal["glass"]))

    # locomotives

    def _locomotive(self):
        return (self._steam_loco() if self.rng.random() < 0.5
                else self._diesel_loco())

    def _steam_loco(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(140, 175)
        wr = self.WHEEL_R + 3
        fy = self._chassis(g, L, wr)

        boiler_h = rng.randint(34, 44)
        boiler_L = L * rng.uniform(0.55, 0.62)
        cab_L = L - boiler_L

        # chaudiere
        g.add(Rectangle(boiler_L / 2, fy - boiler_h / 2, boiler_L, boiler_h, pal["body"]))
        g.add(Circle(boiler_L, fy - boiler_h / 2, boiler_h / 2, pal["body2"], 14))
        g.add(Circle(2, fy - boiler_h / 2, boiler_h / 2 - 2, pal["accent"], 12))
        for i in range(rng.randint(2, 4)):
            g.add(Rectangle(boiler_L * (0.25 + 0.22 * i), fy - boiler_h / 2, 4,
                            boiler_h, pal["body2"]))

        # cheminee + dome
        ch_x = boiler_L * rng.uniform(0.16, 0.24)
        ch_h = rng.randint(20, 30)
        g.add(Trapezoid(ch_x, fy - boiler_h - ch_h / 2, 16, 10, ch_h, pal["dark"]))
        g.add(Rectangle(ch_x, fy - boiler_h - ch_h, 20, 5, pal["metal"]))
        g.add(Circle(boiler_L * 0.55, fy - boiler_h, 8, pal["metal"], 10))
        self.smoke_anchor = (ch_x, fy - boiler_h - ch_h)   # point d'emission fumee

        # cabine
        cab_h = boiler_h + rng.randint(14, 22)
        cab_x = boiler_L + cab_L / 2
        g.add(Rectangle(cab_x, fy - cab_h / 2, cab_L, cab_h, pal["body"]))
        g.add(Trapezoid(cab_x, fy - cab_h - 5, cab_L * 0.85, cab_L + 8, 10, pal["roof"]))
        g.add(Rectangle(cab_x, fy - cab_h * 0.72, cab_L * 0.55, cab_h * 0.32, pal["glass"]))

        # front
        g.add(Quad([(2, fy), (2, fy + self.CHASSIS_H + 6), (-20, -2), (-20, -14)],
                   pal["metal"]))

        # wheels
        self._wheel(g, L * 0.30, wr, spokes=8, hub=pal["accent"])
        self._wheel(g, L * 0.52, wr, spokes=8, hub=pal["accent"])
        for cx in (L * 0.78, L * 0.90):
            self._wheel(g, cx, self.WHEEL_R * 0.7, spokes=5)
        g.add(Rectangle(L * 0.41, -wr + 3, L * 0.26, 4, pal["metal"]))

        self._couplers(g, L, wr)
        return g, L

    def _diesel_loco(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(150, 185)
        wr = self.WHEEL_R + 2
        fy = self._chassis(g, L, wr)

        hood_h = rng.randint(30, 38)
        cab_h = hood_h + rng.randint(16, 24)
        cab_L = L * rng.uniform(0.30, 0.36)
        nose_L = L - cab_L

        g.add(Trapezoid(nose_L / 2, fy - hood_h / 2, nose_L * 0.92, nose_L,
                        hood_h, pal["body"]))
        g.add(Rectangle(nose_L / 2, fy - hood_h * 0.35, nose_L, 6, pal["accent"]))
        for i in range(rng.randint(3, 5)):
            g.add(Rectangle(nose_L * (0.2 + 0.15 * i), fy - hood_h * 0.75, 8,
                            hood_h * 0.3, pal["dark"]))

        cab_x = nose_L + cab_L / 2
        g.add(Rectangle(cab_x, fy - cab_h / 2, cab_L, cab_h, pal["body"]))
        g.add(Trapezoid(cab_x, fy - cab_h - 4, cab_L * 0.8, cab_L + 6, 8, pal["roof"]))
        g.add(Rectangle(cab_x, fy - cab_h * 0.75, cab_L * 0.6, cab_h * 0.28, pal["glass"]))
        g.add(Triangle(6, fy - hood_h * 0.8, 12, 10, pal["glass"]))
        g.add(Rectangle(-3, fy + 3, 8, 14, pal["metal"]))
        self.smoke_anchor = (nose_L * 0.5, fy - hood_h)

        self._wheels(g, L, wr, bogies=True)
        self._couplers(g, L, wr)
        return g, L

    # wagons

    def _passenger(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(120, 160)
        h = rng.randint(46, 56)
        fy = self._chassis(g, L)

        g.add(Rectangle(L / 2, fy - h / 2, L, h, pal["body"]))
        g.add(Trapezoid(L / 2, fy - h - 5, L * 0.9, L, 10, pal["roof"]))
        g.add(Rectangle(L / 2, fy - h * 0.22, L, 5, pal["accent"]))
        self._windows(g, 12, L - 12, fy - h * 0.62, h * 0.38)
        for cx in (8, L - 8):
            g.add(Rectangle(cx, fy - h * 0.45, 9, h * 0.7, pal["body2"]))

        self._wheels(g, L, bogies=True)
        self._couplers(g, L)
        return g, L

    def _boxcar(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(95, 130)
        h = rng.randint(42, 54)
        fy = self._chassis(g, L)

        g.add(Rectangle(L / 2, fy - h / 2, L, h, pal["body2"]))
        g.add(Trapezoid(L / 2, fy - h - 4, L * 0.95, L, 8, pal["roof"]))
        planks = rng.randint(5, 7)
        for i in range(planks):
            g.add(Rectangle(L * (i + 0.5) / planks, fy - h / 2, 3, h * 0.9, pal["dark"]))
        g.add(Rectangle(L / 2, fy - h / 2, L * 0.22, h * 0.8, pal["accent"]))

        self._wheels(g, L, bogies=rng.random() < 0.5)
        self._couplers(g, L)
        return g, L

    def _tank(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(115, 145)
        fy = self._chassis(g, L)
        r = rng.randint(16, 21)
        cy = fy - r - 4

        g.add(Rectangle(L / 2, cy, L - 2 * r, 2 * r, pal["body"]))
        g.add(Circle(r + 2, cy, r, pal["body2"], 14))
        g.add(Circle(L - r - 2, cy, r, pal["body2"], 14))
        g.add(Trapezoid(L / 2, cy - r - 5, 14, 22, 10, pal["accent"]))
        g.add(Rectangle(L / 2, cy, L * 0.7, 5, pal["body2"]))

        self._wheels(g, L, bogies=False)
        self._couplers(g, L)
        return g, L

    def _hopper(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(100, 130)
        h = rng.randint(40, 52)
        fy = self._chassis(g, L)

        g.add(Trapezoid(L / 2, fy - h / 2, L, L * 0.45, h, pal["body"]))
        g.add(Rectangle(L / 2, fy - h + 3, L, 6, pal["accent"]))
        for i in range(rng.randint(3, 5)):   # chargement qui depasse
            g.add(Triangle(L * (0.2 + 0.15 * i), fy - h - 4,
                           rng.randint(16, 24), rng.randint(10, 16), pal["metal"]))

        self._wheels(g, L, bogies=False)
        self._couplers(g, L)
        return g, L

    def _flatcar(self):
        rng, pal = self.rng, self.pal
        g = Group()
        L = rng.randint(95, 125)
        fy = self._chassis(g, L)
        g.add(Rectangle(L / 2, fy - 4, L, 8, pal["body2"]))

        cargo = rng.choice(["crates", "logs", "crates"])
        if cargo == "crates":
            x = 10
            while x < L - 25:
                s = rng.randint(18, 28)
                g.add(Square(x + s / 2, fy - 8 - s / 2, s,
                             rng.choice([pal["accent"], pal["body"], pal["roof"]])))
                x += s + rng.randint(2, 8)
        else:
            r = 9
            for row, count in ((0, 5), (1, 4)):
                for i in range(count):
                    g.add(Circle(20 + i * 2 * r + row * r,
                                 fy - 8 - r - row * 2 * r * 0.9, r, pal["roof"], 8))
        for cx in (4, L - 4):
            g.add(Rectangle(cx, fy - 14, 5, 16, pal["metal"]))

        self._wheels(g, L, bogies=False)
        self._couplers(g, L)
        return g, L