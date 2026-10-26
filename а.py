import random
import sys
import os
import pygame

pygame.init()
pygame.mixer.init()
pygame.key.set_repeat(200, 80)

TILE_SIZE = 40
GRID_WIDTH, GRID_HEIGHT = 19, 15
WIDTH = GRID_WIDTH * TILE_SIZE
HEIGHT = GRID_HEIGHT * TILE_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Backrooms Labyrinth")
screen.fill((15, 15, 25))
pygame.display.flip()

clock = pygame.time.Clock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Завантаження та запуск фонової музики з автоповтором при завершенні (e.mp3)
music_path = os.path.join(BASE_DIR, "e.mp3")
has_music = False
try:
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.6)
    pygame.mixer.music.play(0)  # грає один раз, далі відслідковується в циклі
    has_music = True
except (pygame.error, FileNotFoundError):
    print("Музичний файл e.mp3 не знайдено.")

# Завантаження фону
bg_path = os.path.join(BASE_DIR, "фон до закулісся.jpg")
try:
    bg_img = pygame.image.load(bg_path).convert()
    bg_image = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
except (pygame.error, FileNotFoundError):
    bg_image = pygame.Surface((WIDTH, HEIGHT))
    bg_image.fill((40, 35, 30))

# Завантаження текстури стін
wall_path = os.path.join(BASE_DIR, "gc.jpg")
try:
    wall_img = pygame.image.load(wall_path).convert()
    wall_texture = pygame.transform.scale(wall_img, (TILE_SIZE, TILE_SIZE))
except (pygame.error, FileNotFoundError):
    wall_texture = pygame.Surface((TILE_SIZE, TILE_SIZE))
    wall_texture.fill((120, 110, 95))

# Безпечне завантаження кадру гравця (ідл)
player_idle_frame = None
idle_path = os.path.join(BASE_DIR, "walk_1.png")
try:
    img = pygame.image.load(idle_path).convert_alpha()
    player_idle_frame = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
