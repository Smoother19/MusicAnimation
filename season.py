import pygame
import math
import random
from rain import Rain
from sky import lerp_color
from snows import *
from leaves import *
from shapes import *
from config import *

class Season():
    '''
    Manages the season of the game
    '''
    def __init__(self, nb_cycle):
        '''
        '''
        self.mountain_palettes = [
            [(30, 40, 60), (45, 55, 75), (60, 70, 90)],           # summmer
            [(65, 35, 25), (90, 55, 45), (110, 80, 70)],          # autumn
            [(90, 100, 120), (120, 130, 150), (150, 160, 180) ],   # winter
            [(45, 65, 50), (60, 80, 65), (75, 95, 85)]            # spring
        ]
        autumn_colors = [(200, 75, 25), (220, 120, 30), (160, 60, 20), (210, 160, 40)]
        spring_colors = [(255, 183, 197), (255, 145, 164), (255, 230, 240)]

        self.nb_cycle = nb_cycle #the nb of the current cycle
        self.season_type = 0

        self.rain = Rain(SCREEN_WIDTH, SCREEN_HEIGHT, nb_drops=100)
        self.autumn_leaves = LeavesManager(SCREEN_WIDTH, SCREEN_HEIGHT, autumn_colors)
        self.spring_leaves = LeavesManager(SCREEN_WIDTH, SCREEN_HEIGHT, spring_colors)
        self.snows = SnowsManager(SCREEN_WIDTH, SCREEN_HEIGHT, (255, 255, 255))

        #Manage opacity of season
        self.opacity_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.alpha = 255

    def update(self, dt, total_phase, screen, mountains):
        '''
        Manage the switch between the season
        '''
        self.season_type = (int(total_phase) % 4)

        #actual time in the season
        progression = total_phase % 1.0
        fade_duration = 0.1

        prev_season_type = (self.season_type - 1) % 4

        target_colors = self.mountain_palettes[self.season_type]
        prev_colors = self.mountain_palettes[prev_season_type]

        if progression < fade_duration:
            #Fade in
            percent_mix = progression / fade_duration

            actuals_color = []
            for color_prev, color_target in zip(prev_colors, target_colors):
                actuals_color.append(lerp_color(color_prev, color_target, percent_mix))

            self.alpha = int((progression / fade_duration) * 255)
        elif progression > (1.0 - fade_duration):
            #Fade out
            actuals_color = target_colors
            self.alpha = int(((1.0 - progression) / fade_duration) * 255)
        else:
            #Full opacity
            actuals_color = target_colors
            self.alpha = 255

        for mountain, color in zip(mountains, actuals_color):
            mountain.change_color(color)

        self.opacity_layer.fill((0,0,0,0))

        match self.season_type:
            case 0:
                self.summer(mountains)
            case 1:
                self.autumn(dt, self.opacity_layer, mountains)
            case 2:
                self.winter(dt, self.opacity_layer, mountains)
            case 3:
                self.spring(dt, self.opacity_layer, mountains)

        #set the alpha of the second screen
        self.opacity_layer.set_alpha(self.alpha)

        #set the new screen on the actual one
        screen.blit(self.opacity_layer, (0,0))
        


    def summer(self, mountains):
        '''
        TODO add the fougère
        '''

    def autumn(self, dt, screen, mountains):
        '''
        Add the fall of orange leafs and rain
        '''
        self.rain.update(dt)
        self.rain.draw(screen)

        self.autumn_leaves.update(dt)
        self.autumn_leaves.draw(screen)

    def winter(self, dt, screen, mountains):
        '''
        Add the fall of the snow
        '''
        self.snows.update(dt)
        self.snows.draw(screen)


    def spring(self, dt, screen, mountains):
        '''
        Add the fall of sakura's 
        '''

        self.spring_leaves.update(dt)
        self.spring_leaves.draw(screen)