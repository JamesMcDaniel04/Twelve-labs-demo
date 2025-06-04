# Got Milk Campaign Detection System

A sophisticated AI-powered video content detection system that automatically identifies and validates milk-related campaign content using Twelve Labs' multimodal video understanding API.

## 🎯 Overview

This Flask web application simulates a social media platform that can automatically detect and validate "Got Milk" campaign videos. It uses advanced AI to analyze video content for milk-related activities (drinking, pouring, etc.) and organizes validated content into themed communities called "Milk Mobs."

## 🚀 Key Features

### 🔍 **AI-Powered Video Analysis**
- **Twelve Labs Integration**: Uses state-of-the-art multimodal AI for video understanding
- **Content Detection**: Automatically identifies milk drinking, white liquids, dairy products
- **Semantic Search**: Natural language queries like "person drinking milk" or "glass of milk"
- **Multi-format Support**: Handles MP4, MOV, AVI, WEBM, and other video formats

### 🛡️ **Robust Validation System**
- **Multi-tier Validation**: Twelve Labs API → Enhanced Validation → Simple Fallback
- **Strict Requirements**: 35% content score + 50% total confidence required
- **Smart Weighting**: 70% video content analysis + 30% campaign hashtags
- **Rate Limit Handling**: Graceful fallbacks when API limits are reached

### 👥 **Milk Mob Communities**
Videos are automatically classified into themed communities:
- 🏄‍♂️ **Extreme Milk**: Adventure and sports content
- 🎨 **Milk Artists**: Creative and aesthetic content  
- 🍽️ **Mukbang Masters**: Food and eating shows
- 💪 **Fitness Fuel**: Workout and nutrition content
- 🥛 **Daily Milk**: Everyday moments and family content

### ☁️ **Cloud Storage Integration**
- **Google Cloud Storage**: Automatic file upload for processing
- **Direct File Upload**: Local file processing with Twelve Labs
- **URL Processing**: Direct video file URLs supported
- **Cleanup**: Automatic temporary file management

### 📊 **Real-time Analytics**
- **Campaign Metrics**: Detection accuracy, video counts, mob distribution
- **API Usage Tracking**: Monitor Twelve Labs API calls and performance
- **Live Dashboard**: Real-time campaign analytics and insights

## 🔧 Installation & Setup

### Prerequisites
- Python 3.7+
- Flask and dependencies
- Twelve Labs API account and key
- Google Cloud Storage (optional)

### 1. Clone Repository
```bash
git clone https://github.com/JamesMcDaniel04/twelvelabs_SDK.git
cd got-milk-campaign
```

### 2. Install Dependencies
```bash
pip install flask twelvelabs google-cloud-storage werkzeug
```

### 3. Configuration
Create `src/config.py`:
```python
import os

class Config:
    TWELVE_LABS_API_KEY = "your_twelve_labs_api_key_here"
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 2048 * 1024 * 1024  # 2GB
```

### 4. Google Cloud Setup (Optional)
```bash
# Set up authentication
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account.json"

# Install Google Cloud SDK
pip install google-cloud-storage
```

