# Quick Reference - Agentic AI Debate Trainer

## 🎯 What's New?

Your debate trainer now has an **AI agent system** that:

1. **Researches debate topics** using Google Scholar
2. **Generates AI opening positions** based on research  
3. **Conducts multi-turn debates** with users
4. **Analyzes arguments** for fallacies, evidence, and logic
5. **Provides real-time feedback** and scoring

---

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

# Open in browser
# - Multi-turn UI: http://localhost:8000/debate/chat/
# - Legacy UI: http://localhost:8000/debate/
```

### PythonAnywhere Deployment
```bash
# 1. Upload code via Files tab
# 2. In bash console:
cd /home/KeithLoZeHui/debate_trainer
mkvirtualenv --python=/usr/bin/python3.10 debate_trainer
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic

# 3. Set AI_API_KEY in Web app settings
# 4. Reload web app
```

---

## 📊 API Endpoints

### Start Debate
```bash
POST /api/debate/start/
Content-Type: application/json

{
  "topic": "AI Ethics",
  "user_name": "John",
  "difficulty": "medium"
}
```

### Submit Response  
```bash
POST /api/debate/response/
Content-Type: application/json

{
  "session_id": "uuid",
  "response": "Your argument here"
}
```

### End Debate
```bash
POST /api/debate/end/
Content-Type: application/json

{
  "session_id": "uuid"
}
```

### Get History
```bash
GET /api/debate/history/?session_id=uuid
```

---

## 🔧 Key Files

| File | Purpose |
|------|---------|
| `trainer/models.py` | Added `DebateRound` model |
| `trainer/views.py` | 4 new debate flow endpoints |
| `trainer/services/agent.py` | AI debate methods |
| `trainer/services/research.py` | Google Scholar integration |
| `trainer/debate_chat.py` | Interactive web UI |
| `trainer/urls.py` | New routes |
| `requirements.txt` | Added scholarly, requests |

---

## 💾 Database

New table: `DebateRound`
- Stores multi-turn debate sessions
- Tracks conversation history
- Saves scores and feedback per round

Run migrations:
```bash
python manage.py migrate
```

---

## 🎮 Web Interface

### Multi-Turn Debate Chat
- **URL**: `/debate/chat/`
- **Features**:
  - Enter any debate topic
  - See research papers found
  - Multi-turn conversation display
  - Real-time scoring
  - Coach feedback each round
  - Difficulty selection

### Access from Browser
```
Local: http://localhost:8000/debate/chat/
PythonAnywhere: https://KeithLoZeHui.pythonanywhere.com/debate/chat/
```

---

## 🔐 Environment Variables

```bash
# Required for AI features
export AI_API_KEY="your-openai-api-key"

# Optional
export AI_MODEL_NAME="gpt-4o-mini"  # default
export AI_MODEL_PROVIDER="openai"    # default
export AI_TRACE="false"              # debug mode
```

---

## 📋 Features

| Feature | Status | Details |
|---------|--------|---------|
| Multi-turn debates | ✅ | AI responds each round |
| Research integration | ✅ | Google Scholar papers |
| Argument analysis | ✅ | Fallacy detection, scoring |
| Real-time feedback | ✅ | Per-round coaching |
| Conversation history | ✅ | Full session tracking |
| Web UI | ✅ | Interactive chat interface |
| REST API | ✅ | Full programmatic access |
| Difficulty levels | ✅ | Easy, Medium, Hard |

---

## ⚙️ Configuration

### settings.py
```python
ALLOWED_HOSTS = ['KeithLoZeHui.pythonanywhere.com']
DEBUG = False  # Set to True for debugging

# AI Settings
AI_MODEL_NAME = "gpt-4o-mini"
AI_MODEL_PROVIDER = "openai"
AI_API_KEY = os.environ.get("AI_API_KEY", "")

# Static files
STATIC_ROOT = '/home/KeithLoZeHui/debate_trainer/static'
STATIC_URL = '/static/'
```

---

## 🐛 Troubleshooting

### Migration errors
```bash
python manage.py migrate --run-syncdb
python manage.py makemigrations trainer
python manage.py migrate
```

### Missing modules
```bash
pip install -r requirements.txt
```

### API key issues
- Check `AI_API_KEY` environment variable
- System falls back to template responses if key missing
- Debates still work but less sophisticated

### Google Scholar not working
- Automatic fallback mode activates
- Debates proceed with general topic knowledge
- No impact on debate functionality

---

## 📈 Example Workflow

```python
import requests

BASE = "http://localhost:8000/api"

# Start debate
start = requests.post(f"{BASE}/debate/start/", json={
    "topic": "Climate Policy",
    "user_name": "Alice",
    "difficulty": "medium"
}).json()

print(f"AI: {start['ai_opening_position']}")
# AI: "We should implement carbon taxes..."

session_id = start['session_id']

# User responds
resp = requests.post(f"{BASE}/debate/response/", json={
    "session_id": session_id,
    "response": "But that hurts the economy..."
}).json()

print(f"AI: {resp['ai_counter_argument']}")
# AI: "Consider that long-term costs of climate..."
print(f"Score: {resp['overall_score']}/100")
# Score: 72.5/100

# End debate
end = requests.post(f"{BASE}/debate/end/", json={
    "session_id": session_id
}).json()

print(f"Final: {end['overall_score']} over {end['total_rounds']} rounds")
# Final: 72.5 over 1 rounds
```

---

## 🚀 Deployment Steps

1. **Prepare code**
   ```bash
   git add -A
   git commit -m "Add agentic AI debate features"
   ```

2. **Upload to PythonAnywhere**
   - Use Files tab or Git

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Set environment variables**
   - Web tab → Environment variables
   - Add: `AI_API_KEY = your-key`

6. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

7. **Reload web app**
   - Click Reload button in Web tab

8. **Test endpoints**
   - Visit: `https://KeithLoZeHui.pythonanywhere.com/debate/chat/`

---

## 📚 Documentation Files

- **DEBATE_AI_SETUP.md** - Detailed feature documentation
- **PYTHONANYWHERE_DEPLOYMENT.md** - Deployment guide
- **This file** - Quick reference

---

## 💡 Tips

- **Research often fails** due to rate limiting - that's OK, fallback works
- **Test locally first** before deploying
- **Check error logs** in PythonAnywhere if issues arise
- **Use Postman** to test API endpoints
- **Monitor usage** to ensure you don't exceed API quotas

---

## 🎓 What Happens During a Debate

1. User enters topic
2. AI researches topic (Google Scholar)
3. AI generates opening position
4. User types response
5. AI analyzes user argument (fallacies, evidence, structure)
6. AI generates counter-argument
7. Score calculated per round
8. Overall score averaged across rounds
9. Coach feedback provided
10. Repeat or end debate

---

## Next Steps

- [ ] Deploy to PythonAnywhere
- [ ] Test `/debate/chat/` interface
- [ ] Verify API endpoints work
- [ ] Configure your OpenAI API key
- [ ] Monitor logs for errors
- [ ] Consider adding user authentication
- [ ] Track debate statistics
- [ ] Gather user feedback

---

## Support

For detailed info, see:
- `DEBATE_AI_SETUP.md` - Full feature documentation
- `PYTHONANYWHERE_DEPLOYMENT.md` - Step-by-step deployment
- Code comments in `views.py`, `agent.py`, `research.py`

Your debate trainer is ready to deploy! 🎉
