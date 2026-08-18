import pygame
import math
import random
from shapes import *

class Cloud(TriangularShape):
    '''
    This class will create clouds based on multiple triangles

    Attributes:
            radius: radius of the circle based for the cloud
            center: tuple of (x, y) for the center of the cirle
            nb_points: nb of different points for the triangles in the cloud
            irregularity: create irregularity in the amplitude of the radius
            nb_harmonics: number of harmonics for the radius (to create diversity)
            scale_x: stretch the shape in x
            scale_y: stretch the shape in y
    
        Methods:
            generate_clouds_points(): create list of differents points to be used to create triangle
            points_to_triangle(center, points, color, width, height): Create the triangle based on the points
            generate_cloud(center, radius, color, nb_points=14, width=100, height=50): Drw the shape of the cloud
            def moving_cloud(cloud, speed=1): Generate a little animation of movment to the
    '''

    def __init__(self, radius, center, color, nb_points=100, 
                 irregularity=0.35, nb_harmonics=3, scale_x=1.3, scale_y=0.55, width=100, height=50):
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
        self.points = self.generate_clouds_points()
        self.list_triangle = self.points_to_triangle()

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

    def points_to_triangle(self):
        n = len(self.points)
        triangles = []
        for i in range(n):
            a = self.points[i]
            b = self.points[(i + 1) % n]
            triangles.append(TrianglePoints(self.center, a, b, self.width, self.height, self.color))
        return triangles

    def generate_cloud(self):
        points = self.generate_clouds_points(self.radius, self.center, self.nb_points)
        return self.points_to_triangle(self.center, points, self.color, self.width, self.height)

    def moving_cloud(self, speed=1):
        for triangle in self.list_triangle:
            triangle.setX(speed, speed, speed)

    def is_out_of_screen(self, screen_width):
        for triangle in self.list_triangle:
            for x in triangle.getX():
                if x + self.width <= screen_width:
                    return False

        return True

    def draw(self, screen):
        for triangle in self.list_triangle:
            triangle.draw(screen)