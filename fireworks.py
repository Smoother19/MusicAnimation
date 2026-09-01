import pygame
import math
import random
from shapes import *
from config import *

class Fireworks(TriangularShape):
    '''
    Simulates a firework explosion by rendering expanding particle rays as triangles.

    Attributes:
        x (float): Horizontal origin point of the explosion.
        y (float): Vertical origin point of the explosion.
        based_color (tuple[int, int, int]): Initial RGB color of the firework rays.
        color (tuple[int, int, int]): Current RGB color (fades over time).
        gravity (float): Downward acceleration applied to the rays.
        lifespan (float/int): Maximum age (in frames/ticks) before the firework expires.
        ray_width (float): Thickness of the base of each ray triangle.
        age (float/int): Elapsed time since the explosion started.
        rays (list[tuple[float, float]]): List of (angle, speed) tuples defining each ray.

    Methods:
        get_random_params(): Static helper returning random (x, y, color) values.
        update(delta=1): Advances the age of the firework and updates its color fade.
        is_done(): Returns True if the firework has exceeded its lifespan.
        get_color(): Computes the faded color based on current age and lifespan.
        list_triangles(): Computes the 3 vertices for each ray at the current time t.
    '''

    def __init__(self, x, y, color, nb_rays=30, min_speed=2, max_speed=10, gravity=0.15, lifespan=60, ray_width=4):
        super().__init__(x, y, 0, 0, color)
        self.based_color = color
        self.gravity = gravity      #the gravity for the particule
        self.lifespan = lifespan    #life time of the firework
        self.ray_width = ray_width  #width of the ray of the firework
        self.age = 0                #age of the firework

        self.rays = []  #list of data of firework
        for _ in range(nb_rays):
            angle = random.uniform(0, math.tau) #angle of the direction of the ray
            speed = random.uniform(min_speed, max_speed) #random speed of the ray
            self.rays.append((angle, speed))

        self.opacity_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.alpha = 255

    def get_random_params():
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, int(SCREEN_HEIGHT/2)) #to not have firework in the ground
        color = ((random.randint(0, 255)),(random.randint(0, 255)),(random.randint(0, 255)))
        return (x, y, color)

    def update(self, delta=1):
        '''
        Update the age of the firework
        '''
        self.age += delta
        self.color = self.based_color
        #For opacity
        new_frac = max(0, 1 - self.age / self.lifespan)
        self.alpha = int(new_frac * 255)

    def is_done(self):
        '''
        Returns True if the age of the firework is bigger or equal than the lifespan
        '''
        return self.age >= self.lifespan

    def get_color(self):
        '''
        Get the actual color, gets darker with time
        '''
        new_frac = max(0, 1 - self.age / self.lifespan) #get the new percentage of the color removed based on time, if it's too small, takes 0
        r, g, b = self.based_color
        return (int(r * new_frac), (g * new_frac), (b * new_frac))
    
    def list_triangles(self):
        '''
        Get the points of each triangle, based on the current in the loop and the 4 times old one
        '''
        t = self.age
        triangles = []
        for angle, speed in self.rays:
            #pos de la pointe du rayon au temps t
            tip_x = self.x + math.cos(angle) * speed * t    #get x for time t
            tip_y = self.y + math.sin(angle) * speed * t + 0.5 * self.gravity * t * t # get y for time t, different because of the gravity

            #remain of the firework
            t_back = max(t - 4, 0)      #get the 4 time older version, if < 0 takes 0
            back_x = self.x + math.cos(angle) * speed * t_back
            back_y = self.y + math.sin(angle) * speed * t_back + 0.5 * self.gravity * t_back * t_back

            #make remain bigger
            perp = angle + math.pi / 2  #perpendicular direction
            hw = self.ray_width / 2 #half width
            p1 = (back_x + math.cos(perp) * hw, back_y + math.sin(perp) * hw)
            p2 = (back_x - math.cos(perp) * hw, back_y - math.sin(perp) * hw)
            triangles.append([p1, p2, (tip_x, tip_y)])

        return triangles

    def draw(self, screen, ox=0, oy=0, angle=0, pivot=None):
        '''
        Override of draw from TriangularShape
        '''
        self.opacity_layer.fill((0,0,0,0))

        super().draw(self.opacity_layer, ox, oy, angle, pivot)

        self.opacity_layer.set_alpha(self.alpha)

        screen.blit(self.opacity_layer, (0,0))