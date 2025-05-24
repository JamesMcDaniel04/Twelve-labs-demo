# app.py - Complete version with enhanced mob system and smart URL validation
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import sys
import requests
import tempfile
from urllib.parse import urlparse
import re
from typing import Dict, Any

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config

# Try to import Twelve Labs components, but don't fail if they're not available
try:
    from src.api.twelve_labs import TwelveLabsAPI
    from src.services.video_validator import VideoValidator
    TWELVE_LABS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Twelve Labs components not available: {e}")
    TWELVE_LABS_AVAILABLE = False
    TwelveLabsAPI = None
    VideoValidator = None

app = Flask(__name__)

# Initialize configuration
config = Config()
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Initialize Twelve Labs API and services
twelve_labs_api = None
video_validator = None

if TWELVE_LABS_AVAILABLE:
    try:
        twelve_labs_api = TwelveLabsAPI(config.TWELVE_LABS_API_KEY)
        video_validator = VideoValidator(twelve_labs_api)
        print("✅ Twelve Labs API initialized successfully")
    except Exception as e:
        print(f"⚠️ Warning: Twelve Labs API initialization failed: {e}")
        twelve_labs_api = None
        video_validator = None

# Create upload folder if it doesn't exist
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# Mock database for storing mob memberships
MOB_VIDEOS = {
    'mob001': [  # Extreme Milk
        {'title': 'Skateboarding while drinking milk challenge!', 'user': 'SkaterMike23', 'duration': 23, 'confidence': 0.89},
        {'title': 'Parkour milk run - extreme edition', 'user': 'ParkourPro', 'duration': 45, 'confidence': 0.92}
    ],
    'mob002': [  # Milk Artists  
        {'title': 'Aesthetic milk photography tips', 'user': 'ArtisticAnna', 'duration': 67, 'confidence': 0.85},
        {'title': 'Milk splash art tutorial', 'user': 'CreativeCarl', 'duration': 120, 'confidence': 0.88}
    ],
    'mob003': [  # Mukbang Masters
        {'title': 'I LOVE MILK!!! #mukbang #asmr #milk #drink', 'user': 'MukbangQueen', 'duration': 10, 'confidence': 0.95},
        {'title': 'Trying different types of milk ASMR', 'user': 'ASMRAngel', 'duration': 180, 'confidence': 0.91}
    ],
    'mob004': [  # Fitness Fuel
        {'title': 'Post-workout protein milk shake', 'user': 'FitnessFred', 'duration': 34, 'confidence': 0.87},
        {'title': 'Why milk is perfect for muscle recovery', 'user': 'GymGuru', 'duration': 95, 'confidence': 0.83}
    ],
    'mob005': [  # Daily Milk
        {'title': 'Perfect cereal and milk breakfast', 'user': 'MomLife23', 'duration': 28, 'confidence': 0.79},
        {'title': 'Family milk time traditions', 'user': 'DadBlogger', 'duration': 156, 'confidence': 0.81}
    ]
}

def simple_validate_video(video_path: str, hashtags: str) -> Dict[str, Any]:
    """Simple validation without external API"""
    
    # Check hashtags
    hashtag_match = any(tag in hashtags.lower() for tag in ['#gotmilk', '#milkmob', 'milk'])
    
    # Basic file validation
    file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
    
    # Simple scoring based on available data
    confidence = 0.3  # Base confidence
    
    if hashtag_match:
        confidence += 0.4
    
    if file_size > 1000000:  # > 1MB suggests real video
        confidence += 0.2
    
    # Check filename for milk-related terms
    filename = os.path.basename(video_path).lower()
    if any(term in filename for term in ['milk', 'drink', 'glass', 'dairy']):
        confidence += 0.1
    
    is_valid = confidence >= 0.5
    
    return {
        "is_valid": is_valid,
        "confidence": min(confidence, 1.0),
        "reason": "✅ Passed basic validation with hashtags" if is_valid else "❌ Needs milk-related hashtags",
        "hashtag_match": hashtag_match,
        "method": "simple_validation"
    }

