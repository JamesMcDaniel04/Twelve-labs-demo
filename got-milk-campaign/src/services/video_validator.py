# src/services/video_validator.py
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
        Validate if a video is related to the milk campaign
        Returns validation result with confidence scores
        """
        print(f"🔍 Validating video: {video_path}")
        
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
                    "api_error": analysis_result["error"]
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
                "video_id": analysis_result.get("video_id")
            }
            
        except Exception as e:
            print(f"❌ Error during validation: {e}")
            return {
                "is_valid": hashtag_match,
                "confidence": 0.3 if hashtag_match else 0.1,
                "reason": f"Validation error: {str(e)}. Validated based on hashtags only.",
                "hashtag_match": hashtag_match,
                "error": str(e)
            }
    
    def _check_hashtags(self, hashtags: str) -> bool:
        """Check if provided hashtags match campaign hashtags"""
        if not hashtags:
            return False
            
        hashtag_list = [tag.strip().lower() for tag in hashtags.split()]
        return any(campaign_tag in hashtag_list for campaign_tag in self.campaign_hashtags)
    
    def _calculate_final_confidence(self, milk_score: float, hashtag_match: bool) -> float:
        """Calculate final confidence score combining content and hashtags"""
        # Base confidence from content analysis
        confidence = milk_score
        
        # Boost confidence if hashtags match
        if hashtag_match:
            confidence = min(1.0, confidence + 0.2)
        
        # Ensure minimum confidence
        return max(0.1, confidence)
    
    def _make_validation_decision(self, milk_score: float, hashtag_match: bool) -> bool:
        """Make final validation decision"""
        # Strong content match
        if milk_score >= 0.6:
            return True
        
        # Moderate content match + hashtags
        if milk_score >= 0.3 and hashtag_match:
            return True
        
        # Weak content but strong hashtag match
        if hashtag_match and milk_score >= 0.1:
            return True
        
        return False
    
    def _get_validation_reason(self, is_valid: bool, milk_score: float, hashtag_match: bool) -> str:
        """Generate human-readable validation reason"""
        if is_valid:
            if milk_score >= 0.6:
                return "✅ Video clearly shows milk-related content"
            elif milk_score >= 0.3 and hashtag_match:
                return "✅ Video shows milk content and has appropriate hashtags"
            elif hashtag_match:
                return "✅ Video validated based on campaign hashtags"
            else:
                return "✅ Video passed validation"
        else:
            if milk_score < 0.1:
                return "❌ Video doesn't show milk-related content"
            elif not hashtag_match:
                return "❌ Video needs appropriate campaign hashtags like #GotMilk"
            else:
                return "❌ Video doesn't meet campaign criteria"