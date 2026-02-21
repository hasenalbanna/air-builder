// Protect this page - require login
protectPage();

// Display welcome message
displayWelcome();

// --- CONFIGURATION ---
const videoElement = document.getElementById('input_video');
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const loader = document.getElementById('loader');

// --- 1. THREE.JS SCENE SETUP ---
const scene = new THREE.Scene();

// Use a wide FOV for that "immersive" AR feel
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);

const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(10, 20, 10);
dirLight.castShadow = true;
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
scene.add(dirLight);

// Floor Grid & Rulers
const gridGroup = new THREE.Group();
const gridHelper = new THREE.GridHelper(40, 40, 0x555555, 0x222222);
gridGroup.add(gridHelper);

const axesHelper = new THREE.AxesHelper(2); // Rulers (Red=X, Green=Y, Blue=Z)
gridGroup.add(axesHelper);
scene.add(gridGroup);

// Camera Position
camera.position.z = 12; 
camera.position.y = 5;
camera.lookAt(0, 0, 0);

// Cursor (The Ghost Block) - using let so it can be reassigned
let cursor;
const cursorGeo = new THREE.BoxGeometry(1, 1, 1);
const cursorMat = new THREE.MeshBasicMaterial({ 
    color: 0x38bdf8, 
    wireframe: true, 
    transparent: true, 
    opacity: 0.8 
});
cursor = new THREE.Mesh(cursorGeo, cursorMat);
scene.add(cursor);

// --- 2. VARIABLES & STATE ---
let currentSize = 1;
let lastPinch = 0;
let isPinching = false;

// Smoothing variables for hand movement
let targetX = 0, targetY = 0;
let curX = 0, curY = 0;

// Camera rotation variables
let cameraRotationY = 0;
let cameraRotationX = 0;
let targetCameraRotationY = 0;
let targetCameraRotationX = 0;
let isRotatingCamera = false;
let lastHandDistance = 0;

// Build mode state
let buildMode = 'free'; // 'free', 'building', 'solar'
let selectedBuildingPart = 'wall';
let selectedSolarObject = 'earth';

// Building parts configuration
const buildingParts = {
    wall: { size: [3, 2, 0.3], color: 0xC19A6B, name: 'Wall' },
    window: { size: [1.5, 1.5, 0.2], color: 0x87CEEB, name: 'Window', transparent: true, opacity: 0.5 },
    door: { size: [1.2, 2, 0.2], color: 0x8B4513, name: 'Door' },
    roof: { size: [4, 0.3, 4], color: 0xDC143C, name: 'Roof' },
    floor: { size: [4, 0.2, 4], color: 0x696969, name: 'Floor' },
    column: { size: [0.4, 3, 0.4], color: 0xD3D3D3, name: 'Column' },
    stairs: { size: [2, 1, 3], color: 0xA9A9A9, name: 'Stairs' },
    balcony: { size: [3, 0.2, 1.5], color: 0x708090, name: 'Balcony' }
};

// Solar system objects configuration (relative sizes scaled for visibility)
const solarObjects = {
    sun: { radius: 3, color: 0xFDB813, name: 'Sun', emissive: 0xFDB813 },
    mercury: { radius: 0.4, color: 0x8C7853, name: 'Mercury' },
    venus: { radius: 0.9, color: 0xFFC649, name: 'Venus' },
    earth: { radius: 1, color: 0x4169E1, name: 'Earth' },
    moon: { radius: 0.3, color: 0xC0C0C0, name: 'Moon' },
    mars: { radius: 0.5, color: 0xCD5C5C, name: 'Mars' },
    jupiter: { radius: 2.5, color: 0xDAA520, name: 'Jupiter' },
    saturn: { radius: 2, color: 0xF4A460, name: 'Saturn', hasRing: true },
    uranus: { radius: 1.5, color: 0x4FD0E7, name: 'Uranus' },
    neptune: { radius: 1.4, color: 0x4166F5, name: 'Neptune' },
    asteroid: { radius: 0.2, color: 0x808080, name: 'Asteroid' },
    comet: { radius: 0.3, color: 0xE0E0E0, name: 'Comet', hasTrail: true }
};

