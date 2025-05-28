# src/services/video_validator.py - UPDATED VERSION WITH URL SUPPORT
from typing import Dict, Any
from src.api.twelve_labs import TwelveLabsAPI

class VideoValidator:
    """Service to validate if a video is part of the milk campaign"""
    
    def __init__(self, twelve_labs_api: TwelveLabsAPI):
        """Initialize with API client"""
        self.api = twelve_labs_api
        
        # Define campaign hashtags
        self.campaign_hashtags = [
            "#gotmilk",
            "#milkmob", 
            "#gotmilk2025",
            "#milkchallenge",
            "#milkmovement"
        ]
        
    def validate(self, video_path: str, hashtags: str = "") -> Dict[str, Any]:
        """
        Validate if a video file is related to the milk campaign
        Returns validation result with confidence scores
        """
        print(f"🔍 Validating video file: {video_path}")
        
        # Check hashtags first (quick validation)
        hashtag_match = self._check_hashtags(hashtags)
        
        # Analyze video content using Twelve Labs
        try:
            analysis_result = self.api.analyze_milk_content(video_path)
            
            if "error" in analysis_result:
                # If API analysis fails, fall back to hashtag-only validation
                return {
                    "is_valid": hashtag_match,
                    "confidence": 0.5 if hashtag_match else 0.1,
                    "reason": "API analysis failed, validated based on hashtags only",
                    "hashtag_match": hashtag_match,
                    "api_error": analysis_result["error"],
                    "method": "twelve_labs_api_fallback"
                }
            
            milk_score = analysis_result.get("milk_score", 0)
            is_milk_related = analysis_result.get("is_milk_related", False)
            
            # Combine content analysis with hashtag validation
            final_confidence = self._calculate_final_confidence(milk_score, hashtag_match)
            is_valid = self._make_validation_decision(milk_score, hashtag_match)
            
            return {
                "is_valid": is_valid,
                "confidence": final_confidence,
                "milk_content_score": milk_score,
                "hashtag_match": hashtag_match,
                "reason": self._get_validation_reason(is_valid, milk_score, hashtag_match),
                "detailed_analysis": analysis_result.get("detailed_results", {}),
                "video_id": analysis_result.get("video_id"),
                "method": "twelve_labs_api"
            }
            
        except Exception as e:
            print(f"❌ Error during file validation: {e}")
            return {
                "is_valid": hashtag_match,
                "confidence": 0.3 if hashtag_match else 0.1,
                "reason": f"Validation error: {str(e)}. Validated based on hashtags only.",
                "hashtag_match": hashtag_match,
                "error": str(e),
                "method": "twelve_labs_api_error"
            }
    
    def validate_url(self, video_url: str, hashtags: str = "") -> Dict[str, Any]:
        """
        Validate if a video URL is related to the milk campaign
        Returns validation result with confidence scores
        """
        print(f"🔍 Validating video URL: {video_url}")
        
        # Check hashtags first (quick validation)
        hashtag_match = self._check_hashtags(hashtags)
        
        # Analyze video content using Twelve Labs
        try:
            analysis_result = self.api.analyze_milk_content_url(video_url)
            
            if "error" in analysis_result:
                # If API analysis fails, fall back to hashtag-only validation
                return {
                    "is_valid": hashtag_match,
                    "confidence": 0.5 if hashtag_match else 0.1,
                    "reason": f"API analysis failed ({analysis_result['error']}), validated based on hashtags only",
                    "hashtag_match": hashtag_match,
                    "api_error": analysis_result["error"],
                    "method": "twelve_labs_api_fallback"
                }
            
            milk_score = analysis_result.get("milk_score", 0)
            is_milk_related = analysis_result.get("is_milk_related", False)
            
            # Combine content analysis with hashtag validation
            final_confidence = self._calculate_final_confidence(milk_score, hashtag_match)
            is_valid = self._make_validation_decision(milk_score, hashtag_match)
            
            print(f"🧪 URL Validation Results:")
            print(f"   Milk Score: {milk_score:.3f}")
            print(f"   Hashtag Match: {hashtag_match}")
            print(f"   Final Confidence: {final_confidence:.3f}")
            print(f"   Is Valid: {is_valid}")
            
            return {
                "is_valid": is_valid,
                "confidence": final_confidence,
                "milk_content_score": milk_score,
                "hashtag_match": hashtag_match,
                "reason": self._get_validation_reason(is_valid, milk_score, hashtag_match),
                "detailed_analysis": analysis_result.get("detailed_results", {}),
                "video_id": analysis_result.get("video_id"),
                "method": "twelve_labs_api"
            }
            
        except Exception as e:
            print(f"❌ Error during URL validation: {e}")
            return {
                "is_valid": hashtag_match,
                "confidence": 0.3 if hashtag_match else 0.1,
                "reason": f"Validation error: {str(e)}. Validated based on hashtags only.",
                "hashtag_match": hashtag_match,
                "error": str(e),
                "method": "twelve_labs_api_error"
            }
    
    def _check_hashtags(self, hashtags: str) -> bool:
        """Check if provided hashtags match campaign hashtags"""
        if not hashtags:
            return False
            
        hashtag_list = [tag.strip().lower() for tag in hashtags.split()]
        
        # Check for exact matches
        campaign_matches = []
        for campaign_tag in self.campaign_hashtags:
            if campaign_tag in hashtag_list:
                campaign_matches.append(campaign_tag)
        
        # Also check for partial matches (e.g., "milk" in hashtags)
        milk_indicators = ['milk', 'gotmilk', 'milkmob']
        partial_matches = []
        for indicator in milk_indicators:
            if any(indicator in tag for tag in hashtag_list):
                partial_matches.append(indicator)
        
        has_match = len(campaign_matches) > 0 or len(partial_matches) > 0
        
        if has_match:
            print(f"   ✅ Hashtag matches found: {campaign_matches + partial_matches}")
        else:
            print(f"   ❌ No campaign hashtags found in: {hashtag_list}")
        
        return has_match
    
    def _calculate_final_confidence(self, milk_score: float, hashtag_match: bool) -> float:
        """Calculate final confidence score combining content and hashtags"""
        # Base confidence from content analysis (80% weight)
        confidence = milk_score * 0.8
        
        # Boost confidence if hashtags match (20% weight)
        if hashtag_match:
            confidence += 0.2
        
        # Ensure reasonable bounds
        return max(0.1, min(1.0, confidence))
    
    def _make_validation_decision(self, milk_score: float, hashtag_match: bool) -> bool:
        """Make final validation decision"""
        # Strong content match (API detected clear milk content)
        if milk_score >= 0.6:
            print(f"   ✅ Strong milk content detected: {milk_score:.3f}")
            return True
        
        # Moderate content match + hashtags
        if milk_score >= 0.3 and hashtag_match:
            print(f"   ✅ Moderate milk content + hashtags: {milk_score:.3f}")
            return True
        
        # Weak content but strong hashtag match (for edge cases)
        if hashtag_match and milk_score >= 0.1:
            print(f"   ✅ Weak content but valid hashtags: {milk_score:.3f}")
            return True
        
        # Very strong hashtag evidence even with minimal content
        if hashtag_match and milk_score >= 0.05:
            print(f"   ✅ Strong hashtag evidence: {milk_score:.3f}")
            return True
        
        print(f"   ❌ Failed validation: milk_score={milk_score:.3f}, hashtags={hashtag_match}")
        return False
    
    def _get_validation_reason(self, is_valid: bool, milk_score: float, hashtag_match: bool) -> str:
        """Generate human-readable validation reason"""
        if is_valid:
            if milk_score >= 0.6:
                return f"✅ Video clearly shows milk-related content (confidence: {milk_score:.1%})"
            elif milk_score >= 0.3 and hashtag_match:
                return f"✅ Video shows milk content and has appropriate hashtags (confidence: {milk_score:.1%})"
            elif hashtag_match:
                return f"✅ Video validated based on campaign hashtags (content: {milk_score:.1%})"
            else:
                return f"✅ Video passed validation (confidence: {milk_score:.1%})"
        else:
            if milk_score < 0.1:
                return f"❌ Video doesn't show milk-related content (confidence: {milk_score:.1%})"
            elif not hashtag_match:
                return f"❌ Video needs appropriate campaign hashtags like #GotMilk (content: {milk_score:.1%})"
            else:
                return f"❌ Video doesn't meet campaign criteria (confidence: {milk_score:.1%})"