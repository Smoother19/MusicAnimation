import pygame as ui
import math

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
        for i, triangle in enumerate(triangles):
            pts = [(px + ox, py + oy) for (px, py) in triangle]
            ui.draw.polygon(screen, "white", pts)

    def getX(self):
        '''
        Get the list of the x of the triangular shape
        '''
        return []

    def setX(self):
        '''
        Set new list of x of the triangular shape
        '''

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