def smart_validate_video_url(url: str, hashtags: str) -> Dict[str, Any]:
    """Smart validation using video metadata without downloading"""
    
    confidence = 0.2  # Base confidence
    reasons = []
    
    # Check provided hashtags
    hashtag_match = any(tag in hashtags.lower() for tag in ['#gotmilk', '#milkmob', 'milk'])
    if hashtag_match:
        confidence += 0.3
        reasons.append("campaign hashtags")
    
    # Try to get video metadata
    video_info = {}
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)
            
    except Exception as e:
        print(f"⚠️ Could not extract video info: {e}")
    
    # Analyze video metadata
    if video_info:
        title = video_info.get('title', '').lower()
        description = video_info.get('description', '').lower()
        duration = video_info.get('duration', 0)
        
        # Check title for milk-related content
        milk_keywords = ['milk', 'dairy', 'drink', 'beverage', 'glass', 'pour', 'mukbang']
        title_matches = sum(1 for keyword in milk_keywords if keyword in title)
        
        if title_matches > 0:
            confidence += min(0.4, title_matches * 0.1)
            reasons.append(f"title contains milk-related terms ({title_matches})")
        
        # Check description for milk content
        if any(keyword in description for keyword in milk_keywords):
            confidence += 0.1
            reasons.append("description mentions milk")
        
        # Duration check (reasonable video length)
        if 5 <= duration <= 300:  # 5 seconds to 5 minutes
            confidence += 0.1
            reasons.append("appropriate duration")
        
        # Platform bonus (some platforms more likely to have campaign content)
        extractor = video_info.get('extractor', '').lower()
        if extractor in ['youtube', 'tiktok', 'instagram']:
            confidence += 0.05
            reasons.append(f"from {extractor}")
    
    is_valid = confidence >= 0.5
    confidence = min(confidence, 1.0)
    
    return {
        "is_valid": is_valid,
        "confidence": confidence,
        "reason": f"✅ Validated: {', '.join(reasons)}" if is_valid else f"❌ Low confidence: {', '.join(reasons) if reasons else 'insufficient milk-related content'}",
        "hashtag_match": hashtag_match,
        "method": "smart_url_validation",
        "video_info": {
            "title": video_info.get('title', 'Unknown'),
            "duration": video_info.get('duration', 0),
            "platform": video_info.get('extractor', 'Unknown')
        }
    }

def classify_into_mob(video_info: dict, hashtags: str, validation_result: dict) -> dict:
    """Classify video into appropriate Milk Mob based on content analysis"""
    
    # Extract analyzable content
    title = video_info.get('title', '').lower()
    platform = video_info.get('platform', '').lower()
    duration = video_info.get('duration', 0)
    hashtags_lower = hashtags.lower()
    
    # All available mobs
    mobs = {
        'extreme_milk': {
            'id': 'mob001',
            'name': 'Extreme Milk',
            'description': 'Adventurous milk drinking with sports, stunts, and daring activities',
            'keywords': ['extreme', 'stunt', 'skateboard', 'bike', 'jump', 'trick', 'adventure', 'dare'],
            'hashtags': ['#extrememilk', '#stunts', '#adventure'],
            'icon': '🏄‍♂️',
            'color': '#ff6b35',
            'member_count': 23
        },
        'milk_artists': {
            'id': 'mob002', 
            'name': 'Milk Artists',
            'description': 'Creative artistic expressions involving milk - art, photography, aesthetics',
            'keywords': ['art', 'creative', 'aesthetic', 'photo', 'picture', 'beautiful', 'artistic', 'paint'],
            'hashtags': ['#milkart', '#aesthetic', '#creative'],
            'icon': '🎨',
            'color': '#4ecdc4',
            'member_count': 31
        },
        'mukbang_masters': {
            'id': 'mob003',
            'name': 'Mukbang Masters', 
            'description': 'Food enthusiasts featuring milk in eating shows and food content',
            'keywords': ['mukbang', 'asmr', 'eating', 'food', 'taste', 'review', 'delicious'],
            'hashtags': ['#mukbang', '#asmr', '#foodie'],
            'icon': '🍽️',
            'color': '#45b7d1',
            'member_count': 67
        },
        'fitness_fuel': {
            'id': 'mob004',
            'name': 'Fitness Fuel',
            'description': 'Athletes and fitness enthusiasts using milk for workout nutrition',
            'keywords': ['workout', 'gym', 'fitness', 'protein', 'muscle', 'training', 'exercise', 'athlete'],
            'hashtags': ['#fitnessmilk', '#protein', '#workout'],
            'icon': '💪',
            'color': '#96ceb4',
            'member_count': 45
        },
        'daily_milk': {
            'id': 'mob005',
            'name': 'Daily Milk',
            'description': 'Everyday milk moments - breakfast, cooking, family time',
            'keywords': ['breakfast', 'morning', 'cereal', 'coffee', 'cooking', 'family', 'home', 'daily'],
            'hashtags': ['#dailymilk', '#breakfast', '#family'],
            'icon': '🥛',
            'color': '#feca57',
            'member_count': 89
        }
    }
    
    # Scoring system
    mob_scores = {}
    
    for mob_key, mob_data in mobs.items():
        score = 0
        matched_reasons = []
        
        # Check title keywords
        title_matches = sum(1 for keyword in mob_data['keywords'] if keyword in title)
        if title_matches > 0:
            score += title_matches * 0.3
            matched_reasons.append(f"title keywords ({title_matches})")
        
        # Check hashtags
        hashtag_matches = sum(1 for hashtag in mob_data['hashtags'] if hashtag in hashtags_lower)
        if hashtag_matches > 0:
            score += hashtag_matches * 0.4
            matched_reasons.append(f"hashtag match ({hashtag_matches})")
        
        # Platform bonus
        if platform == 'youtube' and mob_key in ['mukbang_masters', 'fitness_fuel']:
            score += 0.1
        elif platform == 'tiktok' and mob_key in ['extreme_milk', 'milk_artists']:
            score += 0.1
        elif platform == 'instagram' and mob_key == 'milk_artists':
            score += 0.1
        
        # Duration-based classification
        if duration > 0:
            if duration < 30 and mob_key == 'extreme_milk':  # Short clips often stunts
                score += 0.1
            elif duration > 60 and mob_key == 'mukbang_masters':  # Longer videos for mukbang
                score += 0.1
            elif 15 <= duration <= 45 and mob_key == 'daily_milk':  # Medium length for daily content
                score += 0.1
        
        mob_scores[mob_key] = {
            'score': score,
            'reasons': matched_reasons,
            'mob_data': mob_data
        }
    
    # Find best match
    best_mob_key = max(mob_scores.keys(), key=lambda k: mob_scores[k]['score'])
    best_match = mob_scores[best_mob_key]
    
    # Fallback to Daily Milk if no strong matches
    if best_match['score'] < 0.2:
        best_mob_key = 'daily_milk'
        best_match = mob_scores['daily_milk']
        best_match['reasons'] = ['general milk content']
    
    return {
        'mob_id': best_match['mob_data']['id'],
        'mob_key': best_mob_key,
        'mob_name': best_match['mob_data']['name'],
        'mob_description': best_match['mob_data']['description'],
        'mob_icon': best_match['mob_data']['icon'],
        'mob_color': best_match['mob_data']['color'],
        'match_score': best_match['score'],
        'match_reasons': best_match['reasons'],
        'all_mobs': mobs  # For showing other available mobs
    }

