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
        
        # Counter for each leaf to make it fall randomly
        self.time = random.uniform(0, 100) 
        self._respawn(random.uniform(0, screen_height))

    def _respawn(self, y):
        # Give random params when the leaf's respawn
        self.base_x = random.uniform(0, self.screen_width)
        self.x = self.base_x
        self.y = y

        
        self.size = random.uniform(8, 16)
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

        hw = self.size * 0.4 # half-width
        hl = self.size       # half-length

        # the coins of the 2 triangles
        pts = [(0, -hl), (hw, 0), (0, hl), (-hw, 0)]

        # Rotate and position the 4 points on the screen.
        rotated = []
        for px, py in pts:
            rx = self.x + (px * cos_a - py * sin_a)
            ry = self.y + (px * sin_a + py * cos_a)
            rotated.append((rx, ry))

        p_top, p_right, p_bottom, p_left = rotated

        # create a diamond with 2 triangles
        return [
            [p_top, p_left, p_right],
            [p_bottom, p_left, p_right]
        ]


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