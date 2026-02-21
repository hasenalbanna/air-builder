"""
Configuration settings for AI Hand Builder (Python Version)
Enhanced with lighting compensation features
"""

# Camera Settings
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# MediaPipe Settings
MAX_NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.4  # Lowered for better low-light performance
MIN_TRACKING_CONFIDENCE = 0.4   # Lowered for better low-light performance
MODEL_COMPLEXITY = 1  # 0=lite, 1=full, 2=heavy

# Image Enhancement Settings (for poor lighting)
ENABLE_AUTO_BRIGHTNESS = True
BRIGHTNESS_ALPHA = 1.3  # Contrast multiplier (1.0 = no change)
BRIGHTNESS_BETA = 20     # Brightness offset (0 = no change)
ENABLE_CLAHE = True      # Contrast Limited Adaptive Histogram Equalization
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)

# Hand Tracking Settings
PINCH_THRESHOLD = 0.05
SMOOTHING_FACTOR = 0.15
MIN_SIZE = 0.5
MAX_SIZE = 5.0

# 3D World Settings
WORLD_WIDTH = 20
WORLD_HEIGHT = 12
CAMERA_DISTANCE = 12
CAMERA_HEIGHT = 5

# Build Modes
BUILD_MODES = {
    'free': 'Free Build',
    'building': 'Building Blocks',
    'solar': 'Solar System'
}

# Building Parts Configuration
BUILDING_PARTS = {
    'wall': {'size': (3, 2, 0.3), 'color': (0.76, 0.60, 0.42), 'name': 'Wall'},
    'window': {'size': (1.5, 1.5, 0.2), 'color': (0.53, 0.81, 0.92), 'name': 'Window'},
    'door': {'size': (1.2, 2, 0.2), 'color': (0.55, 0.27, 0.07), 'name': 'Door'},
    'roof': {'size': (4, 0.3, 4), 'color': (0.86, 0.08, 0.24), 'name': 'Roof'},
    'floor': {'size': (4, 0.2, 4), 'color': (0.41, 0.41, 0.41), 'name': 'Floor'},
    'column': {'size': (0.4, 3, 0.4), 'color': (0.83, 0.83, 0.83), 'name': 'Column'},
    'stairs': {'size': (2, 1, 3), 'color': (0.66, 0.66, 0.66), 'name': 'Stairs'},
    'balcony': {'size': (3, 0.2, 1.5), 'color': (0.44, 0.50, 0.56), 'name': 'Balcony'}
}

# Solar System Objects
SOLAR_OBJECTS = {
    'sun': {'radius': 3, 'color': (0.99, 0.72, 0.07), 'name': 'Sun'},
    'mercury': {'radius': 0.4, 'color': (0.55, 0.47, 0.33), 'name': 'Mercury'},
    'venus': {'radius': 0.9, 'color': (1.0, 0.78, 0.29), 'name': 'Venus'},
    'earth': {'radius': 1, 'color': (0.25, 0.41, 0.88), 'name': 'Earth'},
    'moon': {'radius': 0.3, 'color': (0.75, 0.75, 0.75), 'name': 'Moon'},
    'mars': {'radius': 0.5, 'color': (0.80, 0.36, 0.36), 'name': 'Mars'},
    'jupiter': {'radius': 2.5, 'color': (0.85, 0.65, 0.13), 'name': 'Jupiter'},
    'saturn': {'radius': 2, 'color': (0.96, 0.64, 0.38), 'name': 'Saturn'},
    'uranus': {'radius': 1.5, 'color': (0.31, 0.82, 0.91), 'name': 'Uranus'},
    'neptune': {'radius': 1.4, 'color': (0.25, 0.40, 0.96), 'name': 'Neptune'},
    'asteroid': {'radius': 0.2, 'color': (0.50, 0.50, 0.50), 'name': 'Asteroid'},
    'comet': {'radius': 0.3, 'color': (0.88, 0.88, 0.88), 'name': 'Comet'}
}

# UI Colors (RGB 0-255)
UI_BG_COLOR = (15, 23, 42)
UI_TEXT_COLOR = (255, 255, 255)
UI_ACCENT_COLOR = (56, 189, 248)
UI_WARNING_COLOR = (239, 68, 68)
UI_SUCCESS_COLOR = (34, 197, 94)

# Quality Thresholds
GOOD_LIGHTING_THRESHOLD = 100  # Average brightness
POOR_LIGHTING_THRESHOLD = 50
CONFIDENCE_WARNING_THRESHOLD = 0.6
