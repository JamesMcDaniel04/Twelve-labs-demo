# src/utils/url_handler.py
import yt_dlp
import tempfile
import os
from typing import Optional, Dict, Any

class VideoURLHandler:
    """Handle downloading videos from various platforms"""
    
    def __init__(self):
        self.supported_platforms = [
            'youtube.com', 'youtu.be',
            'tiktok.com',
            'instagram.com',
            'vimeo.com',
            'twitter.com', 'x.com',
            'facebook.com',
            'reddit.com'
        ]
        
    def is_supported_url(self, url: str) -> bool:
        """Check if URL is from a supported platform"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check direct video files
            video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
            if any(url.lower().endswith(ext) for ext in video_extensions):
                return True
                
            # Check supported platforms
            return any(platform in domain for platform in self.supported_platforms)
            
        except Exception:
            return False
    
    def download_video(self, url: str, max_duration: int = 300) -> Optional[str]:
        """
        Download video from URL and return temporary file path
        max_duration: maximum video duration in seconds (5 minutes default)
        """
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_path = temp_file.name
            temp_file.close()
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[height<=720]/best',  # Max 720p to save bandwidth
                'outtmpl': temp_path,
                'max_duration': max_duration,
                'no_warnings': True,
                'quiet': True,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
            
            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(url, download=False)
                
                # Check duration
                duration = info.get('duration', 0)
                if duration > max_duration:
                    raise Exception(f"Video too long ({duration}s). Max allowed: {max_duration}s")
                
                # Check if it's likely to contain milk-related content
                title = info.get('title', '').lower()
                description = info.get('description', '').lower()
                
                # Download the video
                ydl.download([url])
                
                print(f"✅ Downloaded video: {info.get('title', 'Unknown')}")
                print(f"📏 Duration: {duration}s")
                
                return temp_path
                
        except Exception as e:
            print(f"❌ Failed to download video: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return None
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '')[:200] + '...',
                    'thumbnail': info.get('thumbnail'),
                    'platform': info.get('extractor', 'Unknown')
                }
                
        except Exception as e:
            print(f"❌ Failed to get video info: {e}")
            return {
                'title': 'Unknown',
                'duration': 0,
                'uploader': 'Unknown',
                'error': str(e)
            }
    
    def cleanup_temp_file(self, file_path: str):
        """Clean up temporary downloaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Cleaned up temp file: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup temp file: {e}")

# Example usage functions
def download_video_from_url(url: str) -> Optional[str]:
    """Convenience function to download video from URL"""
    handler = VideoURLHandler()
    
    if not handler.is_supported_url(url):
        print(f"❌ Unsupported URL: {url}")
        return None
    
    return handler.download_video(url)

def get_video_preview(url: str) -> Dict[str, Any]:
    """Get video preview information"""
    handler = VideoURLHandler()
    return handler.get_video_info(url)