except (pygame.error, FileNotFoundError):
    player_idle_frame = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(player_idle_frame, (0, 150, 255), (TILE_SIZE//2, TILE_SIZE//2), TILE_SIZE//3)

# Безпечне завантаження кадру стрибка
player_jump_frame = None
jump_path = os.path.join(BASE_DIR, "jump_1.png")
try:
    img = pygame.image.load(jump_path).convert_alpha()
    player_jump_frame = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
except (pygame.error, FileNotFoundError):
    player_jump_frame = player_idle_frame

# Завантаження картинки програшу розміром з одну клітинку
game_over_frame = None
game_over_path = os.path.join(BASE_DIR, "game_over.png")
try:
    img = pygame.image.load(game_over_path).convert_alpha()
    game_over_frame = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
except (pygame.error, FileNotFoundError):
    game_over_frame = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(game_over_frame, (255, 0, 0), (TILE_SIZE//2, TILE_SIZE//2), TILE_SIZE//3)

is_jumping = False
jump_offset_y = 0.0  
jump_velocity = 0.0  
GRAVITY = 0.6
JUMP_STRENGTH = -8.5

maze = [[1 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
player_x, player_y = 1, 1
level_start_x, level_start_y = 1, 1
key_x, key_y = 1, 1
portal_x, portal_y = 1, 1
trap_base_x, trap_base_y = 1, 1

trap_offset_y = 0.0
trap_direction = 1
trap_speed = 0.04
has_key = False
player_dir_x = 1

LEVEL_TIME_LIMIT = 15.0
level_start_ticks = 0

def generate_grand_maze(w, h):
    res_maze = [[1 for _ in range(w)] for _ in range(h)]
    visited = set()

    def carve_passages_from(cx, cy):
        visited.add((cx, cy))
        res_maze[cy][cx] = 0
        directions = [(0, -2), (2, 0), (0, 2), (-2, 0)]
        random.shuffle(directions)
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 < nx < w - 1 and 0 < ny < h - 1 and (nx, ny) not in visited:
                res_maze[cy + dy // 2][cx + dx // 2] = 0
                carve_passages_from(nx, ny)

    carve_passages_from(1, 1)
    return res_maze

def generate_level_data():
    global maze, player_x, player_y, level_start_x, level_start_y
    global key_x, key_y, portal_x, portal_y, trap_base_x, trap_base_y
    global has_key, player_dir_x, is_jumping, jump_offset_y, level_start_ticks

    maze = generate_grand_maze(GRID_WIDTH, GRID_HEIGHT)

    player_x, player_y = 1, 1
    level_start_x, level_start_y = 1, 1
    key_x, key_y = 1, GRID_HEIGHT - 2
    portal_x, portal_y = GRID_WIDTH - 2, GRID_HEIGHT - 2
    is_jumping = False
    jump_offset_y = 0.0

    maze[key_y][key_x] = 0
    maze[portal_y][portal_x] = 0

    trap_base_x, trap_base_y = GRID_WIDTH - 3, GRID_HEIGHT - 2
    maze[trap_base_y][trap_base_x] = 0
    
    if trap_base_y > 1:
        maze[trap_base_y - 1][trap_base_x] = 0
    if trap_base_y < GRID_HEIGHT - 2:
        maze[trap_base_y + 1][trap_base_x] = 0

    maze[trap_base_y - 1][portal_x] = 0
    maze[trap_base_y - 1][trap_base_x - 1] = 0

    has_key = False
    level_start_ticks = pygame.time.get_ticks()
    pygame.display.set_caption("Backrooms | Знайди ключ!")

def restart_same_level():
    global player_x, player_y, has_key, trap_offset_y, trap_direction, player_dir_x, is_jumping, jump_offset_y, level_start_ticks
    player_x, player_y = level_start_x, level_start_y
    trap_offset_y = 0.0
    trap_direction = 1
    has_key = False
    is_jumping = False
    jump_offset_y = 0.0
    level_start_ticks = pygame.time.get_ticks()

def trigger_time_out_animation():
    screen.blit(bg_image, (0, 0))
    for row in range(GRID_HEIGHT):
        for col in range(GRID_WIDTH):
            if maze[row][col] == 1:
                draw_wall(screen, col * TILE_SIZE, row * TILE_SIZE)

    if not has_key:
        draw_key(screen, key_x * TILE_SIZE, key_y * TILE_SIZE)

    draw_portal(screen, portal_x * TILE_SIZE, portal_y * TILE_SIZE, has_key)
    trap_display_x = trap_base_x * TILE_SIZE
    trap_display_y = int((trap_base_y + trap_offset_y) * TILE_SIZE)
    draw_trap(screen, trap_display_x, trap_display_y)

    screen.blit(game_over_frame, (player_x * TILE_SIZE, player_y * TILE_SIZE + int(jump_offset_y)))

    timer_surf = font.render("Час: 0с", True, (255, 255, 0))
    screen.blit(timer_surf, (15, 15))

    pygame.display.flip()
    pygame.time.delay(1000)
    restart_same_level()

def draw_wall(surface, x, y):
    surface.blit(wall_texture, (x, y))

def draw_player_sprite(surface, x, y):
    if is_jumping:
        current_frame_img = player_jump_frame
    else:
        current_frame_img = player_idle_frame

    if player_dir_x == -1:
        current_frame_img = pygame.transform.flip(current_frame_img, True, False)
        
    surface.blit(current_frame_img, (x, y + int(jump_offset_y)))

def draw_key(surface, x, y):
    cx, cy = x + TILE_SIZE // 2, y + TILE_SIZE // 2
    pygame.draw.circle(surface, (255, 215, 0), (cx - 4, cy), 6, 2)
    pygame.draw.rect(surface, (255, 215, 0), (cx, cy - 2, 10, 4))

def draw_portal(surface, x, y, active):
    cx, cy = x + TILE_SIZE // 2, y + TILE_SIZE // 2
    if active:
        pygame.draw.circle(surface, (255, 0, 255), (cx, cy), 14, 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 6)
    else:
        pygame.draw.circle(surface, (80, 80, 80), (cx, cy), 12, 2)

def draw_trap(surface, x, y):
    cx, cy = x + TILE_SIZE // 2, y + TILE_SIZE // 2
    pygame.draw.circle(surface, (255, 69, 0), (cx, cy), 11)
    pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 3)

generate_level_data()

font = pygame.font.SysFont(None, 36)

running = True
while running:
    clock.tick(60)

    if has_music and not pygame.mixer.music.get_busy():
        pygame.mixer.music.play(0)

    elapsed_seconds = (pygame.time.get_ticks() - level_start_ticks) / 1000.0
    time_left = max(0.0, LEVEL_TIME_LIMIT - elapsed_seconds)

    if time_left <= 0:
        trigger_time_out_animation()
        continue

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            new_x, new_y = player_x, player_y
            
            if event.key == pygame.K_UP:      new_y -= 1
            elif event.key == pygame.K_DOWN:  new_y += 1
            elif event.key == pygame.K_LEFT:
                new_x -= 1
                player_dir_x = -1  
            elif event.key == pygame.K_RIGHT:
                new_x += 1
                player_dir_x = 1   
            elif event.key == pygame.K_SPACE:
                if not is_jumping:
                    is_jumping = True
                    jump_velocity = JUMP_STRENGTH

            if 0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT and maze[new_y][new_x] == 0:
                player_x, player_y = new_x, new_y

    if is_jumping:
        jump_offset_y += jump_velocity
        jump_velocity += GRAVITY
        if jump_offset_y >= 0:
            jump_offset_y = 0.0
            is_jumping = False

    trap_offset_y += trap_speed * trap_direction
    if trap_offset_y > 0.8:
        trap_offset_y = 0.8
        trap_direction = -1
    elif trap_offset_y < -0.8:
        trap_offset_y = -0.8
        trap_direction = 1

    player_rect = pygame.Rect(
        player_x * TILE_SIZE, 
        player_y * TILE_SIZE + int(jump_offset_y), 
        TILE_SIZE, 
        TILE_SIZE
    )
    trap_display_x = trap_base_x * TILE_SIZE
    trap_display_y = int((trap_base_y + trap_offset_y) * TILE_SIZE)
    trap_rect = pygame.Rect(
        trap_display_x, 
        trap_display_y, 
        TILE_SIZE, 
        TILE_SIZE
    )

    if player_rect.colliderect(trap_rect):
        restart_same_level()
        continue

    if not has_key and player_x == key_x and player_y == key_y:
        has_key = True
        pygame.display.set_caption("Backrooms | Ключ взято! Мерщій у портал!")

    if player_x == portal_x and player_y == portal_y and has_key:
        generate_level_data()

    screen.blit(bg_image, (0, 0))
    
    for row in range(GRID_HEIGHT):
        for col in range(GRID_WIDTH):
            if maze[row][col] == 1:
                draw_wall(screen, col * TILE_SIZE, row * TILE_SIZE)

    if not has_key:
        draw_key(screen, key_x * TILE_SIZE, key_y * TILE_SIZE)

    draw_portal(screen, portal_x * TILE_SIZE, portal_y * TILE_SIZE, has_key)

    draw_trap(screen, trap_display_x, trap_display_y)
    draw_player_sprite(screen, player_x * TILE_SIZE, player_y * TILE_SIZE)

    timer_surf = font.render(f"Час: {int(time_left)}с", True, (255, 255, 0))
    screen.blit(timer_surf, (15, 15))

    pygame.display.flip()

pygame.quit()
sys.exit()