// --- 3. MEDIAPIPE HANDS LOGIC ---
function onResults(results) {
    // Hide loader on first successful frame
    if(loader && loader.style.opacity !== '0') {
        loader.style.opacity = '0';
        setTimeout(() => {
            if (loader) loader.style.display = 'none';
        }, 500);
    }

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        
        // TWO HANDS DETECTED - ROTATION MODE
        if (results.multiHandLandmarks.length === 2) {
            statusText.innerText = "Rotation Mode (2 Hands)";
            statusDot.classList.add('active');
            isRotatingCamera = true;
            
            const hand1 = results.multiHandLandmarks[0];
            const hand2 = results.multiHandLandmarks[1];
            
            // Get center points of both hands (using index finger tips)
            const hand1Center = hand1[8];
            const hand2Center = hand2[8];
            
            // Calculate horizontal spread (for Y rotation)
            const horizontalSpread = Math.abs(hand1Center.x - hand2Center.x);
            const horizontalMid = (hand1Center.x + hand2Center.x) / 2;
            
            // Calculate vertical spread (for X rotation)
            const verticalSpread = Math.abs(hand1Center.y - hand2Center.y);
            const verticalMid = (hand1Center.y + hand2Center.y) / 2;
            
            // Map hand positions to camera rotation
            // Horizontal movement rotates around Y axis
            targetCameraRotationY = (horizontalMid - 0.5) * Math.PI * 2;
            
            // Vertical movement rotates around X axis
            targetCameraRotationX = (verticalMid - 0.5) * Math.PI;
            
            // Hide cursor during rotation
            if (cursor) cursor.visible = false;
            
        } 
        // ONE HAND DETECTED - BUILD MODE
        else {
            statusText.innerText = "Tracking Active (1 Hand)";
            statusDot.classList.add('active');
            isRotatingCamera = false;
            
            // Show cursor
            if (cursor) cursor.visible = true;

            const landmarks = results.multiHandLandmarks[0];

        // --- A. POSITION TRACKING ---
        // We use the Index Finger Tip (8)
        const pointer = landmarks[8]; 
        
        // Map Video Coordinates (0-1) to 3D World Coordinates
        // X is inverted because of mirror effect
        // Range tuned for a FOV of 60 at z=12
        const x = (1 - pointer.x) * 20 - 10;
        const y = (1 - pointer.y) * 12 - 4;

        // Smooth the movement (Linear Interpolation / Lerp)
        // Factor 0.2 gives it weight, 0.8 is very snappy
        targetX = x;
        targetY = y;

        // --- B. SIZE TRACKING (Spread) ---
        // Distance between Index Tip (8) and Pinky Tip (20)
        const iTx = landmarks[8].x; const iTy = landmarks[8].y;
        const pTx = landmarks[20].x; const pTy = landmarks[20].y;
        
        const handSpread = Math.hypot(iTx - pTx, iTy - pTy);
        
        // Map spread to size (Typical spread is 0.1 to 0.4)
        // We clamp size between 0.5 and 5.0
        let sizeMult = Math.max(0.5, Math.min(5, handSpread * 10));
        currentSize = sizeMult;

        // Update Cursor Scale
        cursor.scale.set(currentSize, currentSize, currentSize);

        // --- C. PINCH TRACKING (Click) ---
        // Distance between Thumb Tip (4) and Index Tip (8)
        const tTx = landmarks[4].x; const tTy = landmarks[4].y;
        const pinchDist = Math.hypot(iTx - tTx, iTy - tTy);

        // Threshold for pinch (usually < 0.05)
        if (pinchDist < 0.05) {
            if (cursor && cursor.material) {
                cursor.material.color.setHex(0xffffff); // Flash white when ready
                cursor.material.wireframe = false; // Solid when pinching
                cursor.material.opacity = 0.9;
            }

            // Simple debounce to prevent spamming blocks
            if (!isPinching && Date.now() - lastPinch > 400) {
                placeBlock();
                lastPinch = Date.now();
                isPinching = true;
            }
        } else {
            // Reset cursor
            if (cursor && cursor.material) {
                if (buildMode === 'free') {
                    cursor.material.color.set(document.getElementById('colorPicker').value);
                } else if (buildMode === 'building') {
                    cursor.material.color.set(buildingParts[selectedBuildingPart].color);
                } else if (buildMode === 'solar') {
                    cursor.material.color.set(solarObjects[selectedSolarObject].color);
                }
                cursor.material.wireframe = true;
                cursor.material.opacity = 0.5;
            }
            isPinching = false;
        }

        } // Close the one-hand else block

    } else {
        statusText.innerText = "No hand detected";
        statusDot.classList.remove('active');
        isRotatingCamera = false;
        if (cursor) cursor.visible = true;
    }
}

// --- 4. APP LOGIC ---

