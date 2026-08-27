import pygame
import math
import random
from shapes import *

class MountainChunk(Curve):
    '''
    Create a part of the mountain
    '''
    def __init__(self, start, end, width, color, type_curve=-1, 
                 a=1, b=0, c=0, height=0, amplitude=100, resolution=50, bottom_y=200):
        super().__init__(start, end, width, color, type_curve, a, b, c, height, amplitude, resolution)
        self.bottom_y = bottom_y

    def list_triangles(self):
            points = self.get_points()
            triangles = []
    
            for i in range(len(points) - 1):
                top_left = points[i]
                top_right = points[i + 1]
                bottom_left = (top_left[0], self.bottom_y)
                bottom_right = (top_right[0], self.bottom_y)
        
                triangles.append([top_left, bottom_left, top_right])
                triangles.append([bottom_left, bottom_right, top_right])
        
            return triangles

class Mountains():
    '''
    Gestion of the multiple part of the mountian

    Attributes:

    Methods:
    '''

    def __init__(self, start, end, width, color, type_curve=-1, a=1, b=0, c=0, 
                 height=0, amplitude=100, resolution=50, bottom_y = SCREEN_HEIGHT):
        
        # Params of the chain of mountains
        self.y_base = start[1]
        self.width = width
        self.color = color
        self.bottom_y = bottom_y
        
        self.type_curve = type_curve
        self.base_a = a
        self.base_b = b
        self.amplitude = amplitude
        self.resolution = resolution
        
        self.scroll = 0.0
        self.chunk_length = 400  # Longueur de chaque segment
        self.chunks = []

        self.x = 0
        self.last_y = self.y_base

        while self.x < SCREEN_WIDTH + self.chunk_length:
                    chunk, _ = self.create_chunk(self.x, self.last_y)
                    self.chunks.append(chunk)
                    real_end = chunk.point_at(1.0)
                    self.x = real_end[0]
                    self.last_y = real_end[1]

    def create_chunk(self, start_x, start_y):
        end_x = start_x + self.chunk_length
        end_y = self.y_base

        rand_param_a = self.base_a * random.uniform(0.6, 1.0) 
        rand_param_b = self.base_b * random.uniform(0.6, 1.0) 
        rand_param_c = random.uniform(0, math.pi * 2)

        chunk = MountainChunk((start_x, start_y), (end_x, end_y), self.width, 
                              self.color, 1, rand_param_a, rand_param_b, rand_param_c, 
                              0, self.amplitude, self.resolution, self.bottom_y)

        # 1.0 = 100% de la courbe, ce qui donne la hauteur mathématique de fin générée par le random !
        real_end_y = chunk.point_at(1.0)[1] 

        return chunk, real_end_y

    def update(self, dt, speed=10):
        self.scroll += speed * dt

        first_chunk = self.chunks[0]

        if first_chunk.p_end[0] - self.scroll < 0:
            self.chunks.pop(0) #remove the old mountains's part

            last_chunk = self.chunks[-1]
            start_x = last_chunk.p_end[0]
            start_y = last_chunk.point_at(1.0)[1] #to get the real y (why real y ??)

            new_chunk, _ = self.create_chunk(start_x, start_y)
            self.chunks.append(new_chunk)

    def change_color(self, color):
         self.color = color

    def draw(self, screen, ox=0, oy=0, sky=None, angle=0 ,pivot= None):
        for chunk in self.chunks:

            if sky:
                 chunk.color = sky.tint(self.color)
            else:
                 chunk.color = self.color
                 
            chunk.draw(screen, ox=-self.scroll, oy=0)