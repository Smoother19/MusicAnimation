import colorsys
import pygame as ui
import math

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
