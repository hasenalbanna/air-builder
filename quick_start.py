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
        self.selected_solar_object = 'earth'
        self.current_color = [0.22, 0.74, 0.97]
        
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
        self.hovered_button = None
        self._build_ui_buttons()
        
        print("\n" + "="*60)
        print("🚀 AI Hand Builder - Quick Start Mode")
        print("="*60)
        print("✅ Started in BUILDING MODE")
        print("📱 Camera preview: Top-right corner")
        print("🖱️  Click buttons on left to select building parts")
        print("👆 Show your hand to start building!")
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
                x = (1 - index_tip.x) * 20 - 10
                y = (1 - index_tip.y) * 12 - 4
                self.target_pos = [x, y, 0]
                
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
        block_data = {'position': self.cursor_pos.copy(), 'mode': self.build_mode, 'rotation': [0, 0, 0]}
        
        if self.build_mode == 'free':
            block_data['size'] = [self.current_size] * 3
            block_data['color'] = self.current_color.copy()
            block_data['type'] = 'cube'
            block_data['building_part'] = None
        elif self.build_mode == 'building':
            part = config.BUILDING_PARTS[self.selected_building_part]
            block_data['size'] = list(part['size'])
            block_data['color'] = list(part['color'])
            block_data['type'] = 'building'
            block_data['building_part'] = self.selected_building_part
        elif self.build_mode == 'solar':
            obj = config.SOLAR_OBJECTS[self.selected_solar_object]
            block_data['size'] = [obj['radius']]
            block_data['color'] = list(obj['color'])
            block_data['type'] = 'sphere'
            block_data['building_part'] = None
        
        self.blocks.append(block_data)
        print(f"✅ Placed {config.BUILDING_PARTS[self.selected_building_part]['name'] if self.build_mode == 'building' else block_data['type']}")
    
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
        for button in self.ui_buttons:
            if button['rect'].collidepoint(pos):
                if button['type'] == 'building':
                    self.selected_building_part = button['value']
                    print(f"🏗️ Selected: {config.BUILDING_PARTS[button['value']]['name']}")
                elif button['type'] == 'solar':
                    self.selected_solar_object = button['value']
                    print(f"🌍 Selected: {config.SOLAR_OBJECTS[button['value']]['name']}")
                return True
        return False
    
    def handle_mouse_motion(self, pos):
        self.hovered_button = None
        for button in self.ui_buttons:
            if button['rect'].collidepoint(pos):
                self.hovered_button = button
                break
    
    def draw_grid(self):
        if not self.show_grid:
            return
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(-20, 21, 1):
            glVertex3f(-20, 0, i); glVertex3f(20, 0, i)
            glVertex3f(i, 0, -20); glVertex3f(i, 0, 20)
        glEnd()
        glBegin(GL_LINES)
        glColor3f(1, 0, 0); glVertex3f(0, 0, 0); glVertex3f(2, 0, 0)
        glColor3f(0, 1, 0); glVertex3f(0, 0, 0); glVertex3f(0, 2, 0)
        glColor3f(0, 0, 1); glVertex3f(0, 0, 0); glVertex3f(0, 0, 2)
        glEnd()
        glEnable(GL_LIGHTING)
    
    def draw_cursor(self):
        glPushMatrix()
        glTranslatef(*self.cursor_pos)
        if self.build_mode == 'building':
            color = config.BUILDING_PARTS[self.selected_building_part]['color']
        elif self.build_mode == 'solar':
            color = config.SOLAR_OBJECTS[self.selected_solar_object]['color']
        else:
            color = self.current_color
        glColor4f(*color, 0.5)
        self.draw_wireframe_cube(1)
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
            
            if block['type'] == 'building' and block.get('building_part'):
                self.draw_building_part(block['building_part'], block['size'])
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
    
    def render_3d_scene(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        for i in range(3):
            self.cursor_pos[i] += (self.target_pos[i] - self.cursor_pos[i]) * 0.15
        
        # Always update camera rotation and zoom smoothly
        self.camera_rotation_y += (self.target_camera_rotation_y - self.camera_rotation_y) * 0.1
        self.camera_rotation_x += (self.target_camera_rotation_x - self.camera_rotation_x) * 0.1
        self.camera_distance += (self.target_camera_distance - self.camera_distance) * 0.1
        
        # Apply camera position with current rotation and zoom
        cam_x = math.sin(self.camera_rotation_y) * self.camera_distance
        cam_z = math.cos(self.camera_rotation_y) * self.camera_distance
        cam_y = 5 + math.sin(self.camera_rotation_x) * 5
        gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)
        
        self.draw_grid()
        self.draw_blocks()
        if not self.is_rotating_camera:
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
        self._draw_text(f"Mode: {config.BUILD_MODES[self.build_mode]}", 10, y_offset, self.font, (56, 189, 248))
        y_offset += 35
        
        if self.detection_confidence > 0:
            status_color = (34, 197, 94) if self.detection_confidence > 0.6 else (239, 68, 68)
            status_text = "Hand Detected" if not self.is_rotating_camera else "Rotate & Zoom Mode"
        else:
            status_color = (239, 68, 68)
            status_text = "No Hand Detected"
        self._draw_text(status_text, 10, y_offset, self.font_small, status_color)
        y_offset += 30
        
        # Show zoom level
        zoom_pct = int((25 - self.camera_distance) / 20 * 100)
        self._draw_text(f"Zoom: {zoom_pct}%", 10, y_offset, self.font_small, (148, 163, 184))
        y_offset += 5
        
        lighting_color = {"Good": (34, 197, 94), "Fair": (234, 179, 8), "Poor": (239, 68, 68)}.get(self.lighting_quality, (255, 255, 255))
        self._draw_text(f"Light: {self.lighting_quality} ({int(self.avg_brightness)})", 10, y_offset, self.font_small, lighting_color)
        y_offset += 35
        
        if self.build_mode == 'building':
            self._draw_text(f"Selected: {config.BUILDING_PARTS[self.selected_building_part]['name']}", 10, y_offset, self.font, (255, 255, 0))
            y_offset += 30
            
            # Separator line
            glColor4f(0.39, 0.45, 0.55, 1.0)
            glLineWidth(2)
            glBegin(GL_LINES)
            glVertex2f(10, y_offset)
            glVertex2f(240, y_offset)
            glEnd()
            y_offset += 10
            
            self._draw_text("BUILDING PARTS:", 10, y_offset, self.font_small, (255, 255, 255))
            y_offset += 25
            
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
        
        # Camera label
        self._draw_text("Camera Feed", cam_x, cam_y - 20, self.font_small, (255, 255, 255))
        
        # Bottom help text
        y_offset = self.screen_height - 140
        help_texts = ["CONTROLS:", "1 Hand: Index = Move | Pinch = Place", "2 Hands: Rotate camera & Zoom (closer = zoom in)", 
                     "Click buttons | Keys: 1/2/3 = Mode | G = Grid | C = Clear | Q = Quit"]
        for text in help_texts:
            self._draw_text(text, 10, y_offset, self.font_small, (200, 200, 200))
            y_offset += 25
        
        glDisable(GL_BLEND)
    
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
                    elif event.key == K_1:
                        self.build_mode = 'free'
                        self._build_ui_buttons()
                        print("🆓 Free Build Mode")
                    elif event.key == K_2:
                        self.build_mode = 'building'
                        self._build_ui_buttons()
                        print("🏗️ Building Mode")
                    elif event.key == K_3:
                        self.build_mode = 'solar'
                        self._build_ui_buttons()
                        print("🌍 Solar System Mode")
            
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
