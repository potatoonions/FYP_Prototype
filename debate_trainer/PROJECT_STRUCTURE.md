# Project Structure & Organization

## Overview
Clean, production-ready debate trainer with agentic AI capabilities.

```
debate_trainer/
├── manage.py                    # Django entry point
├── requirements.txt             # Python dependencies
├── .env                        # Environment variables (KEEP SECRET)
├── .env.example                # Template for .env
├── db.sqlite3                  # SQLite database
│
├── debate_trainer/             # Main Django project
│   ├── settings.py            # Configuration (uses .env)
│   ├── urls.py                # URL routing
│   ├── wsgi.py                # Production server
│   ├── asgi.py                # Async server
│
├── trainer/                    # Main app
│   ├── models.py              # Database models
│   ├── views.py               # API endpoints
│   ├── urls.py                # App routes
│   ├── admin.py               # Django admin
│   ├── rate_limit.py          # Rate limiting (NEW: enhanced)
│   ├── validators.py          # Input validation
│   │
│   ├── services/              # Business logic
│   │   ├── agent.py           # AI orchestration (NEW: Gemini support)
│   │   ├── analysis.py        # Argument analysis
│   │   └── research.py        # Academic research integration
│   │
│   └── migrations/            # Database migrations
│       └── 0001_initial.py
│
└── static/                    # Static files (CSS, JS)
```

## Key Improvements Made

### 1. Google Gemini Integration ✅
- **File:** `trainer/services/agent.py`
- Added native support for Google Gemini API
- Fallback system if API unavailable
- Can switch providers via environment variable

### 2. Environment Management ✅
- **Files:** `.env`, `.env.example`, `settings.py`
- Uses `python-dotenv` for secure API key management
- No more manual CLI setup needed
- Configuration centralized and documented

### 3. Enhanced Rate Limiting ✅
- **File:** `trainer/rate_limit.py`
- Per-IP rate limiting for public deployments
- Better error responses (429 status code)
- Configurable limits per endpoint
- RateLimitMixin for class-based views

## Setup Instructions

### First Time Setup
```bash
cd debate_trainer

# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env from template
cp .env.example .env

# 3. Edit .env with your API key
# Open .env and add your Google Gemini or OpenAI key

# 4. Run migrations
python manage.py migrate

# 5. Start server
python manage.py runserver
```

### Using Google Gemini (Free)
```env
# In .env:
AI_MODEL_PROVIDER=google
AI_API_KEY=your-google-api-key-here
AI_MODEL_NAME=gemini-1.5-flash
```

### Using OpenAI
```env
# In .env:
AI_MODEL_PROVIDER=openai
AI_API_KEY=your-openai-api-key-here
AI_MODEL_NAME=gpt-4o-mini
```

## API Endpoints

### Debate Endpoints
- `POST /api/debate/` - Single-turn debate (rate limited: 30/min)
- `POST /api/debate/start/` - Multi-turn debate start
- `POST /api/debate/response/` - Multi-turn response
- `POST /api/debate/end/` - End debate session
- `GET /api/sessions/` - Session history

### Web Interface
- `GET /` - API documentation homepage
- `GET /debate/chat/` - Interactive debate interface

## Environment Variables

| Variable | Default | Options |
|----------|---------|---------|
| `DJANGO_DEBUG` | True | true/false |
| `AI_MODEL_PROVIDER` | openai | openai, google |
| `AI_MODEL_NAME` | gpt-4o-mini | gpt-4o-mini, gemini-1.5-flash |
| `AI_API_KEY` | set-me | Your API key |
| `AI_TRACE` | False | true/false (debug mode) |

## For PythonAnywhere Deployment

1. Upload code to PythonAnywhere
2. Create `.env` file with your API key
3. Run: `pip install -r requirements.txt`
4. Run: `python manage.py migrate`
5. Configure WSGI file to load `.env`
6. Restart web app

See `PYTHONANYWHERE_DEPLOYMENT.md` for detailed steps.

## Code Quality Features

✅ Type hints throughout  
✅ Comprehensive logging  
✅ Error handling with fallbacks  
✅ Rate limiting for production  
✅ Clean separation of concerns  
✅ Environment-based configuration  
✅ Multi-provider support  

## Troubleshooting

**Issue:** "No API key available"
- **Solution:** Check `.env` file and ensure API key is set correctly

**Issue:** Rate limit errors
- **Solution:** Wait 60 seconds or increase rate limit in `rate_limit.py`

**Issue:** Slow responses
- **Solution:** Try Google Gemini (faster) or Groq API

**Issue:** ".env not loading"
- **Solution:** Ensure `python-dotenv` is installed: `pip install python-dotenv`
