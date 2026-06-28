"""
Briah Pac-Man — Working Hybrid Starter Build

A custom Pac-Man-style prototype:
- Briah, a black Belgian Malinois, collects purple coins.
- 1 smart bot chases her.
- 1 random bot wanders.
- Bone-shaped power treats temporarily let Briah disable bots.
- Title screen, pause, score, lives, restart.

Setup:
    pip install pygame

Run:
    python briah_pacman.py

Controls:
    Arrow keys or WASD = move
    P = pause/unpause
    R = restart after win/lose
    Enter/Space = start from title screen

This file is intentionally single-file, but organized into classes so it can
later be split into player.py, bot.py, maze.py, game.py, etc.
"""

import os
import random
import sys
from collections import deque

import pygame


# -----------------------------
# Config
# -----------------------------

TILE = 24
FPS = 60
PLAYER_SPEED = 140.0  # pixels per second
BOT_SPEED = 95.0      # pixels per second
POWER_SECONDS = 7.0

WALL_COLOR = (35, 35, 130)
WALL_EDGE = (100, 100, 255)
PATH_COLOR = (7, 8, 18)
COIN_COLOR = (162, 75, 255)
POWER_COIN_COLOR = (210, 150, 255)
TEXT_COLOR = (245, 245, 255)
BOT_SMART_COLOR = (255, 80, 110)
BOT_RANDOM_COLOR = (50, 210, 230)
BOT_DISABLED_COLOR = (100, 100, 110)

# Legend:
# # wall
# . coin
# o bone-shaped power treat
# P Briah start
# S smart bot start
# R random bot start
# space empty path
RAW_MAZE = [
    "#####################",
    "#P........#........o#",
    "#.###.###.#.###.###.#",
    "#o###.###.#.###.###o#",
    "#...................#",
    "#.###.#.#####.#.###.#",
    "#.....#...#...#.....#",
    "#####.### # ###.#####",
    "    #.#       #.#    ",
    "#####.# ## ## #.#####",
    "     .  #SR#  .     ",
    "#####.# ##### #.#####",
    "    #.#       #.#    ",
    "#####.# ##### #.#####",
    "#.........#.........#",
    "#.###.###.#.###.###.#",
    "#o..#...........#..o#",
    "###.#.#.#####.#.#.###",
    "#.....#...#...#.....#",
    "#.#######.#.#######.#",
    "#...................#",
    "#.###.###.#.###.###.#",
    "#o.................o#",
    "#####################",
]

ROWS = len(RAW_MAZE)
COLS = max(len(row) for row in RAW_MAZE)
MAZE = [row.ljust(COLS) for row in RAW_MAZE]

WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 72


# -----------------------------
# Utility
# -----------------------------

def asset_path(filename):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "assets", filename)


def tile_center(col, row):
    return pygame.Vector2(col * TILE + TILE / 2, row * TILE + TILE / 2)


