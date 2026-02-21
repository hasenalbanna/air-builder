"""
AI Hand Builder - Python Version with Enhanced Lighting Compensation
Uses OpenCV preprocessing to improve hand detection in poor lighting conditions
"""

import cv2
import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import sys
import time
from auth_manager import AuthManager
import config

# Import mediapipe with error handling
try:
    import mediapipe as mp
except Exception as e:
    print(f"Error importing mediapipe: {e}")
    print("\nTrying alternative mediapipe import...")
    # Try importing just the hands module directly
    from mediapipe.python.solutions import hands as mp_hands_module
    from mediapipe.python.solutions import drawing_utils as mp_drawing_module
    
    # Create a simple namespace to match expected structure
    class MPNamespace:
        class solutions:
            hands = mp_hands_module
            drawing_utils = mp_drawing_module
    mp = MPNamespace()

class HandBuilder3D:
    def __init__(self):
        """Initialize the Hand Builder application"""
        # Authentication
        self.auth = AuthManager()
        
        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=config.MAX_NUM_HANDS,
            min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            model_complexity=config.MODEL_COMPLEXITY
        )
        
        # Camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        
        # Image enhancement
        if config.ENABLE_CLAHE:
            self.clahe = cv2.createCLAHE(
                clipLimit=config.CLAHE_CLIP_LIMIT,
                tileGridSize=config.CLAHE_TILE_GRID
            )
        
        # PyGame & OpenGL
        pygame.init()
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            DOUBLEBUF | OPENGL
        )
        pygame.display.set_caption(f"AI Hand Builder - {self.auth.get_current_user()}")
        
        # Initialize OpenGL
        self._init_opengl()
        
        # State variables
        self.cursor_pos = [0, 0, 0]
        self.target_pos = [0, 0, 0]
        self.current_size = 1.0
        self.last_pinch_time = 0
        self.is_pinching = False
        self.pinch_cooldown = 0.4
        
        # Camera rotation
        self.camera_rotation_y = 0
        self.camera_rotation_x = 0
        self.target_camera_rotation_y = 0
        self.target_camera_rotation_x = 0
        self.is_rotating_camera = False
        
        # Build mode
        self.build_mode = 'free'  # 'free', 'building', 'solar'
        self.selected_building_part = 'wall'
        self.selected_solar_object = 'earth'
        self.current_color = [0.22, 0.74, 0.97]  # Default cyan
        
        # Scene objects
        self.blocks = []
        self.show_grid = True
        
        # UI State
        self.show_hand_debug = True
        self.detection_confidence = 0
        self.lighting_quality = "Unknown"
        self.avg_brightness = 0
        
        # Font for UI
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 16)
        
        # UI Buttons
        self.ui_buttons = []
        self.hovered_button = None
        self._build_ui_buttons()
        
    def _init_opengl(self):
        """Initialize OpenGL settings"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Lighting
        glLightfv(GL_LIGHT0, GL_POSITION, (10, 20, 10, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.6, 0.6, 0.6, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        
        # Perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(60, self.screen_width / self.screen_height, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        
    def enhance_image(self, frame):
        """
        Apply image enhancements for better hand detection in poor lighting
        This is the KEY ADVANTAGE over JavaScript version!
        """
        # 1. Brightness/Contrast adjustment
        if config.ENABLE_AUTO_BRIGHTNESS:
            frame = cv2.convertScaleAbs(
                frame,
                alpha=config.BRIGHTNESS_ALPHA,
                beta=config.BRIGHTNESS_BETA
            )
        
        # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        if config.ENABLE_CLAHE:
            # Convert to LAB color space
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            l = self.clahe.apply(l)
            
            # Merge back
            lab = cv2.merge([l, a, b])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # 3. Calculate lighting quality
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.avg_brightness = np.mean(gray)
        
        if self.avg_brightness < config.POOR_LIGHTING_THRESHOLD:
            self.lighting_quality = "Poor - Add Light!"
        elif self.avg_brightness < config.GOOD_LIGHTING_THRESHOLD:
            self.lighting_quality = "Fair"
        else:
            self.lighting_quality = "Good"
        
        return frame
    
    def process_hand_tracking(self, frame):
        """Process hand tracking with MediaPipe"""
        # Enhance frame for better detection
        enhanced_frame = self.enhance_image(frame.copy())
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        # Draw on original frame (not enhanced) for display
        display_frame = frame.copy()
        
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            
            # Get detection confidence
            if results.multi_handedness:
                self.detection_confidence = results.multi_handedness[0].classification[0].score
            
            # TWO HANDS - Camera Rotation Mode
            if num_hands == 2:
                self.is_rotating_camera = True
                hand1 = results.multi_hand_landmarks[0]
                hand2 = results.multi_hand_landmarks[1]
                
                # Get index finger tips
                h1_index = hand1.landmark[8]
                h2_index = hand2.landmark[8]
                
                # Calculate rotation based on hand positions
                horizontal_mid = (h1_index.x + h2_index.x) / 2
                vertical_mid = (h1_index.y + h2_index.y) / 2
                
                self.target_camera_rotation_y = (horizontal_mid - 0.5) * math.pi * 2
                self.target_camera_rotation_x = (vertical_mid - 0.5) * math.pi
                
                # Draw both hands with thicker lines
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(
                        display_frame, 
                        hand_landmarks, 
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                        self.mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2)
                    )
                
                # Add text overlay
                cv2.putText(display_frame, "ROTATION MODE", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
            # ONE HAND - Build Mode
            elif num_hands == 1:
                self.is_rotating_camera = False
                landmarks = results.multi_hand_landmarks[0]
                
                # Draw landmarks with nice colors
                self.mp_draw.draw_landmarks(
                    display_frame, 
                    landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                    self.mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2)
                )
                
                # Add text overlay
                cv2.putText(display_frame, "HAND DETECTED", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Conf: {self.detection_confidence:.2f}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                
                # A. Position tracking (Index finger tip)
                index_tip = landmarks.landmark[8]
                x = (1 - index_tip.x) * config.WORLD_WIDTH - config.WORLD_WIDTH / 2
                y = (1 - index_tip.y) * config.WORLD_HEIGHT - config.WORLD_HEIGHT / 2
                
                self.target_pos = [x, y, 0]
                
                # B. Size tracking (Hand spread)
                index_x, index_y = index_tip.x, index_tip.y
                pinky_tip = landmarks.landmark[20]
                pinky_x, pinky_y = pinky_tip.x, pinky_tip.y
                
                hand_spread = math.hypot(index_x - pinky_x, index_y - pinky_y)
                self.current_size = max(config.MIN_SIZE, min(config.MAX_SIZE, hand_spread * 10))
                
                # C. Pinch detection (Thumb tip + Index tip)
                thumb_tip = landmarks.landmark[4]
                thumb_x, thumb_y = thumb_tip.x, thumb_tip.y
                pinch_dist = math.hypot(index_x - thumb_x, index_y - thumb_y)
                
                if pinch_dist < config.PINCH_THRESHOLD:
                    current_time = time.time()
                    if not self.is_pinching and (current_time - self.last_pinch_time) > self.pinch_cooldown:
                        self.place_block()
                        self.last_pinch_time = current_time
                        self.is_pinching = True
                else:
                    self.is_pinching = False
        else:
            self.is_rotating_camera = False
            self.detection_confidence = 0
            
            # Add "No hand detected" overlay
            cv2.putText(display_frame, "NO HAND DETECTED", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_frame, "Show your hand to camera", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return display_frame
    
    def place_block(self):
        """Place a block in the 3D scene"""
        block_data = {
            'position': self.cursor_pos.copy(),
            'mode': self.build_mode,
            'rotation': [0, 0, 0]
        }
        
        if self.build_mode == 'free':
            block_data['size'] = [self.current_size] * 3
            block_data['color'] = self.current_color.copy()
            block_data['type'] = 'cube'
            
        elif self.build_mode == 'building':
            part = config.BUILDING_PARTS[self.selected_building_part]
            block_data['size'] = list(part['size'])
            block_data['color'] = list(part['color'])
            block_data['type'] = 'cube'
            
        elif self.build_mode == 'solar':
            obj = config.SOLAR_OBJECTS[self.selected_solar_object]
            block_data['size'] = [obj['radius']]
            block_data['color'] = list(obj['color'])
            block_data['type'] = 'sphere'
        
        self.blocks.append(block_data)
        print(f"✅ Placed {block_data['type']} at {block_data['position']}")
    
    def draw_grid(self):
        """Draw grid on ground plane"""
        if not self.show_grid:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        
        size = 20
        step = 1
        for i in range(-size, size + 1, step):
            # Lines parallel to X axis
            glVertex3f(-size, 0, i)
            glVertex3f(size, 0, i)
            # Lines parallel to Z axis
            glVertex3f(i, 0, -size)
            glVertex3f(i, 0, size)
        
        glEnd()
        
        # Draw axes
        glBegin(GL_LINES)
        # X axis (Red)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(2, 0, 0)
        # Y axis (Green)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 2, 0)
        # Z axis (Blue)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 2)
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def draw_cursor(self):
        """Draw the cursor (ghost block)"""
        glPushMatrix()
        glTranslatef(*self.cursor_pos)
        
        # Set cursor color based on mode
        if self.build_mode == 'free':
            color = self.current_color
        elif self.build_mode == 'building':
            color = config.BUILDING_PARTS[self.selected_building_part]['color']
        else:
            color = config.SOLAR_OBJECTS[self.selected_solar_object]['color']
        
        glColor4f(*color, 0.5)
        
        # Draw wireframe cube or sphere
        if self.build_mode != 'solar':
            # Cube
            size = self.current_size if self.build_mode == 'free' else 1
            self.draw_wireframe_cube(size)
        else:
            # Sphere
            radius = config.SOLAR_OBJECTS[self.selected_solar_object]['radius']
            self.draw_wireframe_sphere(radius)
        
        glPopMatrix()
    
    def draw_wireframe_cube(self, size):
        """Draw a wireframe cube"""
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)
        s = size / 2
        # Front face
        glVertex3f(-s, -s, s); glVertex3f(s, -s, s)
        glVertex3f(s, -s, s); glVertex3f(s, s, s)
        glVertex3f(s, s, s); glVertex3f(-s, s, s)
        glVertex3f(-s, s, s); glVertex3f(-s, -s, s)
        # Back face
        glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s)
        glVertex3f(s, -s, -s); glVertex3f(s, s, -s)
        glVertex3f(s, s, -s); glVertex3f(-s, s, -s)
        glVertex3f(-s, s, -s); glVertex3f(-s, -s, -s)
        # Connecting lines
        glVertex3f(-s, -s, s); glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, s); glVertex3f(s, -s, -s)
        glVertex3f(s, s, s); glVertex3f(s, s, -s)
        glVertex3f(-s, s, s); glVertex3f(-s, s, -s)
        glEnd()
        glEnable(GL_LIGHTING)
    
    def draw_wireframe_sphere(self, radius):
        """Draw a wireframe sphere"""
        glDisable(GL_LIGHTING)
        slices, stacks = 16, 16
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = radius * math.sin(lat0)
            zr0 = radius * math.cos(lat0)
            
            lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
            z1 = radius * math.sin(lat1)
            zr1 = radius * math.cos(lat1)
            
            glBegin(GL_LINE_LOOP)
            for j in range(slices):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                glVertex3f(x * zr0, y * zr0, z0)
            glEnd()
        glEnable(GL_LIGHTING)
    
    def draw_cube(self, size):
        """Draw a solid cube"""
        s = size / 2
        glBegin(GL_QUADS)
        
        # Front
        glNormal3f(0, 0, 1)
        glVertex3f(-s, -s, s); glVertex3f(s, -s, s); glVertex3f(s, s, s); glVertex3f(-s, s, s)
        # Back
        glNormal3f(0, 0, -1)
        glVertex3f(-s, -s, -s); glVertex3f(-s, s, -s); glVertex3f(s, s, -s); glVertex3f(s, -s, -s)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(-s, s, -s); glVertex3f(-s, s, s); glVertex3f(s, s, s); glVertex3f(s, s, -s)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s); glVertex3f(s, -s, s); glVertex3f(-s, -s, s)
        # Right
        glNormal3f(1, 0, 0)
        glVertex3f(s, -s, -s); glVertex3f(s, s, -s); glVertex3f(s, s, s); glVertex3f(s, -s, s)
        # Left
        glNormal3f(-1, 0, 0)
        glVertex3f(-s, -s, -s); glVertex3f(-s, -s, s); glVertex3f(-s, s, s); glVertex3f(-s, s, -s)
        
        glEnd()
    
    def draw_sphere(self, radius):
        """Draw a solid sphere using GLU"""
        quadric = gluNewQuadric()
        gluSphere(quadric, radius, 32, 32)
        gluDeleteQuadric(quadric)
    
    def draw_blocks(self):
        """Draw all placed blocks"""
        for block in self.blocks:
            glPushMatrix()
            glTranslatef(*block['position'])
            glRotatef(block['rotation'][0], 1, 0, 0)
            glRotatef(block['rotation'][1], 0, 1, 0)
            glRotatef(block['rotation'][2], 0, 0, 1)
            
            glColor3fv(block['color'])
            
            if block['type'] == 'cube':
                size = block['size'][0] if len(block['size']) == 3 else block['size'][0]
                self.draw_cube(size)
            elif block['type'] == 'sphere':
                self.draw_sphere(block['size'][0])
            
            glPopMatrix()
    
    def render_3d_scene(self):
        """Render the 3D scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Smooth cursor movement
        for i in range(3):
            self.cursor_pos[i] += (self.target_pos[i] - self.cursor_pos[i]) * config.SMOOTHING_FACTOR
        
        # Camera positioning
        if self.is_rotating_camera:
            # Smooth rotation
            self.camera_rotation_y += (self.target_camera_rotation_y - self.camera_rotation_y) * 0.1
            self.camera_rotation_x += (self.target_camera_rotation_x - self.camera_rotation_x) * 0.1
            
            radius = config.CAMERA_DISTANCE
            cam_x = math.sin(self.camera_rotation_y) * radius
            cam_z = math.cos(self.camera_rotation_y) * radius
            cam_y = config.CAMERA_HEIGHT + math.sin(self.camera_rotation_x) * 5
            
            gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)
        else:
            gluLookAt(0, config.CAMERA_HEIGHT, config.CAMERA_DISTANCE, 0, 0, 0, 0, 1, 0)
        
        # Draw scene
        self.draw_grid()
        self.draw_blocks()
        
        if not self.is_rotating_camera:
            self.draw_cursor()
    
    def draw_ui_overlay(self, camera_frame):
        """Draw UI overlay on top of 3D scene"""
        # Convert camera frame to pygame surface (with hand landmarks already drawn)
        camera_frame_rgb = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
        camera_preview = cv2.resize(camera_frame_rgb, (320, 240))
        camera_preview = np.rot90(camera_preview)
        camera_surface = pygame.surfarray.make_surface(camera_preview)
        
        # Draw camera feed with border in top-right corner
        cam_x = self.screen_width - 330
        cam_y = 10
        
        # Draw border background
        border_rect = pygame.Rect(cam_x - 5, cam_y - 25, 330, 270)
        pygame.draw.rect(self.screen, (15, 23, 42), border_rect)
        pygame.draw.rect(self.screen, (56, 189, 248), border_rect, 3)
        
        # Draw label
        cam_label = self.font_small.render("📹 Camera Feed", True, (255, 255, 255))
        self.screen.blit(cam_label, (cam_x, cam_y - 20))
        
        # Draw camera feed
        self.screen.blit(camera_surface, (cam_x, cam_y))
        
        # Draw UI text
        y_offset = 10
        
        # User info
        user_text = self.font.render(f"User: {self.auth.get_current_user()}", True, (255, 255, 255))
        self.screen.blit(user_text, (10, y_offset))
        y_offset += 30
        
        # Build mode
        mode_text = self.font.render(f"Mode: {config.BUILD_MODES[self.build_mode]}", True, (56, 189, 248))
        self.screen.blit(mode_text, (10, y_offset))
        y_offset += 30
        
        # Detection status
        if self.detection_confidence > 0:
            status_color = (34, 197, 94) if self.detection_confidence > config.CONFIDENCE_WARNING_THRESHOLD else (239, 68, 68)
            status_text = f"Hand Detected ({self.detection_confidence:.2f})"
            if self.is_rotating_camera:
                status_text = "Rotation Mode (2 Hands)"
        else:
            status_color = (239, 68, 68)
            status_text = "No Hand Detected"
        
        status_surface = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (10, y_offset))
        y_offset += 30
        
        # Lighting quality (KEY FEATURE!)
        lighting_color = {
            "Good": (34, 197, 94),
            "Fair": (234, 179, 8),
            "Poor - Add Light!": (239, 68, 68),
            "Unknown": (156, 163, 175)
        }.get(self.lighting_quality, (255, 255, 255))
        
        lighting_text = self.font.render(
            f"Lighting: {self.lighting_quality} ({int(self.avg_brightness)})",
            True,
            lighting_color
        )
        self.screen.blit(lighting_text, (10, y_offset))
        y_offset += 40
        
        # Draw mode-specific UI panels
        if self.build_mode == 'building':
            # Show selected building part
            selected_text = self.font.render(
                f"Selected: {config.BUILDING_PARTS[self.selected_building_part]['name']}",
                True,
                (56, 189, 248)
            )
            self.screen.blit(selected_text, (10, y_offset))
            y_offset += 30
            
            # Draw building part buttons
            label = self.font_small.render("Building Parts:", True, (200, 200, 200))
            self.screen.blit(label, (10, y_offset))
            y_offset += 25
            
            for button in self.ui_buttons:
                # Determine button color
                is_selected = button['value'] == self.selected_building_part
                is_hovered = self.hovered_button == button
                
                if is_selected:
                    bg_color = (56, 189, 248)
                    text_color = (0, 0, 0)
                elif is_hovered:
                    bg_color = (71, 85, 105)
                    text_color = (255, 255, 255)
                else:
                    bg_color = (30, 41, 59)
                    text_color = (203, 213, 225)
                
                # Draw button background
                pygame.draw.rect(self.screen, bg_color, button['rect'])
                pygame.draw.rect(self.screen, (100, 116, 139), button['rect'], 2)
                
                # Draw button text
                button_text = self.font_tiny.render(
                    f"{button['icon']} {button['text']}",
                    True,
                    text_color
                )
                text_rect = button_text.get_rect(center=button['rect'].center)
                self.screen.blit(button_text, text_rect)
        
        elif self.build_mode == 'solar':
            # Show selected solar object
            selected_text = self.font.render(
                f"Selected: {config.SOLAR_OBJECTS[self.selected_solar_object]['name']}",
                True,
                (56, 189, 248)
            )
            self.screen.blit(selected_text, (10, y_offset))
            y_offset += 30
            
            # Draw solar object buttons
            label = self.font_small.render("Solar System Objects:", True, (200, 200, 200))
            self.screen.blit(label, (10, y_offset))
            y_offset += 25
            
            for button in self.ui_buttons:
                # Determine button color
                is_selected = button['value'] == self.selected_solar_object
                is_hovered = self.hovered_button == button
                
                if is_selected:
                    bg_color = (56, 189, 248)
                    text_color = (0, 0, 0)
                elif is_hovered:
                    bg_color = (71, 85, 105)
                    text_color = (255, 255, 255)
                else:
                    bg_color = (30, 41, 59)
                    text_color = (203, 213, 225)
                
                # Draw button background
                pygame.draw.rect(self.screen, bg_color, button['rect'])
                pygame.draw.rect(self.screen, (100, 116, 139), button['rect'], 2)
                
                # Draw button text
                button_text = self.font_tiny.render(
                    f"{button['icon']} {button['text']}",
                    True,
                    text_color
                )
                text_rect = button_text.get_rect(center=button['rect'].center)
                self.screen.blit(button_text, text_rect)
        
        # Controls help
        y_offset = self.screen_height - 140
        help_texts = [
            "Controls:",
            "👆 Index finger = Move cursor",
            "🤏 Pinch = Place block",
            "🖐️ Spread = Resize (Free mode)",
            "✌️ Two hands = Rotate camera",
            "🖱️ Click buttons to select parts",
            "1/2/3 = Mode | G = Grid | C = Clear | Q = Quit"
        ]
        
        for text in help_texts:
            help_surface = self.font_small.render(text, True, (200, 200, 200))
            self.screen.blit(help_surface, (10, y_offset))
            y_offset += 20
    
    def handle_keyboard(self):
        """Handle keyboard input"""
        keys = pygame.key.get_pressed()
        
        if keys[K_q] or keys[K_ESCAPE]:
            return False
        
        if keys[K_g]:
            self.show_grid = not self.show_grid
            time.sleep(0.2)  # Debounce
        
        if keys[K_c]:
            self.blocks.clear()
            print("🗑️ Scene cleared")
            time.sleep(0.2)
        
        if keys[K_1]:
            self.build_mode = 'free'
            self._build_ui_buttons()
            print("🆓 Free Build Mode")
            time.sleep(0.2)
        
        if keys[K_2]:
            self.build_mode = 'building'
            self._build_ui_buttons()
            print("🏗️ Building Mode")
            time.sleep(0.2)
        
        if keys[K_3]:
            self.build_mode = 'solar'
            self._build_ui_buttons()
            print("🌍 Solar System Mode")
            time.sleep(0.2)
        
        return True
    
    def _build_ui_buttons(self):
        """Build UI buttons based on current mode"""
        self.ui_buttons = []
        x_start = 10
        y_start = 250
        button_width = 110
        button_height = 40
        spacing = 5
        
        # Building mode buttons
        if self.build_mode == 'building':
            parts_list = list(config.BUILDING_PARTS.keys())
            for i, part in enumerate(parts_list):
                row = i // 2
                col = i % 2
                x = x_start + col * (button_width + spacing)
                y = y_start + row * (button_height + spacing)
                
                self.ui_buttons.append({
                    'rect': pygame.Rect(x, y, button_width, button_height),
                    'text': f"{config.BUILDING_PARTS[part]['name']}",
                    'icon': self._get_building_icon(part),
                    'value': part,
                    'type': 'building'
                })
        
        # Solar mode buttons
        elif self.build_mode == 'solar':
            objects_list = list(config.SOLAR_OBJECTS.keys())
            for i, obj in enumerate(objects_list):
                row = i // 2
                col = i % 2
                x = x_start + col * (button_width + spacing)
                y = y_start + row * (button_height + spacing)
                
                self.ui_buttons.append({
                    'rect': pygame.Rect(x, y, button_width, button_height),
                    'text': f"{config.SOLAR_OBJECTS[obj]['name']}",
                    'icon': self._get_solar_icon(obj),
                    'value': obj,
                    'type': 'solar'
                })
    
    def _get_building_icon(self, part):
        """Get emoji icon for building part"""
        icons = {
            'wall': '🧱', 'window': '🪟', 'door': '🚪', 'roof': '🏠',
            'floor': '⬛', 'column': '🏛️', 'stairs': '🪜', 'balcony': '🏗️'
        }
        return icons.get(part, '📦')
    
    def _get_solar_icon(self, obj):
        """Get emoji icon for solar object"""
        icons = {
            'sun': '☀️', 'mercury': '☿', 'venus': '♀', 'earth': '🌍',
            'moon': '🌙', 'mars': '♂', 'jupiter': '♃', 'saturn': '♄',
            'uranus': '♅', 'neptune': '♆', 'asteroid': '☄️', 'comet': '💫'
        }
        return icons.get(obj, '🌟')
    
    def handle_mouse_click(self, pos):
        """Handle mouse clicks on UI buttons"""
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
        """Handle mouse motion for button hover effects"""
        self.hovered_button = None
        for button in self.ui_buttons:
            if button['rect'].collidepoint(pos):
                self.hovered_button = button
                break
    
    def run(self):
        """Main application loop"""
        clock = pygame.time.Clock()
        running = True
        
        print("\n" + "="*60)
        print("🚀 AI Hand Builder - Python Version (Enhanced)")
        print("="*60)
        print(f"👤 Logged in as: {self.auth.get_current_user()}")
        print("💡 Enhanced with lighting compensation for poor conditions!")
        print("="*60 + "\n")
        
        while running:
            # Process events
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_mouse_click(event.pos)
                elif event.type == MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
            
            # Handle keyboard
            if not self.handle_keyboard():
                running = False
                continue
            
            # Capture frame from camera
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Failed to capture frame")
                break
            
            # Process hand tracking (with enhancement!)
            frame = self.process_hand_tracking(frame)
            
            # Render 3D scene
            self.render_3d_scene()
            
            # Switch to 2D for UI overlay
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.screen_width, self.screen_height, 0, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            
            # Draw UI overlay
            self.draw_ui_overlay(frame)
            
            # Restore 3D projection
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            
            pygame.display.flip()
            clock.tick(30)
        
        self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.cap.release()
        self.hands.close()
        pygame.quit()
        cv2.destroyAllWindows()
        print("\n👋 Goodbye!")


def login_screen():
    """Simple console-based login"""
    print("\n" + "="*60)
    print("🔐 AI Hand Builder - Login")
    print("="*60)
    print("Default accounts: demo/demo123 or admin/admin123")
    print("="*60 + "\n")
    
    auth = AuthManager()
    
    while True:
        print("\n1. Login")
        print("2. Register")
        print("3. Exit")
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            success, message = auth.login(username, password)
            print(f"\n{'✅' if success else '❌'} {message}")
            if success:
                return auth
                
        elif choice == '2':
            username = input("New username: ").strip()
            password = input("New password: ").strip()
            success, message = auth.register(username, password)
            print(f"\n{'✅' if success else '❌'} {message}")
            if success:
                auth.login(username, password)
                return auth
                
        elif choice == '3':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    # Login first
    auth = login_screen()
    
    # Start application
    try:
        app = HandBuilder3D()
        app.auth = auth  # Pass authenticated session
        app.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
