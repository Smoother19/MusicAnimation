import pygame
import math
import random
from shapes import *

class Fireworks(TriangularShape):
    '''
    This class will create fireworks based on multiple triangles and make it explode

        Attributes:

        Methods:
    '''

    def __init__(self, x, y, color, nb_rays=30, min_speed=2, max_speed=10, gravity=0.15, lifespan=60, ray_width=4):
        super().__init__(x, y, 0, 0, color)
        self.gravity = gravity      #the gravity for the particule
        self.lifespan = lifespan    #life time of the firework
        self.ray_width = ray_width  #width of the ray of the firework
        self.age = 0                #age of the firework

        self.rays = []  #list of data of firework
        for _ in range(nb_rays):
            angle = random.uniform(0, math.tau) #angle of the direction of the ray
            speed = random.uniform(min_speed, max_speed) #random speed of the ray
            self.rays.append((angle, speed))


    def update(self, delta=1):
        '''
        Update the age of the firework
        '''
        self.age += delta

    def is_done(self):
        '''
        Returns True if the age of the firework is bigger or equal than the lifespan
        '''
        return self.age >= self.lifespan
    
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