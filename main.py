from fps_counter import calculate_fps
from game_utils import *
import time as t
import pygame
import random
import sys

pygame.init()


# ------------------ Setup ------------------
disp = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
clock = pygame.time.Clock()
pygame.key.set_repeat(0, 0)

full_mask = (1 << COLS) - 1  # for full row

blits = []

# Pre-render blocks
block_surfs = {}
for color in COLORS.values():
    # Create surface with alpha for rounded corners
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    # Draw block with rounded corners and border
    pygame.draw.rect(surf, color, surf.get_rect(), border_radius=5)
    pygame.draw.rect(surf, (50, 50, 50), surf.get_rect(), 1, border_radius=5)
    # Store in cache
    block_surfs[color] = surf


# ------------------ Game Variables ------------------
def new_board():
    """Create both binary and color grids"""
    return {
        'binary': [0 for _ in range(ROWS)],
        'color': [[None for _ in range(COLS)] for _ in range(ROWS)]
    }

board = new_board()

score = 0
lines_cleared_total = 0
level = 0
fall_speed = BASE_FALL_SPEED

hold_piece = None
hold_used = False

# Bag system for new pieces
bag = []
def refill_bag(bag_amount, bag_extra=0):
    global bag
    bag = []
    for _ in range(bag_amount):
        for key in tetrominoes.keys():
            bag.append(key)
    for _ in range(bag_extra):
        bag.append(random.choice(list(tetrominoes.keys())))
    random.shuffle(bag)

# Add next pieces queue
next_pieces = []

# Add to game variables
back2back = 0
combo_count = -1

# Modify new_piece to handle next pieces queue
def find_valid_spawn_position(piece, board):
    """Find valid spawn position in center"""
    piece['x'] = COLS // 2
    return valid_move(piece, board, 0, 0, piece['rotation'])

# Verify next pieces list length in new_piece()
def new_piece(bag_amount=1, bag_extra=0):
    global bag, next_pieces, current_piece
    while len(next_pieces) < NEXT_PIECES:
        if not bag:
            refill_bag(bag_amount, bag_extra)
        next_pieces.append(bag.pop(0))

    shape_key = next_pieces.pop(0)
    piece = {
        'shape': shape_key,
        'rotation': 2,
        'x': COLS // 2,  # Initial value, will be adjusted
        'y': 0,
        'color': COLORS[shape_key]
    }

    if not find_valid_spawn_position(piece, board):
        return None

    return piece

# ------------------ Utility Functions ------------------
# Add board_offset (sidebar on left) for drawing board pieces
BOARD_OFFSET_X = SIDEBAR

def createRect(x, y, size=SIZE):
    return pygame.Rect(x * size, y * size, size, size)

fonts = {}
def getFont(size) -> pygame.font.Font:
    match size:
        case 20:
            return font_20
        case 25:
            return font_25
        case 30:
            return font_30
        case 35:
            return font_35

    if size not in fonts:
        fonts[size] = pygame.font.Font(None, size)

    fonts[size] = pygame.font.Font(None, size)
    return fonts[size]

# Improved look: draw blocks with rounded corners and a border
def drawBlock(x, y, color, size=SIZE, offset_x=0, offset_y=0):
    rect = pygame.Rect(offset_x + x * size, offset_y + y * size, size, size)
    pygame.draw.rect(disp, color, rect, border_radius=5)
    pygame.draw.rect(disp, (50, 50, 50), rect, 1, border_radius=5)

def draw_board(board):
    """Draw board using color grid"""
    # Fill board area
    board_area = pygame.Rect(BOARD_OFFSET_X, 0, WIDTH, HEIGHT)
    pygame.draw.rect(disp, GAME_BOARD_COLOR, board_area)

    # Draw placed pieces
    for y, row in enumerate(board['color']):
        for x, piece_letter in enumerate(row):
            if piece_letter:
                drawBlock(x, y, COLORS[piece_letter], offset_x=BOARD_OFFSET_X)

    # Draw grid lines
    for x in range(COLS + 1):
        start = (BOARD_OFFSET_X + x * SIZE, 0)
        end = (BOARD_OFFSET_X + x * SIZE, HEIGHT)
        pygame.draw.line(disp, GRID_COLOR, start, end, 1)
    for y in range(ROWS + 1):
        start = (BOARD_OFFSET_X, y * SIZE)
        end = (BOARD_OFFSET_X + WIDTH, y * SIZE)
        pygame.draw.line(disp, GRID_COLOR, start, end, 1)

