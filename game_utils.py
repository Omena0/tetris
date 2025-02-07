import pygame

# Game dimensions
SIZE = 30
COLS = 10
ROWS = 20
SIDEBAR = 200
WIDTH = COLS * SIZE
HEIGHT = ROWS * SIZE
WINDOW_WIDTH = WIDTH + SIDEBAR
WINDOW_HEIGHT = HEIGHT

# Game speeds
BASE_FALL_SPEED = 500      # Base gravity: ms
FALL_SPEED_DECREMENT = 20  # Decrement/level: ms
MIN_FALL_SPEED = 100       # Gravity: ms
DELAYED_AUTO_SHIFT = 150   # DAS: ms
AUTO_REPEAT_RATE = 40      # ARR: ms

# Lock delay constants
LOCK_DELAY = 5000          # Time in ms before piece locks
MAX_LOCK_RESETS = 15       # Maximum number of lock delay resets

# --- Input Buffering Setup (near global game variables) ---
input_buffer = []  # stores KEYDOWN events that are not auto-repeated
BUFFER_MAX = 5  # maximum buffered events

move_left_held = False
move_left_timer = 0
move_right_held = False
move_right_timer = 0
soft_drop_held = False
soft_drop_timer = 0

# Game controls
KEY_LEFT = pygame.K_a
KEY_RIGHT = pygame.K_d
KEY_SOFT_DROP = pygame.K_s
KEY_HARD_DROP = pygame.K_SPACE
KEY_HOLD = pygame.K_c
KEY_ROTATE_CW = pygame.K_DOWN
KEY_ROTATE_CCW = pygame.K_RIGHT
KEY_ROTATE_180 = pygame.K_f

# Scoring constants
SCORE_PER_LINE = 100
SCORE_HARD_DROP = 2
SPIN_BONUS = 50

# Visual constants
GAME_BOARD_COLOR = (40, 40, 60)
SIDEBAR_COLOR = (30, 30, 30)
GRID_COLOR = (60, 60, 80)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)

COLORS = {
    'I': (0, 255, 255),
    'O': (255, 255, 0),
    'T': (128, 0, 128),
    'S': (0, 255, 0),
    'Z': (255, 0, 0),
    'J': (0, 0, 255),
    'L': (255, 127, 0)
}

# Game rules
NEXT_PIECES = 5
PARTICLES_PER_BLOCK = 10
PARTICLE_LIFETIME = 200
LINE_CLEAR_NAMES = ['Single', 'Double', 'Triple', 'Quad', 'Penta', 'Hexa', 'Hepta', 'Octa', 'Nona', 'Deca']

GAME_OVER = False

# Board offset
BOARD_OFFSET_X = SIDEBAR

# ------------------ Tetromino Definitions ------------------
tetrominoes = {
    'I': [
        [(0,0), (-1,0), (1,0), (2,0)],
        [(0,0), (0,-1), (0,1), (0,2)]
    ],
    'O': [
        [(0,0), (1,0), (0,1), (1,1)]
    ],
    'T': [
        [(0,0), (-1,0), (1,0), (0,1)],
        [(0,0), (0,-1), (0,1), (1,0)],
        [(0,0), (-1,0), (1,0), (0,-1)],
        [(0,0), (0,-1), (0,1), (-1,0)]
    ],
    'S': [
        # Fixed: S now mirrors Z proper
        [(0,0), (1,0), (0,1), (-1,1)],
        [(0,0), (0,-1), (1,0), (1,1)]
    ],
    'Z': [
        # Fixed: Z now mirrors S proper
        [(0,0), (-1,0), (0,1), (1,1)],
        [(0,0), (0,-1), (-1,0), (-1,1)]
    ],
    'J': [
        [(0,0), (-1,0), (1,0), (1,1)],
        [(0,0), (0,-1), (0,1), (1,-1)],
        [(0,0), (-1,-1), (-1,0), (1,0)],
        [(0,0), (0,-1), (0,1), (-1,1)]
    ],
    'L': [
        [(0,0), (-1,0), (1,0), (-1,1)],
        [(0,0), (0,-1), (0,1), (1,1)],
        [(0,0), (-1,0), (1,0), (1,-1)],
        [(0,0), (0,-1), (0,1), (-1,-1)]
    ]
}

# Add SRS wallkick data after tetromino definitions
WALLKICKS = {
    'JLSTZ': [
        [(0,0), (-1,0), (-1,-1), (0,2), (-1,2)],  # 0->1
        [(0,0), (1,0), (1,1), (0,-2), (1,-2)],    # 1->2
        [(0,0), (1,0), (1,-1), (0,2), (1,2)],     # 2->3
        [(0,0), (-1,0), (-1,1), (0,-2), (-1,-2)]  # 3->0
    ],
    'I': [
        [(0,0), (-2,0), (1,0), (-2,1), (1,-2)],   # 0->1
        [(0,0), (-1,0), (2,0), (-1,-2), (2,1)],   # 1->2
        [(0,0), (2,0), (-1,0), (2,-1), (-1,2)],   # 2->3
        [(0,0), (1,0), (-2,0), (1,2), (-2,-1)]    # 3->0
    ]
}

# Add 180° wallkick data after other wallkicks
WALLKICKS_180 = {
    'JLSTZ': [
        [(0,0), (0,1), (1,1), (-1,1), (1,0), (-1,0)],  # More generous kicks for 180
    ],
    'I': [
        [(0,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)],
    ]
}

def createRect(x, y, size=SIZE):
    """Create a pygame Rect at the given grid position"""
    return pygame.Rect(x * size, y * size, size, size)

def drawBlock(x, y, color, size=SIZE, offset_x=0, offset_y=0):
    """Draw a block with rounded corners and border"""
    rect = pygame.Rect(offset_x + x * size, offset_y + y * size, size, size)
    pygame.draw.rect(pygame.display.get_surface(), color, rect, border_radius=5)
    pygame.draw.rect(pygame.display.get_surface(), (50, 50, 50), rect, 1, border_radius=5)
