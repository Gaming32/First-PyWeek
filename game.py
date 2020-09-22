#!/usr/bin/env python3

from enum import Enum
import math
import os
import pickle
import random
from sys import stdout
from typing import Callable, Union
import numpy
import copyreg

import pygame
from pygame import Surface, time
from pygame.display import Info
from pygame.event import Event
from pygame.locals import *
from pygame.math import *


def size_from_ratio(w, h, r):
    rh = w/h
    if rh >= 1:
        return int(h * r), h
    else:
        return w, int(w / r)


WIDTH = 640
HEIGHT = 480
RATIO = 4/3
# FPS = 60
FPS = 0
SPEED = 3
CAMERA_SPEED = 1

PLAYER_SLICE = (26, 36)
PLAYER_ANIMATION_COUNT = 3
PLAYER_ANIMATION_MIN = 350

# Define Colors 
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

mode_2d = False

## initialize pygame and create window
pygame.init()
# pygame.mixer.init()  ## For sound
info = Info()
size = size_from_ratio(info.current_w, info.current_h, RATIO)
screen = pygame.display.set_mode(size, FULLSCREEN)
scale_direct = size[0] / WIDTH
growness = 50
scale = scale_direct * growness
offset = Vector2(640/2/growness, 480/2/growness)
print('Scale:', scale_direct, scale)
clock = pygame.time.Clock()     ## For syncing the FPS


## group all the sprites together for ease of update
foreground_sprites = pygame.sprite.Group()


def clamp(x, mi, ma):
    return max(mi, min(ma, x))


def clamp01(x):
    return clamp(x, 0, 1)


def rot_center(image, angle):

    center = image.get_rect().center
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = center)

    return rotated_image, new_rect


def get_player_animation_rect(x, y):
    return Rect((PLAYER_SLICE[0] * x, PLAYER_SLICE[1] * y), PLAYER_SLICE)


