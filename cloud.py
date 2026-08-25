import pygame
import math
import random
from shapes import *

class Cloud(Group):
    '''
    Procedural cloud shape composed of an interconnected fan of triangles.

    Attributes:
        radius (float): Base radius used to generate the cloud perimeter.
        center (tuple[float, float]): (x, y) coordinates of the cloud's center.
        color (tuple[int, int, int]): Base RGB color of the cloud.
        nb_points (int): Number of perimeter vertices to sample.
        irregularity (float): Amplitude factor controlling radius distortion.
        nb_harmonics (int): Number of sine wave harmonics for shape diversity.
        scale_x (float): Horizontal stretch factor.
        scale_y (float): Vertical stretch factor.
        width (float): Visual width assigned to triangle sub-elements.
        height (float): Visual height assigned to triangle sub-elements.

    Methods:
        get_random_param(): Generates randomized parameters for cloud generation.
        generate_clouds_points(): Computes distorted (x, y) perimeter points.
        list_triangles(points): Creates TrianglePoints connecting center to perimeter points.
        generate_cloud(): Helper method to re-generate the cloud triangles.
        moving_cloud(speed=1): Shifts the cloud horizontally.
        is_out_of_screen(screen_width): Checks if the cloud has moved off-screen.
    '''

    def __init__(self, radius, center, color, nb_points=20, 
                 irregularity=0.35, nb_harmonics=3, scale_x=1.3, scale_y=0.55, width=100, height=50):
        super().__init__(0, 0)
        self.radius = radius
        self.center = center
        self.color = color
        self.nb_points = nb_points
        self.irregularity = irregularity
        self.nb_harmonics = nb_harmonics
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.width = width
        self.height = height

        points = self.generate_clouds_points()
        list_triangle = self.list_triangles(points)
        self.add(*list_triangle)


    def get_random_param():
        rad = random.randint(40, 90)
        center = (random.randint(50, 250), random.randint(50, 250))
        color = (255, 255, 255)
        harmonics = random.randint(3, 10)
        nb_point = random.randint(5, 100)
        return (rad, center, color, nb_point, 0.35, harmonics)

    def generate_clouds_points(self):
        cx, cy = self.center
        harmonics = []#3 formulas to calculate the radius of each point
        for _ in range(self.nb_harmonics):
            harmonics.append((
                random.uniform(0.08, self.irregularity), # amplitude : à quel point ça bosselle
                random.uniform(0, math.tau), # phase : où la bosse commence
                random.randint(2, 5) # fréquence : nb de bosses sur un tour
            ))

        points = []
        n = self.nb_points

        for i in range(n):
            angle = (i / n) * math.tau #current angle
            r = self.radius #current radius
            for amp, phase, freq in harmonics:
                r += self.radius * amp * math.sin(freq * angle + phase) #adjust the radius based on the harmonics

            r = max(r, self.radius * self.irregularity)
            x = cx + r * math.cos(angle) * self.scale_x #get x position of the points
            y = cy + r * math.sin(angle) * self.scale_y #get y
            points.append((x, y))

        return points

    def list_triangles(self, points):
        n = len(points)
        triangles = []
        for i in range(n):
            a = points[i]
            b = points[(i + 1) % n]
            faceted_color = facet(self.color, i)    #to create the difference of colors
            triangles.append(TrianglePoints(self.center, a, b, self.width, self.height, faceted_color))
        return triangles

    def generate_cloud(self):
        points = self.generate_clouds_points(self.radius, self.center, self.nb_points)
        return self.list_triangles(self.center, points, self.color, self.width, self.height)

    def moving_cloud(self, speed=1):
        self.x += speed

    def is_out_of_screen(self, screen_width):
        if self.x + self.width < screen_width:
            return False
        return True