# Deploying Agentic AI Debate Trainer to PythonAnywhere

## Quick Start (5 minutes)

### 1. Upload Code
- Log in to **PythonAnywhere**
- Go to **Files** tab
- Upload your `debate_trainer` folder (or use Git)

### 2. Install Dependencies
Open a **Bash console** and run:

```bash
cd /home/KeithLoZeHui/debate_trainer
mkvirtualenv --python=/usr/bin/python3.10 debate_trainer
pip install -r requirements.txt
```

### 3. Run Migrations
```bash
python manage.py migrate
```

This creates the `DebateRound` table for multi-turn debates.

### 4. Set API Key
In PythonAnywhere Web App settings, add environment variable:
```
AI_API_KEY = your-openai-api-key
```

Or in a `.env` file in your project root:
```
AI_API_KEY=your-openai-api-key
```

### 5. Configure Web App
- Go to **Web** tab
- Click **Add a new web app**
- Choose **Manual configuration** → **Python 3.10**
- Update **WSGI configuration file**:

```python
import os
import sys

path = '/home/KeithLoZeHui/debate_trainer'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'debate_trainer.settings'

# Set API key from environment
if not os.environ.get('AI_API_KEY'):
    os.environ['AI_API_KEY'] = 'set-me'  # Replace with actual key

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 6. Static Files
In the **Web** tab, map static files:
- URL: `/static/`
- Directory: `/home/KeithLoZeHui/debate_trainer/static/`

Then run:
```bash
python manage.py collectstatic --noinput
```

### 7. Update settings.py
Add to `debate_trainer/settings.py`:

```python
ALLOWED_HOSTS = ['KeithLoZeHui.pythonanywhere.com', 'localhost', '127.0.0.1']

STATIC_ROOT = '/home/KeithLoZeHui/debate_trainer/static'
STATIC_URL = '/static/'

# For development
DEBUG = False  # Set to True for debugging
```

### 8. Reload Web App
- Go to **Web** tab
- Click **Reload** button
- Your app is now live! 🎉

## Access Your Debate Trainer

### Main Interface
- **Home**: `https://KeithLoZeHui.pythonanywhere.com/`
- **Multi-turn Debate Chat**: `https://KeithLoZeHui.pythonanywhere.com/debate/chat/`
- **Legacy Debate Interface**: `https://KeithLoZeHui.pythonanywhere.com/debate/`
- **API Docs**: `https://KeithLoZeHui.pythonanywhere.com/` (shows all endpoints)

## API Endpoints

Test your API with curl or Postman:

### Start a Debate
```bash
curl -X POST https://KeithLoZeHui.pythonanywhere.com/api/debate/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Climate Change",
    "user_name": "Your Name",
    "difficulty": "medium"
  }'
```

### Submit Response
```bash
curl -X POST https://KeithLoZeHui.pythonanywhere.com/api/debate/response/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "response": "Your debate response here"
  }'
```

### End Debate
```bash
curl -X POST https://KeithLoZeHui.pythonanywhere.com/api/debate/end/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'
```

## Troubleshooting

### ImportError: No module named 'scholarly'
```bash
# In bash console
pip install scholarly
```

### ModuleNotFoundError in wsgi.py
```bash
# Reinstall packages in correct virtualenv
workon debate_trainer
pip install -r requirements.txt
```

### Database migrations failed
```bash
python manage.py migrate --run-syncdb
```

### Static files not loading
```bash
python manage.py collectstatic --noinput --clear
```

### "scholarly" search not working
This is OK - the system falls back to general knowledge mode.

## Monitoring Your App

### View Logs
- **Web** tab → click app name → scroll to "Log files"
- **Error log**: Check for traceback errors
- **Server log**: Check for requests

### Check Database
All debate sessions are stored in `db.sqlite3`:
```bash
python manage.py dbshell
SELECT * FROM trainer_debateround;
```

## Key Features Now Live

✅ **Multi-Turn Debates** - Continuous debate flow  
✅ **Google Scholar Research** - Real academic sources  
✅ **AI Opponent** - OpenAI-powered debates  
✅ **Real-time Scoring** - Track your improvement  
✅ **Conversation History** - Review past debates  
✅ **REST API** - Programmatic access  
✅ **Web UI** - Interactive chat interface  

## Next Improvements

1. **Add User Accounts**
   - Track individual user statistics
   - Save debate history per user

2. **Add Debate Topics Library**
   - Pre-built popular topics
   - Suggested argument frameworks

3. **Add Social Features**
   - Share debate results
   - Compare scores with others

4. **Analytics Dashboard**
   - View your debate performance
   - Identify weak argument areas

5. **Advanced Difficulty Settings**
   - Custom AI personalities
   - Expert vs. beginner modes

## Support Resources

- **API Docs**: See DEBATE_AI_SETUP.md
- **Django Docs**: https://docs.djangoproject.com/
- **PythonAnywhere Docs**: https://help.pythonanywhere.com/
- **OpenAI Docs**: https://platform.openai.com/docs/

## Production Checklist

- [ ] Set `DEBUG = False` in settings.py
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Set a strong `SECRET_KEY`
- [ ] Configure `AI_API_KEY` environment variable
- [ ] Run `python manage.py collectstatic`
- [ ] Test all endpoints
- [ ] Monitor error logs
- [ ] Set up backups for database
- [ ] Consider adding rate limiting to API
- [ ] Add HTTPS (PythonAnywhere provides this)

Your debate trainer is ready! 🚀
