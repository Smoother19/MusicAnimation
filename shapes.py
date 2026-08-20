import colorsys
import pygame as ui
import math
import random
from config import *

FACET_STRENGTH = 0.12     # 0 = uniforme | 0.06 = leger relief | 0.25 = debug

def facet(color, i):
    if FACET_STRENGTH <= 0:
        return color
    return shade(color, 1.0 + FACET_STRENGTH * (2 * ((i * 0.5) % 1.0) - 1))

def shade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)

STATS = {"triangles": 0}
class TriangularShape():
    '''
    Base class for triangular shapes

    Attributes:
        x (int): x position of the shape
        y (int): y position of the shape
        width (int): width of the shape
        height (int): height of the shape
        color (tuple): color of the shape

    Methods:
        list_triangles(): List all the triangle in the shape
        draw(screen): Draw the shape on the screen
    '''
    def __init__(self, x, y, width, height, color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color

    def list_triangles(self):
        '''
        List all the triangle in the shape
        '''
        return []

    def draw(self, screen, ox=0, oy=0):
        '''
        Draw the shape on the screen
        '''
        triangles = self.list_triangles()
        STATS["triangles"] += len(triangles)
        for i, triangle in enumerate(triangles):
            pts = [(px + ox, py + oy) for (px, py) in triangle]
            ui.draw.polygon(screen, facet(self.color, i), pts)

class Square(TriangularShape):
    def __init__(self, x, y, size, color):
        super().__init__(x, y, size, size, color)

    def list_triangles(self):
        tl = (self.x - self.width/2, self.y - self.height/2)
        tr = (self.x + self.width/2, self.y - self.height/2)
        bl = (self.x - self.width/2, self.y + self.height/2)
        br = (self.x + self.width/2, self.y + self.height/2)

        triangle1 = [tl, tr, bl]
        triangle2 = [tr, br, bl]

        return [triangle1, triangle2]

class Rectangle(TriangularShape):
    def __init__(self, x, y, width, height, color):
        super().__init__(x, y, width, height, color)

    def list_triangles(self):
        tl = (self.x - self.width/2, self.y - self.height/2)
        tr = (self.x + self.width/2, self.y - self.height/2)
        bl = (self.x - self.width/2, self.y + self.height/2)
        br = (self.x + self.width/2, self.y + self.height/2)

        triangle1 = [tl, tr, bl]
        triangle2 = [tr, br, bl]

        return [triangle1, triangle2]

class Triangle(TriangularShape):
    def __init__(self, x, y, width, height, color):
        super().__init__(x, y, width, height, color)

    def list_triangles(self):
        tl = (self.x - self.width/2, self.y + self.height/2)
        tr = (self.x + self.width/2, self.y + self.height/2)
        bl = (self.x, self.y - self.height/2)

        triangle1 = [tl, tr, bl]

        return [triangle1]

class Curve(TriangularShape):
    '''
    Create curve based on triangular shape
    the curve is based on a function that is draw
    '''

    def __init__(self, start, end, width, color, type_curve=-1, a = 1.0, b = 0.0, c = 0.0, height= 0, amplitude=100, resolution=50):
        super().__init__(start[0], start[1], width, height, color)
        self.p_start = start
        self.p_end = end
        self.amplitude = amplitude
        self.resolution = resolution
        self.a = a
        self.b = b 
        self.c = c
        self.type_curve = type_curve
        self.rand = random.randint(0, 100)

    def get_random_params():
        type_curve = 1
        a = random.uniform(0, 3)
        b = random.uniform(0, 3)
        c = random.uniform(0, 3)
        return (type_curve, a, b, c)

    def parabola(self, x):
        return self.a * math.pow(x, 2) + self.b * x + self.c

    def sinus(self, x):
        return self.a * math.sin(x * self.b + self.c)

    def cosinus(self, x):
        return self.a * math.cos(x * self.b + self.c)

    def cubic(self, x):
        return self.a * math.pow(x, 3) + self.b * x + self.c

    def point_at(self, t):
        x = self.p_start[0] + (self.p_end[0] - self.p_start[0]) * t 
        x_norm = -1 + 2 * t     #norm it to be used in function

        y_shape = self.get_y_shape(x_norm)
        y_shape_start = self.get_y_shape(-1)

        y = self.p_start[1] + (self.p_end[1] - self.p_start[1]) * t + (y_shape - y_shape_start) * self.amplitude

        return (x, y)

    def get_y_shape(self, x_norm):
        #it will not be the same because the x isn't the same, it stays between -1 and 1
        if self.type_curve == -1:
            if self.rand <= 25:
                return self.parabola(x_norm)
            elif self.rand <= 50:
                return self.sinus(x_norm)
            elif self.rand <= 75:
                return self.cosinus(x_norm)
            else:
                return self.cubic(x_norm)
        elif self.type_curve == 1:
            return self.sinus(x_norm)


    def get_points(self):
        '''
        
        '''
        points = []
        for i in range(self.resolution):
            t = i / (self.resolution - 1)
            points.append(self.point_at(t))

        return points

    def list_triangles(self):
        points = self.get_points()
        triangles = []
        hw = self.width / 2

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            perp = angle + math.pi / 2

            a1 = (p1[0] + math.cos(perp) * hw, p1[1] + math.sin(perp) * hw)
            a2 = (p1[0] - math.cos(perp) * hw, p1[1] - math.sin(perp) * hw)
            b1 = (p2[0] + math.cos(perp) * hw, p2[1] + math.sin(perp) * hw)
            b2 = (p2[0] - math.cos(perp) * hw, p2[1] - math.sin(perp) * hw)

            triangles.append([a1, a2, b1])
            triangles.append([a2, b2, b1])

        return triangles

class CurvesTrack():
    def __init__(self, y_base, chunk_length=400, amplitude=100, speed=100):
        '''
        Create a track of multiple curves
        '''
        self.y_base = y_base
        self.chunk_length = chunk_length
        self.amplitude = amplitude
        self.speed = speed
        self.scroll = 0.0
        self.chunks = []

        x = 0
        last_y = y_base
        while x < SCREEN_WIDTH + chunk_length:
            chunk, _ = self.make_chunk(x, last_y)
            self.chunks.append(chunk)
            real_end = chunk.point_at(1.0)
            x = real_end[0]
            last_y = real_end[1]

    def make_chunk(self, start_x, start_y):
        '''
        Create new chunk to be added on the screen
        '''
        end_x = start_x + self.chunk_length
        end_y = self.y_base

        type_curve, a, b, c = Curve.get_random_params()
        chunk = Curve((start_x, start_y), (end_x, end_y), 5, (52, 48, 44), type_curve, a, b, c, amplitude=self.amplitude)
        return chunk, end_y

    def update(self, dt):
        self.scroll -= self.speed * dt

        #get the first "curve"'s x position (with the scroll)
        first_chunk = self.chunks[0].p_end[0] + self.scroll
        if first_chunk < 0:
            self.chunks.pop(0)
            last_chunk = self.chunks[-1]

            real_end = last_chunk.point_at(1.0)

            new_chunk, _ = self.make_chunk(real_end[0], real_end[1])
            self.chunks.append(new_chunk)

    def draw(self, screen):
        for chunk in self.chunks:
            chunk.draw(screen, ox=self.scroll, oy=0)

        for chunk in self.chunks:
            joint = chunk.point_at(1.0)
            patch = Circle(joint[0] + self.scroll, joint[1], chunk.width /2, chunk.color, 10)
            patch.draw(screen)


class TrianglePoints(TriangularShape):
    '''
    Create a triangle based on 3 points
    '''
    def __init__(self, a, b, c, width, height, color):
        super().__init__(0, 0, width, height, color)
        self.a = a
        self.b = b
        self.c = c

    def list_triangles(self):
        triangle1 = [self.a, self.b, self.c]
        return [triangle1]

    def getX(self):
        return (self.a[0], self.b[0], self.c[0])

    def setX(self, x_a, x_b, x_c):
        self.a = (self.a[0] + x_a, self.a[1])
        self.b = (self.b[0] + x_b, self.b[1])
        self.c = (self.c[0] + x_c, self.c[1])

class Group(TriangularShape):
    'Permit to group shapes together and move them as a whole'
 
    def __init__(self, x=0, y=0):
        super().__init__(x, y, 0, 0, (0, 0, 0))
        self.children = []
 
    def add(self, *shapes):
        self.children.extend(shapes)
        return shapes[-1]
 
    def list_triangles(self):
        out = []
        for child in self.children:
            for tri in child.list_triangles():
                out.append([(px + self.x, py + self.y) for (px, py) in tri])
        return out
 
    def draw(self, screen, ox=0, oy=0):
        for child in self.children:
            child.draw(screen, ox + self.x, oy + self.y)
    
class Circle(TriangularShape):
    '''
    Circle class

    Attributes:
        x (int): x position of the circle
        y (int): y position of the circle
        radius (int): radius of the circle
        color (tuple): color of the circle
        parts (int): number of parts to split the circle into
    '''
    def __init__(self, x, y, radius, color, parts):
        super().__init__(x, y, radius * 2, radius * 2, color)
        self.radius = radius
        self.parts = parts

    def list_triangles(self):
        angle = 360 / self.parts
        triangles = []

        for i in range(self.parts):
            c = (self.x, self.y)
            a = (self.x + self.radius * math.cos(math.radians(i * angle)), self.y + self.radius * math.sin(math.radians(i * angle)))
            b = (self.x + self.radius * math.cos(math.radians((i + 1) * angle)), self.y + self.radius * math.sin(math.radians((i + 1) * angle)))

            triangle = [c, a, b]
            triangles.append(triangle)

        return triangles

class Quad(TriangularShape):
 
    def __init__(self, points, color):
        xs = []
        ys = []
        for x, y in points:
            xs.append(x)
            ys.append(y)

        super().__init__(sum(xs) / 4, sum(ys) / 4,
                         max(xs) - min(xs), max(ys) - min(ys), color)
        self.points = points
 
    def list_triangles(self):
        a, b, c, d = self.points
        return [[a, b, c], [a, c, d]]

class Trapezoid(TriangularShape):
 
    def __init__(self, x, y, w_top, w_bottom, height, color):
        super().__init__(x, y, max(w_top, w_bottom), height, color)
        self.w_top = w_top
        self.w_bottom = w_bottom
 
    def list_triangles(self):
        tl = (self.x - self.w_top / 2, self.y - self.height / 2)
        tr = (self.x + self.w_top / 2, self.y - self.height / 2)
        bl = (self.x - self.w_bottom / 2, self.y + self.height / 2)
        br = (self.x + self.w_bottom / 2, self.y + self.height / 2)
        return [[tl, tr, bl], [tr, br, bl]]
 
def _rgb(h, s, v):
    return tuple(int(255 * c) for c in colorsys.hsv_to_rgb(h % 1.0, s, v))
 
 
def make_palette(rng):
    '''
    make_palette(rng) -> dict
    Generate a palette of colors for the train and its parts.
    '''
    h = rng.random()
    return {
        "body":    _rgb(h, rng.uniform(0.45, 0.75), rng.uniform(0.55, 0.80)),
        "body2":   _rgb(h + 0.02, rng.uniform(0.40, 0.65), rng.uniform(0.40, 0.60)),
        "accent":  _rgb(h + rng.choice([0.45, 0.5, 0.55]), 0.65, 0.85),
        "roof":    _rgb(h, 0.25, 0.35),
        "chassis": (48, 50, 58),
        "wheel":   (34, 36, 42),
        "hub":     (95, 100, 112),
        "glass":   _rgb(h + 0.5, 0.20, 0.95),
        "metal":   (120, 126, 138),
        "dark":    (28, 30, 36),
    }
