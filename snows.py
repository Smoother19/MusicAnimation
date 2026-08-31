import math
import random
import pygame
from shapes import Circle, Quad

class Snow():
    '''
    Falling snow
    '''
    def __init__(self, screen_width, screen_height, color):
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

        self.size = random.randint(20, 30)  #size of the flake
        self.speed_y = random.uniform(20, 60) #falling speed
        self.speed_x = random.uniform(0.5, 1.5) #horizontal speed
        self.sway_amount = random.uniform(15, 40)

        self.center_x = self.size / 2
        self.center_y = self.size / 2

        #Create the flake's own layer for performance
        self.based = pygame.Surface((self.size, self.size), pygame.SRCALPHA)

        rand_branch = random.randint(5, 7)
        self.derive_snowflake(rand_branch)


    def derive_snowflake(self, n_branch=6):
        '''
        First rule : <Flake> -> <Center> + N * <Branch>
        '''
        self.derive_center(n_branch)

        radius_max = self.size / 2
        inital_len = radius_max * 0.45

        branch_structure = self.derive_branch(inital_len, depth=3) #we want the flake to be 2x smaller and we assure the decoration with -2

        angle_separation = (math.pi * 2) / n_branch

        for i in range(n_branch):
            angle = i * angle_separation
            self.draw_branch(branch_structure, angle)


    def derive_center(self, n_branch):
        ''' 
        Second rule : <Center> -> "Hexagon" | "Empty" 
        '''
        choice = random.choice(["HEXAGON", "EMPTY"])

        if choice == "HEXAGON":
            radius = self.size * 0.15 #the center is 15% of the total size

            center_shape = Circle(self.center_x, self.center_y, radius, self.color, n_branch)

            center_shape.draw(self.based) #we draw our center in our new layer


    def derive_branch(self, length, depth):
        '''
        Third rule: <Branch> -> <Segment> + <Branch>
        Fourth rule : <Segment> -> <Line> + <Decoration>
        '''
        if depth == 0 or length < 2:
            return []

        decoration = random.choice(["V_SPIKE", "DIAMOND", "EMPTY"])

        segment = {"length": length, "deco": decoration}

        next_segment = self.derive_branch(length * 0.6, depth - 1) #we take only the 60% of the total length and we reduce the dept level

        return [segment] + next_segment

    def draw_branch(self, branch_structure, main_angle):
        '''
        Draw the complete branch
        '''
        current_x = self.center_x
        current_y = self.center_y

        for segment in branch_structure:
            length = segment["length"]
            deco = segment["deco"]

            next_x = current_x + math.cos(main_angle) * length
            next_y = current_y + math.sin(main_angle) * length

            self.draw_line_as_quad((current_x, current_y), (next_x, next_y), 1.5)

            if deco == "V_SPIKE":
                spike_len = length * 0.5 #50% of the length of the segment
                angle_open = math.pi / 5

                # Left point of the V
                lx = next_x + math.cos(main_angle + angle_open + math.pi) * spike_len
                ly = next_y + math.sin(main_angle + angle_open + math.pi) * spike_len
                # Right point of the V
                rx = next_x + math.cos(main_angle - angle_open + math.pi) * spike_len
                ry = next_y + math.sin(main_angle - angle_open + math.pi) * spike_len
                
                # We draw or 2 lines with the quads
                self.draw_line_as_quad((next_x, next_y), (lx, ly), thickness=1.5)
                self.draw_line_as_quad((next_x, next_y), (rx, ry), thickness=1.5)

            elif deco == "DIAMOND":
                tail_x = next_x - math.cos(main_angle) * 3
                tail_y = next_y - math.sin(main_angle) * 3
                head_x = next_x + math.cos(main_angle) * 3
                head_y = next_y + math.sin(main_angle) * 3
                
                left_x = next_x + math.cos(main_angle - math.pi/2) * 2
                left_y = next_y + math.sin(main_angle - math.pi/2) * 2
                right_x = next_x + math.cos(main_angle + math.pi/2) * 2
                right_y = next_y + math.sin(main_angle + math.pi/2) * 2
                
                diamond_quad = Quad([(left_x, left_y), (head_x, head_y), (right_x, right_y), (tail_x, tail_y)], self.color)
                diamond_quad.draw(self.based)

            current_x = next_x
            current_y = next_y


    def draw_line_as_quad(self, p1, p2, thickness=1.5):
        x1, y1 = p1
        x2, y2 = p2

        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)

        if length == 0:
            return 

        #we find the perpendicular
        nx = -dy / length
        ny = dx / length
        h = thickness / 2

        #we find the 4 coins
        c1 = (x1 + nx * h, y1 + ny * h) # bottom left
        c2 = (x2 + nx * h, y2 + ny * h) # top left
        c3 = (x2 - nx * h, y2 - ny * h) # top right
        c4 = (x1 - nx * h, y1 - ny * h) # bottom right

        #we draw our line in our new layer
        line_quad = Quad([c1, c2, c3, c4], self.color)
        line_quad.draw(self.based)


    def update(self, dt):
        self.time += dt
        self.y += self.speed_y * dt
        
        # For the ondulation, use sinus of the time with the speed
        self.x = self.base_x + math.sin(self.time * self.speed_x) * self.sway_amount

        # Respawn if out of screen
        if self.y > self.screen_height:
            self._respawn(-self.size * 2)

    def draw(self, screen):
        screen.blit(self.based, (self.x, self.y))


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