def grid_pos(pixel_pos):
    return int(pixel_pos.x // TILE), int(pixel_pos.y // TILE)


def is_wall(col, row):
    if row < 0 or row >= ROWS or col < 0 or col >= COLS:
        return True
    return MAZE[row][col] == "#"


def is_path(col, row):
    return not is_wall(col, row)


def valid_neighbors(col, row):
    result = []
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nc, nr = col + dx, row + dy
        if is_path(nc, nr):
            result.append((nc, nr))
    return result


def direction_to_neighbor(start, target):
    sx, sy = start
    tx, ty = target
    return pygame.Vector2(tx - sx, ty - sy)


def opposite(a, b):
    return a.x == -b.x and a.y == -b.y


def draw_bone_treat(screen, center, scale=1.0):
    """Draw a small purple bone treat without changing game behavior."""
    cx, cy = center
    fill = POWER_COIN_COLOR
    outline = COIN_COLOR
    # soft glow
    glow = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(glow, (210, 150, 255, 45), (16, 16), 15)
    screen.blit(glow, (int(cx - 16), int(cy - 16)))

    w = int(22 * scale)
    h = int(9 * scale)
    knob = int(5 * scale)
    rect = pygame.Rect(0, 0, w, h)
    rect.center = (int(cx), int(cy))

    pygame.draw.rect(screen, fill, rect, border_radius=4)
    for px, py in [
        (rect.left + 3, rect.centery - 4),
        (rect.left + 3, rect.centery + 4),
        (rect.right - 3, rect.centery - 4),
        (rect.right - 3, rect.centery + 4),
    ]:
        pygame.draw.circle(screen, fill, (px, py), knob)

    pygame.draw.rect(screen, outline, rect, 1, border_radius=4)
    for px, py in [
        (rect.left + 3, rect.centery - 4),
        (rect.left + 3, rect.centery + 4),
        (rect.right - 3, rect.centery - 4),
        (rect.right - 3, rect.centery + 4),
    ]:
        pygame.draw.circle(screen, outline, (px, py), knob, 1)


# -----------------------------
# Maze and collectibles
# -----------------------------

class Maze:
    def __init__(self):
        self.coins = set()
        self.power_coins = set()
        self.player_start = (1, 1)
        self.smart_bot_start = (9, 10)
        self.random_bot_start = (10, 10)

        for r, line in enumerate(MAZE):
            for c, char in enumerate(line):
                if char == ".":
                    self.coins.add((c, r))
                elif char == "o":
                    self.power_coins.add((c, r))
                elif char == "P":
                    self.player_start = (c, r)
                elif char == "S":
                    self.smart_bot_start = (c, r)
                elif char == "R":
                    self.random_bot_start = (c, r)

    def draw(self, screen):
        screen.fill(PATH_COLOR)

        for r, line in enumerate(MAZE):
            for c, char in enumerate(line):
                x, y = c * TILE, r * TILE
                if char == "#":
                    rect = pygame.Rect(x, y, TILE, TILE)
                    pygame.draw.rect(screen, WALL_COLOR, rect)
                    pygame.draw.rect(screen, WALL_EDGE, rect, 1)

        for c, r in self.coins:
            pygame.draw.circle(
                screen, COIN_COLOR,
                (c * TILE + TILE // 2, r * TILE + TILE // 2), 4
            )

        for c, r in self.power_coins:
            center = (c * TILE + TILE // 2, r * TILE + TILE // 2)
            draw_bone_treat(screen, center, 1.0)

    def remaining_collectibles(self):
        return len(self.coins) + len(self.power_coins)


# -----------------------------
# Characters
# -----------------------------

class Actor:
    """Tile-centered actor with smooth tile-to-tile movement.

    This avoids the old bug where the actor snapped back to the tile center every
    frame and appeared frozen while only the sprite rotated.
    """

    def __init__(self, col, row, speed):
        self.start_tile = (col, row)
        self.tile = (col, row)
        self.pos = tile_center(col, row)
        self.dir = pygame.Vector2(0, 0)
        self.next_dir = pygame.Vector2(0, 0)
        self.target_tile = None
        self.speed = speed
        self.radius = TILE // 2 - 2

    def reset(self):
        col, row = self.start_tile
        self.tile = (col, row)
        self.pos = tile_center(col, row)
        self.dir = pygame.Vector2(0, 0)
        self.next_dir = pygame.Vector2(0, 0)
        self.target_tile = None

    def can_move_from_tile(self, direction):
        if direction.length_squared() == 0:
            return False
        col, row = self.tile
        nc = col + int(direction.x)
        nr = row + int(direction.y)
        return is_path(nc, nr)

    def begin_step_if_possible(self):
        # Turn first if the requested direction is legal at this tile.
        if self.next_dir.length_squared() and self.can_move_from_tile(self.next_dir):
            self.dir = pygame.Vector2(self.next_dir)

        # Continue straight if possible; otherwise stop at the center.
        if self.dir.length_squared() and self.can_move_from_tile(self.dir):
            col, row = self.tile
            self.target_tile = (col + int(self.dir.x), row + int(self.dir.y))
        else:
            self.dir = pygame.Vector2(0, 0)
            self.target_tile = None

    def move_step(self, dt):
        if self.target_tile is None:
            self.begin_step_if_possible()
            if self.target_tile is None:
                return

        target_pos = tile_center(*self.target_tile)
        delta = target_pos - self.pos
        distance = delta.length()
        travel = self.speed * dt

        if distance <= travel:
            self.pos = target_pos
            self.tile = self.target_tile
            self.target_tile = None
        elif distance > 0:
            self.pos += delta.normalize() * travel


class Player(Actor):
    def __init__(self, col, row):
        super().__init__(col, row, PLAYER_SPEED)
        self.sprite_base = self.load_sprite()
        self.facing = pygame.Vector2(1, 0)

    def load_sprite(self):
        try:
            img = pygame.image.load(asset_path("briah_sprite.png")).convert_alpha()
            return pygame.transform.smoothscale(img, (TILE + 14, TILE + 14))
        except Exception:
            return None

    def set_direction(self, dx, dy):
        self.next_dir = pygame.Vector2(dx, dy)
        if dx or dy:
            self.facing = pygame.Vector2(dx, dy)

    def draw(self, screen, powered):
        x, y = int(self.pos.x), int(self.pos.y)

        if self.sprite_base:
            img = self.sprite_base

            # Original sprite faces right. Keep Briah's head natural when moving up/down.
            if self.facing.x < 0:
                img = pygame.transform.flip(img, True, False)

            rect = img.get_rect(center=(x, y))
            screen.blit(img, rect)

            if powered:
                pygame.draw.circle(screen, POWER_COIN_COLOR, (x, y), TILE, 2)
        else:
            pygame.draw.circle(screen, (10, 10, 12), (x, y), self.radius + 2)
            pygame.draw.polygon(screen, (8, 8, 9), [(x - 10, y - 10), (x - 5, y - 24), (x, y - 10)])
            pygame.draw.polygon(screen, (8, 8, 9), [(x + 10, y - 10), (x + 5, y - 24), (x, y - 10)])
            pygame.draw.circle(screen, (230, 230, 240), (x - 5, y - 3), 2)
            pygame.draw.circle(screen, (230, 230, 240), (x + 5, y - 3), 2)
            pygame.draw.circle(screen, COIN_COLOR, (x, y + 10), 5)


class Bot(Actor):
    def __init__(self, col, row, kind):
        super().__init__(col, row, BOT_SPEED)
        self.kind = kind
        self.color = BOT_SMART_COLOR if kind == "smart" else BOT_RANDOM_COLOR

    def choose_direction(self, player_tile, powered):
        # Only choose a new direction when centered on a tile.
        if self.target_tile is not None:
            return

        col, row = self.tile
        options = valid_neighbors(col, row)
        if not options:
            self.next_dir = pygame.Vector2(0, 0)
            return

        # Prefer not to reverse direction unless that is the only legal move.
        non_reverse = []
        for target in options:
            candidate = direction_to_neighbor((col, row), target)
            if not opposite(candidate, self.dir):
                non_reverse.append(target)
        if non_reverse:
            options = non_reverse

        if self.kind == "smart":
            if powered:
                # Flee during power mode.
                target = max(
                    options,
                    key=lambda t: abs(t[0] - player_tile[0]) + abs(t[1] - player_tile[1])
                )
            else:
                # Simple chase: choose the neighbor closest to Briah.
                target = min(
                    options,
                    key=lambda t: abs(t[0] - player_tile[0]) + abs(t[1] - player_tile[1])
                )
        else:
            target = random.choice(options)

        self.next_dir = direction_to_neighbor((col, row), target)

    def draw(self, screen, powered):
        x, y = int(self.pos.x), int(self.pos.y)
        color = BOT_DISABLED_COLOR if powered else self.color

        body = pygame.Rect(0, 0, TILE - 4, TILE - 2)
        body.center = (x, y)
        pygame.draw.rect(screen, color, body, border_radius=6)
        pygame.draw.circle(screen, color, (x, y - 8), 9)

        pygame.draw.circle(screen, (245, 245, 255), (x - 5, y - 5), 3)
        pygame.draw.circle(screen, (245, 245, 255), (x + 5, y - 5), 3)
        pygame.draw.circle(screen, (20, 20, 30), (x - 5, y - 5), 1)
        pygame.draw.circle(screen, (20, 20, 30), (x + 5, y - 5), 1)
        pygame.draw.rect(screen, (20, 20, 30), (x - 7, y + 5, 14, 2))


# -----------------------------
# Game
# -----------------------------

class Game:
    TITLE = "title"
    PLAYING = "playing"
    PAUSED = "paused"
    WIN = "win"
    LOSE = "lose"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Briah Pac-Man")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.large_font = pygame.font.SysFont("arial", 44, bold=True)

        # Simple sounds. If audio is unavailable, the game still runs silently.
        self.sounds = {
            "coin": None,
            "power": None,
            "bot": None,
            "life": None,
            "win": None,
        }
        try:
            pygame.mixer.init()
            for name in self.sounds:
                path = asset_path(f"{name}.wav")
                if os.path.exists(path):
                    self.sounds[name] = pygame.mixer.Sound(path)
        except pygame.error:
            pass

        self.state = self.TITLE
        self.restart(full=True)

    def restart(self, full=False):
        self.maze = Maze()
        self.player = Player(*self.maze.player_start)
        self.bots = [
            Bot(*self.maze.smart_bot_start, kind="smart"),
            Bot(*self.maze.random_bot_start, kind="random"),
        ]
        self.score = 0
        self.lives = 3
        self.power_timer = 0.0
        if not full:
            self.state = self.PLAYING

    def reset_positions_after_hit(self):
        self.player.reset()
        for bot in self.bots:
            bot.reset()

    def play_sound(self, name):
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    def set_player_direction_from_key(self, key):
        if key in (pygame.K_LEFT, pygame.K_a):
            self.player.set_direction(-1, 0)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.player.set_direction(1, 0)
        elif key in (pygame.K_UP, pygame.K_w):
            self.player.set_direction(0, -1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.player.set_direction(0, 1)

    def handle_events(self):
        movement_keys = (
            pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d,
            pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.state == self.TITLE and event.key in (pygame.K_RETURN, pygame.K_SPACE, *movement_keys):
                    self.restart()
                    self.state = self.PLAYING
                    self.set_player_direction_from_key(event.key)

                elif self.state in (self.WIN, self.LOSE) and event.key == pygame.K_r:
                    self.restart()
                    self.state = self.PLAYING

                elif event.key == pygame.K_p:
                    if self.state == self.PLAYING:
                        self.state = self.PAUSED
                    elif self.state == self.PAUSED:
                        self.state = self.PLAYING

                elif self.state == self.PLAYING:
                    self.set_player_direction_from_key(event.key)

    def poll_held_movement_keys(self):
        if self.state != self.PLAYING:
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.set_direction(-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.set_direction(1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.set_direction(0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.set_direction(0, 1)

    def update(self, dt):
        if self.state != self.PLAYING:
            return

        self.poll_held_movement_keys()

        if self.power_timer > 0:
            self.power_timer = max(0.0, self.power_timer - dt)

        self.player.move_step(dt)
        player_tile = self.player.tile

        if player_tile in self.maze.coins:
            self.maze.coins.remove(player_tile)
            self.score += 10
            self.play_sound("coin")

        if player_tile in self.maze.power_coins:
            self.maze.power_coins.remove(player_tile)
            self.score += 50
            self.power_timer = POWER_SECONDS
            self.play_sound("power")

        powered = self.power_timer > 0
        for bot in self.bots:
            bot.choose_direction(player_tile, powered)
            bot.move_step(dt)

            if self.player.pos.distance_to(bot.pos) < TILE * 0.72:
                if powered:
                    self.score += 200
                    bot.reset()
                    self.play_sound("bot")
                else:
                    self.lives -= 1
                    self.play_sound("life")
                    if self.lives <= 0:
                        self.state = self.LOSE
                    else:
                        self.reset_positions_after_hit()
                    break

        if self.maze.remaining_collectibles() == 0:
            self.state = self.WIN
            self.play_sound("win")

    def draw_hud(self):
        hud_y = ROWS * TILE
        pygame.draw.rect(self.screen, (15, 15, 35), (0, hud_y, WIDTH, 72))

        score = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        lives = self.font.render(f"Lives: {self.lives}", True, TEXT_COLOR)
        self.screen.blit(score, (14, hud_y + 12))
        self.screen.blit(lives, (WIDTH - 120, hud_y + 12))

        if self.power_timer > 0:
            power = self.small_font.render(f"Power mode: {self.power_timer:0.1f}s", True, POWER_COIN_COLOR)
            self.screen.blit(power, (14, hud_y + 44))

        help_text = self.small_font.render("Move: Arrows/WASD   Pause: P   Restart after end: R", True, (190, 190, 220))
        self.screen.blit(help_text, (WIDTH // 2 - help_text.get_width() // 2, hud_y + 45))

    def draw_overlay_message(self, title, subtitle):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        title_img = self.large_font.render(title, True, TEXT_COLOR)
        sub_img = self.font.render(subtitle, True, POWER_COIN_COLOR)

        self.screen.blit(title_img, (WIDTH // 2 - title_img.get_width() // 2, HEIGHT // 2 - 70))
        self.screen.blit(sub_img, (WIDTH // 2 - sub_img.get_width() // 2, HEIGHT // 2 - 10))

    def draw_title(self):
        self.screen.fill(PATH_COLOR)
        title = self.large_font.render("BRIAH PAC-MAN", True, TEXT_COLOR)
        line1 = self.font.render("Collect purple coins. Dodge the bots.", True, POWER_COIN_COLOR)
        line2 = self.small_font.render("Enter/Space or any movement key to start - Arrows/WASD move - P pauses", True, (205, 205, 230))

        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(line1, (WIDTH // 2 - line1.get_width() // 2, HEIGHT // 2 - 36))
        self.screen.blit(line2, (WIDTH // 2 - line2.get_width() // 2, HEIGHT // 2 + 10))

        pygame.draw.circle(self.screen, COIN_COLOR, (WIDTH // 2 - 70, HEIGHT // 2 + 70), 7)
        draw_bone_treat(self.screen, (WIDTH // 2 - 35, HEIGHT // 2 + 70), 1.1)
        pygame.draw.rect(self.screen, BOT_SMART_COLOR, (WIDTH // 2 + 18, HEIGHT // 2 + 58, 24, 24), border_radius=6)
        pygame.draw.rect(self.screen, BOT_RANDOM_COLOR, (WIDTH // 2 + 58, HEIGHT // 2 + 58, 24, 24), border_radius=6)

    def draw(self):
        if self.state == self.TITLE:
            self.draw_title()
            pygame.display.flip()
            return

        self.maze.draw(self.screen)
        powered = self.power_timer > 0

        for bot in self.bots:
            bot.draw(self.screen, powered)

        self.player.draw(self.screen, powered)
        self.draw_hud()

        if self.state == self.PAUSED:
            self.draw_overlay_message("PAUSED", "Press P to continue")
        elif self.state == self.WIN:
            self.draw_overlay_message("YOU WIN!", "Press R to restart")
        elif self.state == self.LOSE:
            self.draw_overlay_message("GAME OVER", "Press R to restart")

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
