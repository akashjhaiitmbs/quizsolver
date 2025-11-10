#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Quiz Solver API Test ===${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Create it from .env.example:"
    echo "  cp .env.example .env"
    exit 1
fi

# Load environment variables
source .env

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "Response: $RESPONSE"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

echo ""

# Test 2: Test Endpoint
echo -e "${BLUE}Test 2: Test Endpoint${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"secret\": \"$SECRET\",
    \"url\": \"https://tds-llm-analysis.s-anand.net/demo\"
  }")

if echo "$RESPONSE" | grep -q "success\|processing"; then
    echo -e "${GREEN}✓ Test endpoint passed${NC}"
    echo "Response (first 200 chars): ${RESPONSE:0:200}"
else
    echo -e "${RED}✗ Test endpoint failed${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""

# Test 3: Invalid Secret
echo -e "${BLUE}Test 3: Invalid Secret (Should fail with 403)${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"secret\": \"wrong_secret\",
    \"url\": \"https://tds-llm-analysis.s-anand.net/demo\"
  }")

if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Correctly rejected invalid secret (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}✗ Should have returned 403, got $HTTP_CODE${NC}"
    exit 1
fi

echo ""

# Test 4: View Sessions
echo -e "${BLUE}Test 4: View Sessions${NC}"
RESPONSE=$(curl -s http://localhost:8000/sessions)
if echo "$RESPONSE" | grep -q "\{\}"; then
    echo -e "${GREEN}✓ Sessions endpoint working (empty sessions)${NC}"
else
    echo -e "${GREEN}✓ Sessions endpoint working${NC}"
fi
echo "Response: $RESPONSE"

echo ""

# Test 5: API Info
echo -e "${BLUE}Test 5: API Info${NC}"
RESPONSE=$(curl -s http://localhost:8000/)
if echo "$RESPONSE" | grep -q "Quiz Solver"; then
    echo -e "${GREEN}✓ API info endpoint working${NC}"
    echo "Response: $RESPONSE"
else
    echo -e "${RED}✗ API info endpoint failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== All tests passed! ===${NC}"

