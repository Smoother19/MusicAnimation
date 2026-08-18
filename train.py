from shapes import *
import pygame as ui

class Train():
    def __init__(self, x, y, color, length=260, height=150, gap=0.1, wagons=1):
        self.x = x
        self.y = y
        self.color = color
        self.length = length          
        self.height = height
        self.gap = gap
        self.wagons = wagons
        self.shapes = []

    @property
    def palette(self):
        return {
            "body": self.color,
            "body_l": shade(self.color, 1.35),
            "body_d": shade(self.color, 0.62),
            "roof": shade(self.color, 0.30),
            "accent": (188, 72, 64),
            "metal": (232, 196, 108),
            "metal_d": (150, 118, 56),
            "window": (255, 226, 150),
        }

    def _loco(self, x0, rail):
            L, H, P = self.length, self.height, self.palette
            
            def pxl(u):
                return x0 + L * u
            
            def pxh(v):
                return rail - v * H
            
            def rect(u0, u1, v0, v1, c):
                return Rectangle(
                    (pxl(u0) + pxl(u1)) / 2, (pxh(v0) + pxh(v1)) / 2,
                    (u1 - u0) * L, (v1 - v0) * H, c)
    
            s = []

            # wheels
            r_drive = 0.21
            for u in (0.42, 0.66):
                s.append(Circle(pxl(u), pxh(r_drive), r_drive * H, P["metal"], 10))
                s.append(Circle(pxl(u), pxh(r_drive), r_drive * H * 0.3, P["metal_d"], 8))
            r_front = 0.11
            s.append(Circle(pxl(0.21), pxh(r_front), r_front * H, P["metal"], 8))
    
            # frame
            s.append(rect(0.05, 0.99, 0.22, 0.30, P["roof"]))
    
            # body
            s.append(Circle(pxl(0.14), pxh(0.51), 0.21 * H, P["body_d"], 12))
            s.append(rect(0.12, 0.62, 0.30, 0.72, P["body"]))
            s.append(rect(0.12, 0.62, 0.66, 0.72, P["body_l"]))
            s.append(rect(0.12, 0.62, 0.30, 0.35, P["body_d"]))
            for u in (0.28, 0.42, 0.55):
                s.append(rect(u, u + 0.02, 0.30, 0.72, P["body_d"]))
    
            # smoke
            s.append(Circle(pxl(0.48), pxh(0.72), 0.09 * H, P["body_l"], 9))
            s.append(rect(0.44, 0.52, 0.66, 0.72, P["body"]))
    
            # chimney
            s.append(rect(0.19, 0.27, 0.72, 1.00, P["roof"]))
            s.append(rect(0.17, 0.29, 0.97, 1.06, shade(P["roof"], 1.6)))
            s.append(rect(0.19, 0.27, 0.90, 0.94, P["metal_d"]))
    
            # light
            s.append(Circle(pxl(0.11), pxh(0.66), 0.07 * H, P["metal_d"], 8))
            s.append(Circle(pxl(0.10), pxh(0.66), 0.05 * H, P["window"], 7))
    
            # cabin
            s.append(rect(0.62, 0.97, 0.22, 0.86, P["accent"]))
            s.append(rect(0.62, 0.66, 0.22, 0.86, shade(P["accent"], 1.2)))
            s.append(rect(0.60, 0.99, 0.86, 0.92, P["roof"]))
            s.append(Triangle(pxl(0.795), pxh(0.97), 0.39 * L, 0.10 * H, P["roof"]))
            s.append(rect(0.68, 0.91, 0.56, 0.80, P["roof"]))
            s.append(rect(0.69, 0.90, 0.57, 0.79, P["window"]))
    
            # rear
            s.append(rect(0.97, 1.08, 0.28, 0.34, P["roof"]))
            return s

    def _wagon(self, x0, rail, n_windows):
        L = self.length
        H = self.height
        P = self.palette

        def pxl(u):
            return x0 + L * u

        def pxh(v):
            return rail - H * v

        def rect(u0, u1, v0, v1, c):
            return  Rectangle((pxl(u1) + pxl(u0)) / 2, (pxh(v0) + pxh(v1)) / 2, (u1 - u0) * L, (v1 - v0) * H, c)

        s = []

        # wheels
        r_wheel = .13
        for u in (0.18, 0.32, 0.68, 0.82):
            s.append(Circle(pxl(u), pxh(r_wheel), 0.05 * L, P["metal_d"], 8))
            s.append(Circle(pxl(u), pxh(r_wheel), 0.05 * L, P["metal"], 6))

        s.append(rect(0.04, 0.96, 0.18, 0.26, P["roof"]))
        s.append(rect(0.02, 0.98, 0.24, 0.92, P["body"]))
        s.append(rect(0.02, 0.98, 0.86, 0.92, P["body_l"]))
        s.append(rect(0.02, 0.98, 0.24, 0.32, P["body_d"]))
        s.append(rect(0.00, 1.00, 0.92, 1.00, P["roof"]))

        u0, u1 = 0.08, 0.92
        pitch = (u1 - u0) / n_windows
        w = pitch * 0.66
        for i in range(n_windows):
            c = u0 + pitch * (i + 0.5)
            s.append(rect(c - w / 2 - 0.01, c + w / 2 + 0.01, 0.50, 0.82, P["roof"]))
            s.append(rect(c - w / 2, c + w / 2, 0.52, 0.80, P["window"]))
 
        s.append(rect(0.02, 0.98, 0.42, 0.46, P["metal_d"]))
        return s

    def build(self):
        shapes = []
        cursor = self.x
        shapes += self._loco(cursor, self.y)
        cursor += self.length + self.gap
        for _ in range(self.wagons):
            shapes += self._wagon(cursor, self.y, n_windows=4)
            cursor += self.length * 1.05 + self.gap
        return shapes
 
    def list_shapes(self):
        if not self.shapes:
            self.shapes = self.build()
        return self.shapes
 
    def draw(self, screen):
        for shape in self.list_shapes():
            shape.draw(screen)