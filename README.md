# AI Hand Builder

An augmented reality application that uses AI hand tracking to build 3D structures in real-time.

## 🚀 Features

- **AI Hand Tracking**: Uses MediaPipe to detect and track hand movements
- **Multiple Build Modes**:
  - **Free Build**: Create custom colored blocks of any size
  - **Building Mode**: Use predefined building parts (walls, windows, doors, roofs, floors, columns, stairs, balconies)
  - **Solar System Mode**: Place celestial objects (Sun, planets, moons, asteroids, comets) with realistic colors and sizes
- **3D Building**: Create 3D structures in space using hand gestures
- **Gesture Controls**:
  - 👆 Index finger to move the cursor
  - 🤏 Pinch gesture to place blocks/objects
  - � Show 2 hands to rotate the camera view (see from all angles!)
  - �🖐 Spread fingers to resize blocks (in Free Build mode)
- **Customizable Colors**: Choose any color for your blocks in Free Build mode
- **Grid System**: Toggle grid and rulers for precise building
- **Secure Login**: User authentication system
- **Animated Objects**: Solar system objects rotate automatically

## 📁 Project Structure

```
i hnd builder/
├── index.html          # Entry point with auto-redirect
├── login.html          # Login page
├── login-style.css     # Login page styles
├── app.html            # Main application
├── app-style.css       # Application styles
├── app.js              # Main application logic
├── auth.js             # Authentication system
└── README.md           # This file
```

## 🔐 Login Credentials

Default demo accounts:

- **Username**: `demo` | **Password**: `demo123`
- **Username**: `admin` | **Password**: `admin123`

You can also register a new account using the "Register here" link on the login page.

## 🎮 How to Use

1. **Login**: Open `index.html` in a browser (will redirect to login page)
2. **Camera Access**: Allow camera access when prompted
3. **Select Mode**: Choose your build mode:
   - **Free Build**: For custom colored blocks
   - **Building Blocks**: For architectural construction
   - **Solar System**: For creating space scenes
4. **Build**: 
   - Show **one hand** to the camera to build
   - Use your index finger to move the cursor
   - Pinch your thumb and index finger to place a block/object
   - Show **both hands** to rotate the camera view (see from all angles!)
   - In Free Build mode, spread your fingers to change block size
5. **Customize**:
   - In Free Build: Change block color using the color picker
   - In Building Mode: Select from 8 different building parts
   - In Solar System: Choose from 12 celestial objects
   - Toggle grid visibility
   - Reset camera view to default position
   - Clear all objects

### Building Parts Available:
- 🧱 **Wall**: Large rectangular blocks for walls
- 🪟 **Window**: Transparent glass-like blocks
- 🚪 **Door**: Door-sized blocks
- 🏠 **Roof**: Wide flat blocks for roofing
- ⬛ **Floor**: Foundation and floor blocks
- 🏛️ **Column**: Vertical support pillars
- 🪜 **Stairs**: Staircase blocks
- 🏗️ **Balcony**: Extended platform blocks

### Solar System Objects:
- ☀️ **Sun**: Large glowing yellow sphere
- ☿ **Mercury**: Small gray planet
- ♀ **Venus**: Bright yellow planet
- 🌍 **Earth**: Blue planet
- 🌙 **Moon**: Small gray satellite
- ♂ **Mars**: Red planet
- ♃ **Jupiter**: Large orange planet
- ♄ **Saturn**: Orange planet with rings
- ♅ **Uranus**: Bright blue planet
- ♆ **Neptune**: Deep blue planet
- ☄️ **Asteroid**: Small rocky object
- 💫 **Comet**: Object with glowing tail
- **MediaPipe Hands**: AI-powered hand tracking
- **Vanilla JavaScript**: No framework dependencies
- **LocalStorage**: Client-side data persistence

## 📝 Notes

- Requires a webcam for hand tracking
- Works best in well-lit environments
- The authentication system uses localStorage (for demo purposes only - not secure for production)
- For production use, implement proper backend authentication

## 🔒 Security Notice

The current authentication system is for demonstration purposes only. For production:

- Implement server-side authentication
- Use HTTPS
- Hash passwords properly (bcrypt, argon2, etc.)
- Use secure session management
- Add CSRF protection

## 🌐 Browser Compatibility

Works best in modern browsers with WebGL support:

- Chrome 90+
- Edge 90+
- Firefox 88+
- Safari 14+

## 📄 License

This project is for educational and demonstration purposes.
