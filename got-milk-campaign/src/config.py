# src/config.py
import os
from dotenv import load_dotenv

class Config:
    """Configuration management for the application"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        # Load environment variables from .env file
        load_dotenv()
        
        # API keys
        self.TWELVE_LABS_API_KEY = os.getenv('TWELVE_LABS_API_KEY', 'your_api_key_here')
        
        # Application settings
        self.UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
        self.ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}
        self.MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # 100MB
        
        # Twelve Labs settings
        self.TWELVE_LABS_INDEX_ID = os.getenv('TWELVE_LABS_INDEX_ID', None)  # We'll create this later