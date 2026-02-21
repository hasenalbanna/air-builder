# AI Hand Builder - Python Version 🐍

**Enhanced with OpenCV Preprocessing for Poor Lighting Conditions**

This is the Python implementation of the AI Hand Builder with **significantly improved hand detection in low-light environments**. Unlike the JavaScript version, this uses OpenCV's image processing capabilities to enhance video frames before hand tracking.

---

## 🌟 Key Advantages Over JavaScript Version

### ✅ **Lighting Compensation** (THE MAIN FEATURE!)

- **Automatic Brightness & Contrast Adjustment** - Brightens dark scenes in real-time
- **CLAHE (Contrast Limited Adaptive Histogram Equalization)** - Improves hand visibility
- **Real-time Lighting Quality Monitoring** - Shows current lighting conditions
- **Adaptive Detection Thresholds** - More forgiving in poor conditions

### ✅ **Better Control & Debugging**

- Full access to OpenCV's image processing toolkit
- Real-time detection confidence display
- Console logging for troubleshooting
- More configurable parameters

### ✅ **Standalone Desktop Application**

- No browser required
- Runs natively on Windows/Mac/Linux
- Better performance potential

---

## 📋 Requirements

- **Python 3.8+** (Recommended: Python 3.10 or 3.11)
- **Webcam** (Any USB or built-in camera)
- **Windows/Mac/Linux** (Tested on Windows 10/11)

---

## 🚀 Installation & Setup

### Step 1: Install Python