@app.route('/')
def index():
    """Home page with campaign information"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Handle video upload (file or URL) and validation"""
    if request.method == 'POST':
        try:
            hashtags = request.form.get('hashtags', '')
            video_url = request.form.get('video_url', '').strip()
            upload_type = request.form.get('upload_type', 'file')
            
            if upload_type == 'url' and video_url:
                # Handle URL upload with smart validation (no download needed)
                print(f"📺 Processing video URL: {video_url}")
                
                # Validate URL
                if not _is_valid_video_url(video_url):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid video URL. Please provide a direct link to a video file or supported platform URL.'
                    })
                
                # Use smart validation (no download needed)
                print("🔍 Using smart URL validation...")
                validation_result = smart_validate_video_url(video_url, hashtags)
                
                if validation_result['is_valid']:
                    # Classify into mob
                    video_info = validation_result.get('video_info', {})
                    mob_classification = classify_into_mob(video_info, hashtags, validation_result)
                    
                    # Add to mob (simulate)
                    new_video = {
                        'title': video_info.get('title', 'User Video'),
                        'user': 'You',
                        'duration': video_info.get('duration', 0),
                        'confidence': validation_result['confidence']
                    }
                    
                    if mob_classification['mob_id'] not in MOB_VIDEOS:
                        MOB_VIDEOS[mob_classification['mob_id']] = []
                    MOB_VIDEOS[mob_classification['mob_id']].append(new_video)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Video validated and classified successfully!',
                        'mob_name': mob_classification['mob_name'],
                        'mob_id': mob_classification['mob_id'],
                        'mob_icon': mob_classification['mob_icon'],
                        'mob_description': mob_classification['mob_description'],
                        'mob_color': mob_classification['mob_color'],
                        'confidence': validation_result['confidence'],
                        'reason': validation_result['reason'],
                        'source': 'URL',
                        'validation_method': validation_result['method'],
                        'mob_match_reasons': mob_classification['match_reasons'],
                        'video_info': video_info
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': validation_result['reason'],
                        'confidence': validation_result['confidence'],
                        'video_info': validation_result.get('video_info', {})
                    })
                
            elif upload_type == 'file':
                # Handle file upload
                if 'video' not in request.files:
                    return jsonify({'success': False, 'error': 'No video file uploaded'})
                
                file = request.files['video']
                
                if file.filename == '':
                    return jsonify({'success': False, 'error': 'No file selected'})
                
                # Check file extension
                if not _allowed_file(file.filename):
                    return jsonify({
                        'success': False, 
                        'error': 'File type not supported. Please use MP4, MOV, AVI, or WEBM files.'
                    })
                
                # Save the file
                filename = file.filename
                file_path = os.path.join(config.UPLOAD_FOLDER, filename)
                file.save(file_path)
                print(f"📁 File saved: {file_path}")
                
                # Validate file content with fallback
                if video_validator:
                    try:
                        print("🔍 Starting video validation...")
                        validation_result = video_validator.validate(file_path, hashtags)
                    except Exception as e:
                        print(f"⚠️ API validation failed: {e}")
                        print("🔄 Using simple validation...")
                        validation_result = simple_validate_video(file_path, hashtags)
                else:
                    print("🔄 Using simple validation (API not available)...")
                    validation_result = simple_validate_video(file_path, hashtags)
                
                if validation_result['is_valid']:
                    # Create video info for classification
                    video_info = {
                        'title': filename,
                        'duration': 0,  # Could extract from file metadata
                        'platform': 'upload'
                    }
                    
                    # Classify into mob
                    mob_classification = classify_into_mob(video_info, hashtags, validation_result)
                    
                    # Add to mob
                    new_video = {
                        'title': filename,
                        'user': 'You',
                        'duration': 0,
                        'confidence': validation_result['confidence']
                    }
                    
                    if mob_classification['mob_id'] not in MOB_VIDEOS:
                        MOB_VIDEOS[mob_classification['mob_id']] = []
                    MOB_VIDEOS[mob_classification['mob_id']].append(new_video)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Video validated and classified successfully!',
                        'mob_name': mob_classification['mob_name'],
                        'mob_id': mob_classification['mob_id'],
                        'mob_icon': mob_classification['mob_icon'],
                        'mob_description': mob_classification['mob_description'],
                        'mob_color': mob_classification['mob_color'],
                        'confidence': validation_result['confidence'],
                        'reason': validation_result['reason'],
                        'source': 'Upload',
                        'validation_method': validation_result.get('method', 'api_validation'),
                        'mob_match_reasons': mob_classification['match_reasons']
                    })
                else:
                    # Clean up uploaded file if validation fails
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    
                    return jsonify({
                        'success': False,
                        'error': validation_result['reason'],
                        'confidence': validation_result['confidence']
                    })
                    
            else:
                return jsonify({
                    'success': False,
                    'error': 'Please provide either a video file or a valid video URL.'
                })
                    
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(e)}'
            })
    
    return render_template('upload.html')