def get_rotation_index(piece):
    """Get valid rotation index for piece type"""
    if not piece:
        return piece
    total_rotations = len(tetrominoes[piece['shape']])
    return piece['rotation'] % total_rotations

def valid_move(piece, board, offset_x, offset_y, rotation):
    """Check collision using binary grid"""
    rotation = rotation % len(tetrominoes[piece['shape']])
    shape = tetrominoes[piece['shape']][rotation]
    for dx, dy in shape:
        new_x = piece['x'] + dx + offset_x
        new_y = piece['y'] + dy + offset_y
        if new_x < 0 or new_x >= COLS or new_y >= ROWS:
            return False
        if new_y >= 0 and (board['binary'][new_y] & (1 << new_x)):
            return False
    return True

def lock_piece(piece, board):
    """Lock piece into both grids"""
    rotation = get_rotation_index(piece)
    shape = tetrominoes[piece['shape']][rotation]
    for dx, dy in shape:
        new_x = piece['x'] + dx
        new_y = piece['y'] + dy
        # Only lock if within board bounds
        if 0 <= new_y < ROWS and 0 <= new_x < COLS:
            # Set binary grid bit
            board['binary'][new_y] |= (1 << new_x)
            # Store piece letter in color grid
            board['color'][new_y][new_x] = piece['shape']

def blit(surf,x,y):
    blits.append((surf,(x,y)))

text_cache = {}
def draw_text_cached(text,x,y,size=20,color=(255,255,255),bg_color=None,alpha=None):
    if (text,size,color,bg_color) not in text_cache:
        font = getFont(size)
        surf = font.render(text, True, color, bg_color)
        text_cache[(text,size,color,bg_color)] = surf
    else:
        surf = text_cache[(text,size,color,bg_color)]

    if alpha:
        surf = surf.copy()
        surf.set_alpha(alpha)

    blit(surf,x,y)

def align_piece(piece_letter):
    align_x = 0
    align_y = 0
    if piece_letter in {'T','L','J','I'}:
        align_y = 20
    if piece_letter == 'O':
        align_x = -20
    return align_x,align_y

# Add a small particle system and message display
# Update Particle class
class Particle:
    def __init__(self, x, y, vx, vy, lifetime=PARTICLE_LIFETIME):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self, dt):
        self.lifetime -= dt
        self.x += self.vx * (dt / 1000.0)
        self.y += self.vy * (dt / 1000.0)
        # Calculate alpha based on remaining lifetime
        self.alpha = int(25 * (self.lifetime / self.max_lifetime))

def spawn_particles(x, y):
    for _ in range(PARTICLES_PER_BLOCK):
        vx = random.uniform(-100, 100)
        vy = random.uniform(-200, -50)
        particles.append(Particle(x, y, vx, vy))

particles = []
current_message = None
message_timer = 0

def update_particles(dt):
    for p in particles[:]:
        p.update(dt)
        if p.lifetime <= 0:
            particles.remove(p)

def draw_particles(offset_x=0, offset_y=0):
    for p in particles:
        size = max(8, int(16 * (p.lifetime / p.max_lifetime)))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 255, 255, p.alpha), surf.get_rect())
        blit(surf, offset_x + p.x, offset_y + p.y)

# Message fade times
MESSAGE_FADE_IN_DURATION = 150
MESSAGE_HOLD_DURATION = 700
MESSAGE_FADE_OUT_DURATION = 200
MESSAGE_TOTAL_DURATION = MESSAGE_FADE_IN_DURATION + MESSAGE_HOLD_DURATION + MESSAGE_FADE_OUT_DURATION

