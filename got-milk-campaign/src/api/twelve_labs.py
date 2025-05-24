# src/api/twelve_labs.py - FIXED VERSION
import requests
import json
import time
import os
from typing import Dict, List, Any

class TwelveLabsAPI:
    """Integration with Twelve Labs Video Understanding API"""
    
    def __init__(self, api_key: str):
        """Initialize with API key"""
        self.api_key = api_key
        self.base_url = "https://api.twelvelabs.io/v1.2"
        self.headers = {
            "x-api-key": self.api_key
        }
        self.index_id = None
        
    def create_index(self, index_name: str = "milk-campaign-videos") -> str:
        """Create a new index for video analysis"""
        url = f"{self.base_url}/indexes"
        
        payload = {
            "index_name": index_name,
            "engines": [
                {
                    "engine_name": "marengo2.6",
                    "engine_options": ["visual", "conversation", "text_in_video", "logo"]
                }
            ],
            "addons": []
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 201:
                result = response.json()
                self.index_id = result["_id"]
                print(f"✅ Created index: {self.index_id}")
                return self.index_id
            else:
                print(f"❌ Failed to create index: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating index: {e}")
            return None
    
    def list_indexes(self) -> List[Dict]:
        """List all available indexes"""
        url = f"{self.base_url}/indexes"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                print(f"❌ Failed to list indexes: {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error listing indexes: {e}")
            return []
    
    def get_or_create_index(self) -> str:
        """Get existing index or create a new one"""
        # First try to get existing indexes
        indexes = self.list_indexes()
        
        # Look for our milk campaign index
        for index in indexes:
            if "milk" in index.get("index_name", "").lower():
                self.index_id = index["_id"]
                print(f"📋 Using existing index: {self.index_id}")
                return self.index_id
        
        # If no suitable index found, create one
        return self.create_index()
    
    def upload_video(self, video_path: str, metadata: Dict = None) -> str:
        """Upload a video for analysis"""
        if not self.index_id:
            self.get_or_create_index()
            
        if not self.index_id:
            print("❌ No index available for upload")
            return None
            
        url = f"{self.base_url}/tasks"
        
        try:
            with open(video_path, 'rb') as video_file:
                files = {
                    'video_file': (os.path.basename(video_path), video_file, 'video/mp4')
                }
                
                data = {
                    'index_id': self.index_id,
                    'language': 'en'
                }
                
                # Add metadata if provided
                if metadata:
                    data['metadata'] = json.dumps(metadata)
                
                # Use separate headers for multipart upload
                headers = {"x-api-key": self.api_key}
                
                response = requests.post(url, headers=headers, files=files, data=data)
                
                if response.status_code == 201:
                    task_id = response.json()["_id"]
                    print(f"📤 Video upload started. Task ID: {task_id}")
                    return task_id
                else:
                    print(f"❌ Upload failed: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error uploading video: {e}")
            return None
    
    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check the status of a video processing task"""
        url = f"{self.base_url}/tasks/{task_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Status check failed: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Error checking task status: {e}")
            return {}
    
    def wait_for_processing(self, task_id: str, timeout: int = 180) -> bool:
        """Wait for video processing to complete"""
        start_time = time.time()
        
        print("⏳ Processing video...")
        while (time.time() - start_time) < timeout:
            status_data = self.check_task_status(task_id)
            status = status_data.get('status')
            
            if status == 'ready':
                print("✅ Video processing completed!")
                return True
            elif status == 'failed':
                print(f"❌ Processing failed: {status_data.get('error', 'Unknown error')}")
                return False
            
            print(f"⏳ Status: {status}...")
            time.sleep(15)  # Check every 15 seconds
            
        print("⏰ Processing timed out")
        return False
    
    def search_videos(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for videos based on query"""
        if not self.index_id:
            print("❌ No index available for search")
            return []
            
        url = f"{self.base_url}/search"
        
        payload = {
            "query": query,
            "index_id": self.index_id,
            "search_options": ["visual", "conversation", "text_in_video"],
            "page_limit": limit
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                print(f"❌ Search failed: {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error searching videos: {e}")
            return []
    
    def analyze_milk_content(self, video_path: str) -> Dict[str, Any]:
        """Analyze video for milk-related content"""
        print(f"🔍 Analyzing video: {os.path.basename(video_path)}")
        
        try:
            # Upload video
            task_id = self.upload_video(video_path)
            if not task_id:
                return {"error": "Failed to upload video"}
            
            # Wait for processing
            if not self.wait_for_processing(task_id):
                return {"error": "Video processing failed or timed out"}
            
            # Get video ID from task
            task_info = self.check_task_status(task_id)
            video_id = task_info.get('video_id')
            
            if not video_id:
                return {"error": "Could not get video ID"}
            
            # Search for milk-related content
            milk_queries = [
                "person drinking milk",
                "glass of milk", 
                "milk container",
                "pouring milk",
                "milk mustache"
            ]
            
            results = {}
            total_confidence = 0
            
            for query in milk_queries:
                search_results = self.search_videos(query)
                
                # Find matches for our specific video
                video_matches = [r for r in search_results if r.get('video_id') == video_id]
                
                if video_matches:
                    # Get highest confidence score
                    confidence = max([match.get('confidence', 0) for match in video_matches])
                    results[query] = {
                        'confidence': confidence,
                        'matches': len(video_matches)
                    }
                    total_confidence += confidence
                else:
                    results[query] = {'confidence': 0, 'matches': 0}
            
            # Calculate overall milk content score
            milk_score = total_confidence / len(milk_queries) if milk_queries else 0
            
            return {
                "video_id": video_id,
                "milk_score": milk_score,
                "detailed_results": results,
                "is_milk_related": milk_score > 0.3  # Threshold for milk content
            }
            
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return {"error": str(e)}