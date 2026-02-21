// Simple Authentication System
// For production, use a real backend with secure authentication

// Store users in localStorage (for demo purposes only)
const STORAGE_KEY = 'aiHandBuilder_users';
const SESSION_KEY = 'aiHandBuilder_session';

// Default demo users
const DEFAULT_USERS = [
    { username: 'demo', password: 'demo123' },
    { username: 'admin', password: 'admin123' }
];

// Initialize users in localStorage if not exists
function initializeUsers() {
    if (!localStorage.getItem(STORAGE_KEY)) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_USERS));
    }
}

// Get all users
function getUsers() {
    const usersJson = localStorage.getItem(STORAGE_KEY);
    return usersJson ? JSON.parse(usersJson) : [];
}

// Add new user
function registerUser(username, password) {
    const users = getUsers();
    
    // Check if username already exists
    if (users.find(u => u.username === username)) {
        return { success: false, message: 'Username already exists' };
    }
    
    // Add new user
    users.push({ username, password });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(users));
    
    return { success: true, message: 'Registration successful' };
}

// Validate login
function validateLogin(username, password) {
    const users = getUsers();
    const user = users.find(u => u.username === username && u.password === password);
    
    if (user) {
        // Create session
        const session = {
            username: user.username,
            loginTime: new Date().toISOString()
        };
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        return { success: true, user: user.username };
    }
    
    return { success: false, message: 'Invalid username or password' };
}

// Check if user is logged in
function isLoggedIn() {
    const session = localStorage.getItem(SESSION_KEY);
    return session !== null;
}

// Get current session
function getSession() {
    const sessionJson = localStorage.getItem(SESSION_KEY);
    return sessionJson ? JSON.parse(sessionJson) : null;
}

// Logout
function logout() {
    localStorage.removeItem(SESSION_KEY);
    window.location.href = 'login.html';
}

// Initialize users on load
initializeUsers();

// Login Form Handler
if (document.getElementById('loginForm')) {
    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('error-message');
    const loginText = document.getElementById('loginText');
    const loginSpinner = document.getElementById('loginSpinner');
    
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        // Clear previous error
        errorMessage.classList.remove('show');
        errorMessage.textContent = '';
        
        // Show loading state
        loginText.textContent = 'Signing in...';
        loginSpinner.classList.remove('hidden');
        loginForm.querySelector('.btn-login').disabled = true;
        
        // Simulate network delay for better UX
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Validate credentials
        const result = validateLogin(username, password);
        
        if (result.success) {
            // Success - redirect to main app
            loginText.textContent = 'Success! Redirecting...';
            await new Promise(resolve => setTimeout(resolve, 500));
            window.location.href = 'app.html';
        } else {
            // Show error
            errorMessage.textContent = result.message;
            errorMessage.classList.add('show');
            
            // Reset button
            loginText.textContent = 'Sign In';
            loginSpinner.classList.add('hidden');
            loginForm.querySelector('.btn-login').disabled = false;
        }
    });
    
    // Register link handler
    document.getElementById('registerLink').addEventListener('click', (e) => {
        e.preventDefault();
        
        const username = prompt('Enter a username:');
        if (!username) return;
        
        const password = prompt('Enter a password:');
        if (!password) return;
        
        const result = registerUser(username, password);
        
        if (result.success) {
            alert('Registration successful! You can now login.');
            document.getElementById('username').value = username;
        } else {
            alert(result.message);
        }
    });
}

// Protect app pages - redirect to login if not authenticated
function protectPage() {
    if (!isLoggedIn() && !window.location.pathname.includes('login.html')) {
        window.location.href = 'login.html';
    }
}

// Display welcome message on app page
function displayWelcome() {
    const session = getSession();
    if (session && document.getElementById('welcome-user')) {
        document.getElementById('welcome-user').textContent = `Welcome, ${session.username}!`;
    }
}
