@echo off
REM Windows batch script to test Quiz Solver API

setlocal enabledelayedexpansion

echo === Quiz Solver API Test ===
echo.

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found
    echo Create it from .env.example:
    echo   copy .env.example .env
    exit /b 1
)

REM Load .env variables (simple parser)
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%a:~0,1%%" == "#" (
        set "%%a=%%b"
    )
)

REM Test 1: Health Check
echo Test 1: Health Check
curl -s http://localhost:8000/health
echo.
echo.

REM Test 2: Test Endpoint
echo Test 2: Test Endpoint
curl -s -X POST http://localhost:8000/test ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"%EMAIL%\", \"secret\": \"%SECRET%\", \"url\": \"https://tds-llm-analysis.s-anand.net/demo\"}"
echo.
echo.

REM Test 3: Invalid Secret
echo Test 3: Invalid Secret (Should fail with 403)
curl -s -w "HTTP Status: %%{http_code}\n" -X POST http://localhost:8000/test ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"%EMAIL%\", \"secret\": \"wrong_secret\", \"url\": \"https://tds-llm-analysis.s-anand.net/demo\"}"
echo.
echo.

REM Test 4: View Sessions
echo Test 4: View Sessions
curl -s http://localhost:8000/sessions
echo.
echo.

REM Test 5: API Info
echo Test 5: API Info
curl -s http://localhost:8000/
echo.
echo.

echo === Tests completed ===

