# AI Debate Trainer - Multi-Turn Debate Guide

## Overview
Your debate trainer now includes an **agentic AI system** that:
1. **Researches the debate topic** using Google Scholar
2. **Generates an opening position** based on research
3. **Engages in multi-turn debates** with the user
4. **Analyzes arguments** in real-time
5. **Provides feedback** after each round

## New Features

### 1. Multi-Turn Debate Flow
The AI now initiates debates with a researched position and responds to your arguments across multiple rounds.

**How it works:**
- User enters a topic → AI researches it
- AI presents opening position
- User responds → AI generates counter-argument
- Process repeats with scoring and feedback each round

### 2. Google Scholar Research Integration
The system searches academic papers to inform debate positions.
- Fetches real research papers on the topic
- Summarizes findings for context
- Uses evidence in AI arguments

### 3. Conversation History
All debate rounds are tracked with:
- User responses and AI counter-arguments
- Analysis of each argument
- Feedback and scores per round
- Overall debate performance

## API Endpoints

### Start a Debate
**POST** `/api/debate/start/`

Request:
```json
{
  "topic": "Artificial Intelligence Ethics",
  "user_name": "John Doe",
  "difficulty": "medium"
}
```

Response:
```json
{
  "session_id": "uuid-string",
  "topic": "Artificial Intelligence Ethics",
  "ai_opening_position": "AI should be heavily regulated...",
  "research_context": {
    "papers_found": 5,
    "summary": "Research papers about AI ethics..."
  },
  "difficulty": "medium",
  "current_round": 1
}
```

### Submit User Response
**POST** `/api/debate/response/`

Request:
```json
{
  "session_id": "uuid-string",
  "response": "I disagree because..."
}
```

Response:
```json
{
  "session_id": "uuid-string",
  "round": 1,
  "user_analysis": {
    "fallacies": [],
    "unsupported_claims": [],
    "strengths": ["uses_examples", "logical_connectors"],
    "score": 0.75
  },
  "ai_counter_argument": "However, consider that...",
  "coach_feedback": "• Strength: Clear reasoning\n• Gap: Needs more evidence\n• Improvement: Add specific examples",
  "current_score": 75.0,
  "overall_score": 75.0,
  "next_round": 2
}
```

### End Debate
**POST** `/api/debate/end/`

Request:
```json
{
  "session_id": "uuid-string"
}
```

Response:
```json
{
  "session_id": "uuid-string",
  "topic": "Artificial Intelligence Ethics",
  "user_name": "John Doe",
  "total_rounds": 3,
  "overall_score": 78.5,
  "difficulty": "medium",
  "conversation_length": 6,
  "research_used": {
    "papers_found": 5,
    "sources": 5
  }
}
```

### Get Debate History
**GET** `/api/debate/history/?session_id=uuid-string`

Response:
```json
{
  "session_id": "uuid-string",
  "topic": "Artificial Intelligence Ethics",
  "user_name": "John Doe",
  "difficulty": "medium",
  "overall_score": 78.5,
  "total_rounds": 3,
  "conversation": [
    {
      "role": "ai",
      "content": "AI should be heavily regulated...",
      "round": 1,
      "type": "opening"
    },
    {
      "role": "user",
      "content": "I disagree because...",
      "round": 1,
      "analysis": {...}
    }
  ],
  "feedbacks": {...},
  "scores": {...},
  "is_active": false,
  "created_at": "2025-12-17T10:30:00Z"
}
```

## Web Interface

### Access the Multi-Turn Debate UI
Navigate to: `/debate/chat/`

**Features:**
- 🎯 Enter any debate topic
- 📚 See research papers found
- 💬 Real-time conversation display
- 📊 Live score tracking
- 💡 Coach feedback after each round
- 🎚️ Difficulty levels (Easy, Medium, Hard)

## Database Models

### DebateRound Model
Stores complete debate sessions with multi-turn tracking:
- `session_id`: Unique debate identifier
- `topic`: Debate topic
- `ai_position`: AI's opening argument
- `research_summary`: JSON with papers and summaries
- `conversation`: List of all messages with metadata
- `ai_feedbacks`: Feedback per round
- `scores`: Score per round
- `overall_score`: Average score across rounds
- `difficulty`: Debate difficulty level
- `is_active`: Whether debate is ongoing

