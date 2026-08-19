import pygame
import random
import math
from shapes import *
from config import BACKGROUND

class Particle(TriangularShape):
    def __init__(self, x, y, color, lifetime=1.8, size=None, fade_to=BACKGROUND):
        size = size if size else random.uniform(10, 20)
        super().__init__(x, y, size, size, color)
        self.size = size
        self.growth = random.uniform(14, 26)
        self.vx = random.uniform(-12, 12)
        self.vy = random.uniform(-70, -40)
        self.lifetime = lifetime
        self.age = 0.0
        self.angle = random.uniform(0, 2 * math.pi)
        self.spin = random.uniform(-1.5, 1.5)
        self.start_color = color
        self.fade_to = fade_to

    @property
    def dead(self):
        return self.age >= self.lifetime

    def update(self, dt, wind=0.0):
        self.age += dt
        self.x += (self.vx + wind) * dt
        self.y += self.vy * dt
        self.vy *= (1 - 0.8 * dt)
        self.size += self.growth * dt
        self.width = self.height = self.size
        self.angle += self.spin * dt

        t = min(1.0, self.age / self.lifetime)
        self.color = tuple(int(a + (b - a) * t)
                           for a, b in zip(self.start_color, self.fade_to))

    def list_triangles(self):
        if self.dead:
            return []
        r = self.size / 2
        return [[(self.x + r * math.cos(self.angle + 2 * math.pi * i / 3),
                  self.y + r * math.sin(self.angle + 2 * math.pi * i / 3))
                 for i in range(3)]]