@app.route('/explore/<mob_id>')
def explore_mob(mob_id):
    """Explore videos in a specific mob"""
    
    # Get all available mobs for navigation
    all_mobs = {
        'extreme_milk': {
            'id': 'mob001',
            'name': 'Extreme Milk',
            'description': 'Adventurous milk drinking with sports, stunts, and daring activities',
            'icon': '🏄‍♂️',
            'color': '#ff6b35',
            'member_count': 23
        },
        'milk_artists': {
            'id': 'mob002', 
            'name': 'Milk Artists',
            'description': 'Creative artistic expressions involving milk - art, photography, aesthetics',
            'icon': '🎨',
            'color': '#4ecdc4',
            'member_count': 31
        },
        'mukbang_masters': {
            'id': 'mob003',
            'name': 'Mukbang Masters', 
            'description': 'Food enthusiasts featuring milk in eating shows and food content',
            'icon': '🍽️',
            'color': '#45b7d1',
            'member_count': 67
        },
        'fitness_fuel': {
            'id': 'mob004',
            'name': 'Fitness Fuel',
            'description': 'Athletes and fitness enthusiasts using milk for workout nutrition',
            'icon': '💪',
            'color': '#96ceb4',
            'member_count': 45
        },
        'daily_milk': {
            'id': 'mob005',
            'name': 'Daily Milk',
            'description': 'Everyday milk moments - breakfast, cooking, family time',
            'icon': '🥛',
            'color': '#feca57',
            'member_count': 89
        }
    }
    
    # Find current mob info
    current_mob = None
    for mob_key, mob_data in all_mobs.items():
        if mob_data['id'] == mob_id:
            current_mob = mob_data
            break
    
    if not current_mob:
        # Default to first mob if not found
        current_mob = list(all_mobs.values())[0]
        mob_id = current_mob['id']
    
    # Get videos for this mob
    videos = MOB_VIDEOS.get(mob_id, [])
    
    # Calculate average confidence
    avg_confidence = 0
    if videos:
        avg_confidence = round(sum(v['confidence'] for v in videos) / len(videos) * 100)
    
    current_mob['avg_confidence'] = avg_confidence
    current_mob['member_count'] = len(videos) + current_mob.get('member_count', 0)
    
    # Get other mobs for sidebar (exclude current)
    other_mobs = {k: v for k, v in all_mobs.items() if v['id'] != mob_id}
    
    return render_template('explore.html', 
                         mob_id=mob_id, 
                         videos=videos,
                         mob_info=current_mob,
                         other_mobs=other_mobs,
                         latest_video_title=videos[-1]['title'] if videos else None)

