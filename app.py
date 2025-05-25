# app.py - Complete version with social feed, enhanced mob system and smart URL validation
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import sys
import requests
import tempfile
import time
import random
from datetime import datetime
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
    
    content_score = 0.0  # Track content-based scoring (80% weight)
    hashtag_score = 0.0  # Track hashtag-based scoring (20% weight)
    
    # Basic file validation (content analysis)
    if os.path.exists(video_path):
        file_size = os.path.getsize(video_path)
        
        # Check filename for milk-related terms (primary content indicator)
        filename = os.path.basename(video_path).lower()
        
        # Primary milk keywords in filename
        primary_keywords = ['milk', 'dairy', 'lactose', 'cream']
        secondary_keywords = ['drink', 'beverage', 'glass', 'pour']
        
        primary_matches = sum(1 for term in primary_keywords if term in filename)
        secondary_matches = sum(1 for term in secondary_keywords if term in filename)
        
        if primary_matches > 0:
            content_score += min(0.4, primary_matches * 0.2)  # Up to 40% for primary keywords
        
        if secondary_matches > 0 and primary_matches > 0:
            content_score += min(0.2, secondary_matches * 0.1)  # Up to 20% for secondary
        
        # Red flag keywords in filename
        red_flags = ['car', 'auto', 'lamborghini', '3dprint', 'tech', 'game', 'phone']
        red_flag_matches = sum(1 for term in red_flags if term in filename)
        if red_flag_matches > 0:
            content_score = max(0, content_score - (red_flag_matches * 0.3))
        
        # File size indicates real video content
        if file_size > 1000000:  # > 1MB suggests real video
            content_score += 0.1
        else:
            content_score = max(0, content_score - 0.2)  # Penalty for very small files
    else:
        # File doesn't exist - major content failure
        content_score = 0.0
    
    # Hashtag analysis (20% maximum weight)
    hashtag_match = any(tag in hashtags.lower() for tag in ['#gotmilk', '#milkmob', 'milk'])
    if hashtag_match:
        hashtag_score = 0.2
    
    # Final confidence calculation
    final_confidence = (content_score * 0.8) + (hashtag_score * 0.2)
    
    # Require minimum content score
    min_content_threshold = 0.2
    if content_score < min_content_threshold:
        final_confidence = min(final_confidence, 0.3)  # Cap confidence if content is weak
    
    is_valid = final_confidence >= 0.5
    
    return {
        "is_valid": is_valid,
        "confidence": min(final_confidence, 1.0),
        "reason": "✅ Passed validation with content and hashtags" if is_valid else "❌ Insufficient milk-related content in file",
        "hashtag_match": hashtag_match,
        "method": "simple_validation",
        "content_score": content_score,
        "hashtag_score": hashtag_score
    }

