import math
import random
from shapes import TriangularShape
from shapes import Circle

class Snow(Circle):
    '''
    Falling snow
    '''
    def __init__(self, screen_width, screen_height, color):
        super().__init__(0, 0, 2, color, 6)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.color = color
        
        # Counter for each leaf to make it fall randomly
        self.time = random.uniform(0, 100) 
        self._respawn(random.uniform(0, screen_height))

    def _respawn(self, y):
        self.base_x = random.uniform(0, self.screen_width)
        self.x = self.base_x
        self.y = y

        self.radius = random.uniform(2, 4)

        self.speed_y = random.uniform(20, 60) #falling speed
        self.speed_x = random.uniform(0.5, 1.5) #horizontal speed
        self.sway_amount = random.uniform(15, 40)

    def update(self, dt):
        self.time += dt
        self.y += self.speed_y * dt
        
        # For the ondulation, use sinus of the time with the speed
        self.x = self.base_x + math.sin(self.time * self.speed_x) * self.sway_amount

        # Respawn if out of screen
        if self.y > self.screen_height:
            self._respawn(-self.radius * 2)

class SnowsManager:
    '''
    Manage the leaves
    '''
    def __init__(self, screen_width, screen_height, color=(255, 255, 255), nb_snow=100):
        self.snowflakes = [Snow(screen_width, screen_height, color) for _ in range(nb_snow)]

    def update(self, dt):
        for snow in self.snowflakes:
            snow.update(dt)

    def draw(self, screen):
        for snow in self.snowflakes:
            snow.draw(screen)