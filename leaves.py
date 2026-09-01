import math
import random
from shapes import TriangularShape

class Leaf(TriangularShape):
    '''
    Falling leaf
    '''
    def __init__(self, screen_width, screen_height, palette_couleurs):
        super().__init__(0, 0, 0, 0, (255, 255, 255))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.palette = palette_couleurs

        #self.axiom = "F++F++F"  #based triangle it's a full circled leaf
        self.axiom = "F+F+F+F+F" #erable leaf
        self.rules = {"F": "F-F++F-F"} # Each edge becomes serrated
        self.iteration = 2

        self.local_points = self._build_local_contour()
        
        # Counter for each leaf to make it fall randomly
        self.time = random.uniform(0, 100) 
        self._respawn(random.uniform(0, screen_height))

    def _build_local_contour(self):
        '''
        Take the L-System to create the leaf
        '''
        current = self.axiom

        for _ in range(self.iteration):
            next_string = ""
            for char in current:
                next_string += self.rules.get(char, char)
            current = next_string

        points = []
        x, y = 0.0, 0.0
        angle = 0.0
        step = 1.0

        for char in current:
            if char == 'F':
                x += math.cos(angle) * step
                y += math.sin(angle) * step
                points.append((x, y))
            elif char == '+':
                angle += math.radians(72) # to create a pantagon
            elif char == '-':
                angle -= math.radians(72)

        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2

        stretch_x = random.uniform(1.1, 1.4)
        stretch_y = random.uniform(0.9, 1.1)
        return[((p[0] - cx) * stretch_x, (p[1]- cy) * stretch_y) for p in points]

    def _respawn(self, y):
        # Give random params when the leaf's respawn
        self.base_x = random.uniform(0, self.screen_width)
        self.x = self.base_x
        self.y = y

        
        self.size = random.uniform(0.8, 2)
        self.speed_y = random.uniform(40, 100)  # Fall speed
        self.speed_x = random.uniform(1, 3)     # Swinging speed (left/right)
        self.sway_amount = random.uniform(20, 60) # Amplitude of the swing
        
        # Rotation
        self.angle = random.uniform(0, math.tau)
        self.rotation_speed = random.uniform(-3, 3) # Rotate around itself
        
        # Take random color in the palette
        self.color = random.choice(self.palette)

    def update(self, dt):
        self.time += dt
        self.y += self.speed_y * dt
        
        # For the ondulation, use sinus of the time with the speed
        self.x = self.base_x + math.sin(self.time * self.speed_x) * self.sway_amount
        
        # Rotate the leaf
        self.angle += self.rotation_speed * dt

        # Respawn if out of screen
        if self.y > self.screen_height:
            self._respawn(-self.size * 2)

    def list_triangles(self):
        '''
        Dessine la feuille sous forme de losange (2 triangles collés)
        '''
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        transformed_points = []
        for px, py in self.local_points:
            # Scale
            px *= self.size
            py *= self.size
            # Rotation
            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a
            # Final position
            transformed_points.append((self.x + rx, self.y + ry))

        # Create the triangles
        triangles = []
        center = (self.x, self.y)
        
        for i in range(len(transformed_points)):
            p1 = transformed_points[i]
            p2 = transformed_points[(i + 1) % len(transformed_points)]            
            triangles.append([center, p1, p2])

        return triangles


class LeavesManager:
    '''
    Manage the leaves
    '''
    def __init__(self, screen_width, screen_height, colors, nb_leaves=50):
        self.leaves = [Leaf(screen_width, screen_height, colors) for _ in range(nb_leaves)]

    def update(self, dt):
        for leaf in self.leaves:
            leaf.update(dt)

    def draw(self, screen):
        for leaf in self.leaves:
            leaf.draw(screen)