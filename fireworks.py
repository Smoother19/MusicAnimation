import pygame
import math
import random
from shapes import *

class Fireworks(Group):
    '''
    This class will create fireworks based on multiple triangles and make it explode

        Attributes:

        Methods:
    '''

    def __init__(self, x, y, color, nb_):
        super().__init__(0, 0)
        