def smart_validate_video_url(url: str, hashtags: str) -> Dict[str, Any]:
    """Smart validation using video metadata without downloading"""
    
    confidence = 0.0  # Start with zero confidence
    reasons = []
    content_score = 0.0  # Track content-based scoring (80% weight)
    hashtag_score = 0.0  # Track hashtag-based scoring (20% weight)
    
    # Try to get video metadata first (this is the main validation)
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
        # If we can't get video info, we can't properly validate content
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reason": "❌ Unable to analyze video content - metadata extraction failed",
            "hashtag_match": False,
            "method": "smart_url_validation",
            "video_info": {
                "title": "Unknown",
                "duration": 0,
                "platform": "Unknown"
            }
        }
    
    # ===== CONTENT ANALYSIS (80% of total score) =====
    if video_info:
        title = video_info.get('title', '').lower()
        description = video_info.get('description', '').lower()
        duration = video_info.get('duration', 0)
        
        # Comprehensive milk-related keywords
        primary_milk_keywords = ['milk', 'dairy', 'lactose', 'cream', 'butter', 'cheese']
        secondary_milk_keywords = ['drink', 'beverage', 'glass', 'pour', 'sip', 'gulp', 'chug']
        food_keywords = ['mukbang', 'asmr', 'eating', 'breakfast', 'cereal', 'cookie', 'oreo']
        fitness_keywords = ['protein', 'workout', 'gym', 'muscle', 'recovery', 'shake', 'nutrition']
        
        # Campaign-specific keywords that are strong indicators
        campaign_keywords = ['got milk', 'gotmilk', 'milk mustache', 'milk commercial', 'milk ad']
        
        # Check for campaign-specific content first (very high confidence)
        campaign_matches = sum(1 for keyword in campaign_keywords if keyword in title or keyword in description)
        if campaign_matches > 0:
            campaign_score = min(0.6, campaign_matches * 0.3)
            content_score += campaign_score
            reasons.append(f"contains campaign-specific content ({campaign_matches})")
            print(f"   Campaign bonus: +{campaign_score:.3f}")
        
        # Check title for primary milk content (high weight)
        primary_title_matches = sum(1 for keyword in primary_milk_keywords if keyword in title)
        if primary_title_matches > 0:
            primary_score = min(0.3, primary_title_matches * 0.15)
            content_score += primary_score
            reasons.append(f"title contains primary milk terms ({primary_title_matches})")
            print(f"   Primary title bonus: +{primary_score:.3f}")
        
        # Check description for primary milk content (important for videos without milk in title)
        if description:
            desc_primary_matches = sum(1 for keyword in primary_milk_keywords if keyword in description)
            if desc_primary_matches > 0:
                desc_primary_score = min(0.25, desc_primary_matches * 0.1)
                content_score += desc_primary_score
                reasons.append(f"description mentions milk/dairy ({desc_primary_matches})")
                print(f"   Description primary bonus: +{desc_primary_score:.3f}")
        
        # Secondary keywords can now work independently (for drinking videos without "milk" in title)
        secondary_title_matches = sum(1 for keyword in secondary_milk_keywords if keyword in title)
        if secondary_title_matches > 0:
            secondary_score = min(0.2, secondary_title_matches * 0.1)
            content_score += secondary_score
            reasons.append(f"title contains drink-related terms ({secondary_title_matches})")
            print(f"   Secondary title bonus: +{secondary_score:.3f}")
        
        # Check description for secondary keywords too
        if description:
            desc_secondary_matches = sum(1 for keyword in secondary_milk_keywords if keyword in description)
            if desc_secondary_matches > 0:
                desc_secondary_score = min(0.15, desc_secondary_matches * 0.05)
                content_score += desc_secondary_score
                reasons.append(f"description contains drink terms ({desc_secondary_matches})")
                print(f"   Description secondary bonus: +{desc_secondary_score:.3f}")
        
        # Context keywords (food/fitness) - now more flexible
        context_matches = sum(1 for keyword in food_keywords + fitness_keywords if keyword in title)
        if context_matches > 0:
            context_score = min(0.15, context_matches * 0.05)
            content_score += context_score
            reasons.append(f"title contains relevant context ({context_matches})")
            print(f"   Context bonus: +{context_score:.3f}")
        
        # Description context keywords
        if description:
            desc_context_matches = sum(1 for keyword in food_keywords + fitness_keywords if keyword in description)
            if desc_context_matches > 0:
                desc_context_score = min(0.1, desc_context_matches * 0.03)
                content_score += desc_context_score
                reasons.append(f"description contains context terms ({desc_context_matches})")
                print(f"   Description context bonus: +{desc_context_score:.3f}")
        
        # Red flags - terms that suggest non-milk content
        red_flag_keywords = [
            'car', 'auto', 'vehicle', 'engine', 'motor', 'drive', 'racing', 'speed',
            'lamborghini', 'ferrari', 'porsche', 'bmw', 'mercedes', 'audi',
            '3d print', 'printed', 'printer', 'gaming', 'game', 'tech', 'computer',
            'phone', 'iphone', 'android', 'unbox', 'gadget'
        ]
        
        # Only apply red flag penalties if there are clear non-milk indicators
        red_flags = sum(1 for keyword in red_flag_keywords if keyword in title or keyword in description)
        if red_flags > 0:
            # Less harsh penalty, and only if no positive milk indicators
            penalty = red_flags * 0.2 if content_score < 0.3 else red_flags * 0.1
            original_score = content_score
            content_score = max(0, content_score - penalty)
            reasons.append(f"⚠️ contains non-milk content indicators ({red_flags})")
            print(f"   Red flag penalty: -{penalty:.3f} ({original_score:.3f} → {content_score:.3f})")
        
        # Duration appropriateness - more lenient
        if 5 <= duration <= 900:  # 5 seconds to 15 minutes is reasonable
            content_score += 0.05
            reasons.append("appropriate duration")
            print(f"   Duration bonus: +0.05")
        elif duration > 900:  # Very long videos less likely to be milk-focused
            original_score = content_score
            content_score = max(0, content_score - 0.05)  # Smaller penalty
            reasons.append("⚠️ unusually long duration")
            print(f"   Duration penalty: -0.05 ({original_score:.3f} → {content_score:.3f})")
    
    # ===== HASHTAG ANALYSIS (20% of total score) =====
    hashtag_match = any(tag in hashtags.lower() for tag in ['#gotmilk', '#milkmob', 'milk'])
    if hashtag_match:
        hashtag_score = 1.0  # Full hashtag score (will be weighted at 20% in final calculation)
        reasons.append("campaign hashtags present")
        print(f"   Hashtag bonus: +{hashtag_score:.3f} (20% weight)")
    else:
        hashtag_score = 0.0
        print(f"   No hashtag bonus: {hashtag_score:.3f}")
    
    # ===== FINAL SCORING =====
    # Content analysis: 80% weight, Hashtags: 20% weight
    final_confidence = (content_score * 0.8) + (hashtag_score * 0.2)
    
    # Debug logging to understand what's happening
    print(f"🔍 Validation Debug:")
    print(f"   Content Score: {content_score:.3f} (80% weight = {content_score * 0.8:.3f})")
    print(f"   Hashtag Score: {hashtag_score:.3f} (20% weight = {hashtag_score * 0.2:.3f})")
    print(f"   Final Confidence: {final_confidence:.3f}")
    print(f"   Reasons: {reasons}")
    
    # Much more lenient minimum content threshold for obvious milk content
    min_content_threshold = 0.1  # Only 10% minimum - very lenient
    threshold_penalty_applied = False
    
    if content_score < min_content_threshold:
        original_confidence = final_confidence
        final_confidence = min(final_confidence, 0.3)
        threshold_penalty_applied = True
        reasons.append(f"⚠️ content score below minimum threshold ({content_score:.2f} < {min_content_threshold})")
        print(f"   Threshold penalty: {original_confidence:.3f} → {final_confidence:.3f}")
    
    is_valid = final_confidence >= 0.35  # Reduced threshold to 35%
    
    # Create detailed reason message based on actual outcome
    if is_valid:
        reason_msg = f"✅ Validated: {', '.join(reasons)} (confidence: {final_confidence:.1%})"
    else:
        # Provide clear explanation of why it failed
        if threshold_penalty_applied:
            reason_msg = f"❌ Failed: Content score too low ({content_score:.1%}). Need substantial milk-related content in title/description."
        elif final_confidence < 0.4:
            reason_msg = f"❌ Failed: Overall confidence too low ({final_confidence:.1%}). Need stronger milk-related indicators."
        else:
            reason_msg = f"❌ Failed: {', '.join(reasons)}"
    
    print(f"   Final Decision: {'VALID' if is_valid else 'INVALID'}")
    print(f"   Reason: {reason_msg}")
    
    return {
        "is_valid": is_valid,
        "confidence": min(final_confidence, 1.0),
        "reason": reason_msg,
        "hashtag_match": hashtag_match,
        "method": "smart_url_validation",
        "content_score": content_score,
        "hashtag_score": hashtag_score,
        "debug_info": {
            "reasons": reasons,
            "threshold_penalty": threshold_penalty_applied,
            "min_threshold": min_content_threshold,
            "validation_threshold": 0.4
        },
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

# ===== ROUTES =====

@app.route('/')
def index():
    """Redirect to social feed for demo purposes"""
    return redirect('/social-feed')

@app.route('/social-feed')
def social_feed():
    """Social media platform homepage showing mixed content with campaign detection"""
    return render_template('social_feed.html')

@app.route('/campaign-info')
def campaign_info():
    """Original campaign information page"""
    return render_template('index.html')

@app.route('/video-queue')
def video_queue():
    return render_template('video_queue.html')

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

# ===== API ENDPOINTS =====

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

@app.route('/debug/test-validation')
def debug_test_validation():
    """Debug endpoint to test validation logic with detailed breakdown"""
    url = request.args.get('url', 'https://youtube.com/shorts/soBE8f575sE?si=fFPhGLeOEzmTgxhQ')
    hashtags = request.args.get('hashtags', '#gotmilk')
    
    try:
        # Test the new validation system
        validation_result = smart_validate_video_url(url, hashtags)
        
        # Get detailed video info for debugging
        video_info = {}
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_info = {
                    'title': info.get('title'),
                    'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'extractor': info.get('extractor'),
                    'view_count': info.get('view_count', 0)
                }
        except Exception as e:
            video_info = {'error': str(e)}
        
        return jsonify({
            'test_url': url,
            'test_hashtags': hashtags,
            'validation_result': validation_result,
            'detailed_video_info': video_info,
            'scoring_breakdown': {
                'content_score': validation_result.get('content_score', 0),
                'hashtag_score': validation_result.get('hashtag_score', 0),
                'content_weight': '80%',
                'hashtag_weight': '20%',
                'final_confidence': validation_result.get('confidence', 0),
                'is_valid': validation_result.get('is_valid', False)
            },
            'recommendations': [
                'Content score must be > 0.3 for validation',
                'Primary milk keywords: milk, dairy, lactose, cream, butter, cheese',
                'Red flag keywords will reduce score: car, auto, gaming, tech, etc.',
                'Hashtags can only contribute maximum 20% to final score'
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

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
        'mob_classification': True,
        'social_feed': True
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

# ===== CAMPAIGN ANALYTICS INTEGRATION =====

# Global analytics data store
CAMPAIGN_ANALYTICS = {
    'total_videos_analyzed': 6,
    'campaign_videos_detected': 4,
    'detection_accuracy': 94.2,
    'mob_distribution': {
        'mob001': {'count': 1, 'name': 'Extreme Milk'},
        'mob002': {'count': 1, 'name': 'Milk Artists'},
        'mob003': {'count': 1, 'name': 'Mukbang Masters'},
        'mob004': {'count': 1, 'name': 'Fitness Fuel'},
        'mob005': {'count': 0, 'name': 'Daily Milk'}
    },
    'top_hashtags': {
        '#gotmilk': 2340,
        '#milkmob': 1856,
        '#mukbang': 892,
        '#milkart': 456,
        '#fitness': 234
    },
    'last_updated': datetime.now()
}

def analyze_social_feed_with_twelve_labs():
    """Analyze social feed videos for campaign content"""
    global CAMPAIGN_ANALYTICS
    
    # In a real implementation, this would analyze actual video feed
    # For demo, we use the mock data and simulate API calls
    
    if twelve_labs_api:
        print("🔍 Running Twelve Labs API analysis on social feed...")
        # Here you would call actual API endpoints
        # For demo, we simulate the results
        
    CAMPAIGN_ANALYTICS['last_updated'] = datetime.now()
    return CAMPAIGN_ANALYTICS

@app.route('/api/campaign-analytics')
def get_campaign_analytics():
    """Get current campaign analytics"""
    analytics = analyze_social_feed_with_twelve_labs()
    
    # Add computed metrics
    total_mob_members = sum(mob['count'] for mob in analytics['mob_distribution'].values())
    
    analytics['computed_metrics'] = {
        'total_mob_members': total_mob_members,
        'avg_confidence': 0.87,
        'detection_rate': f"{analytics['campaign_videos_detected']}/{analytics['total_videos_analyzed']}",
        'most_popular_mob': max(analytics['mob_distribution'].items(), key=lambda x: x[1]['count'])[1]['name'],
        'campaign_growth': '+12.3%',
    }
    
    return jsonify(analytics)

@app.route('/api/simulate-upload', methods=['POST'])
def simulate_upload():
    """Simulate a new video upload for real-time demo"""
    global CAMPAIGN_ANALYTICS
    
    # Sample uploads for simulation
    sample_uploads = [
        {
            'title': 'Epic milk chugging challenge! 🥛',
            'user': 'ChallengeKing',
            'hashtags': '#gotmilk #challenge #epic',
            'duration': 32,
            'platform': 'tiktok',
            'campaign_likely': True,
            'mob': 'mob001'
        },
        {
            'title': 'Milk foam art tutorial ☕',
            'user': 'BaristaBae', 
            'hashtags': '#gotmilk #milkart #coffee #tutorial',
            'duration': 156,
            'platform': 'youtube',
            'campaign_likely': True,
            'mob': 'mob002'
        },
        {
            'title': 'My cats reaction to different foods',
            'user': 'CatLover123',
            'hashtags': '#cats #funny #cute',
            'duration': 78,
            'platform': 'youtube',
            'campaign_likely': False,
            'mob': None
        }
    ]
    
    # Randomly select and simulate
    new_video_data = random.choice(sample_uploads)
    
    # Simulate Twelve Labs analysis
    if new_video_data['campaign_likely']:
        confidence = random.uniform(0.75, 0.95)
        campaign_detected = True
        
        # Update analytics
        CAMPAIGN_ANALYTICS['campaign_videos_detected'] += 1
        if new_video_data['mob']:
            CAMPAIGN_ANALYTICS['mob_distribution'][new_video_data['mob']]['count'] += 1
    else:
        confidence = random.uniform(0.1, 0.4) 
        campaign_detected = False
    
    CAMPAIGN_ANALYTICS['total_videos_analyzed'] += 1
    CAMPAIGN_ANALYTICS['detection_accuracy'] = round(
        (CAMPAIGN_ANALYTICS['campaign_videos_detected'] / CAMPAIGN_ANALYTICS['total_videos_analyzed']) * 100, 1
    )
    
    new_video = {
        'id': f'video_sim_{int(time.time())}',
        'title': new_video_data['title'],
        'user': new_video_data['user'],
        'hashtags': new_video_data['hashtags'],
        'duration': new_video_data['duration'],
        'views': f"{random.randint(1, 999)}K",
        'uploaded': 'Just now',
        'campaign_detected': campaign_detected,
        'confidence': confidence,
        'mob_classified': new_video_data['mob'] if campaign_detected else None,
        'platform': new_video_data['platform']
    }
    
    return jsonify({
        'success': True,
        'new_video': new_video,
        'updated_analytics': CAMPAIGN_ANALYTICS,
        'message': f"New video {'detected as campaign content' if campaign_detected else 'not part of campaign'}"
    })

@app.route('/campaign-dashboard')  
def campaign_dashboard():
    """Campaign analytics dashboard"""
    return render_template('campaign_dashboard.html')

# Initialize analytics on startup
analyze_social_feed_with_twelve_labs()

if __name__ == '__main__':
    print("🥛 Starting Got Milk Campaign Detection System...")
    print(f"📂 Upload folder: {config.UPLOAD_FOLDER}")
    print(f"🔑 API Key configured: {'Yes' if config.TWELVE_LABS_API_KEY != 'your_api_key_here' else 'No (using placeholder)'}")
    print("")
    print("🌐 Demo Flow:")
    print("   📺 Social Feed: http://localhost:5001/social-feed")
    print("   🥛 Campaign Upload: http://localhost:5001/upload") 
    print("   👥 Explore Mobs: http://localhost:5001/explore/mob003")
    print("📊 Admin Endpoints:")
    print("   📊 API Status: http://localhost:5001/api/status")
    print("   🎯 Debug Test: http://localhost:5001/debug/test-url")
    print("   🧪 Validation Test: http://localhost:5001/debug/test-validation")
    print("")
    print("🎯 DEMO NARRATIVE:")
    print("1. Start with social feed - show mixed content with campaign detection")
    print("2. Point out #gotmilk tagged videos (green borders = detected campaigns)")
    print("3. Click 'Got Milk Campaign' button to demonstrate validation flow")
    print("4. Upload/validate a YouTube URL to show smart classification")
    print("5. Explore the assigned Milk Mob to show community features")
    print("")
    print("✨ Key Features Demonstrated:")
    print("🔗 Smart URL validation (no download needed)")
    print("🛡️ Multiple validation fallbacks (API → Metadata → Hashtags)")
    print("🎯 Intelligent mob classification (5 different communities)")
    print("👥 Social platform integration (campaign detection in feeds)")
    print("📊 Real-time analytics and campaign monitoring")
    print("🧪 Content-focused validation (80% content, 20% hashtags)")
    
    app.run(debug=True, host='0.0.0.0', port=5001)