def get_player_animation_frame(surface: Surface, direction):
    return surface.subsurface(
        get_player_animation_rect(
            (pygame.time.get_ticks() // PLAYER_ANIMATION_MIN) % PLAYER_ANIMATION_COUNT + 3,
            direction
        )
    )


class Camera:
    def __init__(self):
        self.position = Vector2()

    def update(self, player):
        value = clamp01(CAMERA_SPEED * delta_time)
        newpos = self.position.lerp(player.position, value)
        if newpos.distance_squared_to(player.position) > 1:
            self.position.update(newpos)

camera = Camera()


def floor_vector(vec: Union[Vector2, Vector3]):
    return type(vec)([int(part) for part in vec])


class PositionBasedSprite(pygame.sprite.Sprite):
    base_image: Surface

    def __init__(self, size=None):
        super().__init__()
        self.position = Vector2()
        self.rotation = 0
        self.size = size
        self._last_position_pos = [None, None]
        self._last_position_image = [None, None]

    def _get_image(self):
        if self._last_position_image[0] == ((self.position, self.rotation), camera.position):
            return self._last_position_image[1]
        self._last_position_image[0] = ((Vector2(self.position), self.rotation), Vector2(camera.position))
        scaled_size = math.floor(self.size * scale)
        result = pygame.transform.scale(self.base_image, (scaled_size, scaled_size))
        result = rot_center(result, self.rotation)
        self._last_position_image[1] = result
        return result

    @property
    def image(self):
        if self._pos_on_screen() is None:
            return Surface((0, 0))
        return self._get_image()[0]

    @property
    def radius(self):
        return self.size // 2 * scale

    def _pos_on_screen(self):
        if self._last_position_pos[0] == (self.position, camera.position):
            return self._last_position_pos[1]
        self._last_position_pos[0] = (Vector2(self.position), Vector2(camera.position))
        base_vector = Vector2(self.position)
        base_vector += offset
        base_vector -= camera.position
        if self.size <= 1 and (
               base_vector.x < -1
            or base_vector.y < -1
            or base_vector.x > growness * 4 / 3 + 1
            or base_vector.y > growness + 1
        ):
            self._last_position_pos[1] = None
            return None
        self._last_position_pos[1] = base_vector
        return base_vector

    @property
    def rect(self):
        # scaled_size = math.floor(self.size * scale)
        base_vector = self._pos_on_screen()
        # base_vector = Vector2(self.position)
        # base_vector += offset
        # base_vector -= camera.position
        if base_vector is None:
            return Rect(-1920, -1080, 0, 0)
        base_vector = floor_vector(base_vector * scale)
        base_vector.y = HEIGHT * scale_direct - base_vector.y
        rect = Rect(self._get_image()[1])
        rect.x += round(base_vector[0])
        rect.y += round(base_vector[1])
        return rect


class Player(PositionBasedSprite):
    player_raw_image = pygame.image.load('assets/player.png').convert_alpha()

    def __init__(self):
        super().__init__(1)
        self.base_image = get_player_animation_frame(self.player_raw_image, 0)
        self.animation_time_passed = 0

    def update(self, *args, **kwargs):
        # mouse_pos = pygame.mouse.get_pos()
        # mouse_rel = Vector2(mouse_pos) - Vector2(self.rect.center)
        # mouse_direction = -mouse_rel.as_polar()[1] - 90
        # self.rotation = mouse_direction
        if movement:
            to_move = movement.normalize()
            if mode_2d:
                to_move.y *= 2
            self.position += to_move * delta_time * SPEED
            # self.position.update(clamp(self.position.x, -24, 24), clamp(self.position.y, -2, 18))
            oldpos = Vector2(self.position)
            self.position.update(((-self.position.x) % 24) * -1, clamp(self.position.y, -2, 18))
            if abs(self.position.x - oldpos.x) > 12:
                camera_offset = oldpos - camera.position
                camera.position.update(self.position - camera_offset)
            general_direction = (math.degrees(math.atan2(movement.y, movement.x)) + 45) // 45
            if not mode_2d:
                if general_direction == -1:
                    animation_direction = 0
                elif general_direction in (5, 4, -2):
                    animation_direction = 1
                elif general_direction == 3:
                    animation_direction = 3
                else:
                    animation_direction = 2
            else:
                if general_direction == 5:
                    animation_direction = 1
                else:
                    animation_direction = 2
            self.base_image = get_player_animation_frame(self.player_raw_image,
                                                         animation_direction)

player = Player()
# player.position += (16, 12)


map_point = (-40, 32)
map_size = (80, 56)
water_size = 8
total_size = (map_size[0], map_size[1] + water_size)

if os.path.exists('cache'):
    bg_image = pygame.image.load('cache/bigmap.png')

else:
    os.mkdir('cache')

    sand_base = pygame.image.load('assets/sand.png')
    water_base = pygame.image.load('assets/water.png')
    bg_image = Surface((total_size[0] * 16, total_size[1] * 16))
    sand = []
    water = []
    for r in range(4):
        sand.append(pygame.transform.rotate(sand_base, 90 * r))
        water.append(pygame.transform.rotate(water_base, 90 * r))
    for x in range(map_size[0]):
        for y in range(map_size[1]):
            rect = Rect(x * 16, y * 16, 16, 16)
            bg_image.blit(random.choice(sand), rect)
    for x in range(map_size[0]):
        for y in range(water_size):
            rect = Rect(x * 16, (y + map_size[1]) * 16, 16, 16)
            bg_image.blit(random.choice(water), rect)
    pygame.image.save(bg_image, 'cache/bigmap.png')


class Background(PositionBasedSprite):
    base_image = bg_image
    position = Vector2(map_point)


class StandalonePositionBasedRenderer:
    def __init__(self, surface: Surface, position: Vector2):
        self.surface = surface
        # self.resize(scale)
        self.position = position
        self._last_position = [None, None]

    def resize(self, scale):
        self.surface = pygame.transform.scale(self.surface,
            [round(x * scale) for x in self.surface.get_size()])

    def _pos_on_screen(self):
        if self._last_position[0] == (self.position, camera.position):
            return self._last_position[1]
        self._last_position[0] = (Vector2(self.position), Vector2(camera.position))
        base_vector = Vector2(self.position)
        base_vector += offset
        base_vector -= camera.position
        self._last_position[1] = base_vector
        return base_vector

    def _pos_in_screen(self):
        rel_pos = self._pos_on_screen()
        base_vector = floor_vector(rel_pos * scale)
        base_vector.y = HEIGHT * scale_direct - base_vector.y
        return base_vector * -1

    def draw(self, on: Surface):
        base_vector = self._pos_in_screen()
        # base_vector = floor_vector(base_vector * scale)
        # base_vector.y = HEIGHT * scale_direct - base_vector.y
        subrect = Rect(base_vector // 4, (160, 120))
        if self.surface.get_rect().colliderect(subrect):
            surf = self.surface.subsurface(subrect)
            # print(tuple(int(x) for x in Vector2(size) * 16))
            surf = pygame.transform.scale(surf, size)
            rect = Rect((0, 0), size)
            on.blit(surf, rect)


level_font = pygame.font.SysFont('calibri', 20)


class Tile(PositionBasedSprite):
    def __init__(self, x, y):
        if not isinstance(self.__class__.base_image, Surface):
            self.__class__.base_image = pygame.image.load(self.__class__.base_image)
        super().__init__(1)
        self.position.update(x, y)


class TileTypes(Enum):
    Air = 0xffffff
    Spawn = 0x00ff00
    Wall = 0x006080
    Ground = 0x008000


class GroundTile(Tile):
    base_image = 'assets/grass.png'


class LevelData:
    def __init__(self, number):
        self.number = number
        self.root = f'levels/level{number}'
        self._init_attrs()
        if not os.path.isdir(self.root):
            print(f'Warning: "{self.root}" does not exist or is not a directory. Level skipped.')
        else:
            self._load_level()
            # self.background = pygame.image.load(self._get_file_path('background.jpg'))

    def _get_file_path(self, file):
        return os.path.join(self.root, file)

    def _init_attrs(self):
        self.size = (0, 0)
        self.tiles = []
    
    def _load_level(self):
        map_path = self._get_file_path('map.png')
        level_map_image = pygame.image.load(map_path)
        level_map = pygame.surfarray.array2d(level_map_image)
        del level_map_image
        self.size = level_map.shape
        height = self.size[1]
        for x in range(self.size[0]):
            row = []
            self.tiles.append(row)
            for y in range(height):
                pixel = level_map[x, y]
                if pixel == TileTypes.Air.value:
                    row.append(None)
                elif pixel == TileTypes.Spawn.value:
                    row.append(None)
                elif pixel == TileTypes.Ground.value:
                    tile = GroundTile(x, height - y)
                    row.append(tile)
                else:
                    print(f'Unknown color in {map_path}({x},{y}): {hex(pixel)} Skipping tile.')


class GameStartingItem(PositionBasedSprite):
    current_level = None
    base_image = pygame.image.load('assets/tree.png').convert_alpha()
    levels = []

    def __init__(self, number):
        super().__init__(1)
        self.levels.append(self)
        self.position += (-number * 2.5, 2)
        self.number = number
        foreground_sprites.add(self)
        self.base_image = self.base_image.copy()
        text = level_font.render(str(number + 1), False, WHITE)
        rect = text.get_rect()
        rect.x = rect.x + 11 - rect.width // 2
        rect.y = rect.y + 11 - rect.height // 2
        self.base_image.blit(text, rect)
        self.data = self._load_data()

    def _load_data(self) -> LevelData:
        cached_level = f'cache/level{self.number}.pkl'
        if os.path.exists(cached_level):
            with open(cached_level, 'rb') as fp:
                result = pickle.load(fp)
                if not isinstance(result, LevelData):
                    raise TypeError('Cached level is not an instance of LevelData')
                return result
        else:
            result = LevelData(self.number)
            with open(cached_level, 'wb') as fp:
                pickle.dump(result, fp)
            return result

    def update(self, *args, **kwargs):
        if self.rect.colliderect(player.rect):
            print('Level', self.number, 'started')
            global mode_2d
            mode_2d = True
            player.position.y = 0
            movement.update(0, 0)
            foreground_sprites.remove(*self.levels)
            self._begin_level()

    def _begin_level(self):
        for row in self.data.tiles:
            foreground_sprites.add(*(tile for tile in row if tile is not None))
        GameStartingItem.current_level = self

    def _end_level(self):
        for row in self.data.tiles:
            foreground_sprites.remove(*(tile for tile in row if tile is not None))


level0 = GameStartingItem(0)
level1 = GameStartingItem(1)
level2 = GameStartingItem(2)
level3 = GameStartingItem(3)
level4 = GameStartingItem(4)
level5 = GameStartingItem(5)
level6 = GameStartingItem(6)
level7 = GameStartingItem(7)
level8 = GameStartingItem(8)
level9 = GameStartingItem(9)


# background_sprites = pygame.sprite.Group()
# background_sprites.add(Background(max(total_size)))
background = StandalonePositionBasedRenderer(bg_image, map_point)
foreground_sprites.add(player)


ui_group = pygame.sprite.Group()


def inverted_colors(img):
    inv = Surface(img.get_rect().size, SRCALPHA)
    inv.fill((255, 255, 255, 255))
    inv.blit(img, (0, 0), None, pygame.constants.BLEND_RGB_SUB)
    return inv


class UIButton(pygame.sprite.Sprite):
    bgleft = pygame.image.load('assets/button-bg-left.png').convert_alpha()
    bgmiddle = pygame.image.load('assets/button-bg-middle.png').convert_alpha()
    bgright = pygame.image.load('assets/button-bg-right.png').convert_alpha()

    def __init__(self, content: Surface, rect: Rect, commands: Callable[[Event], None] =None, include_background=True):
        if commands is None:
            commands = []
        super().__init__()
        self.background = Surface(rect.size, pygame.SRCALPHA, 32).convert_alpha()
        self.content = content
        self.rect = rect
        self.commands = commands
        self.include_background = include_background
        self.background_elements = [
            pygame.transform.scale(element, (11, rect.height))
            for element in (self.bgleft, self.bgmiddle, self.bgright)
        ]
        self.inverted_background_elements = [
            # inverted_colors(element)
            element.copy()
            for element in self.background_elements
        ]
        for elem in self.inverted_background_elements:
            array = pygame.surfarray.pixels2d(elem)
            # array ^= 2 ** 32 - 1
            LIGHT_BLUE = 0xFF0094FF
            DARK_BLUE = 0xFF0026FF
            array[array == LIGHT_BLUE] = DARK_BLUE
            array[array == DARK_BLUE] = LIGHT_BLUE
            del array
    
    def _call(self, event):
        for command in self.commands:
            command(event)

    def update(self, mouse_events):
        if self.include_background:
            self.background.fill((0, 0, 0, 0))
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                elements = self.inverted_background_elements
            else:
                elements = self.background_elements
            self.background.blit(
                elements[0],
                Rect(0, 0, 11, self.rect.height)
            )
            for i in range(1, self.rect.width // 11):
                self.background.blit(
                    elements[1],
                    Rect(i * 11, 0, 11, self.rect.height)
                )
            self.background.blit(
                elements[2],
                Rect(self.rect.width - 11, 0, 11, self.rect.height)
            )
        for event in mouse_events:
            if (
                event.type == MOUSEBUTTONUP
                and event.button == 1
                and self.rect.collidepoint(event.pos)
            ):
                print(event)
                self._call(event)

    @property
    def image(self):
        result = self.background.copy()
        result.blit(self.content, Rect((0, 0), self.rect.size))
        return result


def on_quit_button(event):
    global running
    running = False

quit_button = UIButton(
    pygame.transform.scale(
        pygame.image.load('assets/exit.png').convert_alpha(), (50, 50)),
    Rect(size[0] - 60, 10, 50, 50),
    [on_quit_button]
)

ui_group.add(quit_button)


movement = Vector2()
## Game loop
running = True
smoothfps = FPS if FPS > 0 else 1000
fps_smoothing = 0.9

MOUSE_EVENT_TYPES = [MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION, MOUSEWHEEL]
mouse_events = []
while running:

    delta_time = clock.tick(FPS) / 1000     ## will make the loop run at the same speed all the time
    if delta_time > 0:
        thisfps = 1 / delta_time
    else:
        thisfps = 1000
    smoothfps = (smoothfps * fps_smoothing) + (thisfps * (1 - fps_smoothing))
    # if delta_time > 0:
    #     print('FPS:', 1/delta_time, ' '*24, end='\r')
    # else:
    #     print('FPS:', '>1000', ' '*24, end='\r')
    stdout.write(f'FPS: {int(smoothfps)}{" " * 24}\r')
    
    # if mode_2d:
    #     movement.y = 0
    mouse_events.clear()
    #1 Process input/events
    for event in pygame.event.get():        # gets all the events which have occured till now and keeps tab of them.
        ## listening for the the X button at the top
        if event.type == pygame.QUIT:
            running = False
        elif event.type == KEYDOWN:
            if event.key == K_a:
                movement.x -= 1
            elif event.key == K_d:
                movement.x += 1
            if not mode_2d:
                if event.key == K_w:
                    movement.y += 1
                elif event.key == K_s:
                    movement.y -= 1
            else:
                if event.key == K_SPACE:
                    movement.y = 1000
        elif event.type == KEYUP:
            if event.key == K_a:
                movement.x += 1
            elif event.key == K_d:
                movement.x -= 1
            if not mode_2d:
                if event.key == K_w:
                    movement.y -= 1
                elif event.key == K_s:
                    movement.y += 1
            else:
                if event.key == K_SPACE:
                    movement.y = 0
        elif event.type in MOUSE_EVENT_TYPES:
            mouse_events.append(event)

    #2 Update
    # background_sprites.update()
    foreground_sprites.update()
    camera.update(player)

    #3 Draw/render
    if mode_2d:
        # screen.fill(BLACK)
        # screen.blit(GameStartingItem.current_level.data.background, Rect((0, 0), size))
        pass

    # background_sprites.draw(screen)
    if not mode_2d:
        background.draw(screen)
    foreground_sprites.draw(screen)
    ########################

    ### Your code comes here

    ########################

    ## Done after drawing everything to the screen
    ui_group.update(mouse_events)
    ui_group.draw(screen)
    pygame.display.flip()       

pygame.quit()
