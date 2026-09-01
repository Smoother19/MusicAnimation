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
        s0, s1 = self.get_y_shape(-1), self.get_y_shape(1)
        self.slope = s1 - s0
        self.end_y = end[1] + self.slope * amplitude

    def point_at(self, t):
        x = self.p_start[0] + (self.p_end[0] - self.p_start[0]) * t
        x_norm = -1 + 2 * t
        s0 = self.get_y_shape(-1)
        detrended = self.get_y_shape(x_norm) - (s0 + self.slope * t)
        y = self.p_start[1] + (self.end_y - self.p_start[1]) * t + detrended * self.amplitude
        return (x, y)

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

    def __init__(self, start, end, width, color, type_curve=-1, a=1, b=0, c=0, 
                 height=0, amplitude=100, resolution=50, bottom_y = SCREEN_HEIGHT,
                 reactivity=0.0):

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
        self.chunk_length = 400
        self.chunks = []

        self.reactivity = reactivity
        self.base_amplitude = amplitude
        self.pulse = 0.0

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

        real_end_y = chunk.point_at(1.0)[1] 

        return chunk, real_end_y

    def update(self, dt, speed=10, level=0.0):
        # Montee immediate, retombee amortie : sans ce lissage la chaine
        # sautille au lieu de respirer.
        self.pulse = level if level > self.pulse else self.pulse + (level - self.pulse) * min(1.0, dt * 6.0)

        self.scroll += speed * dt

        first_chunk = self.chunks[0]

        if first_chunk.p_end[0] - self.scroll < 0:
            self.chunks.pop(0)

            last_chunk = self.chunks[-1]
            start_x = last_chunk.p_end[0]
            start_y = last_chunk.point_at(1.0)[1]

            new_chunk, _ = self.create_chunk(start_x, start_y)
            self.chunks.append(new_chunk)

    def change_color(self, color):
         self.color = color

    def draw(self, screen, sky=None, ox=0, oy=0, angle=0, pivot=None):
        base = sky.tint(self.color) if sky else self.color
        color = shade(base, 1.0 + 0.35 * self.pulse)
        lift = -self.reactivity * self.pulse
        amplitude = self.base_amplitude * (0.5 + 1.4 * self.pulse)

        for chunk in self.chunks:
            chunk.color = color
            chunk.amplitude = amplitude
            chunk.draw(screen, ox=-self.scroll, oy=oy + lift)