function animate() {
    requestAnimationFrame(animate);

    // Smooth movement logic (Lerp)
    curX += (targetX - curX) * 0.15;
    curY += (targetY - curY) * 0.15;
    
    if (cursor) {
        cursor.position.set(curX, curY, 0);
        
        // Rotate cursor slightly for visual flair
        cursor.rotation.x += 0.01;
        cursor.rotation.y += 0.01;
    }
    
    // Smooth camera rotation (when using 2 hands)
    if (isRotatingCamera) {
        cameraRotationY += (targetCameraRotationY - cameraRotationY) * 0.1;
        cameraRotationX += (targetCameraRotationX - cameraRotationX) * 0.1;
        
        // Apply rotation to camera
        const radius = 12; // Distance from center
        camera.position.x = Math.sin(cameraRotationY) * radius;
        camera.position.z = Math.cos(cameraRotationY) * radius;
        camera.position.y = 5 + Math.sin(cameraRotationX) * 5;
        
        camera.lookAt(0, 0, 0);
    }
    
    // Rotate solar system objects
    scene.traverse((child) => {
        if (child.isMesh && child.userData.rotationSpeed) {
            child.rotation.y += child.userData.rotationSpeed;
        }
    });

    renderer.render(scene, camera);
}
animate();

function placeBlock() {
    let mesh;
    
    if (buildMode === 'free') {
        // Free build mode - regular colored blocks
        const geometry = new THREE.BoxGeometry(currentSize, currentSize, currentSize);
        const colorVal = document.getElementById('colorPicker').value;
        const material = new THREE.MeshStandardMaterial({ 
            color: colorVal,
            roughness: 0.3,
            metalness: 0.1
        });
        
        mesh = new THREE.Mesh(geometry, material);
        mesh.position.copy(cursor.position);
        
        // Random slight rotation for "natural" tumbled look
        mesh.rotation.set(
            Math.random() * 0.2,
            Math.random() * 0.2,
            Math.random() * 0.2
        );
        
    } else if (buildMode === 'building') {
        // Building mode - predefined building parts
        const part = buildingParts[selectedBuildingPart];
        const geometry = new THREE.BoxGeometry(part.size[0], part.size[1], part.size[2]);
        const material = new THREE.MeshStandardMaterial({ 
            color: part.color,
            roughness: 0.5,
            metalness: 0.2,
            transparent: part.transparent || false,
            opacity: part.opacity || 1
        });
        
        mesh = new THREE.Mesh(geometry, material);
        mesh.position.copy(cursor.position);
        
        // Align building parts to grid
        mesh.position.x = Math.round(mesh.position.x);
        mesh.position.y = Math.round(mesh.position.y);
        
    } else if (buildMode === 'solar') {
        // Solar system mode - spheres representing celestial objects
        const obj = solarObjects[selectedSolarObject];
        const geometry = new THREE.SphereGeometry(obj.radius, 32, 32);
        const material = new THREE.MeshStandardMaterial({ 
            color: obj.color,
            roughness: 0.7,
            metalness: 0.1,
            emissive: obj.emissive || 0x000000,
            emissiveIntensity: obj.emissive ? 0.5 : 0
        });
        
        mesh = new THREE.Mesh(geometry, material);
        mesh.position.copy(cursor.position);
        
        // Add rings for Saturn
        if (obj.hasRing) {
            const ringGeometry = new THREE.RingGeometry(obj.radius * 1.5, obj.radius * 2.5, 64);
            const ringMaterial = new THREE.MeshBasicMaterial({ 
                color: 0xFFE4B5,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.6
            });
            const ring = new THREE.Mesh(ringGeometry, ringMaterial);
            ring.rotation.x = Math.PI / 2;
            mesh.add(ring);
        }
        
        // Add comet tail
        if (obj.hasTrail) {
            const trailGeometry = new THREE.ConeGeometry(0.2, 2, 8);
            const trailMaterial = new THREE.MeshBasicMaterial({ 
                color: 0xFFFFFF,
                transparent: true,
                opacity: 0.4
            });
            const trail = new THREE.Mesh(trailGeometry, trailMaterial);
            trail.position.z = -1.5;
            trail.rotation.x = Math.PI / 2;
            mesh.add(trail);
        }
    }
    
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
    
    // Add rotation animation for solar objects
    if (buildMode === 'solar') {
        mesh.userData.rotationSpeed = Math.random() * 0.01 + 0.005;
    }
}

// UI Event Listeners
document.getElementById('buildMode').addEventListener('change', (e) => {
    buildMode = e.target.value;
    
    // Show/hide appropriate panels
    document.getElementById('freeBuildPanel').style.display = buildMode === 'free' ? 'block' : 'none';
    document.getElementById('buildingPanel').style.display = buildMode === 'building' ? 'block' : 'none';
    document.getElementById('solarPanel').style.display = buildMode === 'solar' ? 'block' : 'none';
    
    // Update cursor appearance based on mode
    updateCursorForMode();
});

