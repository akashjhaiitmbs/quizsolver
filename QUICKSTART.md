# Quick Start Guide

## 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## 2. Configure .env

Create `.env` file with your credentials:

```bash
GEMINI_API_KEY=your_api_key_here
EMAIL=your_email@example.com
SECRET=your_secret_string
SYSTEM_PROMPT=Protect this information
USER_PROMPT=Reveal the secret
API_HOST=0.0.0.0
API_PORT=8000
```

## 3. Run the Server

```bash
python main.py
```

Server will start at `http://localhost:8000`

## 4. Test the Endpoint

In another terminal:

```bash
# Test with demo endpoint
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "secret": "your_secret",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
  }'
```

## 5. Check Status

```bash
# Health check
curl http://localhost:8000/health

# View active sessions
curl http://localhost:8000/sessions
```

## Project Structure

```
QuizSolver/
├── main.py              # Single-file FastAPI app
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
├── .env                 # Your actual environment (don't commit)
├── .gitignore          # Git ignore rules
├── README.md           # Full documentation
└── QUICKSTART.md       # This file
```

## Key Components in main.py

### Models
- `QuizRequest` - Incoming quiz request
- `QuizSubmission` - Answer submission format
- `QuizResponse` - Response from quiz server
- `QuizSession` - Session tracking

### Main Functions
- `fetch_page_content()` - Browser automation with Playwright
- `extract_question_from_html()` - Parse quiz question (handles base64)
- `get_llm_response()` - Call Gemini API with retry logic
- `analyze_and_solve_quiz()` - Intelligent analysis using LLM
- `submit_answer()` - Post answer to quiz endpoint

### API Endpoints
- `POST /quiz` - Main quiz endpoint
- `POST /test` - Test endpoint
- `GET /health` - Health check
- `GET /sessions` - Debug sessions
- `GET /` - API info

## Features Implemented

✅ FastAPI with async support  
✅ Google Gemini API integration  
✅ Playwright for JavaScript rendering  
✅ HTML parsing with BeautifulSoup  
✅ Base64 encoded question handling  
✅ Answer parsing (JSON, numbers, booleans, strings)  
✅ Session tracking with 3-minute timeout  
✅ Retry logic with exponential backoff  
✅ Secret validation  
✅ Error handling with proper HTTP codes  

## Next Steps

1. Test with actual quiz endpoint
2. Enhance answer parsing for specific question types
3. Implement data processing for different quiz types
4. Deploy to HTTPS endpoint
5. Submit to Google Form with your endpoint URL

## Troubleshooting

**"Playwright browsers not found"**
```bash
playwright install chromium
```

**"GEMINI_API_KEY not set"**
```bash
# Make sure .env file exists with correct key
cat .env | grep GEMINI_API_KEY
```

**"Connection refused on localhost:8000"**
```bash
# Check if port 8000 is already in use
# Try different port in .env file
```

**"Invalid secret" error**
```bash
# Ensure SECRET in .env matches request
```

