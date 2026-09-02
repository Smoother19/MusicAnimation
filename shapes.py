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

    def rotate_point(self, point, pivot, angle):
            px, py = point
            ox, oy = pivot
            dx, dy = px - ox, py - oy
            cos_a, sin_a = math.cos(angle), math.sin(angle)

            return (ox + dx * cos_a - dy * sin_a, oy + dx * sin_a + dy * cos_a)

    def draw(self, screen, ox=0, oy=0, angle=0, pivot=None):
        '''
        Draw the shape on the screen
        '''
        triangles = self.list_triangles()
        STATS["triangles"] += len(triangles)
        for i, triangle in enumerate(triangles):
            pts = [(px + ox, py + oy) for (px, py) in triangle]
            if angle != 0 and pivot is not None:
                pts = [self.rotate_point(p, pivot, angle) for p in pts]
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
        b = random.uniform(0, 2)
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

    RAIL_COLORS = ((52, 48, 44), (107, 103, 92))
    GROUND_COLOR = (25, 28, 38)

    DIRECTION = -1

    def __init__(self, y_base, sync, span=380, width=8, step=8,
                 px_per_s=SPEED, anchor_x=SCREEN_WIDTH / 2):
        self.y_base = y_base
        self.sync = sync
        self.span = span
        self.width = width
        self.step = step
        self.px_per_s = px_per_s
        self.anchor_x = anchor_x
        self.t = 0.0

    def time_at(self, x_screen):
        return self.t + self.DIRECTION * (x_screen - self.anchor_x) / self.px_per_s

    def get_height(self, x_screen):
        return self.height_at_time(self.time_at(x_screen))

    def height_at_time(self, t):
        # relief <= 1 et |2p - 1| <= 1, donc la voie reste dans la plage.
        d = self.sync.relief(t) * (2 * self.sync.profile(t) - 1)
        return self.y_base - 0.5 * self.span * d

    def x_at(self, t_music):
        return self.anchor_x + self.DIRECTION * (t_music - self.t) * self.px_per_s

    def update(self, dt, t=None):
        if t is not None and t >= 0:
            self.t = t
        else:
            self.t += dt

    def get_info_track(self, x_screen, length):
        '''
        Return the y_center and the angle of the track based on the length and the x of the screen (y_center, angle)
        '''
        back_x = x_screen
        front_x = x_screen + length

        back_y = self.get_height(back_x)
        front_y = self.get_height(front_x)

        # Chaque wagon suit la voie sur sa propre longueur (~150 px), pas sur
        # les 582 px du train entier. Avec des pentes franches la bride a 35
        # degres coupait un passage sur quinze et decollait le wagon du rail.
        MAX_LEAN_ANGLE = math.radians(50)
        angle = math.atan2(front_y - back_y, front_x - back_x)

        angle = max(-MAX_LEAN_ANGLE, min(MAX_LEAN_ANGLE, angle))
        y_center = (front_y + back_y) / 2

        return y_center, angle

    def draw(self, screen):
        xs = range(0, SCREEN_WIDTH + self.step, self.step)
        points = [(x, self.get_height(x)) for x in xs]

        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            TrianglePoints((x0, y0), (x0, SCREEN_HEIGHT), (x1, y1),
                           0, 0, self.GROUND_COLOR).draw(screen)
            TrianglePoints((x0, SCREEN_HEIGHT), (x1, SCREEN_HEIGHT), (x1, y1),
                           0, 0, self.GROUND_COLOR).draw(screen)

            # Une traverse par demi-seconde de musique : la voie sert aussi
            # de reglet, on voit defiler le tempo.
            color = self.RAIL_COLORS[int(self.time_at(x0) * 2) % 2]
            TrianglePoints((x0, y0), (x1, y1), (x0, y0 + self.width),
                           0, 0, color).draw(screen)
            TrianglePoints((x1, y1), (x1, y1 + self.width), (x0, y0 + self.width),
                           0, 0, color).draw(screen)

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
        self.scroll = 0.0
 
    def add(self, *shapes):
        self.children.extend(shapes)
        return shapes[-1]
 
    def list_triangles(self):
        out = []
        for child in self.children:
            for tri in child.list_triangles():
                out.append([(px + self.x, py + self.y) for (px, py) in tri])
        return out
 
    def draw(self, screen, ox=0, oy=0, angle=0, pivot=None):
        for child in self.children:
            child.draw(screen, ox + self.x, oy + self.y, angle=angle, pivot=pivot)
    
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
