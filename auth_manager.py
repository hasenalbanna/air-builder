"""
Authentication Manager for AI Hand Builder (Python Version)
Simple user authentication system with JSON storage
"""

import json
import os
import hashlib
from datetime import datetime

class AuthManager:
    def __init__(self, users_file='users.json'):
        self.users_file = users_file
        self.current_user = None
        self._load_users()
        
    def _load_users(self):
        """Load users from JSON file or create default users"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            # Create default demo accounts
            self.users = {
                'demo': {
                    'password': self._hash_password('demo123'),
                    'created': datetime.now().isoformat()
                },
                'admin': {
                    'password': self._hash_password('admin123'),
                    'created': datetime.now().isoformat()
                }
            }
            self._save_users()
    
    def _save_users(self):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def _hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def login(self, username, password):
        """
        Attempt to login with username and password
        Returns: (success: bool, message: str)
        """
        if username not in self.users:
            return False, "Username not found"
        
        hashed_password = self._hash_password(password)
        if self.users[username]['password'] != hashed_password:
            return False, "Incorrect password"
        
        self.current_user = username
        return True, f"Welcome back, {username}!"
    
    def register(self, username, password):
        """
        Register a new user
        Returns: (success: bool, message: str)
        """
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        if username in self.users:
            return False, "Username already exists"
        
        self.users[username] = {
            'password': self._hash_password(password),
            'created': datetime.now().isoformat()
        }
        self._save_users()
        
        return True, f"Account created successfully! Welcome, {username}!"
    
    def logout(self):
        """Logout current user"""
        user = self.current_user
        self.current_user = None
        return f"Goodbye, {user}!"
    
    def is_logged_in(self):
        """Check if a user is currently logged in"""
        return self.current_user is not None
    
    def get_current_user(self):
        """Get the current logged-in username"""
        return self.current_user