def draw_message(dt):
    global current_message, message_timer
    if current_message is None:
        return

    cleared, spin, combo, b2b = current_message

    message_timer -= dt
    if message_timer < 0:
        current_message = None
        return

    # Calculate alpha based on current phase
    if message_timer > MESSAGE_TOTAL_DURATION - MESSAGE_FADE_IN_DURATION:
        # Fade in phase
        progress = (MESSAGE_TOTAL_DURATION - message_timer) / MESSAGE_FADE_IN_DURATION
        alpha = int(255 * progress)
    elif message_timer < MESSAGE_FADE_OUT_DURATION:
        # Fade out phase
        progress = message_timer / MESSAGE_FADE_OUT_DURATION
        alpha = int(255 * progress)
    else:
        # Fully visible phase
        alpha = 255

    alpha = max(0, min(255, alpha))
    posx, posy = 20, 95

    # T-spin
    if spin:
        draw_text_cached(
            f'{spin}-spin',
            posx,
            posy,
            25,
            COLORS[spin],
            (0,0,0),
            alpha
        )

    # Double
    if cleared:
        draw_text_cached(
            LINE_CLEAR_NAMES[cleared],
            posx,
            posy+20,
            30,
            (255,255,255),
            (0,0,0),
            alpha
        )

    # B2B x2
    if b2b:
        draw_text_cached(
            f'B2B x{b2b}',
            posx,
            posy+40,
            20,
            (255,255,255),
            (0,0,0),
            alpha
        )

    # 5 Combo
    if combo:
        draw_text_cached(
            f'{combo} Combo',
            posx,
            posy+55,
            25,
            (255,255,255),
            (0,0,0),
            alpha
        )

def set_message(cleared, spin=None, combo=None, b2b=None):
    global current_message, message_timer
    current_message = cleared, spin, combo, b2b
    message_timer = MESSAGE_TOTAL_DURATION

def clear_lines(board):
    global score, lines_cleared_total, level, fall_speed, combo_count, combo_bonus, back2back
    cleared = 0
    new_binary = []
    new_color = []
    was_spin = False

    # Check if last move was a spin
    if hasattr(clear_lines, 'last_move_was_spin'):
        was_spin = clear_lines.last_move_was_spin
    clear_lines.last_move_was_spin = False

    # Process each row
    for y in range(ROWS):
        if board['binary'][y] == full_mask:
            cleared += 1
            # Spawn particles for cleared line
            for x in range(COLS):
                if board['color'][y][x]:
                    spawn_particles(x * SIZE, y * SIZE)
        else:
            new_binary.append(board['binary'][y])
            new_color.append(board['color'][y][:])  # Make copy of row

    # Fill empty rows at top
    while len(new_binary) < ROWS:
        new_binary.insert(0, 0)
        new_color.insert(0, [None for _ in range(COLS)])

    if cleared > 0:
        # Update combo
        combo_count += 1
        combo_bonus = combo_count*50

        # Set back to back
        if was_spin or cleared >= 4:
            back2back += 1
        else:
            back2back = 0


        set_message(
            cleared,
            spin=current_piece['shape'] if was_spin else None,
            combo=combo_count,
            b2b=back2back
        )

        # Calculate score with multipliers
        base_score = cleared * SCORE_PER_LINE
        score += int(base_score + combo_bonus * (1.5 if back2back > 1 else 1.0))

        # Update level
        lines_cleared_total += cleared
        level = lines_cleared_total // 10
        fall_speed = max(MIN_FALL_SPEED, BASE_FALL_SPEED - level * FALL_SPEED_DECREMENT)

    else:
        # Combo initializes to -1 according to tetris spec
        combo_count = -1

    # Update board with new state
    board['binary'] = new_binary
    board['color'] = new_color
    return board

def draw_piece(piece):
    if not piece:
        return
    rotation = get_rotation_index(piece)
    shape = tetrominoes[piece['shape']][rotation]
    for dx, dy in shape:
        x = piece['x'] + dx
        y = piece['y'] + dy
        if y >= 0:
            drawBlock(x, y, piece['color'], offset_x=BOARD_OFFSET_X)

def draw_ghost(piece):
    if not piece:
        return
    ghost = piece.copy()
    while valid_move(ghost, board, 0, 1, ghost['rotation']):
        ghost['y'] += 1
    ghost_color = tuple(int(c * 0.3) for c in piece['color'])
    rotation = get_rotation_index(ghost)
    shape = tetrominoes[ghost['shape']][rotation]
    for dx, dy in shape:
        x = ghost['x'] + dx
        y = ghost['y'] + dy
        if y >= 0:
            drawBlock(x, y, ghost_color, offset_x=BOARD_OFFSET_X)

