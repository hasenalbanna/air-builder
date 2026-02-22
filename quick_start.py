"""
Quick Start Version - AI Hand Builder
Launches directly into Building Mode without login
"""

import cv2
import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import time

# Import mediapipe with error handling
try:
    import mediapipe as mp
except Exception as e:
    print(f"Error importing mediapipe: {e}")
    from mediapipe.python.solutions import hands as mp_hands_module
    from mediapipe.python.solutions import drawing_utils as mp_drawing_module
    class MPNamespace:
        class solutions:
            hands = mp_hands_module
            drawing_utils = mp_drawing_module
    mp = MPNamespace()

import config

class QuickStart3D:
    def __init__(self):
        """Initialize Quick Start version"""
        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.4,
            min_tracking_confidence=0.4,
            model_complexity=1
        )
        
        # Camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Image enhancement
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # PyGame & OpenGL
        pygame.init()
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            DOUBLEBUF | OPENGL
        )
        pygame.display.set_caption("AI Hand Builder - Quick Start")
        
        self._init_opengl()
        
        # State
        self.cursor_pos = [0, 0, 0]
        self.target_pos = [0, 0, 0]
        self.current_size = 1.0
        self.last_pinch_time = 0
        self.is_pinching = False
        
        # Camera rotation and zoom
        self.camera_rotation_y = 0
        self.camera_rotation_x = 0
        self.target_camera_rotation_y = 0
        self.target_camera_rotation_x = 0
        self.is_rotating_camera = False
        self.camera_distance = 12.0
        self.target_camera_distance = 12.0
        self.last_hand_distance = None
        
        # Build mode - START IN BUILDING MODE
        self.build_mode = 'building'  # Default to building mode!
        self.selected_building_part = 'wall'
        self.selected_city_asset = 'road'
        self.selected_solar_object = 'earth'
        self.current_color = [0.22, 0.74, 0.97]
        
        # Zone/Area system
        self.current_zone = 'zone1'
        self.zone_offset = [0, 0, 0]  # Offset for current zone
        self.show_zone_selector = False
        
        # Grid-based placement system
        self.grid_size = 2.0  # Each grid cell is 2x2 units
        self.snap_to_grid = True  # Enable grid snapping by default
        self.placement_height = 0  # Current height level (0=ground, 1=2 units up, etc.)
        self.max_height_level = 10  # Maximum 10 levels (20 units high)
        self.show_placement_grid = True  # Show the placement grid
        
        self.blocks = []
        self.show_grid = True
        
        # UI
        self.detection_confidence = 0
        self.lighting_quality = "Unknown"
        self.avg_brightness = 0
        
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
        self.font_tiny = pygame.font.Font(None, 16)
        
        self.ui_buttons = []
        self.zone_buttons = []
        self.hovered_button = None
        self._build_ui_buttons()
        
        print("\n" + "="*60)
        print("🚀 AI Hand Builder - Quick Start Mode")
        print("="*60)
        print("✅ Started in BUILDING MODE")
        print("📱 Camera preview: Top-right corner")
        print("🖱️  Click buttons on left to select parts")
        print("👆 Show your hand to start building!")
        print("🗺️  9 empty zones ready - click 'TELEPORT TO ZONES' to navigate!")
        print("🔍 Zoom: Bring 2 hands CLOSER together = Zoom IN")
        print("="*60 + "\n")
        
    def _init_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glLightfv(GL_LIGHT0, GL_POSITION, (10, 20, 10, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.6, 0.6, 0.6, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        glMatrixMode(GL_PROJECTION)
        gluPerspective(60, self.screen_width / self.screen_height, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
    
    def enhance_image(self, frame):
        frame = cv2.convertScaleAbs(frame, alpha=1.3, beta=20)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe.apply(l)
        lab = cv2.merge([l, a, b])
        frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.avg_brightness = np.mean(gray)
        if self.avg_brightness < 50:
            self.lighting_quality = "Poor"
        elif self.avg_brightness < 100:
            self.lighting_quality = "Fair"
        else:
            self.lighting_quality = "Good"
        return frame
    
    def process_hand_tracking(self, frame):
        enhanced_frame = self.enhance_image(frame.copy())
        rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        display_frame = frame.copy()
        
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            if results.multi_handedness:
                self.detection_confidence = results.multi_handedness[0].classification[0].score
            
            if num_hands == 2:
                self.is_rotating_camera = True
                hand1 = results.multi_hand_landmarks[0]
                hand2 = results.multi_hand_landmarks[1]
                h1_index = hand1.landmark[8]
                h2_index = hand2.landmark[8]
                
                # Camera rotation based on mid-point
                horizontal_mid = (h1_index.x + h2_index.x) / 2
                vertical_mid = (h1_index.y + h2_index.y) / 2
                self.target_camera_rotation_y = (horizontal_mid - 0.5) * math.pi * 2
                self.target_camera_rotation_x = (vertical_mid - 0.5) * math.pi
                
                # Zoom based on distance between hands
                hand_distance = math.hypot(h1_index.x - h2_index.x, h1_index.y - h2_index.y)
                if self.last_hand_distance is not None:
                    # Map hand distance to camera distance (closer hands = zoom in)
                    # Distance range: 0.1 (close) to 1.0 (far)
                    # Camera range: 5 (close) to 20 (far)
                    self.target_camera_distance = 5 + (hand_distance * 15)
                    self.target_camera_distance = max(5, min(25, self.target_camera_distance))
                self.last_hand_distance = hand_distance
                
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(
                        display_frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                        self.mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2)
                    )
                zoom_pct = int((25 - self.target_camera_distance) / 20 * 100)
                cv2.putText(display_frame, "ROTATE & ZOOM MODE", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Zoom: {zoom_pct}%", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            elif num_hands == 1:
                self.is_rotating_camera = False
                landmarks = results.multi_hand_landmarks[0]
                self.mp_draw.draw_landmarks(
                    display_frame, landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                    self.mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2)
                )
                cv2.putText(display_frame, "HAND DETECTED", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Conf: {self.detection_confidence:.2f}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                
                index_tip = landmarks.landmark[8]
                # Expanded movement range: X and Z axes cover full zone (±15 units)
                # Map hand X (0-1) to world X (-15 to +15) = 30 units range
                x = (1 - index_tip.x) * 30 - 15
                # Map hand Y (0-1) to world Z (-15 to +15) = 30 units range (forward/back)
                z = (index_tip.y - 0.5) * 30
                # Y stays at current height level for now (controlled by arrow keys)
                y = self.placement_height * self.grid_size
                self.target_pos = [x, y, z]
                
                index_x, index_y = index_tip.x, index_tip.y
                pinky_tip = landmarks.landmark[20]
                pinky_x, pinky_y = pinky_tip.x, pinky_tip.y
                hand_spread = math.hypot(index_x - pinky_x, index_y - pinky_y)
                self.current_size = max(0.5, min(5, hand_spread * 10))
                
                thumb_tip = landmarks.landmark[4]
                thumb_x, thumb_y = thumb_tip.x, thumb_tip.y
                pinch_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
                
                if pinch_dist < 0.05:
                    current_time = time.time()
                    if not self.is_pinching and (current_time - self.last_pinch_time) > 0.4:
                        self.place_block()
                        self.last_pinch_time = current_time
                        self.is_pinching = True
                else:
                    self.is_pinching = False
        else:
            self.is_rotating_camera = False
            self.detection_confidence = 0
            self.last_hand_distance = None
            cv2.putText(display_frame, "NO HAND DETECTED", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_frame, "Show your hand to camera", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return display_frame
    
    def place_block(self):
        # Get snapped position if grid is enabled
        if self.snap_to_grid:
            snapped_x = round(self.cursor_pos[0] / self.grid_size) * self.grid_size
            snapped_z = round(self.cursor_pos[2] / self.grid_size) * self.grid_size
            snapped_y = self.placement_height * self.grid_size
        else:
            snapped_x = self.cursor_pos[0]
            snapped_z = self.cursor_pos[2]
            snapped_y = self.cursor_pos[1]
        
        # Apply zone offset to placement position
        adjusted_pos = [
            snapped_x + self.zone_offset[0],
            snapped_y + self.zone_offset[1],
            snapped_z + self.zone_offset[2]
        ]
        block_data = {'position': adjusted_pos, 'mode': self.build_mode, 'rotation': [0, 0, 0], 'zone': self.current_zone}
        
        if self.build_mode == 'free':
            block_data['size'] = [self.current_size] * 3
            block_data['color'] = self.current_color.copy()
            block_data['type'] = 'cube'
            block_data['asset_type'] = None
        elif self.build_mode == 'building':
            part = config.BUILDING_PARTS[self.selected_building_part]
            block_data['size'] = list(part['size'])
            block_data['color'] = list(part['color'])
            block_data['type'] = 'building'
            block_data['asset_type'] = self.selected_building_part
        elif self.build_mode == 'city':
            asset = config.CITY_ASSETS[self.selected_city_asset]
            block_data['size'] = list(asset['size'])
            block_data['color'] = list(asset['color'])
            block_data['type'] = 'city'
            block_data['asset_type'] = self.selected_city_asset
        elif self.build_mode == 'solar':
            obj = config.SOLAR_OBJECTS[self.selected_solar_object]
            block_data['size'] = [obj['radius']]
            block_data['color'] = list(obj['color'])
            block_data['type'] = 'sphere'
            block_data['asset_type'] = None
        
        self.blocks.append(block_data)
        
        # Print placement message
        if self.build_mode == 'building':
            print(f"✅ Placed {config.BUILDING_PARTS[self.selected_building_part]['name']}")
        elif self.build_mode == 'city':
            asset_name = config.CITY_ASSETS[self.selected_city_asset]['name']
            print(f"✅ Placed {asset_name}")
            if self.selected_city_asset == 'sun':
                print("   ☀️ Sun will emit dynamic lighting!")
        else:
            print(f"✅ Placed {block_data['type']}")
    
    def _build_ui_buttons(self):
        self.ui_buttons = []
        x_start = 10
        y_start = 200
        button_width = 110
        button_height = 40
        spacing = 5
        
        if self.build_mode == 'building':
            parts_list = list(config.BUILDING_PARTS.keys())
            for i, part in enumerate(parts_list):
                row = i // 2
                col = i % 2
                x = x_start + col * (button_width + spacing)
                y = y_start + row * (button_height + spacing)
                icons = {'wall': '🧱', 'window': '🪟', 'door': '🚪', 'roof': '🏠',
                        'floor': '⬛', 'column': '🏛️', 'stairs': '🪜', 'balcony': '🏗️'}
                self.ui_buttons.append({
                    'rect': pygame.Rect(x, y, button_width, button_height),
                    'text': config.BUILDING_PARTS[part]['name'],
                    'icon': icons.get(part, '📦'),
                    'value': part,
                    'type': 'building'
                })
        elif self.build_mode == 'city':
            assets_list = list(config.CITY_ASSETS.keys())
            for i, asset in enumerate(assets_list):
                row = i // 2
                col = i % 2
                x = x_start + col * (button_width + spacing)
                y = y_start + row * (button_height + spacing)
                icons = {'road': '🛣️', 'apartment': '🏢', 'house': '🏠', 'skyscraper': '🏙️',
                        'shop': '🏪', 'streetlight': '💡', 'bench': '🪑', 'tree': '🌳',
                        'grass': '🌿', 'fountain': '⛲', 'car': '🚗', 'person': '🧍', 'sun': '☀️'}
                self.ui_buttons.append({
                    'rect': pygame.Rect(x, y, button_width, button_height),
                    'text': config.CITY_ASSETS[asset]['name'],
                    'icon': icons.get(asset, '📦'),
                    'value': asset,
                    'type': 'city'
                })
        elif self.build_mode == 'solar':
            objects_list = list(config.SOLAR_OBJECTS.keys())
            for i, obj in enumerate(objects_list):
                row = i // 2
                col = i % 2
                x = x_start + col * (button_width + spacing)
                y = y_start + row * (button_height + spacing)
                icons = {'sun': '☀️', 'mercury': '☿', 'venus': '♀', 'earth': '🌍',
                        'moon': '🌙', 'mars': '♂', 'jupiter': '♃', 'saturn': '♄',
                        'uranus': '♅', 'neptune': '♆', 'asteroid': '☄️', 'comet': '💫'}
                self.ui_buttons.append({
                    'rect': pygame.Rect(x, y, button_width, button_height),
                    'text': config.SOLAR_OBJECTS[obj]['name'],
                    'icon': icons.get(obj, '🌟'),
                    'value': obj,
                    'type': 'solar'
                })
    
    def handle_mouse_click(self, pos):
        # Check zone buttons first if zone selector is shown
        if self.show_zone_selector:
            for button in self.zone_buttons:
                if button['rect'].collidepoint(pos):
                    self.teleport_to_zone(button['value'])
                    self.show_zone_selector = False
                    return True
        
        # Check mode switch buttons first (highest priority)
        if hasattr(self, 'mode_buttons'):
            for button in self.mode_buttons:
                if button['rect'].collidepoint(pos):
                    self.build_mode = button['value']
                    self._build_ui_buttons()
                    print(f"🎮 Switched to {config.BUILD_MODES[self.build_mode]} mode")
                    return True
        
        # Check regular UI buttons (building/city/solar element buttons)
        for button in self.ui_buttons:
            if button['rect'].collidepoint(pos):
                if button['type'] == 'building':
                    self.selected_building_part = button['value']
                    print(f"🏗️ Selected: {config.BUILDING_PARTS[button['value']]['name']}")
                elif button['type'] == 'city':
                    self.selected_city_asset = button['value']
                    print(f"🏙️ Selected: {config.CITY_ASSETS[button['value']]['name']}")
                elif button['type'] == 'solar':
                    self.selected_solar_object = button['value']
                    print(f"🌍 Selected: {config.SOLAR_OBJECTS[button['value']]['name']}")
                return True
        
        # Check zones opener button (lower priority)
        if hasattr(self, 'zones_opener_button') and self.zones_opener_button['rect'].collidepoint(pos):
            self.show_zone_selector = not self.show_zone_selector
            print(f"📍 Zone Selector: {'OPENED' if self.show_zone_selector else 'CLOSED'}")
            return True
        
        return False
    
    def teleport_to_zone(self, zone_name):
        """Teleport the camera to a different zone/area"""
        self.current_zone = zone_name
        zone_data = config.ZONES[zone_name]
        self.zone_offset = list(zone_data['position'])
        
        # Move camera to look at the zone
        # Reset camera rotation to default view of the zone
        self.target_camera_rotation_y = 0
        self.target_camera_rotation_x = 0
        
        print(f"📍 Teleported to: {zone_data['name']}")
        print(f"   Position: {zone_data['position']}")
        
        # Count blocks in this zone
        blocks_in_zone = sum(1 for b in self.blocks if b.get('zone') == zone_name)
        print(f"   ({blocks_in_zone} objects in this area)")
    
    def handle_mouse_motion(self, pos):
        self.hovered_button = None
        # Check zone buttons if zone selector is shown
        if self.show_zone_selector:
            for button in self.zone_buttons:
                if button['rect'].collidepoint(pos):
                    self.hovered_button = button
                    return
        
        # Check zones opener button
        if hasattr(self, 'zones_opener_button') and self.zones_opener_button['rect'].collidepoint(pos):
            self.hovered_button = self.zones_opener_button
            return
        
        # Check mode switch buttons
        if hasattr(self, 'mode_buttons'):
            for button in self.mode_buttons:
                if button['rect'].collidepoint(pos):
                    self.hovered_button = button
                    return
        
        # Check regular UI buttons
        for button in self.ui_buttons:
            if button['rect'].collidepoint(pos):
                self.hovered_button = button
                break
    
    def draw_grid(self):
        if not self.show_grid:
            return
        glDisable(GL_LIGHTING)
        
        # Draw zone boundaries and colored grids for each zone
        zone_colors = {
            'zone1': (0.3, 0.5, 0.9),   # Blue - Central Plaza
            'zone2': (0.9, 0.5, 0.3),   # Orange - East District
            'zone3': (0.5, 0.3, 0.9),   # Purple - West District
            'zone4': (0.3, 0.9, 0.3),   # Green - North Park
            'zone5': (0.9, 0.9, 0.3),   # Yellow - South Beach
            'zone6': (0.9, 0.3, 0.3),   # Red - NE Industrial
            'zone7': (0.3, 0.9, 0.9),   # Cyan - NW Residential
            'zone8': (0.5, 0.9, 0.5),   # Light Green - SE Harbor
            'zone9': (0.7, 0.5, 0.3)    # Brown - SW Mountain
        }
        
        # Draw colored zone areas
        for zone_id, zone_data in config.ZONES.items():
            pos = zone_data['position']
            color = zone_colors.get(zone_id, (0.3, 0.3, 0.3))
            
            # Brighten current zone
            if zone_id == self.current_zone:
                color = tuple(min(c * 1.5, 1.0) for c in color)
            else:
                color = tuple(c * 0.5 for c in color)
            
            # Draw zone floor (semi-transparent)
            glColor4f(color[0], color[1], color[2], 0.15)
            glBegin(GL_QUADS)
            glVertex3f(pos[0] - 12, 0.01, pos[2] - 12)
            glVertex3f(pos[0] + 12, 0.01, pos[2] - 12)
            glVertex3f(pos[0] + 12, 0.01, pos[2] + 12)
            glVertex3f(pos[0] - 12, 0.01, pos[2] + 12)
            glEnd()
            
            # Draw zone boundary lines
            glColor3f(*color)
            glLineWidth(3)
            glBegin(GL_LINE_LOOP)
            glVertex3f(pos[0] - 12, 0.02, pos[2] - 12)
            glVertex3f(pos[0] + 12, 0.02, pos[2] - 12)
            glVertex3f(pos[0] + 12, 0.02, pos[2] + 12)
            glVertex3f(pos[0] - 12, 0.02, pos[2] + 12)
            glEnd()
            
            # Draw corner markers
            glPointSize(8)
            glBegin(GL_POINTS)
            glVertex3f(pos[0] - 12, 0.02, pos[2] - 12)
            glVertex3f(pos[0] + 12, 0.02, pos[2] - 12)
            glVertex3f(pos[0] + 12, 0.02, pos[2] + 12)
            glVertex3f(pos[0] - 12, 0.02, pos[2] + 12)
            glEnd()
        
        # Draw placement grid (visible and aligned to grid_size)
        if self.show_placement_grid:
            glColor3f(0.3, 0.4, 0.5)
            glLineWidth(1)
            glBegin(GL_LINES)
            # Draw grid in current zone
            zone_x, zone_z = self.zone_offset[0], self.zone_offset[2]
            grid_range = 12  # +/- 12 from zone center
            step = int(self.grid_size)
            for i in range(-grid_range, grid_range + 1, step):
                # Lines parallel to X axis
                glVertex3f(zone_x - grid_range, 0.001, zone_z + i)
                glVertex3f(zone_x + grid_range, 0.001, zone_z + i)
                # Lines parallel to Z axis
                glVertex3f(zone_x + i, 0.001, zone_z - grid_range)
                glVertex3f(zone_x + i, 0.001, zone_z + grid_range)
            glEnd()
            
            # Draw current grid cell highlight
            if hasattr(self, 'display_cursor_pos'):
                cx, cy, cz = self.display_cursor_pos
                half_grid = self.grid_size / 2
                
                # Highlight the cell where cursor is
                glColor4f(0.2, 0.8, 0.2, 0.3)  # Green transparent
                glBegin(GL_QUADS)
                glVertex3f(cx - half_grid, cy + 0.01, cz - half_grid)
                glVertex3f(cx + half_grid, cy + 0.01, cz - half_grid)
                glVertex3f(cx + half_grid, cy + 0.01, cz + half_grid)
                glVertex3f(cx - half_grid, cy + 0.01, cz + half_grid)
                glEnd()
                
                # Border of highlighted cell
                glColor3f(0.2, 1.0, 0.2)
                glLineWidth(3)
                glBegin(GL_LINE_LOOP)
                glVertex3f(cx - half_grid, cy + 0.02, cz - half_grid)
                glVertex3f(cx + half_grid, cy + 0.02, cz - half_grid)
                glVertex3f(cx + half_grid, cy + 0.02, cz + half_grid)
                glVertex3f(cx - half_grid, cy + 0.02, cz + half_grid)
                glEnd()
        
        # Draw fine grid lines (faded) - original background grid
        glColor3f(0.15, 0.15, 0.15)
        glLineWidth(1)
        glBegin(GL_LINES)
        for i in range(-50, 51, 5):
            glVertex3f(-50, 0, i); glVertex3f(50, 0, i)
            glVertex3f(i, 0, -50); glVertex3f(i, 0, 50)
        glEnd()
        
        # Draw axis indicators at origin
        glLineWidth(3)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0); glVertex3f(0, 0, 0); glVertex3f(2, 0, 0)
        glColor3f(0, 1, 0); glVertex3f(0, 0, 0); glVertex3f(0, 2, 0)
        glColor3f(0, 0, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, 2)
        glEnd()
        
        # Draw zone labels as 3D text markers
        self.draw_zone_labels()
        
        glEnable(GL_LIGHTING)
    
    def draw_zone_labels(self):
        """Draw 3D markers and labels for each zone"""
        zone_icons = {
            'zone1': '🏛️', 'zone2': '🏙️', 'zone3': '🌆',
            'zone4': '🌳', 'zone5': '🏖️', 'zone6': '⚓',
            'zone7': '🏘️', 'zone8': '🏭', 'zone9': '⛰️'
        }
        
        for zone_id, zone_data in config.ZONES.items():
            pos = zone_data['position']
            
            # Draw a tall pole marker at zone center
            glDisable(GL_LIGHTING)
            
            # Make current zone marker brighter and taller
            if zone_id == self.current_zone:
                glColor3f(1.0, 1.0, 0.0)  # Bright yellow
                marker_height = 8
                glLineWidth(4)
            else:
                glColor3f(0.5, 0.5, 0.5)  # Gray
                marker_height = 5
                glLineWidth(2)
            
            # Draw vertical marker pole
            glBegin(GL_LINES)
            glVertex3f(pos[0], 0, pos[2])
            glVertex3f(pos[0], marker_height, pos[2])
            glEnd()
            
            # Draw marker top (small pyramid)
            glBegin(GL_TRIANGLES)
            # 4 sides of pyramid
            glVertex3f(pos[0], marker_height + 1, pos[2])
            glVertex3f(pos[0] - 0.5, marker_height, pos[2] - 0.5)
            glVertex3f(pos[0] + 0.5, marker_height, pos[2] - 0.5)
            
            glVertex3f(pos[0], marker_height + 1, pos[2])
            glVertex3f(pos[0] + 0.5, marker_height, pos[2] - 0.5)
            glVertex3f(pos[0] + 0.5, marker_height, pos[2] + 0.5)
            
            glVertex3f(pos[0], marker_height + 1, pos[2])
            glVertex3f(pos[0] + 0.5, marker_height, pos[2] + 0.5)
            glVertex3f(pos[0] - 0.5, marker_height, pos[2] + 0.5)
            
            glVertex3f(pos[0], marker_height + 1, pos[2])
            glVertex3f(pos[0] - 0.5, marker_height, pos[2] + 0.5)
            glVertex3f(pos[0] - 0.5, marker_height, pos[2] - 0.5)
            glEnd()
            
            glEnable(GL_LIGHTING)
    
    def draw_cursor(self):
        # Use snapped position for cursor display
        cursor_display = self.display_cursor_pos if hasattr(self, 'display_cursor_pos') else self.cursor_pos
        
        glPushMatrix()
        glTranslatef(*cursor_display)
        if self.build_mode == 'building':
            color = config.BUILDING_PARTS[self.selected_building_part]['color']
        elif self.build_mode == 'city':
            color = config.CITY_ASSETS[self.selected_city_asset]['color']
        elif self.build_mode == 'solar':
            color = config.SOLAR_OBJECTS[self.selected_solar_object]['color']
        else:
            color = self.current_color
        
        # Draw bright wireframe cursor
        glDisable(GL_LIGHTING)
        glLineWidth(3)
        glColor3f(*color)
        
        # Draw wireframe box
        s = 0.5
        glBegin(GL_LINES)
        # Bottom face
        glVertex3f(-s, -s, s); glVertex3f(s, -s, s)
        glVertex3f(s, -s, s); glVertex3f(s, -s, -s)
        glVertex3f(s, -s, -s); glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, -s); glVertex3f(-s, -s, s)
        # Top face
        glVertex3f(-s, s, s); glVertex3f(s, s, s)
        glVertex3f(s, s, s); glVertex3f(s, s, -s)
        glVertex3f(s, s, -s); glVertex3f(-s, s, -s)
        glVertex3f(-s, s, -s); glVertex3f(-s, s, s)
        # Vertical edges
        glVertex3f(-s, -s, s); glVertex3f(-s, s, s)
        glVertex3f(s, -s, s); glVertex3f(s, s, s)
        glVertex3f(s, -s, -s); glVertex3f(s, s, -s)
        glVertex3f(-s, -s, -s); glVertex3f(-s, s, -s)
        glEnd()
        
        # Draw center crosshair
        glColor3f(1, 1, 0)  # Yellow
        glBegin(GL_LINES)
        glVertex3f(-0.8, 0, 0); glVertex3f(0.8, 0, 0)
        glVertex3f(0, -0.8, 0); glVertex3f(0, 0.8, 0)
        glVertex3f(0, 0, -0.8); glVertex3f(0, 0, 0.8)
        glEnd()
        
        glLineWidth(1)
        glEnable(GL_LIGHTING)
        glPopMatrix()
    
    def draw_wireframe_cube(self, size):
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)
        s = size / 2
        glVertex3f(-s, -s, s); glVertex3f(s, -s, s); glVertex3f(s, -s, s); glVertex3f(s, s, s)
        glVertex3f(s, s, s); glVertex3f(-s, s, s); glVertex3f(-s, s, s); glVertex3f(-s, -s, s)
        glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s); glVertex3f(s, -s, -s); glVertex3f(s, s, -s)
        glVertex3f(s, s, -s); glVertex3f(-s, s, -s); glVertex3f(-s, s, -s); glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s); glVertex3f(-s, -s, -s); glVertex3f(s, -s, s); glVertex3f(s, -s, -s)
        glVertex3f(s, s, s); glVertex3f(s, s, -s); glVertex3f(-s, s, s); glVertex3f(-s, s, -s)
        glEnd()
        glEnable(GL_LIGHTING)
    
    def draw_cube(self, size):
        s = size / 2
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1); glVertex3f(-s, -s, s); glVertex3f(s, -s, s); glVertex3f(s, s, s); glVertex3f(-s, s, s)
        glNormal3f(0, 0, -1); glVertex3f(-s, -s, -s); glVertex3f(-s, s, -s); glVertex3f(s, s, -s); glVertex3f(s, -s, -s)
        glNormal3f(0, 1, 0); glVertex3f(-s, s, -s); glVertex3f(-s, s, s); glVertex3f(s, s, s); glVertex3f(s, s, -s)
        glNormal3f(0, -1, 0); glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s); glVertex3f(s, -s, s); glVertex3f(-s, -s, s)
        glNormal3f(1, 0, 0); glVertex3f(s, -s, -s); glVertex3f(s, s, -s); glVertex3f(s, s, s); glVertex3f(s, -s, s)
        glNormal3f(-1, 0, 0); glVertex3f(-s, -s, -s); glVertex3f(-s, -s, s); glVertex3f(-s, s, s); glVertex3f(-s, s, -s)
        glEnd()
    
    def draw_blocks(self):
        for block in self.blocks:
            glPushMatrix()
            glTranslatef(*block['position'])
            glColor3fv(block['color'])
            
            if block['type'] == 'building' and block.get('asset_type'):
                self.draw_building_part(block['asset_type'], block['size'])
            elif block['type'] == 'city' and block.get('asset_type'):
                self.draw_city_asset(block['asset_type'], block['size'])
            elif block['type'] == 'sphere':
                quadric = gluNewQuadric()
                gluSphere(quadric, block['size'][0], 20, 20)
                gluDeleteQuadric(quadric)
            else:
                size = block['size'][0] if len(block['size']) == 1 else block['size'][0]
                self.draw_cube(size)
            
            glPopMatrix()
    
    def draw_building_part(self, part_name, size):
        """Draw specific 3D shape for each building part"""
        if part_name == 'wall':
            self.draw_wall(size)
        elif part_name == 'window':
            self.draw_window(size)
        elif part_name == 'door':
            self.draw_door(size)
        elif part_name == 'roof':
            self.draw_roof(size)
        elif part_name == 'floor':
            self.draw_floor(size)
        elif part_name == 'column':
            self.draw_column(size)
        elif part_name == 'stairs':
            self.draw_stairs(size)
        elif part_name == 'balcony':
            self.draw_balcony(size)
        else:
            self.draw_cube(size[0])
    
    def draw_wall(self, size):
        """Draw a thin, tall wall"""
        w, h, d = 2.0, 2.5, 0.3
        glBegin(GL_QUADS)
        # Front
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, 0, d/2); glVertex3f(w/2, 0, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(-w/2, h, d/2)
        # Back
        glNormal3f(0, 0, -1)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(-w/2, h, -d/2)
        glVertex3f(w/2, h, -d/2); glVertex3f(w/2, 0, -d/2)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(w/2, 0, -d/2)
        glVertex3f(w/2, 0, d/2); glVertex3f(-w/2, 0, d/2)
        # Left
        glNormal3f(-1, 0, 0)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(-w/2, 0, d/2)
        glVertex3f(-w/2, h, d/2); glVertex3f(-w/2, h, -d/2)
        # Right
        glNormal3f(1, 0, 0)
        glVertex3f(w/2, 0, -d/2); glVertex3f(w/2, h, -d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, 0, d/2)
        glEnd()
    
    def draw_window(self, size):
        """Draw a window with frame"""
        w, h, d = 1.5, 1.8, 0.2
        frame_thickness = 0.1
        
        # Window frame (darker)
        glColor3f(0.4, 0.3, 0.2)
        glBegin(GL_QUADS)
        # Outer frame
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, 0, d/2); glVertex3f(w/2, 0, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(-w/2, h, d/2)
        glEnd()
        
        # Glass pane (lighter blue-ish)
        glColor3f(0.6, 0.8, 0.9)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2+frame_thickness, frame_thickness, d/2+0.01)
        glVertex3f(w/2-frame_thickness, frame_thickness, d/2+0.01)
        glVertex3f(w/2-frame_thickness, h-frame_thickness, d/2+0.01)
        glVertex3f(-w/2+frame_thickness, h-frame_thickness, d/2+0.01)
        glEnd()
        
        # Cross bars
        glColor3f(0.4, 0.3, 0.2)
        glBegin(GL_QUADS)
        # Vertical bar
        glVertex3f(-0.05, frame_thickness, d/2+0.02)
        glVertex3f(0.05, frame_thickness, d/2+0.02)
        glVertex3f(0.05, h-frame_thickness, d/2+0.02)
        glVertex3f(-0.05, h-frame_thickness, d/2+0.02)
        # Horizontal bar
        glVertex3f(-w/2+frame_thickness, h/2-0.05, d/2+0.02)
        glVertex3f(w/2-frame_thickness, h/2-0.05, d/2+0.02)
        glVertex3f(w/2-frame_thickness, h/2+0.05, d/2+0.02)
        glVertex3f(-w/2+frame_thickness, h/2+0.05, d/2+0.02)
        glEnd()
    
    def draw_door(self, size):
        """Draw a door with frame"""
        w, h, d = 1.2, 2.2, 0.15
        
        # Door frame
        glColor3f(0.35, 0.25, 0.15)
        glBegin(GL_QUADS)
        # Main door
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, 0, d/2); glVertex3f(w/2, 0, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(-w/2, h, d/2)
        glEnd()
        
        # Door panels (lighter)
        glColor3f(0.5, 0.4, 0.3)
        panel_margin = 0.15
        panel_height = (h - 3*panel_margin) / 2
        
        # Upper panel
        glBegin(GL_QUADS)
        glVertex3f(-w/2+panel_margin, h-panel_margin-panel_height, d/2+0.01)
        glVertex3f(w/2-panel_margin, h-panel_margin-panel_height, d/2+0.01)
        glVertex3f(w/2-panel_margin, h-panel_margin, d/2+0.01)
        glVertex3f(-w/2+panel_margin, h-panel_margin, d/2+0.01)
        
        # Lower panel
        glVertex3f(-w/2+panel_margin, panel_margin, d/2+0.01)
        glVertex3f(w/2-panel_margin, panel_margin, d/2+0.01)
        glVertex3f(w/2-panel_margin, panel_margin+panel_height, d/2+0.01)
        glVertex3f(-w/2+panel_margin, panel_margin+panel_height, d/2+0.01)
        glEnd()
        
        # Door knob
        glColor3f(0.8, 0.7, 0.1)
        glPushMatrix()
        glTranslatef(w/2-0.2, h/2, d/2+0.05)
        quadric = gluNewQuadric()
        gluSphere(quadric, 0.08, 10, 10)
        gluDeleteQuadric(quadric)
        glPopMatrix()
    
    def draw_roof(self, size):
        """Draw a triangular roof"""
        w, h, d = 2.5, 1.5, 2.0
        
        glBegin(GL_TRIANGLES)
        # Front triangle
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, 0, d/2); glVertex3f(w/2, 0, d/2); glVertex3f(0, h, d/2)
        # Back triangle
        glNormal3f(0, 0, -1)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(0, h, -d/2); glVertex3f(w/2, 0, -d/2)
        glEnd()
        
        glBegin(GL_QUADS)
        # Left slope
        glNormal3f(-0.6, 0.8, 0)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(-w/2, 0, d/2)
        glVertex3f(0, h, d/2); glVertex3f(0, h, -d/2)
        # Right slope
        glNormal3f(0.6, 0.8, 0)
        glVertex3f(w/2, 0, -d/2); glVertex3f(0, h, -d/2)
        glVertex3f(0, h, d/2); glVertex3f(w/2, 0, d/2)
        glEnd()
    
    def draw_floor(self, size):
        """Draw a flat floor tile"""
        w, h, d = 2.0, 0.2, 2.0
        
        glBegin(GL_QUADS)
        # Top surface
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h/2, -d/2); glVertex3f(-w/2, h/2, d/2)
        glVertex3f(w/2, h/2, d/2); glVertex3f(w/2, h/2, -d/2)
        # Bottom surface
        glNormal3f(0, -1, 0)
        glVertex3f(-w/2, -h/2, -d/2); glVertex3f(w/2, -h/2, -d/2)
        glVertex3f(w/2, -h/2, d/2); glVertex3f(-w/2, -h/2, d/2)
        # Sides
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, -h/2, d/2); glVertex3f(w/2, -h/2, d/2)
        glVertex3f(w/2, h/2, d/2); glVertex3f(-w/2, h/2, d/2)
        
        glNormal3f(0, 0, -1)
        glVertex3f(-w/2, -h/2, -d/2); glVertex3f(-w/2, h/2, -d/2)
        glVertex3f(w/2, h/2, -d/2); glVertex3f(w/2, -h/2, -d/2)
        
        glNormal3f(-1, 0, 0)
        glVertex3f(-w/2, -h/2, -d/2); glVertex3f(-w/2, -h/2, d/2)
        glVertex3f(-w/2, h/2, d/2); glVertex3f(-w/2, h/2, -d/2)
        
        glNormal3f(1, 0, 0)
        glVertex3f(w/2, -h/2, -d/2); glVertex3f(w/2, h/2, -d/2)
        glVertex3f(w/2, h/2, d/2); glVertex3f(w/2, -h/2, d/2)
        glEnd()
    
    def draw_column(self, size):
        """Draw a tall cylindrical column"""
        radius = 0.3
        height = 3.0
        slices = 16
        
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        quadric = gluNewQuadric()
        gluCylinder(quadric, radius, radius, height, slices, 1)
        
        # Top cap
        glPushMatrix()
        glTranslatef(0, 0, height)
        gluDisk(quadric, 0, radius, slices, 1)
        glPopMatrix()
        
        # Bottom cap
        glRotatef(180, 1, 0, 0)
        gluDisk(quadric, 0, radius, slices, 1)
        
        gluDeleteQuadric(quadric)
        glPopMatrix()
    
    def draw_stairs(self, size):
        """Draw a staircase with 5 steps"""
        step_count = 5
        step_width = 1.5
        step_depth = 0.4
        step_height = 0.3
        
        for i in range(step_count):
            glPushMatrix()
            glTranslatef(0, i * step_height, -i * step_depth)
            
            # Draw each step
            glBegin(GL_QUADS)
            h = step_height
            w = step_width
            d = step_depth
            
            # Top
            glNormal3f(0, 1, 0)
            glVertex3f(-w/2, h/2, -d/2); glVertex3f(-w/2, h/2, d/2)
            glVertex3f(w/2, h/2, d/2); glVertex3f(w/2, h/2, -d/2)
            
            # Front
            glNormal3f(0, 0, 1)
            glVertex3f(-w/2, -h/2, d/2); glVertex3f(w/2, -h/2, d/2)
            glVertex3f(w/2, h/2, d/2); glVertex3f(-w/2, h/2, d/2)
            
            # Sides
            glNormal3f(-1, 0, 0)
            glVertex3f(-w/2, -h/2, -d/2); glVertex3f(-w/2, -h/2, d/2)
            glVertex3f(-w/2, h/2, d/2); glVertex3f(-w/2, h/2, -d/2)
            
            glNormal3f(1, 0, 0)
            glVertex3f(w/2, -h/2, -d/2); glVertex3f(w/2, h/2, -d/2)
            glVertex3f(w/2, h/2, d/2); glVertex3f(w/2, -h/2, d/2)
            
            glEnd()
            glPopMatrix()
    
    def draw_balcony(self, size):
        """Draw a balcony platform with railing"""
        w, h, d = 2.0, 0.15, 1.5
        
        # Platform
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        
        glNormal3f(0, -1, 0)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(w/2, 0, -d/2)
        glVertex3f(w/2, 0, d/2); glVertex3f(-w/2, 0, d/2)
        glEnd()
        
        # Railings
        rail_height = 1.0
        rail_thickness = 0.05
        
        # Front railing
        glBegin(GL_QUADS)
        # Top rail
        glVertex3f(-w/2, h+rail_height, d/2)
        glVertex3f(w/2, h+rail_height, d/2)
        glVertex3f(w/2, h+rail_height-rail_thickness, d/2)
        glVertex3f(-w/2, h+rail_height-rail_thickness, d/2)
        
        # Left post
        glVertex3f(-w/2, h, d/2)
        glVertex3f(-w/2+rail_thickness, h, d/2)
        glVertex3f(-w/2+rail_thickness, h+rail_height, d/2)
        glVertex3f(-w/2, h+rail_height, d/2)
        
        # Right post
        glVertex3f(w/2-rail_thickness, h, d/2)
        glVertex3f(w/2, h, d/2)
        glVertex3f(w/2, h+rail_height, d/2)
        glVertex3f(w/2-rail_thickness, h+rail_height, d/2)
        glEnd()
    
    def draw_city_asset(self, asset_name, size):
        """Draw specific 3D shape for each city asset"""
        if asset_name == 'road':
            self.draw_road(size)
        elif asset_name == 'apartment':
            self.draw_apartment(size)
        elif asset_name == 'house':
            self.draw_house(size)
        elif asset_name == 'skyscraper':
            self.draw_skyscraper(size)
        elif asset_name == 'shop':
            self.draw_shop(size)
        elif asset_name == 'streetlight':
            self.draw_streetlight(size)
        elif asset_name == 'bench':
            self.draw_bench(size)
        elif asset_name == 'tree':
            self.draw_tree(size)
        elif asset_name == 'grass':
            self.draw_grass(size)
        elif asset_name == 'fountain':
            self.draw_fountain(size)
        elif asset_name == 'car':
            self.draw_car(size)
        elif asset_name == 'person':
            self.draw_person(size)
        elif asset_name == 'sun':
            self.draw_sun(size)
        else:
            self.draw_cube(size[0])
    
    def draw_road(self, size):
        """Draw a road segment"""
        w, h, d = size
        glBegin(GL_QUADS)
        # Top surface with road markings
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        glEnd()
        # Road lines (white)
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS)
        glVertex3f(-0.1, h+0.01, -d/2); glVertex3f(-0.1, h+0.01, d/2)
        glVertex3f(0.1, h+0.01, d/2); glVertex3f(0.1, h+0.01, -d/2)
        glEnd()
    
    def draw_apartment(self, size):
        """Draw an apartment building"""
        w, h, d = size
        # Main building
        self.draw_cube(w)
        # Windows (darker)
        glColor3f(0.3, 0.5, 0.7)
        for floor in range(5):
            for col in range(3):
                y_pos = -h/2 + 0.5 + floor * 0.8
                x_pos = -w/2 + 0.5 + col * 0.8
                glPushMatrix()
                glTranslatef(x_pos, y_pos, w/2 + 0.01)
                glBegin(GL_QUADS)
                glVertex3f(-0.2, -0.3, 0); glVertex3f(0.2, -0.3, 0)
                glVertex3f(0.2, 0.3, 0); glVertex3f(-0.2, 0.3, 0)
                glEnd()
                glPopMatrix()
    
    def draw_house(self, size):
        """Draw a residential house"""
        w, h, d = size
        # Base (cube)
        glPushMatrix()
        glTranslatef(0, -h*0.2, 0)
        self.draw_cube(w * 0.8)
        glPopMatrix()
        # Roof (pyramid)
        glBegin(GL_TRIANGLES)
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h/2, -d/2); glVertex3f(w/2, h/2, -d/2); glVertex3f(0, h, 0)
        glVertex3f(-w/2, h/2, d/2); glVertex3f(0, h, 0); glVertex3f(w/2, h/2, d/2)
        glVertex3f(-w/2, h/2, -d/2); glVertex3f(0, h, 0); glVertex3f(-w/2, h/2, d/2)
        glVertex3f(w/2, h/2, -d/2); glVertex3f(w/2, h/2, d/2); glVertex3f(0, h, 0)
        glEnd()
    
    def draw_skyscraper(self, size):
        """Draw a tall skyscraper"""
        w, h, d = size
        # Main tower (elongated cube) - draw all 4 sides + top + bottom
        glBegin(GL_QUADS)
        # Front
        glNormal3f(0, 0, 1)
        glVertex3f(-w/2, 0, d/2); glVertex3f(w/2, 0, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(-w/2, h, d/2)
        # Back
        glNormal3f(0, 0, -1)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(-w/2, h, -d/2)
        glVertex3f(w/2, h, -d/2); glVertex3f(w/2, 0, -d/2)
        # Left
        glNormal3f(-1, 0, 0)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(-w/2, 0, d/2)
        glVertex3f(-w/2, h, d/2); glVertex3f(-w/2, h, -d/2)
        # Right
        glNormal3f(1, 0, 0)
        glVertex3f(w/2, 0, -d/2); glVertex3f(w/2, h, -d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, 0, d/2)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(w/2, 0, -d/2)
        glVertex3f(w/2, 0, d/2); glVertex3f(-w/2, 0, d/2)
        glEnd()
    
    def draw_shop(self, size):
        """Draw a small shop"""
        w, h, d = size
        self.draw_cube(w)
        # Awning
        glColor3f(0.9, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex3f(-w/2-0.2, h/2, d/2); glVertex3f(w/2+0.2, h/2, d/2)
        glVertex3f(w/2+0.2, h/2-0.3, d/2+0.3); glVertex3f(-w/2-0.2, h/2-0.3, d/2+0.3)
        glEnd()
    
    def draw_streetlight(self, size):
        """Draw a street light"""
        w, h, d = size
        # Pole
        quadric = gluNewQuadric()
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, 0.1, 0.1, h, 8, 1)
        glPopMatrix()
        # Light (sphere on top)
        glPushMatrix()
        glTranslatef(0, h, 0)
        gluSphere(quadric, 0.3, 10, 10)
        glPopMatrix()
        gluDeleteQuadric(quadric)
    
    def draw_bench(self, size):
        """Draw a park bench"""
        w, h, d = size
        # Seat
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        glEnd()
        # Back rest
        glBegin(GL_QUADS)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h+0.4, -d/2-0.1)
        glVertex3f(w/2, h+0.4, -d/2-0.1); glVertex3f(w/2, h, -d/2)
        glEnd()
    
    def draw_tree(self, size):
        """Draw a tree"""
        w, h, d = size
        # Trunk (brown)
        glColor3f(0.4, 0.25, 0.1)
        quadric = gluNewQuadric()
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, 0.2, 0.15, h*0.6, 8, 1)
        glPopMatrix()
        # Foliage (green sphere)
        glColor3f(0.13, 0.55, 0.13)
        glPushMatrix()
        glTranslatef(0, h*0.7, 0)
        gluSphere(quadric, 0.8, 12, 12)
        glPopMatrix()
        gluDeleteQuadric(quadric)
    
    def draw_grass(self, size):
        """Draw grass patch"""
        w, h, d = size
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        glEnd()
    
    def draw_fountain(self, size):
        """Draw a fountain"""
        w, h, d = size
        # Base
        quadric = gluNewQuadric()
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, w/2, w/2, h*0.3, 16, 1)
        glPopMatrix()
        # Central column
        glPushMatrix()
        glTranslatef(0, h*0.3, 0)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, 0.2, 0.2, h*0.5, 8, 1)
        glPopMatrix()
        # Top sphere
        glPushMatrix()
        glTranslatef(0, h, 0)
        gluSphere(quadric, 0.4, 12, 12)
        glPopMatrix()
        gluDeleteQuadric(quadric)
    
    def draw_car(self, size):
        """Draw a simple car"""
        w, h, d = size
        # Body
        glBegin(GL_QUADS)
        # Bottom
        glVertex3f(-w/2, 0, -d/2); glVertex3f(w/2, 0, -d/2)
        glVertex3f(w/2, 0, d/2); glVertex3f(-w/2, 0, d/2)
        # Top
        glVertex3f(-w/2, h, -d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(w/2, h, -d/2)
        # Sides
        glVertex3f(-w/2, 0, d/2); glVertex3f(w/2, 0, d/2)
        glVertex3f(w/2, h, d/2); glVertex3f(-w/2, h, d/2)
        glVertex3f(-w/2, 0, -d/2); glVertex3f(-w/2, h, -d/2)
        glVertex3f(w/2, h, -d/2); glVertex3f(w/2, 0, -d/2)
        glEnd()
        # Wheels (black)
        glColor3f(0.1, 0.1, 0.1)
        quadric = gluNewQuadric()
        for pos in [(-w/3, 0.2, d/2+0.1), (w/3, 0.2, d/2+0.1), (-w/3, 0.2, -d/2-0.1), (w/3, 0.2, -d/2-0.1)]:
            glPushMatrix()
            glTranslatef(*pos)
            gluSphere(quadric, 0.2, 8, 8)
            glPopMatrix()
        gluDeleteQuadric(quadric)
    
    def draw_person(self, size):
        """Draw a simple person figure"""
        w, h, d = size
        quadric = gluNewQuadric()
        # Body (cylinder)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, w/2, w/2, h*0.6, 8, 1)
        glPopMatrix()
        # Head (sphere)
        glPushMatrix()
        glTranslatef(0, h*0.85, 0)
        gluSphere(quadric, w/2, 10, 10)
        glPopMatrix()
        gluDeleteQuadric(quadric)
    
    def draw_sun(self, size):
        """Draw a bright sun with rays"""
        w, h, d = size
        quadric = gluNewQuadric()
        
        # Enable emission for glowing effect
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.8, 0.7, 0.2, 1.0))
        
        # Main sun sphere (bright yellow/orange)
        glPushMatrix()
        gluSphere(quadric, w, 20, 20)
        glPopMatrix()
        
        # Reset emission
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
        
        # Sun rays (lines radiating outward)
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 0.95, 0.3)
        glLineWidth(3)
        glBegin(GL_LINES)
        for angle in range(0, 360, 30):
            rad = angle * 3.14159 / 180
            # Horizontal rays
            glVertex3f(w * 1.2 * math.cos(rad), 0, w * 1.2 * math.sin(rad))
            glVertex3f(w * 1.8 * math.cos(rad), 0, w * 1.8 * math.sin(rad))
            # Vertical rays
            glVertex3f(0, w * 1.2 * math.cos(rad), w * 1.2 * math.sin(rad))
            glVertex3f(0, w * 1.8 * math.cos(rad), w * 1.8 * math.sin(rad))
        glEnd()
        glEnable(GL_LIGHTING)
        
        gluDeleteQuadric(quadric)
    
    def _update_dynamic_lighting(self):
        """Update lighting based on sun positions"""
        # Find all sun objects
        sun_blocks = [b for b in self.blocks if b.get('asset_type') == 'sun']
        
        # Disable additional lights first
        for i in range(1, 8):
            glDisable(GL_LIGHT0 + i)
        
        # Enable lights for each sun (up to 7 additional lights)
        for i, sun in enumerate(sun_blocks[:7]):
            light_id = GL_LIGHT0 + i + 1  # Use LIGHT1-LIGHT7
            sun_pos = sun['position']
            
            glEnable(light_id)
            # Position the light at the sun's location
            glLightfv(light_id, GL_POSITION, (sun_pos[0], sun_pos[1], sun_pos[2], 1.0))
            # Bright yellow/orange light
            glLightfv(light_id, GL_AMBIENT, (0.3, 0.25, 0.1, 1.0))
            glLightfv(light_id, GL_DIFFUSE, (1.0, 0.9, 0.5, 1.0))
            glLightfv(light_id, GL_SPECULAR, (1.0, 1.0, 0.8, 1.0))
    
    def render_3d_scene(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Update cursor position with smooth interpolation
        for i in range(3):
            self.cursor_pos[i] += (self.target_pos[i] - self.cursor_pos[i]) * 0.15
        
        # Snap cursor to grid if enabled (for visual feedback)
        if self.snap_to_grid:
            self.display_cursor_pos = [
                round(self.cursor_pos[0] / self.grid_size) * self.grid_size,
                self.placement_height * self.grid_size,
                round(self.cursor_pos[2] / self.grid_size) * self.grid_size
            ]
        else:
            self.display_cursor_pos = self.cursor_pos.copy()
        
        # Always update camera rotation and zoom smoothly
        self.camera_rotation_y += (self.target_camera_rotation_y - self.camera_rotation_y) * 0.1
        self.camera_rotation_x += (self.target_camera_rotation_x - self.camera_rotation_x) * 0.1
        self.camera_distance += (self.target_camera_distance - self.camera_distance) * 0.1
        
        # Apply camera position with current rotation and zoom
        # Camera looks at current zone position
        zone_pos = self.zone_offset
        cam_x = zone_pos[0] + math.sin(self.camera_rotation_y) * self.camera_distance
        cam_z = zone_pos[2] + math.cos(self.camera_rotation_y) * self.camera_distance
        cam_y = 5 + math.sin(self.camera_rotation_x) * 5
        gluLookAt(cam_x, cam_y, cam_z, zone_pos[0], 0, zone_pos[2], 0, 1, 0)
        
        # Dynamic lighting from sun objects
        self._update_dynamic_lighting()
        
        self.draw_grid()
        self.draw_blocks()
        # Always show cursor (even during rotation for better visibility)
        self.draw_cursor()
    
    def draw_ui_overlay(self, camera_frame):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Left panel background
        glColor4f(0.059, 0.090, 0.165, 0.85)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(250, 0)
        glVertex2f(250, self.screen_height)
        glVertex2f(0, self.screen_height)
        glEnd()
        
        # Camera preview
        camera_frame_rgb = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
        camera_preview = cv2.resize(camera_frame_rgb, (320, 240))
        # Don't flip - let texture coordinates handle orientation
        
        cam_x = self.screen_width - 330
        cam_y = self.screen_height - 280
        
        # Camera border
        glColor4f(0.059, 0.090, 0.165, 0.9)
        glBegin(GL_QUADS)
        glVertex2f(cam_x - 5, cam_y - 25)
        glVertex2f(cam_x + 325, cam_y - 25)
        glVertex2f(cam_x + 325, cam_y + 245)
        glVertex2f(cam_x - 5, cam_y + 245)
        glEnd()
        
        glColor4f(0.22, 0.74, 0.97, 1.0)
        glLineWidth(3)
        glBegin(GL_LINE_LOOP)
        glVertex2f(cam_x - 5, cam_y - 25)
        glVertex2f(cam_x + 325, cam_y - 25)
        glVertex2f(cam_x + 325, cam_y + 245)
        glVertex2f(cam_x - 5, cam_y + 245)
        glEnd()
        
        # Draw camera frame as texture
        glEnable(GL_TEXTURE_2D)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        texture_data = camera_preview.tobytes()
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 320, 240, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(cam_x, cam_y)
        glTexCoord2f(1, 0); glVertex2f(cam_x + 320, cam_y)
        glTexCoord2f(1, 1); glVertex2f(cam_x + 320, cam_y + 240)
        glTexCoord2f(0, 1); glVertex2f(cam_x, cam_y + 240)
        glEnd()
        
        glDeleteTextures([texture_id])
        glDisable(GL_TEXTURE_2D)
        
        # Bottom help panel
        glColor4f(0.059, 0.090, 0.165, 0.85)
        glBegin(GL_QUADS)
        glVertex2f(0, self.screen_height - 150)
        glVertex2f(600, self.screen_height - 150)
        glVertex2f(600, self.screen_height)
        glVertex2f(0, self.screen_height)
        glEnd()
        
        # Render text using pygame surfaces converted to OpenGL
        y_offset = 10
        
        # Mode title with better styling
        self._draw_text("MODE:", 10, y_offset, self.font_small, (148, 163, 184))
        y_offset += 25
        
        # Mode switching buttons - larger and more prominent
        mode_buttons_data = [
            {'key': '1', 'mode': 'free', 'label': 'FREE', 'icon': '🆓'},
            {'key': '2', 'mode': 'building', 'label': 'BUILD', 'icon': '🏗️'},
            {'key': '3', 'mode': 'city', 'label': 'CITY', 'icon': '🏙️'},
            {'key': '4', 'mode': 'solar', 'label': 'SPACE', 'icon': '🌌'}
        ]
        
        # Clear mode buttons list
        self.mode_buttons = []
        
        mode_btn_x = 10
        mode_btn_width = 55
        mode_btn_height = 50
        mode_btn_spacing = 8
        
        for btn_data in mode_buttons_data:
            is_active = self.build_mode == btn_data['mode']
            is_hovered = False
            if self.hovered_button and self.hovered_button.get('type') == 'mode_switch':
                is_hovered = self.hovered_button.get('value') == btn_data['mode']
            
            # Button background with gradient effect
            if is_active:
                bg_color = (0.22, 0.74, 0.97, 1.0)
                text_color = (255, 255, 255)
                icon_y_offset = 8
            elif is_hovered:
                bg_color = (0.35, 0.40, 0.50, 1.0)
                text_color = (255, 255, 255)
                icon_y_offset = 8
            else:
                bg_color = (0.118, 0.161, 0.231, 0.9)
                text_color = (148, 163, 184)
                icon_y_offset = 8
            
            glColor4f(*bg_color)
            glBegin(GL_QUADS)
            glVertex2f(mode_btn_x, y_offset)
            glVertex2f(mode_btn_x + mode_btn_width, y_offset)
            glVertex2f(mode_btn_x + mode_btn_width, y_offset + mode_btn_height)
            glVertex2f(mode_btn_x, y_offset + mode_btn_height)
            glEnd()
            
            # Button border - thicker for active
            border_color = (0.22, 0.74, 0.97, 1.0) if is_active else (0.39, 0.45, 0.55, 1.0)
            glColor4f(*border_color)
            glLineWidth(4 if is_active else 2)
            glBegin(GL_LINE_LOOP)
            glVertex2f(mode_btn_x, y_offset)
            glVertex2f(mode_btn_x + mode_btn_width, y_offset)
            glVertex2f(mode_btn_x + mode_btn_width, y_offset + mode_btn_height)
            glVertex2f(mode_btn_x, y_offset + mode_btn_height)
            glEnd()
            
            # Icon centered at top
            self._draw_text(btn_data['icon'], mode_btn_x + 15, y_offset + icon_y_offset, self.font, text_color)
            # Key number bottom center (smaller)
            self._draw_text(f"{btn_data['key']}", mode_btn_x + 22, y_offset + 32, self.font_tiny, text_color)
            
            # Store button for click detection
            btn_rect = pygame.Rect(mode_btn_x, y_offset, mode_btn_width, mode_btn_height)
            self.mode_buttons.append({
                'rect': btn_rect,
                'value': btn_data['mode'],
                'type': 'mode_switch'
            })
            
            mode_btn_x += mode_btn_width + mode_btn_spacing
        
        y_offset += 60
        
        # Separator line
        glColor4f(0.39, 0.45, 0.55, 0.5)
        glLineWidth(2)
        glBegin(GL_LINES)
        glVertex2f(10, y_offset)
        glVertex2f(240, y_offset)
        glEnd()
        y_offset += 15
        
        if self.detection_confidence > 0:
            status_color = (34, 197, 94) if self.detection_confidence > 0.6 else (239, 68, 68)
            status_text = "✋ Hand Detected" if not self.is_rotating_camera else "🔄 Rotate & Zoom Mode"
        else:
            status_color = (239, 68, 68)
            status_text = "❌ No Hand Detected"
        self._draw_text(status_text, 10, y_offset, self.font_small, status_color)
        y_offset += 25
        
        # Show zoom level
        zoom_pct = int((25 - self.camera_distance) / 20 * 100)
        self._draw_text(f"Zoom: {zoom_pct}%", 10, y_offset, self.font_small, (148, 163, 184))
        y_offset += 5
        
        lighting_color = {"Good": (34, 197, 94), "Fair": (234, 179, 8), "Poor": (239, 68, 68)}.get(self.lighting_quality, (255, 255, 255))
        self._draw_text(f"Light: {self.lighting_quality} ({int(self.avg_brightness)})", 10, y_offset, self.font_small, lighting_color)
        y_offset += 30
        
        # Grid and height info
        grid_status = "✅ ON" if self.snap_to_grid else "❌ OFF"
        grid_color = (34, 197, 94) if self.snap_to_grid else (148, 163, 184)
        self._draw_text(f"Grid Snap [{grid_status}]", 10, y_offset, self.font_small, grid_color)
        y_offset += 20
        
        height_text = f"Height: Lvl {self.placement_height} ({self.placement_height * self.grid_size:.0f}m)"
        self._draw_text(height_text, 10, y_offset, self.font_small, (255, 200, 50))
        y_offset += 25
        
        # Zone info and button
        zone_name = config.ZONES[self.current_zone]['name']
        self._draw_text(f"Zone: {zone_name}", 10, y_offset, self.font_small, (148, 163, 184))
        y_offset += 30
        
        # ZONES button (always visible)
        zones_button_rect = pygame.Rect(10, y_offset, 230, 45)
        is_zones_hovered = self.hovered_button and self.hovered_button.get('type') == 'zones_opener'
        zones_bg = (0.22, 0.74, 0.97, 1.0) if is_zones_hovered else (0.118, 0.161, 0.231, 0.9)
        
        glColor4f(*zones_bg)
        glBegin(GL_QUADS)
        glVertex2f(zones_button_rect.left, zones_button_rect.top)
        glVertex2f(zones_button_rect.right, zones_button_rect.top)
        glVertex2f(zones_button_rect.right, zones_button_rect.bottom)
        glVertex2f(zones_button_rect.left, zones_button_rect.bottom)
        glEnd()
        
        glColor4f(0.22, 0.74, 0.97, 1.0)
        glLineWidth(3)
        glBegin(GL_LINE_LOOP)
        glVertex2f(zones_button_rect.left, zones_button_rect.top)
        glVertex2f(zones_button_rect.right, zones_button_rect.top)
        glVertex2f(zones_button_rect.right, zones_button_rect.bottom)
        glVertex2f(zones_button_rect.left, zones_button_rect.bottom)
        glEnd()
        
        zones_text_color = (0, 0, 0) if is_zones_hovered else (56, 189, 248)
        self._draw_text("📍 TELEPORT TO ZONES", zones_button_rect.centerx - 85, zones_button_rect.centery - 10, self.font, zones_text_color)
        
        # Store zones button for click detection
        if not hasattr(self, 'zones_opener_button'):
            self.zones_opener_button = {'rect': zones_button_rect, 'type': 'zones_opener'}
        else:
            self.zones_opener_button['rect'] = zones_button_rect
        
        y_offset += 70  # Increased spacing to prevent overlap
        
        if self.build_mode == 'building':
            # Section header with icon
            self._draw_text("🏗️ BUILDING PARTS", 10, y_offset, self.font, (56, 189, 248))
            y_offset += 25
            
            # Selected item display
            selected_name = config.BUILDING_PARTS[self.selected_building_part]['name']
            self._draw_text(f"Selected: {selected_name}", 10, y_offset, self.font_small, (255, 255, 0))
            y_offset += 30
            
            # Separator line
            glColor4f(0.39, 0.45, 0.55, 1.0)
            glLineWidth(2)
            glBegin(GL_LINES)
            glVertex2f(10, y_offset)
            glVertex2f(240, y_offset)
            glEnd()
            y_offset += 15
            
            for button in self.ui_buttons:
                is_selected = button['value'] == self.selected_building_part
                is_hovered = self.hovered_button == button
                if is_selected:
                    bg_color = (0.22, 0.74, 0.97, 1.0)
                    text_color = (0, 0, 0)
                elif is_hovered:
                    bg_color = (0.39, 0.45, 0.55, 1.0)
                    text_color = (255, 255, 255)
                else:
                    bg_color = (0.118, 0.161, 0.231, 0.9)
                    text_color = (203, 213, 225)
                
                rect = button['rect']
                glColor4f(*bg_color)
                glBegin(GL_QUADS)
                glVertex2f(rect.left, rect.top)
                glVertex2f(rect.right, rect.top)
                glVertex2f(rect.right, rect.bottom)
                glVertex2f(rect.left, rect.bottom)
                glEnd()
                
                glColor4f(0.59, 0.59, 0.59, 1.0)
                glLineWidth(2)
                glBegin(GL_LINE_LOOP)
                glVertex2f(rect.left, rect.top)
                glVertex2f(rect.right, rect.top)
                glVertex2f(rect.right, rect.bottom)
                glVertex2f(rect.left, rect.bottom)
                glEnd()
                
                self._draw_text(f"{button['icon']} {button['text']}", rect.centerx - 35, rect.centery - 8, self.font_tiny, text_color)
        
        elif self.build_mode == 'city':
            # Section header with icon
            self._draw_text("🏙️ CITY BUILDER", 10, y_offset, self.font, (56, 189, 248))
            y_offset += 25
            
            # Selected item display
            selected_name = config.CITY_ASSETS[self.selected_city_asset]['name']
            self._draw_text(f"Selected: {selected_name}", 10, y_offset, self.font_small, (255, 255, 0))
            y_offset += 30
            
            # Separator line
            glColor4f(0.39, 0.45, 0.55, 1.0)
            glLineWidth(2)
            glBegin(GL_LINES)
            glVertex2f(10, y_offset)
            glVertex2f(240, y_offset)
            glEnd()
            y_offset += 15
            
            for button in self.ui_buttons:
                is_selected = button['value'] == self.selected_city_asset
                is_hovered = self.hovered_button == button
                if is_selected:
                    bg_color = (0.22, 0.74, 0.97, 1.0)
                    text_color = (0, 0, 0)
                elif is_hovered:
                    bg_color = (0.39, 0.45, 0.55, 1.0)
                    text_color = (255, 255, 255)
                else:
                    bg_color = (0.118, 0.161, 0.231, 0.9)
                    text_color = (203, 213, 225)
                
                rect = button['rect']
                glColor4f(*bg_color)
                glBegin(GL_QUADS)
                glVertex2f(rect.left, rect.top)
                glVertex2f(rect.right, rect.top)
                glVertex2f(rect.right, rect.bottom)
                glVertex2f(rect.left, rect.bottom)
                glEnd()
                
                glColor4f(0.59, 0.59, 0.59, 1.0)
                glLineWidth(2)
                glBegin(GL_LINE_LOOP)
                glVertex2f(rect.left, rect.top)
                glVertex2f(rect.right, rect.top)
                glVertex2f(rect.right, rect.bottom)
                glVertex2f(rect.left, rect.bottom)
                glEnd()
                
                self._draw_text(f"{button['icon']} {button['text']}", rect.centerx - 35, rect.centery - 8, self.font_tiny, text_color)
        
        elif self.build_mode == 'solar':
            # Section header with icon
            self._draw_text("🌌 SOLAR SYSTEM", 10, y_offset, self.font, (56, 189, 248))
            y_offset += 25
            
            # Selected item display
            selected_name = config.SOLAR_OBJECTS[self.selected_solar_object]['name']
            self._draw_text(f"Selected: {selected_name}", 10, y_offset, self.font_small, (255, 255, 0))
            y_offset += 30
            
            # Separator line
            glColor4f(0.39, 0.45, 0.55, 1.0)
            glLineWidth(2)
            glBegin(GL_LINES)
            glVertex2f(10, y_offset)
            glVertex2f(240, y_offset)
            glEnd()
            y_offset += 15
            
            for button in self.ui_buttons:
                is_selected = button['value'] == self.selected_solar_object
                is_hovered = self.hovered_button == button
                if is_selected:
                    bg_color = (0.22, 0.74, 0.97, 1.0)
                    text_color = (0, 0, 0)
                elif is_hovered:
                    bg_color = (0.39, 0.45, 0.55, 1.0)
                    text_color = (255, 255, 255)
                else:
                    bg_color = (0.118, 0.161, 0.231, 0.9)
                    text_color = (203, 213, 225)
                
                rect = button['rect']
                glColor4f(*bg_color)
                glBegin(GL_QUADS)
                glVertex2f(rect.left, rect.top)
                glVertex2f(rect.right, rect.top)
                glVertex2f(rect.right, rect.bottom)
                glVertex2f(rect.left, rect.bottom)
                glEnd()
                
                glColor4f(0.59, 0.59, 0.59, 1.0)
                glLineWidth(2)
                glBegin(GL_LINE_LOOP)
                glVertex2f(rect.left, rect.top)
                glVertex2f(rect.right, rect.top)
                glVertex2f(rect.right, rect.bottom)
                glVertex2f(rect.left, rect.bottom)
                glEnd()
                
                self._draw_text(f"{button['icon']} {button['text']}", rect.centerx - 35, rect.centery - 8, self.font_tiny, text_color)
        
        # Camera label
        self._draw_text("Camera Feed", cam_x, cam_y - 20, self.font_small, (255, 255, 255))
        
        # Bottom help text
        y_offset = self.screen_height - 165
        help_texts = ["CONTROLS:", "1 Hand: Index = Move | Pinch = Place", 
                     "2 Hands: Rotate | Zoom: Hands CLOSER = Zoom IN", 
                     "Keys: 1=Free 2=Building 3=City 4=Solar | Z=Zones | G=Grid C=Clear Q=Quit",
                     "↑↓ = Change Height | H=Grid Snap | J=Show Grid"]
        for text in help_texts:
            self._draw_text(text, 10, y_offset, self.font_small, (200, 200, 200))
            y_offset += 25
        
        # Zone selector overlay
        if self.show_zone_selector:
            self._draw_zone_selector()
        
        glDisable(GL_BLEND)
    
    def _draw_zone_selector(self):
        """Draw the zone selector overlay"""
        # Semi-transparent backdrop
        glColor4f(0, 0, 0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(self.screen_width, 0)
        glVertex2f(self.screen_width, self.screen_height)
        glVertex2f(0, self.screen_height)
        glEnd()
        
        # Main panel
        panel_width = 650
        panel_height = 550
        panel_x = (self.screen_width - panel_width) / 2
        panel_y = (self.screen_height - panel_height) / 2
        
        glColor4f(0.059, 0.090, 0.165, 0.95)
        glBegin(GL_QUADS)
        glVertex2f(panel_x, panel_y)
        glVertex2f(panel_x + panel_width, panel_y)
        glVertex2f(panel_x + panel_width, panel_y + panel_height)
        glVertex2f(panel_x, panel_y + panel_height)
        glEnd()
        
        # Panel border
        glColor4f(0.22, 0.74, 0.97, 1.0)
        glLineWidth(3)
        glBegin(GL_LINE_LOOP)
        glVertex2f(panel_x, panel_y)
        glVertex2f(panel_x + panel_width, panel_y)
        glVertex2f(panel_x + panel_width, panel_y + panel_height)
        glVertex2f(panel_x, panel_y + panel_height)
        glEnd()
        
        # Title
        self._draw_text("SELECT ZONE TO TELEPORT", panel_x + 20, panel_y + 20, self.font, (56, 189, 248))
        self._draw_text(f"Current: {config.ZONES[self.current_zone]['name']}", panel_x + 20, panel_y + 50, self.font_small, (34, 197, 94))
        
        # Zone colors matching the 3D world
        zone_colors = {
            'zone1': (0.3, 0.5, 0.9),   # Blue - Central Plaza
            'zone2': (0.9, 0.5, 0.3),   # Orange - East District
            'zone3': (0.5, 0.3, 0.9),   # Purple - West District
            'zone4': (0.3, 0.9, 0.3),   # Green - North Park
            'zone5': (0.9, 0.9, 0.3),   # Yellow - South Beach
            'zone6': (0.9, 0.3, 0.3),   # Red - NE Industrial
            'zone7': (0.3, 0.9, 0.9),   # Cyan - NW Residential
            'zone8': (0.5, 0.9, 0.5),   # Light Green - SE Harbor
            'zone9': (0.7, 0.5, 0.3)    # Brown - SW Mountain
        }
        
        # Build zone buttons in 3x3 grid
        self.zone_buttons = []
        button_size = 180
        button_spacing = 15
        grid_start_x = panel_x + (panel_width - (button_size * 3 + button_spacing * 2)) / 2
        grid_start_y = panel_y + 100
        
        # Zones arranged as they appear in 3D space
        # zone7 (-25, 25)  zone4 (0, 25)  zone6 (25, 25)   <- North (top row)
        # zone2 (-25, 0)   zone1 (0, 0)   zone3 (25, 0)    <- Center (middle row)
        # zone9 (-25, -25) zone5 (0, -25) zone8 (25, -25)  <- South (bottom row)
        zones_order = ['zone7', 'zone4', 'zone6',  # Top row (NW, North, NE)
                      'zone2', 'zone1', 'zone3',  # Middle row (West, Central, East)
                      'zone9', 'zone5', 'zone8']  # Bottom row (SW, South, SE)
        
        zone_icons = {
            'zone1': '🏛️', 'zone2': '🏙️', 'zone3': '🌆',
            'zone4': '🌳', 'zone5': '🏖️', 'zone6': '⚓',
            'zone7': '🏘️', 'zone8': '🏭', 'zone9': '⛰️'
        }
        
        for i, zone_id in enumerate(zones_order):
            row = i // 3
            col = i % 3
            x = grid_start_x + col * (button_size + button_spacing)
            y = grid_start_y + row * (button_size + button_spacing)
            
            zone_data = config.ZONES[zone_id]
            is_current = zone_id == self.current_zone
            is_hovered = self.hovered_button and self.hovered_button.get('value') == zone_id
            zone_color = zone_colors.get(zone_id, (0.3, 0.3, 0.3))
            
            # Color indicator bar at top of button
            glColor4f(*zone_color, 1.0)
            glBegin(GL_QUADS)
            glVertex2f(x, y)
            glVertex2f(x + button_size, y)
            glVertex2f(x + button_size, y + 25)
            glVertex2f(x, y + 25)
            glEnd()
            
            # Button background
            if is_current:
                bg_color = (0.22, 0.74, 0.97, 1.0)
            elif is_hovered:
                bg_color = (0.35, 0.40, 0.50, 1.0)
            else:
                bg_color = (0.118, 0.161, 0.231, 0.9)
            
            glColor4f(*bg_color)
            glBegin(GL_QUADS)
            glVertex2f(x, y + 25)
            glVertex2f(x + button_size, y + 25)
            glVertex2f(x + button_size, y + button_size)
            glVertex2f(x, y + button_size)
            glEnd()
            
            # Button border with zone color
            glColor4f(*zone_color, 1.0)
            glLineWidth(4 if is_current else 3)
            glBegin(GL_LINE_LOOP)
            glVertex2f(x, y)
            glVertex2f(x + button_size, y)
            glVertex2f(x + button_size, y + button_size)
            glVertex2f(x, y + button_size)
            glEnd()
            
            # Zone info
            text_color = (0, 0, 0) if is_current else (255, 255, 255)
            icon = zone_icons.get(zone_id, '📍')
            self._draw_text(icon, x + button_size/2 - 15, y + 35, self.font, (255, 255, 255))
            
            # Zone name (split into multiple lines if too long)
            name_parts = zone_data['name'].split()
            if len(name_parts) > 1:
                self._draw_text(name_parts[0], x + 10, y + 85, self.font_small, text_color)
                self._draw_text(' '.join(name_parts[1:]), x + 10, y + 105, self.font_small, text_color)
            else:
                self._draw_text(zone_data['name'], x + 10, y + 95, self.font_small, text_color)
            
            # Count blocks in zone
            blocks_count = sum(1 for b in self.blocks if b.get('zone') == zone_id)
            count_text = f"{blocks_count} objects"
            self._draw_text(count_text, x + 10, y + button_size - 30, self.font_tiny, text_color)
            
            # Add to clickable buttons
            self.zone_buttons.append({
                'rect': pygame.Rect(x, y, button_size, button_size),
                'value': zone_id,
                'type': 'zone'
            })
        
        # Close instruction
        self._draw_text("Press Z to close | Click zone to teleport", panel_x + 20, panel_y + panel_height - 30, self.font_small, (148, 163, 184))
    
    def _draw_text(self, text, x, y, font, color):
        """Helper to draw text using OpenGL"""
        text_surface = font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(), 
                     0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x, y)
        glTexCoord2f(1, 1); glVertex2f(x + text_surface.get_width(), y)
        glTexCoord2f(1, 0); glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())
        glTexCoord2f(0, 0); glVertex2f(x, y + text_surface.get_height())
        glEnd()
        
        glDeleteTextures([texture_id])
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse_click(event.pos)
                elif event.type == MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                elif event.type == KEYDOWN:
                    if event.key in [K_q, K_ESCAPE]:
                        running = False
                    elif event.key == K_g:
                        self.show_grid = not self.show_grid
                    elif event.key == K_c:
                        self.blocks.clear()
                        print("🗑️ Scene cleared")
                    elif event.key == K_z:
                        self.show_zone_selector = not self.show_zone_selector
                        print(f"📍 Zone Selector: {'ON' if self.show_zone_selector else 'OFF'}")
                    elif event.key == K_1:
                        self.build_mode = 'free'
                        self._build_ui_buttons()
                        print("🆓 Free Build Mode")
                    elif event.key == K_2:
                        self.build_mode = 'building'
                        self._build_ui_buttons()
                        print("🏗️ Building Mode")
                    elif event.key == K_3:
                        self.build_mode = 'city'
                        self._build_ui_buttons()
                        print("🏙️ City Builder Mode")
                    elif event.key == K_4:
                        self.build_mode = 'solar'
                        self._build_ui_buttons()
                        print("🌍 Solar System Mode")
                    elif event.key == K_UP:
                        # Increase height level
                        if self.placement_height < self.max_height_level:
                            self.placement_height += 1
                            print(f"⬆️ Height Level: {self.placement_height} ({self.placement_height * self.grid_size}m)")
                    elif event.key == K_DOWN:
                        # Decrease height level
                        if self.placement_height > 0:
                            self.placement_height -= 1
                            print(f"⬇️ Height Level: {self.placement_height} ({self.placement_height * self.grid_size}m)")
                    elif event.key == K_h:
                        # Toggle grid snapping
                        self.snap_to_grid = not self.snap_to_grid
                        print(f"🎯 Grid Snap: {'ON' if self.snap_to_grid else 'OFF'}")  
                    elif event.key == K_j:
                        # Toggle placement grid visibility
                        self.show_placement_grid = not self.show_placement_grid
                        print(f"🏛️ Placement Grid: {'ON' if self.show_placement_grid else 'OFF'}")
            
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Failed to capture frame")
                break
            
            frame = self.process_hand_tracking(frame)
            self.render_3d_scene()
            
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.screen_width, self.screen_height, 0, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            
            self.draw_ui_overlay(frame)
            
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            
            pygame.display.flip()
            clock.tick(30)
        
        self.cap.release()
        self.hands.close()
        pygame.quit()
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    try:
        app = QuickStart3D()
        app.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