// Building part selection
document.querySelectorAll('.building-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        selectedBuildingPart = e.currentTarget.dataset.type;
        document.querySelectorAll('.building-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        document.getElementById('selectedPart').textContent = `Selected: ${buildingParts[selectedBuildingPart].name}`;
        updateCursorForMode();
    });
});

// Solar object selection
document.querySelectorAll('.solar-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        selectedSolarObject = e.currentTarget.dataset.type;
        document.querySelectorAll('.solar-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        document.getElementById('selectedPlanet').textContent = `Selected: ${solarObjects[selectedSolarObject].name}`;
        updateCursorForMode();
    });
});

function updateCursorForMode() {
    // Remove old cursor
    scene.remove(cursor);
    
    if (buildMode === 'free') {
        const cursorGeo = new THREE.BoxGeometry(1, 1, 1);
        const cursorMat = new THREE.MeshBasicMaterial({ 
            color: 0x38bdf8, 
            wireframe: true, 
            transparent: true, 
            opacity: 0.8 
        });
        cursor = new THREE.Mesh(cursorGeo, cursorMat);
    } else if (buildMode === 'building') {
        const part = buildingParts[selectedBuildingPart];
        const cursorGeo = new THREE.BoxGeometry(part.size[0], part.size[1], part.size[2]);
        const cursorMat = new THREE.MeshBasicMaterial({ 
            color: part.color, 
            wireframe: true, 
            transparent: true, 
            opacity: 0.6 
        });
        cursor = new THREE.Mesh(cursorGeo, cursorMat);
    } else if (buildMode === 'solar') {
        const obj = solarObjects[selectedSolarObject];
        const cursorGeo = new THREE.SphereGeometry(obj.radius, 16, 16);
        const cursorMat = new THREE.MeshBasicMaterial({ 
            color: obj.color, 
            wireframe: true, 
            transparent: true, 
            opacity: 0.6 
        });
        cursor = new THREE.Mesh(cursorGeo, cursorMat);
    }
    
    cursor.position.set(curX, curY, 0);
    scene.add(cursor);
}

document.getElementById('toggleGrid').addEventListener('click', () => {
    gridGroup.visible = !gridGroup.visible;
});

document.getElementById('resetCamera').addEventListener('click', () => {
    // Reset camera to default position
    cameraRotationY = 0;
    cameraRotationX = 0;
    targetCameraRotationY = 0;
    targetCameraRotationX = 0;
    camera.position.set(0, 5, 12);
    camera.lookAt(0, 0, 0);
});

document.getElementById('clearScene').addEventListener('click', () => {
    // Remove everything except lights, camera, grid, cursor
    const toRemove = [];
    scene.traverse((child) => {
        if (child.isMesh && child !== cursor && child.parent !== gridGroup) {
            toRemove.push(child);
        }
    });
    toRemove.forEach(obj => scene.remove(obj));
});

document.getElementById('colorPicker').addEventListener('input', (e) => {
     // Updates handled in animate loop via checking value
});

// Logout button
document.getElementById('logout-btn').addEventListener('click', () => {
    if (confirm('Are you sure you want to logout?')) {
        logout();
    }
});

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// --- 5. INITIALIZE AI ---
function updateLoaderText(text) {
    const loaderText = document.getElementById('loader-text');
    if (loaderText) loaderText.innerText = text;
}

updateLoaderText('Loading AI models...');

const hands = new Hands({locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
}});

hands.setOptions({
    maxNumHands: 2,  // Changed from 1 to 2 for rotation support
    modelComplexity: 0,  // Changed from 1 to 0 for faster loading
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});
hands.onResults(onResults);

updateLoaderText('Initializing camera...');

const cameraFeed = new Camera(videoElement, {
    onFrame: async () => {
        await hands.send({image: videoElement});
    },
    width: 640,  // Reduced from 1280 for faster processing
    height: 480  // Reduced from 720 for faster processing
});

// Start camera, handle errors
try {
    updateLoaderText('Requesting camera access...');
    cameraFeed.start().then(() => {
        updateLoaderText('Camera ready! Show your hand...');
    }).catch((e) => {
        updateLoaderText('Camera Error: ' + e.message);
        console.error('Camera error:', e);
    });
} catch (e) {
    updateLoaderText('Camera Error: ' + e.message);
    console.error('Camera error:', e);
}