# Draw hold piece in left sidebar
def draw_hold_piece():
    hold_area = pygame.Rect(10, 10, SIDEBAR - 20, 75)
    pygame.draw.rect(disp, SIDEBAR_COLOR, hold_area)

    # Draw text
    hold_label = font_25.render('HOLD', True, (255, 255, 255))
    blit(hold_label, hold_area.x + 10, hold_area.y + 30)

    if hold_piece:
        # Get valid rotation index
        rotation = hold_piece['rotation'] % len(tetrominoes[hold_piece['shape']])
        shape = tetrominoes[hold_piece['shape']][rotation]

        align_x,align_y = align_piece(hold_piece['shape'])

        for dx, dy in shape:
            block_x = dx * 20 + 100 + align_x
            block_y = dy * 20 + 30 + align_y
            pygame.draw.rect(
                disp,
                COLORS[hold_piece['shape']],
                (block_x, block_y, 20, 20),
                border_radius=4
            )
            pygame.draw.rect(
                disp,
                (50, 50, 50),
                (block_x, block_y, 20, 20),
                1,
                border_radius=4
            )


# Display score and level in left sidebar below hold
font_20 = pygame.font.Font(None, 20)
font_25 = pygame.font.Font(None, 25)
font_30 = pygame.font.Font(None, 30)
font_35 = pygame.font.Font(None, 35)
def draw_score():
    draw_text_cached(
        f"Score: {score}  Level: {level}",
        10,
        170,
        25,
        (255,255,255),
        (0,0,0)
    )

# --- New: spin detection function ---
def is_spin(piece, board):
    """Check if piece rotation qualifies as a spin (3+ corners blocked)"""
    cnt = 0
    cx, cy = piece['x'], piece['y']
    for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
        x = cx + dx
        y = cy + dy
        # Count blocked corners (wall or other piece)
        if (x < 0 or x >= COLS or
            y < 0 or y >= ROWS or
            (y >= 0 and (board['binary'][y] & (1 << x)))):
            cnt += 1
    if cnt >= 3:
        clear_lines.last_move_was_spin = True
    return cnt >= 3

# --- Modify attempt_rotation to use SRS wallkicks ---
def attempt_rotation(piece, board, new_rotation):
    """Try rotating the piece using SRS wallkicks"""
    old_rot = piece['rotation']
    kickset = 'I' if piece['shape'] == 'I' else 'JLSTZ'

    # Get correct wallkick tests based on rotation
    rot_index = old_rot
    if new_rotation > old_rot:
        kicks = WALLKICKS[kickset][rot_index]
    else:
        # Counter-clockwise: use reversed kicks from opposite rotation
        rot_index = (old_rot - 1) % 4
        kicks = [(-x, -y) for x,y in WALLKICKS[kickset][rot_index]]

    # Try each wallkick
    for dx, dy in kicks:
        if valid_move(piece, board, dx, dy, new_rotation):
            return dx, dy
    return None

def attempt_180_rotation(piece, board):
    """Try rotating piece 180° using special wallkicks"""
    new_rotation = (piece['rotation'] + 2) % len(tetrominoes[piece['shape']])
    kickset = 'I' if piece['shape'] == 'I' else 'JLSTZ'

    # Try each wallkick position
    for dx, dy in WALLKICKS_180[kickset][0]:
        if valid_move(piece, board, dx, dy, new_rotation):
            return dx, dy
    return None

# --- Input Buffering Setup (near global game variables) ---
input_buffer = []  # stores KEYDOWN events that are not auto-repeated
BUFFER_MAX = 5  # maximum buffered events

# Movement repeat timing (milliseconds):
MOVE_INITIAL_DELAY = 175
MOVE_REPEAT_RATE = 40

move_left_held = False
move_left_timer = 0
move_right_held = False
move_right_timer = 0
soft_drop_held = False
soft_drop_timer = 0

# Add function to draw next pieces preview
def draw_next_pieces():
    next_area = pygame.Rect(10, 200, SIDEBAR - 20, 400)
    pygame.draw.rect(disp, SIDEBAR_COLOR, next_area)
    next_label = font_25.render("NEXT", True, (255, 255, 255))
    blit(next_label, next_area.x + 10, next_area.y + 10)

    y_offset = next_area.y + 50
    piece_spacing = 70  # Increased spacing between pieces

    for shape in next_pieces:
        # Center each piece
        center_x = next_area.centerx
        shape_data = tetrominoes[shape][2] if len(tetrominoes[shape]) > 2 else tetrominoes[shape][0]

        # Draw preview centered
        min_x = min(dx for dx, _ in shape_data)
        max_x = max(dx for dx, _ in shape_data)
        width = (max_x - min_x + 1) * 20
        piece_center = center_x - width // 2

        for dx, dy in shape_data:
            block_x = piece_center + dx * 20
            block_y = y_offset + dy * 20
            pygame.draw.rect(disp, COLORS[shape],
                           pygame.Rect(block_x, block_y, 20, 20),
                           border_radius=4)
            pygame.draw.rect(disp, (50,50,50),
                           pygame.Rect(block_x, block_y, 20, 20),
                           1, border_radius=4)
        y_offset += piece_spacing

