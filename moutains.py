import pygame
import math
import random
from shapes import *

class Mountains(Curve):
    '''
    Procedural moutains shape composed of an interconnected fan of triangles.

    Attributes:

    Methods:
    '''

    def __init__(self, start, end, width, color, type_curve=-1, a=1, b=0, c=0, 
                 height=0, amplitude=100, resolution=50, bottom_y = SCREEN_HEIGHT):
        super().__init__(start, end, width, color, type_curve, a, b, c, 
                         height, amplitude, resolution)
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