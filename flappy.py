import pygame, sys, random, json, os, math, array

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# ---------------------------------------------------------------------------
# Tim file tai nguyen (khong bao loi neu thieu, dung phuong an du phong)
# ---------------------------------------------------------------------------


def _search(name, root, max_depth=4):
    root_depth = root.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - root_depth >= max_depth:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != 'node_modules']
        if name in filenames:
            return os.path.join(dirpath, name)
        # so khop khong phan biet hoa thuong
        for fn in filenames:
            if fn.lower() == name.lower():
                return os.path.join(dirpath, fn)
    return None


def find_res(name, *folders):
    """Tra ve duong dan file, hoac None neu khong tim thay."""
    known = list(folders) + [os.path.join('font and sound', f) for f in folders] + ['', 'font and sound']
    for folder in known:
        path = os.path.join(BASE_DIR, folder, name)
        if os.path.exists(path):
            return path
    for root in (BASE_DIR, os.path.dirname(BASE_DIR)):
        if '.venv' in root:
            continue
        found = _search(name, root)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
RECORD_FILE = os.path.join(BASE_DIR, 'records.json')
MAX_NAME = 10


def _clean_list(lst):
    out = []
    for x in lst:
        try:
            if isinstance(x, dict):
                out.append({'name': str(x.get('name', '???'))[:MAX_NAME], 'score': int(x.get('score', 0))})
            else:
                out.append({'name': '???', 'score': int(x)})
        except (ValueError, TypeError):
            continue
    return sorted(out, key=lambda e: e['score'], reverse=True)[:5]


def load_records():
    data = {'single': [], 'names': ['PLAYER 1', 'PLAYER 2']}
    try:
        with open(RECORD_FILE, 'r') as f:
            loaded = json.load(f)
        data['single'] = _clean_list(loaded.get('single', []))
        nm = loaded.get('names', [])
        for i in range(2):
            if i < len(nm) and str(nm[i]).strip():
                data['names'][i] = str(nm[i])[:MAX_NAME]
    except (OSError, ValueError, AttributeError):
        pass
    return data


def save_records():
    try:
        with open(RECORD_FILE, 'w') as f:
            json.dump(records, f)
    except OSError:
        pass


def add_record(key, name, value):
    value = int(value)
    if value <= 0:
        return
    records[key].append({'name': name, 'score': value})
    records[key] = sorted(records[key], key=lambda e: e['score'], reverse=True)[:5]
    save_records()


# ---------------------------------------------------------------------------
# Game helpers
# ---------------------------------------------------------------------------
def draw_floor():
    screen.blit(floor_surface, (floor_x_pos, 480))
    screen.blit(floor_surface, (floor_x_pos + 480, 480))


def create_pipe():
    random_pipe_pos = random.choice(pipe_height)
    bottom_pipe = pipe_surface.get_rect(midtop=(520, random_pipe_pos))
    top_pipe = pipe_surface.get_rect(midbottom=(520, random_pipe_pos - 180))
    return bottom_pipe, top_pipe


def move_pipes(pipes):
    for pipe in pipes:
        pipe.centerx -= 3
    return pipes


def draw_pipes(pipes):
    for pipe in pipes:
        if pipe.bottom >= 520:
            screen.blit(pipe_surface, pipe)
        else:
            screen.blit(pipe_surface_flipped, pipe)


def remove_pipes(pipes):
    return [pipe for pipe in pipes if pipe.centerx > -50]


def hit_pipe(bird, pipes):
    return any(bird['rect'].colliderect(pipe) for pipe in pipes)


def hit_bounds(bird):
    return bird['rect'].top <= -40 or bird['rect'].bottom >= 480


def handle_collision(b):
    now = pygame.time.get_ticks()
    invincible = now < b['invincible_until']
    pipe_hit = hit_pipe(b, pipe_list)
    bounds_hit = hit_bounds(b)
    if not (pipe_hit or bounds_hit):
        return

    if bounds_hit and (invincible or b['shield']):
        if b['rect'].bottom >= 480:
            b['rect'].bottom = 470
            b['movement'] = -6.5
        else:
            b['rect'].top = -30
            b['movement'] = 0

    if invincible:
        return
    if b['shield']:
        b['shield'] = False
        b['invincible_until'] = now + 1500
        death_sound.play()
        return

    b['alive'] = False
    b['score'] = score
    death_sound.play()


def draw_text(text, font, pos, color=(255, 255, 255), shadow=True, anchor='center'):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        screen.blit(s, s.get_rect(**{anchor: (pos[0] + 2, pos[1] + 2)}))
    surf = font.render(text, True, color)
    rect = surf.get_rect(**{anchor: pos})
    screen.blit(surf, rect)
    return rect