def piece_touches_ground(piece, board):
    """Check if piece is touching ground or other pieces below"""
    return not valid_move(piece, board, 0, 1, piece['rotation'])

def try_move_piece(piece, board, dx, dy):
    """Try to move piece and handle lock delay reset"""
    global lock_delay_start, lock_reset_count

    if valid_move(piece, board, dx, dy, piece['rotation']):
        piece['x'] += dx
        piece['y'] += dy

        # Reset lock delay if moved while touching ground
        if piece_touches_ground(piece, board) and lock_reset_count < MAX_LOCK_RESETS:
            lock_delay_start = pygame.time.get_ticks()
            lock_reset_count += 1
        return True
    return False

def update_piece(piece, board):
    """Update piece state including lock delay"""
    global lock_delay_start, lock_reset_count

    if piece_touches_ground(piece, board):
        # Start lock delay when piece first touches ground
        if lock_delay_start == 0:
            lock_delay_start = t.time()

        # Check if lock delay expired
        elif t.time() - lock_delay_start >= LOCK_DELAY:
            lock_piece(piece, board)
            lock_delay_start = 0
            lock_reset_count = 0
            return new_piece()
    else:
        # Reset lock delay when piece is in air
        lock_delay_start = 0
        lock_reset_count = 0

    return piece

# ------------------ Main Game Loop ------------------
current_piece = new_piece(bag_amount=1, bag_extra=0)
fall_timer = 0
running = True