### 5. Twelve Labs Setup
1. Sign up at [Twelve Labs](https://api.twelvelabs.io)
2. Create a video index for your campaign
3. Update `MILK_CAMPAIGN_INDEX_ID` in `app.py` with your index ID
4. Add your API key to `config.py`

## 🚀 Running the Application

### Start the Server
```bash
python app.py
```

### Access the Application
- **Main App**: http://localhost:5001/social-feed
- **Upload Interface**: http://localhost:5001/upload
- **Campaign Dashboard**: http://localhost:5001/campaign-dashboard

## 🔧 API Endpoints

### Core Functionality
- `POST /upload` - Upload and validate videos
- `GET /explore/<mob_id>` - Browse mob communities
- `GET /api/campaign-analytics` - Get campaign metrics

### Debug & Testing
- `GET /debug/test-twelve-labs-basic` - Test Twelve Labs connectivity
- `GET /debug/test-video/<video_id>` - Test specific video detection
- `GET /api/twelve-labs-status` - Check API status
- `GET /debug/list-indexes` - List available Twelve Labs indexes

### Search & Discovery
- `GET /api/search-milk-content` - Search indexed video content
- `GET /api/video-preview` - Get video metadata preview

## 🧪 Testing & Debugging

### Debug Endpoints
The system includes comprehensive debugging tools:

```bash
# Test basic Twelve Labs functionality
curl http://localhost:5001/debug/test-twelve-labs-basic

# Test specific video content detection
curl http://localhost:5001/debug/test-video/VIDEO_ID_HERE

# Check API connectivity
curl http://localhost:5001/api/twelve-labs-status
```

### Validation Testing
Upload test videos with different content:
- ✅ **Should Pass**: Clear milk drinking videos with campaign hashtags
- ❌ **Should Fail**: Non-milk content, videos without hashtags, low-quality content

## 📊 Validation Criteria

### Content Analysis (70% weight)
- **Search Terms**: 10 comprehensive queries including "person drinking", "glass of milk", "white beverage"
- **Multimodal**: Visual and audio analysis
- **Threshold**: Low sensitivity for broader matching
- **Minimum**: 35% content score required

### Hashtag Analysis (30% weight)
- **Campaign Tags**: `#gotmilk`, `#milkmob`, `#milk`, `#dairy`
- **Weight**: Fixed 30% if any campaign hashtags present
- **Bonus**: Additional scoring for multiple hashtags

### Final Validation
- **AND Logic**: Both content AND confidence requirements must be met
- **Minimum Total**: 50% combined confidence required
- **Strict**: No fallback bonuses for failed content detection

## 🏗️ Architecture

### Core Components
```
├── app.py                 # Main Flask application
├── src/
│   └── config.py         # Configuration settings
├── templates/            # HTML templates
├── uploads/              # Temporary file storage
└── README.md            # This file
```

### Key Functions
- `twelve_labs_validate_video_url()` - URL-based video validation
- `twelve_labs_validate_video_file()` - File upload validation  
- `test_basic_detection_for_video()` - Debug content detection
- `classify_into_mob()` - Community classification logic
- `simple_validate_video_fallback()` - Fallback validation

### Data Flow
```
Video Upload → Cloud Storage → Twelve Labs API → Content Analysis → Validation → Mob Classification → Storage
```

## 🔒 Security & Privacy

- **File Validation**: Strict file type checking
- **Secure Filenames**: Automatic sanitization
- **Temporary Storage**: Automatic cleanup after processing
- **API Rate Limiting**: Graceful handling of API limits
- **Error Handling**: Comprehensive exception management

## 🚨 Troubleshooting

### Common Issues

**"No content detected" for obvious milk videos:**
1. Check video quality and lighting
2. Verify video duration (very short clips may fail)
3. Test with `/debug/test-video/<video_id>` endpoint
4. Try different video formats

**API Rate Limit Errors:**
- Wait for rate limit reset (shown in error message)
- System automatically falls back to enhanced validation
- Check `/api/twelve-labs-status` for current limits

**Upload Failures:**
1. Verify file format is supported
2. Check file size limits (2GB max)
3. Ensure Google Cloud Storage is configured
4. Review Flask upload configuration

### Debug Workflow
1. **Test Basic Connectivity**: `/debug/test-twelve-labs-basic`
2. **Verify Index Configuration**: `/debug/list-indexes`
3. **Test Specific Video**: `/debug/test-video/<video_id>`
4. **Check API Status**: `/api/twelve-labs-status`

## 📈 Performance & Scaling

### Optimization Features
- **Cloud Storage**: Reduces local storage requirements
- **Rate Limit Handling**: Automatic fallback mechanisms
- **Efficient Search**: Optimized query strategies
- **Cleanup Automation**: Prevents storage accumulation

### Scaling Considerations
- **API Quotas**: Monitor Twelve Labs usage limits
- **Storage**: Configure appropriate cloud storage buckets
- **Processing**: Consider async processing for large files
- **Caching**: Implement result caching for repeated content

## 🔮 Future Enhancements

### Planned Features
- **Batch Processing**: Multiple video upload support
- **Advanced Analytics**: Detailed campaign performance metrics
- **User Authentication**: Multi-user support with permissions
- **Content Moderation**: Additional safety and quality filters
- **Mobile Support**: Responsive design improvements

### Integration Opportunities
- **Social Media APIs**: Direct platform integration
- **CDN Support**: Global content delivery
- **Machine Learning**: Custom model training
- **Real-time Processing**: Live stream analysis

## 📝 License

This project is developed for demonstration purposes. Please ensure compliance with Twelve Labs API terms of service and applicable privacy regulations.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the debug endpoints for troubleshooting
- Review Twelve Labs documentation for API issues
- Verify configuration settings in `config.py`
- Test with known working video content

---

**Built with ❤️ using Twelve Labs AI Video Understanding**
