import os
import json
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import io
import csv
import httpx
import pandas as pd
import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "")
USER_PROMPT = os.getenv("USER_PROMPT", "")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# FastAPI app
app = FastAPI(title="Quiz Solver", version="1.0.0")

# ==================== Models ====================


class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str


class QuizSubmission(BaseModel):
    email: str
    secret: str
    url: str
    answer: Any = Field(...)


class QuizResponse(BaseModel):
    correct: bool
    url: Optional[str] = None
    reason: Optional[str] = None


# ==================== Quiz Task Tracking ====================

class QuizSession:
    def __init__(self, url: str, start_time: datetime):
        self.url = url
        self.start_time = start_time
        self.submission_count = 0
        self.last_attempt = None

    def is_timeout(self) -> bool:
        """Check if 3 minutes have passed since start"""
        return datetime.now() - self.start_time > timedelta(minutes=3)

    def can_submit(self) -> bool:
        """Check if still within 3 minute window"""
        return not self.is_timeout()


# Global session tracker
quiz_sessions: Dict[str, QuizSession] = {}


# ==================== Utility Functions ====================


def validate_secret(provided_secret: str) -> bool:
    """Validate the provided secret against stored secret"""
    return provided_secret == SECRET


async def fetch_page_content(url: str) -> str:
    """
    Fetch page content using headless browser to handle JavaScript rendering.
    Returns the rendered HTML content.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # Wait for any dynamic content
            content = await page.content()
            return content
        finally:
            await browser.close()


async def extract_question_from_html(html_content: str) -> str:
    """
    Extract the quiz question from HTML.
    Handles base64 encoded content in <script> tags.
    """
    soup = BeautifulSoup(html_content, "lxml")
    
    # Look for script tags with atob calls
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "atob" in script.string:
            try:
                # Extract base64 string from atob
                import re
                match = re.search(r"atob\(['\"`]([^'\"]+)['\"`]\)", script.string)
                if match:
                    encoded = match.group(1)
                    decoded = base64.b64decode(encoded).decode("utf-8")
                    return decoded
            except Exception:
                pass
    
    # Fallback: look for result div or any text content
    result_div = soup.find(id="result")
    if result_div:
        return result_div.get_text(strip=True)
    
    # Return full text content
    return soup.get_text(strip=True)


async def download_file(url: str) -> bytes:
    """Download a file from a URL"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content


