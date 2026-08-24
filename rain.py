import pygame
import math
import random
from shapes import *
from config import *

class RainDrop(TriangularShape):
    '''
    This class will create fireworks based on multiple triangles and make it explode

        Attributes:

        Methods:
    '''

    def __init__(self, screen_width, screen_height, width=2):
        super().__init__(0, 0, 0, 0, (255, 255, 255))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._respawn(random.uniform(0, screen_height))

    def _respawn(self, y):
        self.x = random.uniform(0, self.screen_width)
        self.y = y
        self.speed = random.uniform(400, 700)
        self.length = random.uniform(12, 24)
        self.drift = random.uniform(-30, -10)

    def update(self, delta=1):
        '''
        Update the age of the firework
        '''
        self.y += self.speed * delta
        self.x += self.drift * delta
        if self.y > self.screen_height:
            self._respawn(-self.length)
    
    def list_triangles(self):
        '''
        Get the points of each triangle, based on the current in the loop and the 4 times old one
        '''
        angle = math.atan2(self.speed, self.drift)
        tip = (self.x, self.y)
        tail = (self.x - math.cos(angle) * self.length, self.y - math.sin(angle) * self.length)

        perp = angle + math.pi
        hw = self.width / 2
        a1 = (tail[0] + math.cos(perp) * hw, tail[1] + math.sin(perp) * hw)
        a2 = (tail[0] - math.cos(perp) * hw, tail[1] - math.sin(perp) * hw)

        return [[a1, a2, tip]]


class Rain:
    def __init__(self, screen_width, screen_height, nb_drops=120):
        self.drops = [RainDrop(screen_width, screen_height) for _ in range(nb_drops)]

    def update(self, delta):
        for drop in self.drops:
            drop.update(delta)

    def draw(self, screen):
        for drop in self.drops:
            drop.draw(screen)