## Requirements Installation

```bash
pip install -r requirements.txt
```

New dependencies:
- `scholarly>=1.7.11` - Google Scholar research integration
- `requests>=2.31.0` - HTTP requests

## Environment Setup

1. **Run migrations** for the new `DebateRound` model:
```bash
python manage.py makemigrations
python manage.py migrate
```

2. **Configure your AI provider (Gemini recommended)**  
In this project, the agent already supports multiple providers (OpenAI, Google Gemini, Groq).  
For your FYP debate trainer, the cheapest and simplest option is **Google Gemini**:

```bash
# Google Gemini (recommended)
export AI_API_KEY="your-gemini-api-key"     # from Generative Language API
export AI_MODEL_PROVIDER="google"
export AI_MODEL_NAME="gemini-1.5-flash"
```

If you prefer to use OpenAI instead:

```bash
export AI_API_KEY="your-openai-api-key"
export AI_MODEL_PROVIDER="openai"
export AI_MODEL_NAME="gpt-4o-mini"
```

3. **Run the development server**:
```bash
python manage.py runserver
```

## Usage Example

### Python Client Example
```python
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Start a debate
start_response = requests.post(f"{BASE_URL}/debate/start/", json={
    "topic": "Climate Change Policy",
    "user_name": "Alex",
    "difficulty": "medium"
})

session_data = start_response.json()
session_id = session_data["session_id"]
print(f"AI Opening: {session_data['ai_opening_position']}")

# Submit user response
response_data = requests.post(f"{BASE_URL}/debate/response/", json={
    "session_id": session_id,
    "response": "I think we need market-based solutions rather than regulation."
}).json()

print(f"AI Counter: {response_data['ai_counter_argument']}")
print(f"Score: {response_data['overall_score']}/100")

# End debate
end_response = requests.post(f"{BASE_URL}/debate/end/", json={
    "session_id": session_id
}).json()

print(f"Final Score: {end_response['overall_score']}")
```

## Features Overview

| Feature | Details |
|---------|---------|
| **Research Integration** | Fetches academic papers from Google Scholar |
| **Multi-Turn Debates** | Continuous debate across multiple rounds |
| **Real-Time Analysis** | Scores arguments for fallacies, evidence, structure |
| **Coach Feedback** | Contextual feedback after each round |
| **Score Tracking** | Individual round scores + overall average |
| **Conversation History** | Full history stored in database |
| **Difficulty Levels** | Easy, Medium, Hard debates |
| **Web UI** | Interactive chat interface for debates |
| **REST API** | Complete API for programmatic access |

## Troubleshooting

### "scholarly" import error
```bash
pip install scholarly
```

### "OpenAI" connection issues
- Check your `AI_API_KEY` is set correctly
- Fallback mode activates automatically if API unavailable
- Debates still work but with template responses

### Research not fetching
- Google Scholar rate limiting may apply
- Fallback research context is used automatically
- Debates proceed normally with general topic knowledge

## Next Steps

1. ✅ Deploy to PythonAnywhere
2. ✅ Update static files: `python manage.py collectstatic`
3. ✅ Test the `/debate/chat/` interface
4. ✅ Monitor API usage and adjust difficulty levels
5. ✅ Add user authentication for profile tracking

## File Changes Summary

**New Files:**
- `trainer/services/research.py` - Google Scholar integration
- `trainer/debate_chat.py` - Interactive UI component

**Modified Files:**
- `trainer/models.py` - Added DebateRound model
- `trainer/views.py` - Added 4 new debate flow endpoints
- `trainer/services/agent.py` - Added debate flow methods
- `trainer/urls.py` - Added new routes
- `requirements.txt` - Added scholarly & requests

## Support

For issues or questions about the agentic debate system, check:
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Run migrations: `python manage.py migrate`
3. Check environment variables are set
4. Test API endpoints with the provided examples
