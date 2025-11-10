# Quiz Solver - LLM Analysis

A FastAPI-based application that automatically solves data analysis quizzes using Google Gemini API.

## Features

- **FastAPI** web framework for handling quiz requests
- **Playwright** for JavaScript-enabled web scraping
- **Google Gemini API** for intelligent question analysis and answer generation
- **Async-first** design for efficient processing
- **Retry logic** with exponential backoff for API resilience
- **Session tracking** for managing multiple quiz attempts

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Playwright Browsers

```bash
playwright install chromium
```

### 3. Environment Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Then edit `.env` with your values:

```
GEMINI_API_KEY=your_google_gemini_api_key
EMAIL=your_email@example.com
SECRET=your_secret_string
SYSTEM_PROMPT=Your system prompt (max 100 chars)
USER_PROMPT=Your user prompt (max 100 chars)
API_HOST=0.0.0.0
API_PORT=8000
```

### Getting Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy it to your `.env` file

## Running the Application

```bash
python main.py
```

The API will start on `http://localhost:8000`

## API Endpoints

### POST /quiz
Main endpoint for quiz submission.

**Request:**
```json
{
  "email": "your_email@example.com",
  "secret": "your_secret",
  "url": "https://example.com/quiz-123"
}
```

**Response:**
```json
{
  "status": "processing",
  "message": "Quiz task received and processing started"
}
```

### POST /test
Test endpoint to verify setup.

**Request:**
```json
{
  "email": "your_email@example.com",
  "secret": "your_secret",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456",
  "active_sessions": 0
}
```

### GET /sessions
View active quiz sessions (debugging).

**Response:**
```json
{
  "email_url": {
    "url": "https://example.com/quiz-123",
    "elapsed_seconds": 45.2,
    "submission_count": 1,
    "timeout": false,
    "last_attempt": {...}
  }
}
```

### GET /
Root endpoint with API info.

## How It Works

1. **Receive Request**: API receives POST request with quiz URL
2. **Validate Secret**: Checks if provided secret matches configured secret
3. **Fetch Page**: Uses Playwright to load page (handles JavaScript)
4. **Extract Question**: Parses HTML to find and decode quiz question
5. **Analyze**: Sends question to Gemini API for analysis
6. **Generate Answer**: Uses LLM to determine appropriate answer
7. **Submit**: Posts answer back to quiz endpoint (in background)
8. **Handle Response**: Processes correct/incorrect responses and new quiz URLs

## Architecture

- **Single-file structure** for simplicity and ease of deployment
- **Async/await** for non-blocking operations
- **Session tracking** to manage concurrent quizzes
- **Retry logic** for resilient API calls
- **Pydantic** models for request validation

## Error Handling

- HTTP 403: Invalid secret
- HTTP 408: Quiz timeout (>3 minutes)
- HTTP 400: Invalid request format
- HTTP 500: Internal server error

## Configuration

All settings are managed via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| GEMINI_API_KEY | Google Gemini API key | Required |
| EMAIL | Student email | Required |
| SECRET | Authentication secret | Required |
| SYSTEM_PROMPT | Defensive prompt (max 100 chars) | "" |
| USER_PROMPT | Offensive prompt (max 100 chars) | "" |
| API_HOST | Server host | 0.0.0.0 |
| API_PORT | Server port | 8000 |

## Deployment

### Using Docker

```bash
docker build -t quiz-solver .
docker run -p 8000:8000 --env-file .env quiz-solver
```

### Using Gunicorn

```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Testing

Test against the demo endpoint:

```bash
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "secret": "your_secret",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
  }'
```

## Timeout Management

- Each quiz has a **3-minute window** from initial request
- System tracks elapsed time for each session
- Submissions only allowed within timeout window
- Can re-submit within timeout on incorrect answers

## License

MIT License

## Support

For issues and questions, check the API health endpoint and review logs.

