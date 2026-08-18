import pygame as ui
import random
from shapes import *

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

shapes = [
    Square(50, 50, 100, (255, 0, 0)),         
    Rectangle(200, 50, 150, 80, (0, 255, 0)),
    Triangle(400, 50, 100, 100, (0, 0, 255)),
    Circle(200, 300, 50, (255, 255, 0), 30)
]

def generate_clouds_points(radius: int, center, nb_points=14, irregularity=0.35,nb_harmonics=3, scale_x=1.3, scale_y=0.55):
    cx, cy = center
    harmonics = []#3 formulas to calculate the radius of each point
    for _ in range(nb_harmonics):
        harmonics.append((
            random.uniform(0.08, irregularity), # amplitude : à quel point ça bosselle
            random.uniform(0, math.tau), # phase : où la bosse commence
            random.randint(2, 5) # fréquence : nb de bosses sur un tour
        ))

    points = []
    n = nb_points

    for i in range(n):
        angle = (i / n) * math.tau #current angle
        r = radius #current radius
        for amp, phase, freq in harmonics:
            r += radius * amp * math.sin(freq * angle + phase) #adjust the radius based on the harmonics

        r = max(r, radius * 0.35)
        x = cx + r * math.cos(angle) * scale_x #get x position of the points
        y = cy + r * math.sin(angle) * scale_y #get y
        points.append((x, y))

    return points


def points_to_triangle(center, points, color, width, height):
    n = len(points)
    triangles = []
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        triangles.append(TrianglePoints(center, a, b, width, height, color))
    return triangles


def generate_cloud(center, radius, color, nb_points=14, width=100, height=50):
    points = generate_clouds_points(radius, center, nb_points=nb_points)
    return points_to_triangle(center, points, color, width, height)

def moving_cloud(cloud):
    for triangle in cloud:
        triangle.setX(1, 1, 1)

def start_gui():
    ui.init()
    screen = ui.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = ui.time.Clock()
    gui(screen)

cloud = generate_cloud((400, 300), 80, "white", 100)

def gui(screen: ui.display):
    RUNNING = True
    while RUNNING:
        for event in ui.event.get():
            if event.type == ui.QUIT:
                RUNNING = False

        screen.fill((0, 0, 0))
        for shape in shapes:
            shape.draw(screen)

        for x in cloud:
            x.draw(screen)
        moving_cloud(cloud)
        ui.display.flip()

    ui.quit()

if __name__ == "__main__":
    start_gui()