def process_file(content: bytes, filename: str) -> str:
    """Process file content based on extension and return text representation"""
    filename = filename.lower()
    
    if filename.endswith(".pdf"):
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return f"--- PDF CONTENT ({filename}) ---\n{text}\n--- END PDF CONTENT ---"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
            
    elif filename.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(content))
            return f"--- CSV CONTENT ({filename}) ---\n{df.to_markdown()}\n--- END CSV CONTENT ---"
        except Exception as e:
            return f"Error reading CSV: {str(e)}"
            
    elif filename.endswith(".txt") or filename.endswith(".json"):
        return f"--- FILE CONTENT ({filename}) ---\n{content.decode('utf-8')}\n--- END FILE CONTENT ---"
        
    return f"Unsupported file type: {filename}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def get_llm_response(prompt: str, system_instruction: Optional[str] = None) -> str:
    """
    Get response from Google Gemini API with retry logic.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        if system_instruction:
            response = model.generate_content(
                [system_instruction, prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                )
            )
        else:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                )
            )
        
        return response.text
    except Exception as e:
        raise RuntimeError(f"LLM API error: {str(e)}")


async def analyze_and_solve_quiz(question: str, url: str, file_context: str = "") -> Any:
    """
    Use Gemini to understand the question and determine what answer is needed.
    Returns the answer in appropriate format.
    """
    analysis_prompt = f"""
    You are an expert data analyst. Analyze this quiz question carefully:
    
    Question:
    {question}
    
    Context from files (if any):
    {file_context}
    
    Based on the question, determine:
    1. What type of data source is mentioned (website, API, file, etc.)
    2. What data processing is needed
    3. What the expected answer format should be (number, string, boolean, JSON, etc.)
    4. Step-by-step approach to solve it
    
    Provide a structured analysis.
    """
    
    analysis = await get_llm_response(analysis_prompt)
    
    return analysis


async def submit_answer(
    answer: Any,
    url: str,
    email: str,
    secret: str
) -> QuizResponse:
    """
    Submit the answer to the quiz endpoint.
    """
    payload = {
        "email": email,
        "secret": secret,
        "url": url,
        "answer": answer
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url.rsplit("/", 1)[0] + "/submit", json=payload)
            return QuizResponse(**response.json())
        except Exception as e:
            raise RuntimeError(f"Submission error: {str(e)}")


# ==================== API Endpoints ====================


@app.post("/quiz")
async def quiz_endpoint(request: QuizRequest):
    """
    Main quiz endpoint that receives quiz tasks.
    Validates secret and initiates quiz solving.
    """
    # Validate request
    if not validate_secret(request.secret):
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    if request.email != EMAIL:
        # Optional: enforce email match
        pass
    
    # Create session
    session_key = f"{request.email}_{request.url}"
    if session_key not in quiz_sessions:
        quiz_sessions[session_key] = QuizSession(request.url, datetime.now())
    
    session = quiz_sessions[session_key]
    
    if not session.can_submit():
        raise HTTPException(status_code=408, detail="Quiz timeout (3 minutes exceeded)")
    
    # Start background task to solve quiz
    asyncio.create_task(solve_quiz_task(request.url, request.email, request.secret, session_key))
    
    return {
        "status": "processing",
        "message": "Quiz task received and processing started"
    }


async def solve_quiz_task(url: str, email: str, secret: str, session_key: str):
    """
    Background task to solve quiz.
    Handles the complete flow: fetch -> analyze -> submit -> loop.
    """
    session = quiz_sessions.get(session_key)
    if not session:
        return
    
    current_url = url
    recursion_limit = 10
    attempts = 0
    
    while attempts < recursion_limit and session.can_submit():
        try:
            attempts += 1
            print(f"[{session_key}] Step {attempts}: Processing {current_url}")
            
            # Step 1: Fetch page content
            html_content = await fetch_page_content(current_url)
            
            # Step 2: Extract question and look for files
            question = await extract_question_from_html(html_content)
            print(f"[{session_key}] Question: {question[:200]}...")
            
            # Check for file links (simple heuristic)
            file_context = ""
            soup = BeautifulSoup(html_content, "lxml")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.lower().endswith((".pdf", ".csv", ".txt", ".json")):
                    file_url = urljoin(current_url, href)
                    print(f"[{session_key}] Found file: {file_url}")
                    try:
                        content = await download_file(file_url)
                        file_context += process_file(content, href.split("/")[-1]) + "\n\n"
                    except Exception as e:
                        print(f"[{session_key}] Failed to download/process file {file_url}: {e}")

            # Step 3: Analyze with LLM
            print(f"[{session_key}] Analyzing with Gemini...")
            analysis = await analyze_and_solve_quiz(question, current_url, file_context)
            
            # Step 4: Determine answer based on analysis
            answer_prompt = f"""
            Based on this quiz question and analysis, provide ONLY the final answer in the format requested.
            
            Question:
            {question}
            
            File Context:
            {file_context}
            
            Analysis:
            {analysis}
            
            Return ONLY the answer, nothing else. If it's a JSON, return valid JSON.
            """
            
            answer_text = await get_llm_response(answer_prompt)
            answer = parse_answer(answer_text, question)
            
            # Step 5: Submit answer
            print(f"[{session_key}] Submitting answer: {answer}")
            response = await submit_answer(answer, current_url, email, secret)
            
            session.submission_count += 1
            session.last_attempt = {
                "url": current_url,
                "answer": answer,
                "timestamp": datetime.now(),
                "correct": response.correct,
                "reason": response.reason
            }
            
            if response.correct:
                print(f"[{session_key}] Answer CORRECT!")
                if response.url:
                    print(f"[{session_key}] Proceeding to next URL: {response.url}")
                    current_url = response.url
                else:
                    print(f"[{session_key}] Quiz COMPLETED!")
                    break
            else:
                print(f"[{session_key}] Answer WRONG. Reason: {response.reason}")
                # In a real scenario, we might want to retry with the reason as feedback
                # For now, we'll just stop or maybe retry once (logic can be added here)
                # Let's try to re-analyze with the error reason
                retry_prompt = f"""
                The previous answer was wrong.
                Reason: {response.reason}
                
                Please re-analyze and provide the correct answer.
                """
                # For simplicity in this loop, we might just break or continue. 
                # To prevent infinite loops on the same URL, we should probably break if we fail twice on the same URL
                # But for this implementation, let's just break on failure to avoid spamming
                break
                
        except Exception as e:
            print(f"[{session_key}] Error: {str(e)}")
            session.last_attempt = {
                "error": str(e),
                "timestamp": datetime.now()
            }
            break


def parse_answer(answer_text: str, question: str) -> Any:
    """
    Parse the answer into appropriate format.
    Tries to infer format from question context.
    """
    answer_text = answer_text.strip()
    
    # Try JSON
    try:
        return json.loads(answer_text)
    except:
        pass
    
    # Try number
    try:
        if "." in answer_text:
            return float(answer_text)
        return int(answer_text)
    except:
        pass
    
    # Try boolean
    if answer_text.lower() in ["true", "yes"]:
        return True
    if answer_text.lower() in ["false", "no"]:
        return False
    
    # Return as string
    return answer_text


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(quiz_sessions)
    }


@app.get("/sessions")
async def get_sessions():
    """Get active quiz sessions (for debugging)"""
    sessions_info = {}
    for key, session in quiz_sessions.items():
        sessions_info[key] = {
            "url": session.url,
            "elapsed_seconds": (datetime.now() - session.start_time).total_seconds(),
            "submission_count": session.submission_count,
            "timeout": session.is_timeout(),
            "last_attempt": session.last_attempt
        }
    return sessions_info


@app.post("/test")
async def test_endpoint(request: QuizRequest):
    """
    Test endpoint for development.
    Accepts quiz request and returns simple response.
    """
    if not validate_secret(request.secret):
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    try:
        # Fetch and parse
        html = await fetch_page_content(request.url)
        question = await extract_question_from_html(html)
        
        return {
            "status": "success",
            "question": question[:500],
            "message": "Test endpoint working"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Quiz Solver API",
        "version": "1.0.0",
        "endpoints": {
            "POST /quiz": "Submit quiz task",
            "POST /test": "Test endpoint",
            "GET /health": "Health check",
            "GET /sessions": "View active sessions"
        }
    }


# ==================== Startup ====================


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    print("=" * 50)
    print("Quiz Solver API Starting")
    print(f"Email: {EMAIL}")
    print(f"Gemini API configured: {'Yes' if GEMINI_API_KEY else 'No'}")
    print("=" * 50)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)