def _is_valid_video_url(url):
    """Validate if URL is a valid video URL"""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check for direct video file extensions
        video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv']
        if any(url.lower().endswith(ext) for ext in video_extensions):
            return True
        
        # Check for supported platforms
        supported_domains = [
            'youtube.com', 'youtu.be',
            'vimeo.com',
            'tiktok.com',
            'instagram.com',
            'twitter.com', 'x.com',
            'facebook.com',
            'drive.google.com',
            'dropbox.com',
            'reddit.com'
        ]
        
        domain = parsed.netloc.lower()
        return any(supported_domain in domain for supported_domain in supported_domains)
        
    except:
        return False

@app.route('/api/video-preview')
def video_preview():
    """Get video preview information from URL"""
    url = request.args.get('url', '')
    
    try:
        # Try to use yt-dlp for preview
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return jsonify({
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'platform': info.get('extractor', 'Unknown'),
                    'view_count': info.get('view_count', 0)
                })
        except ImportError:
            # Fallback: basic URL validation
            return jsonify({
                'title': 'Video Preview',
                'duration': 0,
                'uploader': 'Unknown',
                'supported': _is_valid_video_url(url)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/validate-url')
def validate_url():
    """API endpoint to validate video URL"""
    url = request.args.get('url', '')
    is_valid = _is_valid_video_url(url)
    
    return jsonify({
        'valid': is_valid,
        'supported': is_valid
    })

@app.route('/debug/test-url')
def debug_test_url():
    """Debug endpoint to test URL downloading"""
    url = request.args.get('url', 'https://youtube.com/shorts/soBE8f575sE?si=fFPhGLeOEzmTgxhQ')
    
    try:
        # Test yt-dlp availability
        try:
            import yt_dlp
            ytdlp_available = True
        except ImportError:
            ytdlp_available = False
        
        # Test URL validation
        url_valid = _is_valid_video_url(url)
        
        # Try to get info without downloading
        info = {}
        if ytdlp_available:
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    info = {
                        'title': info.get('title'),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'extractor': info.get('extractor')
                    }
            except Exception as e:
                info = {'error': str(e)}
        
        # Test smart validation
        smart_validation = {}
        if ytdlp_available:
            smart_validation = smart_validate_video_url(url, '#gotmilk')
        
        return jsonify({
            'url': url,
            'yt_dlp_available': ytdlp_available,
            'url_valid': url_valid,
            'video_info': info,
            'twelve_labs_available': TWELVE_LABS_AVAILABLE,
            'smart_validation': smart_validation
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/status')
def api_status():
    """Check API status"""
    status = {
        'twelve_labs_api': twelve_labs_api is not None,
        'video_validator': video_validator is not None,
        'upload_folder': os.path.exists(config.UPLOAD_FOLDER),
        'url_upload_supported': True,
        'yt_dlp_available': False,
        'fallback_validation': True,
        'smart_url_validation': True,
        'mob_classification': True
    }
    
    # Check yt-dlp availability
    try:
        import yt_dlp
        status['yt_dlp_available'] = True
    except ImportError:
        status['yt_dlp_available'] = False
    
    return jsonify(status)

def _allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

if __name__ == '__main__':
    print("🥛 Starting Got Milk Campaign app...")
    print(f"📂 Upload folder: {config.UPLOAD_FOLDER}")
    print(f"🔑 API Key configured: {'Yes' if config.TWELVE_LABS_API_KEY != 'your_api_key_here' else 'No (using placeholder)'}")
    print("🌐 Visit: http://localhost:5001")
    print("📊 Check API status: http://localhost:5001/api/status")
    print("🔗 URL upload with smart validation enabled")
    print("🛡️ Multiple validation fallbacks enabled")
    print("🎯 Enhanced mob classification system")
    print("👥 5 different Milk Mobs available")
    print("🎯 Debug endpoint: http://localhost:5001/debug/test-url")
    
    app.run(debug=True, host='0.0.0.0', port=5001)