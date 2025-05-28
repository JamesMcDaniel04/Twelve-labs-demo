import os
from pathlib import Path

class Config:
    """Configuration settings for Got Milk Campaign Detection System"""
    
    def __init__(self):
        # Twelve Labs API Configuration
        self.TWELVE_LABS_API_KEY = os.getenv('TWELVE_LABS_API_KEY', 'your_api_key_here')
        
        # Upload Configuration
        self.UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        self.MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB max file size (Twelve Labs limit)
        
        # Allowed video extensions (FFmpeg supported formats)
        self.ALLOWED_EXTENSIONS = {
            'mp4', 'mov', 'avi', 'webm', 'mkv', 'flv', 'wmv', 
            'm4v', '3gp', 'ogv', 'mts', 'm2ts', 'ts', 'mpg', 
            'mpeg', 'asf', 'vob'
        }
        
        # Flask Configuration
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        self.DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        
        # Ensure upload directory exists
        Path(self.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Upload folder configured: {self.UPLOAD_FOLDER}")
        print(f"📊 Max file size: {self.MAX_CONTENT_LENGTH / (1024*1024):.0f}MB")
        print(f"📋 Allowed extensions: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}")
        
    def is_allowed_file(self, filename):
        """Check if file extension is allowed"""
        if not filename or '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.ALLOWED_EXTENSIONS