tick = 0
while running:
    dt = clock.tick()  # increased fps limit to 240
    fall_timer += dt
    tick += 1

    if current_piece is None or GAME_OVER:
        print("Game Over")
        break

    # Handle input
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            # Check if it’s a movement or soft drop key:
            if event.key == KEY_LEFT:
                move_left_held = True
                move_left_timer = 0     # resets timing so it moves immediately
            elif event.key == KEY_RIGHT:
                move_right_held = True
                move_right_timer = 0
            elif event.key == KEY_SOFT_DROP:
                soft_drop_held = True
                soft_drop_timer = 0

            elif event.key == KEY_ROTATE_CW:
                # Rotate once, no repeats
                new_rot = (current_piece['rotation'] + 1) % len(tetrominoes[current_piece['shape']])
                kick = attempt_rotation(current_piece, board, new_rot)
                if kick is not None:
                    current_piece['x'] += kick[0]
                    current_piece['y'] += kick[1]
                    current_piece['rotation'] = new_rot
                    if is_spin(current_piece, board):
                        score *= SPIN_BONUS

            elif event.key == KEY_ROTATE_CCW:
                # Rotate once, no repeats
                new_rot = (current_piece['rotation'] - 1) % len(tetrominoes[current_piece['shape']])
                kick = attempt_rotation(current_piece, board, new_rot)
                if kick is not None:
                    current_piece['x'] += kick[0]
                    current_piece['y'] += kick[1]
                    current_piece['rotation'] = new_rot
                    if is_spin(current_piece, board):
                        score *= SPIN_BONUS

            elif event.key == KEY_HARD_DROP:
                # Hard drop once, no repeats
                drop_distance = 0
                while valid_move(current_piece, board, 0, 1, current_piece['rotation']):
                    current_piece['y'] += 1
                    drop_distance += 1
                score += drop_distance * SCORE_HARD_DROP
                lock_piece(current_piece, board)
                board = clear_lines(board)
                current_piece = new_piece(bag_amount=1, bag_extra=0)
                hold_used = False
                fall_timer = 0

            elif event.key == KEY_HOLD:
                if not hold_used:
                    hold_used = True
                    temp = hold_piece
                    hold_piece = {
                        'shape': current_piece['shape'],
                        'rotation': 2,  # Reset rotation to 180°
                        'color': COLORS[current_piece['shape']]
                    }
                    if temp is None:
                        current_piece = new_piece(bag_amount=1, bag_extra=0)
                    else:
                        current_piece = {
                            'shape': temp['shape'],
                            'rotation': 2,  # Reset rotation to 180°
                            'x': COLS // 2,
                            'y': 0,
                            'color': COLORS[temp['shape']]
                        }

            elif event.key == KEY_ROTATE_180:
                kick = attempt_180_rotation(current_piece, board)
                if kick is not None:
                    current_piece['x'] += kick[0]
                    current_piece['y'] += kick[1]
                    current_piece['rotation'] = (current_piece['rotation'] + 2) % len(tetrominoes[current_piece['shape']])
                    if is_spin(current_piece, board):
                        score += SPIN_BONUS * 2  # Double bonus for 180° spin
                        set_message("180° Spin!")

        elif event.type == pygame.KEYUP:
            if event.key == KEY_LEFT:
                move_left_held = False
            elif event.key == KEY_RIGHT:
                move_right_held = False
            elif event.key == KEY_SOFT_DROP:
                soft_drop_held = False

    # Movement auto-repeat logic
    # If move_left_held is True, move piece left if it’s time
    if move_left_held:
        move_left_timer += dt
        if move_left_timer == dt:
            try_move_piece(current_piece, board, -1, 0)
        else:
            if move_left_timer >= MOVE_INITIAL_DELAY:
                repeats = (move_left_timer - MOVE_INITIAL_DELAY) // MOVE_REPEAT_RATE
                while repeats > 0:
                    try_move_piece(current_piece, board, -1, 0)
                    repeats -= 1
                move_left_timer = MOVE_INITIAL_DELAY + (move_left_timer - MOVE_INITIAL_DELAY) % MOVE_REPEAT_RATE

    # Similarly for move_right_held
    if move_right_held:
        move_right_timer += dt
        if move_right_timer == dt:
            try_move_piece(current_piece, board, 1, 0)
        else:
            if move_right_timer >= MOVE_INITIAL_DELAY:
                repeats = (move_right_timer - MOVE_INITIAL_DELAY) // MOVE_REPEAT_RATE
                while repeats > 0:
                    try_move_piece(current_piece, board, 1, 0)
                    repeats -= 1
                move_right_timer = MOVE_INITIAL_DELAY + (move_right_timer - MOVE_INITIAL_DELAY) % MOVE_REPEAT_RATE

    # Similarly for soft_drop_held
    if soft_drop_held:
        soft_drop_timer += dt
        if soft_drop_timer == dt:
            if valid_move(current_piece, board, 0, 1, current_piece['rotation']):
                current_piece['y'] += 1
                fall_timer = 0
        else:
            if soft_drop_timer >= MOVE_INITIAL_DELAY:
                repeats = (soft_drop_timer - MOVE_INITIAL_DELAY) // MOVE_REPEAT_RATE
                while repeats > 0:
                    if valid_move(current_piece, board, 0, 1, current_piece['rotation']):
                        current_piece['y'] += 1
                        fall_timer = 0
                    repeats -= 1
                soft_drop_timer = MOVE_INITIAL_DELAY + (soft_drop_timer - MOVE_INITIAL_DELAY) % MOVE_REPEAT_RATE

    if fall_timer > fall_speed:
        if valid_move(current_piece, board, 0, 1, current_piece['rotation']):
            current_piece['y'] += 1
        # Get the current time for lock delay
        # Update piece state with lock delay
        current_piece = update_piece(current_piece, board)
        fall_timer = 0

    # Update and draw particles, messages
    update_particles(dt)

    disp.fill((0,0,0))
    draw_board(board)
    draw_ghost(current_piece)
    draw_piece(current_piece)
    draw_particles(BOARD_OFFSET_X, 0)  # board offset for particle positions
    draw_hold_piece()
    draw_next_pieces()  # Add this line
    draw_score()
    draw_message(dt)

    areas = disp.blits(blits)
    blits.clear()

    fps = calculate_fps(clock.get_fps(),500)
    pygame.display.set_caption(f'Tetris | FPS: {fps}')

    if tick % 10 == 0:
        pygame.display.update()
    else:
        pygame.display.update(areas)

pygame.quit()