def draw_button(rect, text, selected):
    color = (255, 200, 60) if selected else (222, 216, 149)
    border = (255, 255, 255) if selected else (84, 56, 71)
    pygame.draw.rect(screen, (84, 56, 71), rect.move(3, 4), border_radius=8)
    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 3, border_radius=8)
    draw_text(text, game_font, rect.center, (84, 56, 71) if not selected else (60, 30, 10), shadow=False)


def make_bird(x, frames, key, name):
    return {
        'frames': frames,
        'rect': frames[0].get_rect(center=(x, 280)),
        'x': x,
        'movement': 0,
        'alive': True,
        'score': 0,
        'key': key,
        'name': name,
        'shield': False,
        'invincible_until': 0,
    }


def tint_frames(frames):
    out = []
    for f in frames:
        t = f.copy()
        t.fill((255, 110, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
        out.append(t)
    return out


def start_game(new_mode):
    global state, mode, game_active, score, birds, pipe_list, score_sound_countdown, shield_list
    mode = new_mode
    pipe_list = []
    shield_list = []
    score = 0
    score_sound_countdown = 100
    game_active = True
    state = 'playing'
    if mode == 1:
        birds = [make_bird(90, bird_frames, pygame.K_SPACE, names[0])]
    else:
        birds = [make_bird(80, bird_frames, pygame.K_SPACE, names[0]),
                 make_bird(130, bird_frames_p2, pygame.K_UP, names[1])]


def go_menu():
    global state, selected
    state = 'menu'
    selected = 0


def begin_name_entry(new_mode):
    global state, pending_mode, name_step, name_buffer
    pending_mode = new_mode
    name_step = 0
    name_buffer = names[0]
    state = 'name'


def confirm_name():
    global name_step, name_buffer
    name = name_buffer.strip() or f'PLAYER {name_step + 1}'
    names[name_step] = name
    if pending_mode == 2 and name_step == 0:
        name_step = 1
        name_buffer = names[1]
    else:
        save_records()
        start_game(pending_mode)


def finish_game():
    global game_active
    game_active = False
    if mode == 1:
        add_record('single', birds[0]['name'], score)


def activate_menu(index):
    global state
    if index == 0:
        begin_name_entry(1)
    elif index == 1:
        begin_name_entry(2)
    else:
        state = 'records'


# ---------------------------------------------------------------------------
# Khoi tao pygame
# ---------------------------------------------------------------------------
pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
pygame.init()

SCREEN_W, SCREEN_H = 480, 560
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption('Flappy Bird')
clock = pygame.time.Clock()


# ---- Icon ------------------------------------------------------------------
def load_window_icon():
    for name in ('icon.png', 'bluebird-midflap.png'):
        path = find_res(name, 'assets')
        if not path:
            continue
        try:
            img = pygame.image.load(path)
        except pygame.error:
            continue
        size = 128
        w, h = img.get_size()
        k = size / max(w, h)
        img = pygame.transform.scale(img, (max(1, int(w * k)), max(1, int(h * k))))
        icon = pygame.Surface((size, size), pygame.SRCALPHA)
        icon.blit(img, img.get_rect(center=(size // 2, size // 2)))
        return icon
    return None


_icon = load_window_icon()
if _icon is not None:
    pygame.display.set_icon(_icon)


# ---- Font (co phuong an du phong) -------------------------------------------
_FONT_PATH = find_res('04B_19.ttf', 'font', 'fonts', 'assets')
if _FONT_PATH is None:
    print("[CANH BAO] Khong tim thay '04B_19.ttf' -> dung font mac dinh cua pygame.")


def load_font(size):
    if _FONT_PATH:
        try:
            return pygame.font.Font(_FONT_PATH, size)
        except (pygame.error, OSError):
            pass
    return pygame.font.Font(None, int(size * 1.3))


game_font = load_font(24)
small_font = load_font(16)
title_font = load_font(54)


# ---- Anh (co phuong an du phong) --------------------------------------------
def load_img(name, size, fallback, alpha=True):
    path = find_res(name, 'assets', 'images', 'image', 'img')
    if path:
        try:
            img = pygame.image.load(path)
            img = img.convert_alpha() if alpha else img.convert()
            return pygame.transform.scale(img, size)
        except pygame.error:
            pass
    print(f"[CANH BAO] Khong tim thay anh '{name}' -> dung hinh ve tam.")
    return fallback(size)


def fb_background(size):
    s = pygame.Surface(size)
    for y in range(size[1]):
        t = y / size[1]
        pygame.draw.line(s, (int(90 + 100 * t), int(190 + 40 * t), int(235 + 10 * t)), (0, y), (size[0], y))
    return s


def fb_floor(size):
    s = pygame.Surface(size)
    s.fill((222, 216, 149))
    pygame.draw.rect(s, (115, 191, 46), (0, 0, size[0], 14))
    pygame.draw.line(s, (84, 56, 71), (0, 14), (size[0], 14), 3)
    return s


def fb_bird(wing):
    def make(size):
        s = pygame.Surface(size, pygame.SRCALPHA)
        w, h = size
        pygame.draw.ellipse(s, (255, 210, 0), (0, 2, w - 6, h - 4))
        pygame.draw.ellipse(s, (84, 56, 71), (0, 2, w - 6, h - 4), 1)
        pygame.draw.circle(s, (255, 255, 255), (w - 13, 8), 4)
        pygame.draw.circle(s, (0, 0, 0), (w - 12, 8), 2)
        pygame.draw.polygon(s, (240, 90, 30), [(w - 8, 11), (w, 13), (w - 8, 16)])
        wy = {0: 14, 1: 11, 2: 7}[wing]
        pygame.draw.ellipse(s, (255, 240, 140), (4, wy - 3, 11, 7))
        return s
    return make


def fb_pipe(size):
    s = pygame.Surface(size)
    s.fill((115, 191, 46))
    pygame.draw.rect(s, (160, 225, 80), (6, 0, 8, size[1]))
    pygame.draw.rect(s, (84, 56, 71), (0, 0, size[0], size[1]), 3)
    pygame.draw.rect(s, (115, 191, 46), (0, 0, size[0], 24))
    pygame.draw.rect(s, (84, 56, 71), (0, 0, size[0], 24), 3)
    return s


def fb_shield(size):
    s = pygame.Surface(size, pygame.SRCALPHA)
    c = (size[0] // 2, size[1] // 2)
    pygame.draw.circle(s, (80, 170, 255, 110), c, size[0] // 2 - 1)
    pygame.draw.circle(s, (200, 235, 255, 230), c, size[0] // 2 - 1, 3)
    return s


def fb_message(size):
    s = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(s, (222, 216, 149, 235), s.get_rect(), border_radius=14)
    pygame.draw.rect(s, (84, 56, 71), s.get_rect(), 4, border_radius=14)
    t = game_font.render('GAME OVER', True, (84, 56, 71))
    s.blit(t, t.get_rect(center=(size[0] // 2, size[1] // 2)))
    return s


bg_surface = load_img('background-day.png', (SCREEN_W, SCREEN_H), fb_background, alpha=False)

floor_surface = load_img('base.png', (480, 80), fb_floor, alpha=False)
floor_x_pos = 0

BIRD_SIZE = (30, 21)
bird_frames = [
    load_img('bluebird-downflap.png', BIRD_SIZE, fb_bird(0)),
    load_img('bluebird-midflap.png', BIRD_SIZE, fb_bird(1)),
    load_img('bluebird-upflap.png', BIRD_SIZE, fb_bird(2)),
]


def load_red_frames():
    names_ = ['redbird-downflap.png', 'redbird-midflap.png', 'redbird-upflap.png']
    paths = [find_res(n, 'assets', 'images', 'image', 'img') for n in names_]
    if all(paths):
        try:
            return [pygame.transform.scale(pygame.image.load(p).convert_alpha(), BIRD_SIZE) for p in paths]
        except pygame.error:
            pass
    return tint_frames(bird_frames)


bird_frames_p2 = load_red_frames()
bird_index = 0
birds = []

BIRDFLAP = pygame.USEREVENT + 1
pygame.time.set_timer(BIRDFLAP, 200)

pipe_surface = load_img('pipe-green.png', (55, 320), fb_pipe)
pipe_surface_flipped = pygame.transform.flip(pipe_surface, False, True)
pipe_list = []
shield_list = []

_shield_path = find_res('procted.png', 'assets', 'images', 'image', 'img')
if _shield_path:
    try:
        _shield_img = pygame.image.load(_shield_path).convert_alpha()
        shield_pickup_surface = pygame.transform.smoothscale(_shield_img, (40, 40))
        shield_aura_surface = pygame.transform.smoothscale(_shield_img, (64, 64))
    except pygame.error:
        shield_pickup_surface = fb_shield((40, 40))
        shield_aura_surface = fb_shield((64, 64))
else:
    print("[CANH BAO] Khong tim thay anh 'procted.png' -> dung hinh ve tam.")
    shield_pickup_surface = fb_shield((40, 40))
    shield_aura_surface = fb_shield((64, 64))

SPAWNPIPE = pygame.USEREVENT
pygame.time.set_timer(SPAWNPIPE, 1300)
pipe_height = [200, 280, 360]

game_over_surface = load_img('message.png', (220, 220), fb_message)
game_over_rect = game_over_surface.get_rect(center=(240, 280))


# ---- Am thanh (co phuong an du phong) ---------------------------------------
class _SilentSound:
    def play(self, *a, **k):
        pass


def make_beep(freq, ms, volume=0.25):
    """Tao tieng bip tong hop khi thieu file .wav"""
    init = pygame.mixer.get_init()
    if not init:
        return _SilentSound()
    rate, fmt, channels = init
    n = int(rate * ms / 1000)
    buf = array.array('h')
    for i in range(n):
        env = 1 - i / n
        v = int(32767 * volume * env * (1 if math.sin(2 * math.pi * freq * i / rate) >= 0 else -1))
        for _ in range(channels):
            buf.append(v)
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except pygame.error:
        return _SilentSound()


def load_sound(name, freq, ms):
    if pygame.mixer.get_init():
        path = find_res(name, 'sound', 'sounds', 'audio')
        if path:
            try:
                return pygame.mixer.Sound(path)
            except pygame.error:
                pass
        print(f"[CANH BAO] Khong tim thay am thanh '{name}' -> dung tieng bip.")
        return make_beep(freq, ms)
    return _SilentSound()


flap_sound = load_sound('sfx_wing.wav', 600, 80)
death_sound = load_sound('sfx_hit.wav', 160, 220)
score_sound = load_sound('sfx_point.wav', 900, 100)
score_sound_countdown = 100

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
gravity = 0.17
game_active = False
score = 0
state = 'menu'
mode = 1
pending_mode = 1
selected = 0
name_step = 0
name_buffer = ''
records = load_records()
names = records['names']

menu_labels = ['PLAY', 'TWO PEOPLE', 'RECORD']
menu_rects = [pygame.Rect(0, 0, 240, 50) for _ in menu_labels]
for i, r in enumerate(menu_rects):
    r.center = (240, 230 + i * 70)
back_rect = pygame.Rect(0, 0, 160, 44)
back_rect.center = (240, 420)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == SPAWNPIPE and state == 'playing' and game_active:
            new_pipes = create_pipe()
            pipe_list.extend(new_pipes)
            if mode == 1 and not birds[0]['shield'] and not shield_list and random.random() < 0.35:
                gap_center_y = new_pipes[1].bottom + 90
                shield_list.append(shield_pickup_surface.get_rect(
                    center=(520, gap_center_y + random.randint(-45, 45))))

        if event.type == BIRDFLAP:
            bird_index = (bird_index + 1) % 3

        if state == 'menu':
            if event.type == pygame.MOUSEMOTION:
                for i, r in enumerate(menu_rects):
                    if r.collidepoint(event.pos):
                        selected = i
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(menu_rects):
                    if r.collidepoint(event.pos):
                        selected = i
                        activate_menu(i)
                        break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(menu_labels)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(menu_labels)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    activate_menu(selected)

        elif state == 'name':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    go_menu()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    confirm_name()
                elif event.key == pygame.K_BACKSPACE:
                    name_buffer = name_buffer[:-1]
                elif (event.unicode and len(event.unicode) == 1
                      and 32 <= ord(event.unicode) <= 126
                      and len(name_buffer) < MAX_NAME):
                    name_buffer += event.unicode

        elif state == 'records':
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    go_menu()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
                go_menu()

        elif state == 'playing':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    go_menu()
                elif game_active:
                    for b in birds:
                        if event.key == b['key'] and b['alive']:
                            b['movement'] = -6.5
                            flap_sound.play()
                elif event.key == pygame.K_SPACE:
                    start_game(mode)

    screen.blit(bg_surface, (0, 0))

    if state == 'menu':
        draw_text('FLAPPY', title_font, (240, 90), (255, 220, 60))
        draw_text('BIRD', title_font, (240, 145), (255, 220, 60))
        for i, (r, label) in enumerate(zip(menu_rects, menu_labels)):
            draw_button(r, label, i == selected)
        draw_text('P1: SPACE    P2: UP ARROW', small_font, (240, 450))

    elif state == 'name':
        if pending_mode == 1:
            prompt = 'ENTER YOUR NAME'
            prompt_color = (255, 220, 60)
        else:
            prompt = f'PLAYER {name_step + 1} NAME'
            prompt_color = (255, 220, 60) if name_step == 0 else (255, 140, 140)
        draw_text(prompt, game_font, (240, 170), prompt_color)

        box = pygame.Rect(0, 0, 300, 56)
        box.center = (240, 250)
        pygame.draw.rect(screen, (222, 216, 149), box, border_radius=8)
        pygame.draw.rect(screen, (84, 56, 71), box, 3, border_radius=8)
        cursor = '_' if (pygame.time.get_ticks() // 500) % 2 == 0 else ' '
        draw_text(name_buffer + cursor, game_font, box.center, (84, 56, 71), shadow=False)

        draw_text(f'{len(name_buffer)}/{MAX_NAME}', small_font, (240, 300))
        draw_text('ENTER: OK    ESC: BACK', small_font, (240, 450))

    elif state == 'records':
        draw_text('RECORD', title_font, (240, 70), (255, 220, 60))
        for i in range(5):
            y = 150 + i * 46
            if i < len(records['single']):
                e = records['single'][i]
                draw_text(f'{i + 1}. {e["name"]}', game_font, (120, y), anchor='midleft')
                draw_text(str(e['score']), game_font, (360, y), anchor='midright')
            else:
                draw_text(f'{i + 1}. -', game_font, (120, y), anchor='midleft')
        draw_button(back_rect, 'BACK', True)

    else:
        if game_active:
            for b in birds:
                if not b['alive']:
                    continue
                b['movement'] += gravity
                b['rect'].centery += b['movement']
                handle_collision(b)

            pipe_list = move_pipes(pipe_list)
            pipe_list = remove_pipes(pipe_list)

            for r in shield_list:
                r.centerx -= 3
            shield_list = [r for r in shield_list if r.centerx > -50]
            for b in birds:
                if b['alive'] and not b['shield']:
                    got = [r for r in shield_list if b['rect'].colliderect(r)]
                    if got:
                        b['shield'] = True
                        shield_list = [r for r in shield_list if r not in got]
                        score_sound.play()

            if any(b['alive'] for b in birds):
                score += 0.01
                score_sound_countdown -= 1
                if score_sound_countdown <= 0:
                    score_sound.play()
                    score_sound_countdown = 100
            else:
                finish_game()

        draw_pipes(pipe_list)

        for r in shield_list:
            bob = int(4 * pygame.math.Vector2(1, 0).rotate(pygame.time.get_ticks() * 0.4).x)
            screen.blit(shield_pickup_surface, r.move(0, bob))

        for b in birds:
            surf = b['frames'][bird_index]
            if b['alive']:
                blink_off = (pygame.time.get_ticks() < b['invincible_until']
                             and (pygame.time.get_ticks() // 100) % 2 == 0)
                if not blink_off:
                    rotated = pygame.transform.rotozoom(surf, -b['movement'] * 3, 1)
                    screen.blit(rotated, rotated.get_rect(center=b['rect'].center))
                if b['shield']:
                    screen.blit(shield_aura_surface, shield_aura_surface.get_rect(center=b['rect'].center))
            elif game_active:
                ghost = surf.copy()
                ghost.set_alpha(90)
                screen.blit(ghost, ghost.get_rect(center=(b['x'], 460)))

        if game_active:
            draw_text(str(int(score)), game_font, (240, 50))
            if mode == 1:
                draw_text(birds[0]['name'], small_font, (240, 20))
            else:
                draw_text(birds[0]['name'], small_font, (70, 20))
                draw_text(birds[1]['name'], small_font, (410, 20), (255, 140, 140))
        else:
            screen.blit(game_over_surface, game_over_rect)
            if mode == 1:
                high = records['single'][0]['score'] if records['single'] else 0
                draw_text(birds[0]['name'], small_font, (240, 20))
                draw_text(f'Score: {int(score)}', game_font, (240, 50))
                draw_text(f'High score: {max(high, int(score))}', game_font, (240, 440))
            else:
                b1, b2 = birds
                s1, s2 = int(b1['score']), int(b2['score'])
                draw_text(f'{b1["name"]}: {s1}    {b2["name"]}: {s2}', small_font, (240, 40))
                if s1 > s2:
                    result = f'{b1["name"]} WINS!'
                elif s2 > s1:
                    result = f'{b2["name"]} WINS!'
                else:
                    result = 'DRAW'
                draw_text(result, game_font, (240, 80), (255, 220, 60))
            draw_text('SPACE: replay    ESC: menu', small_font, (240, 505))

    floor_x_pos -= 1.5
    draw_floor()
    if floor_x_pos <= -480:
        floor_x_pos = 0

    pygame.display.update()
    clock.tick(120)