Download from [python.org](https://www.python.org/downloads/) (Make sure to check "Add Python to PATH")

### Step 2: Clone/Download Project

```bash
cd "e:\1.PROFESSIONAL APPLICATIONS\i hnd builder - python"
```

### Step 3: Create Virtual Environment (Recommended)

```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** If you encounter issues with PyOpenGL on Windows:

```powershell
pip install pyopengl-accelerate
```

### Step 5: Run the Application

```powershell
python main.py
```

---

## 🎮 How to Use

### Login Screen

1. Run `python main.py`
2. Default accounts:
   - Username: `demo` / Password: `demo123`
   - Username: `admin` / Password: `admin123`
3. Or register a new account

### Main Application

#### Hand Gestures

- 👆 **Index Finger Extended** = Move cursor in 3D space
- 🤏 **Pinch (Thumb + Index)** = Place block/object
- 🖐️ **Spread Fingers** = Resize block (Free Build mode only)
- ✌️ **Two Hands Visible** = Rotate camera view (move hands to change angle)

#### Keyboard Controls

| Key         | Action               |
| ----------- | -------------------- |
| `1`         | Free Build Mode      |
| `2`         | Building Blocks Mode |
| `3`         | Solar System Mode    |
| `G`         | Toggle Grid/Rulers   |
| `C`         | Clear All Objects    |
| `Q` / `ESC` | Quit Application     |

#### Mouse Controls

- **Click on building part buttons** to select (Wall, Window, Door, Roof, etc.)
- **Click on solar object buttons** to select (Sun, Planets, Asteroids, etc.)
- **Interactive UI panels** appear based on current mode

---

## 🔧 Configuration

Edit [`config.py`](config.py) to customize:

### Lighting Enhancement (For Poor Lighting)

```python
# Increase these for darker environments
BRIGHTNESS_ALPHA = 1.5      # Default: 1.3 (higher = more contrast)
BRIGHTNESS_BETA = 30        # Default: 20 (higher = brighter)
ENABLE_CLAHE = True         # Keep enabled for best results
```

### Detection Sensitivity

```python
# Lower these if detection is too strict
MIN_DETECTION_CONFIDENCE = 0.4  # Default: 0.4 (range: 0.0-1.0)
MIN_TRACKING_CONFIDENCE = 0.4   # Default: 0.4 (range: 0.0-1.0)
```

### Camera Settings

```python
CAMERA_WIDTH = 640          # Higher = better quality, slower
CAMERA_HEIGHT = 480
```

---

## 🎨 Build Modes

### 1. Free Build Mode (Press `1`)

- Create custom colored blocks
- Adjust size by spreading fingers
- Default color: Cyan blue
- Full creative freedom

### 2. Building Blocks Mode (Press `2`)

- Pre-defined architectural parts
- Available parts: Wall, Window, Door, Roof, Floor, Column, Stairs, Balcony
- Realistic sizes and colors
- Perfect for constructing buildings

### 3. Solar System Mode (Press `3`)

- Place celestial objects
- Available: Sun, Mercury, Venus, Earth, Moon, Mars, Jupiter, Saturn, Uranus, Neptune, Asteroids, Comets
- Spherical shapes with realistic colors
- Correct relative sizes

---

## 💡 Lighting Tips

The Python version has **automatic lighting compensation**, but you'll get best results with:

### ✅ Good Lighting

- Natural daylight from window (not backlit)
- Bright room lighting from above or side
- Desk lamp pointing at your hands
- Webcam facing you with light behind the camera

### ❌ Poor Lighting (Avoid)

- Complete darkness (no algorithm can fix this!)
- Strong backlighting (window behind you)
- Colored/tinted lighting (affects color detection)
- Flickering lights (causes instability)

### 📊 Lighting Quality Indicator

The app shows real-time lighting quality:

- **Good** (Green) - Optimal conditions ✅
- **Fair** (Yellow) - Acceptable, enhancement active ⚠️
- **Poor** (Red) - Add more light! ❌

---

## 🆚 Python vs JavaScript Comparison

| Feature                      | JavaScript (Browser)    | Python (This Version)     |
| ---------------------------- | ----------------------- | ------------------------- |
| **Lighting Compensation**    | ❌ None                 | ✅ **OpenCV Enhancement** |
| **Image Preprocessing**      | ❌ Limited              | ✅ **Full Control**       |
| **Detection in Poor Light**  | ❌ Struggles            | ✅ **Much Better**        |
| **Interactive UI Buttons**   | ✅ Click to select      | ✅ **Click to select**    |
| **Building Parts Selection** | ✅ 8 parts              | ✅ **8 parts**            |
| **Solar Objects Selection**  | ✅ 12 objects           | ✅ **12 objects**         |
| **Deployment**               | ✅ Just open in browser | ⚠️ Requires Python setup  |
| **Performance**              | ✅ Fast                 | ✅ Fast (native)          |
| **3D Graphics**              | ✅ Three.js (excellent) | ✅ PyOpenGL (good)        |
| **Debugging**                | ⚠️ Browser console      | ✅ Better tools           |
| **Real-time Feedback**       | ⚠️ Limited              | ✅ **Comprehensive**      |

---

## 🔬 Technical Details

### Image Enhancement Pipeline

```
Raw Camera Frame
    ↓
Brightness/Contrast Adjustment (cv2.convertScaleAbs)
    ↓
CLAHE Enhancement (cv2.createCLAHE)
    ↓
RGB Conversion
    ↓
MediaPipe Hand Detection
    ↓
Landmark Extraction
```

### Why This Works Better in Poor Lighting

1. **Automatic Brightness** - Compensates for underexposed camera input
2. **Adaptive Contrast** - CLAHE enhances local contrast without oversaturating
3. **Pre-processing** - Enhancement happens BEFORE MediaPipe sees the image
4. **Real-time** - All processing at 30 FPS with minimal latency

---

## 🐛 Troubleshooting

### "No module named cv2"

```powershell
pip install opencv-python
```

### "Failed to capture frame"

- Check if another app is using the camera
- Try different camera index in code: `cv2.VideoCapture(1)` or `(2)`
- Grant camera permissions in Windows Settings

### OpenGL/Pygame Issues on Windows

```powershell
pip install pyopengl-accelerate
pip install --upgrade pygame
```

### Hand Not Detected

1. Check lighting quality indicator (should be Fair or Good)
2. Make sure hand is clearly visible against background
3. Try lowering `MIN_DETECTION_CONFIDENCE` in config.py
4. Increase `BRIGHTNESS_ALPHA` and `BRIGHTNESS_BETA` in config.py

### Poor Performance

1. Lower camera resolution in config.py
2. Set `MODEL_COMPLEXITY = 0` (faster but less accurate)
3. Reduce `MAX_NUM_HANDS = 1` if not using rotation

---

## 📸 Screenshots & Demo

### Lighting Quality Display

The app shows real-time metrics:

- **Detection Confidence**: How confident MediaPipe is (0.0-1.0)
- **Lighting Quality**: Good/Fair/Poor with brightness value
- **Hand Status**: Detected / Rotation Mode / Not Detected

### Camera Feed

Live camera feed with hand landmarks drawn in top-right corner

---

## 📦 File Structure

```
i hnd builder - python/
├── main.py              # Main application (run this!)
├── config.py            # Configuration settings
├── auth_manager.py      # Authentication system
├── requirements.txt     # Python dependencies
├── README_PYTHON.md     # This file
├── users.json          # User database (created automatically)
│
├── index.html          # JavaScript version (original)
├── app.html
├── app.js
└── ... (other web files)
```

---

## 🎯 Future Enhancements

Potential improvements:

- [ ] GUI settings panel (instead of editing config.py)
- [ ] Save/Load 3D scenes
- [ ] Export to OBJ/STL files
- [ ] Multiplayer/networked building
- [ ] VR support
- [ ] Advanced gesture recognition (snap, swipe, etc.)

---

## 📝 License & Credits

- **MediaPipe** by Google (Hand Tracking)
- **OpenCV** (Computer Vision & Image Processing)
- **PyGame + PyOpenGL** (3D Graphics)
- Built with ❤️ for better low-light performance

---

## 🤝 Comparison Summary

**Choose JavaScript version if:**

- You want easy deployment (just share the files)
- Users don't want to install anything
- Lighting conditions are always good

**Choose Python version if:**

- You have poor/inconsistent lighting ⭐
- You want better control and debugging
- You prefer desktop applications
- You need to customize image processing

---

## 🚦 Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created (`python -m venv venv`)
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Camera connected and working
- [ ] Run `python main.py`
- [ ] Login with demo/demo123
- [ ] Show your hand to the camera
- [ ] Check lighting quality indicator
- [ ] Start building! 🎉

---

**Need help?** Check the troubleshooting section or review the inline code comments in `main.py`.

**Enjoy building in 3D with enhanced hand tracking!** 🏗️✨
