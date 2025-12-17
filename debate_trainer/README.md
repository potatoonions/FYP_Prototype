# AI Debate Trainer (Django)

Agentic AI debate practice tool with real-time analysis and feedback.

## Quickstart
1. Create venv and install deps:
   ```bash
   cd debate_trainer
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
2. Run migrations and server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

## Environment
- `AI_API_KEY`: API key for the model provider (OpenAI supported out of box).
- `AI_MODEL_NAME`: defaults to `gpt-4o-mini`.
- `AI_MODEL_PROVIDER`: defaults to `openai`.
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` for standard Django config.

## API
POST `http://localhost:8000/api/debate/`
```json
{
  "topic": "Nuclear energy",
  "argument": "We should expand nuclear because it is low carbon.",
  "user_name": "Alex",
  "difficulty": "medium"
}
```
Example response:
```json
{
  "session_id": 1,
  "topic": "Nuclear energy",
  "counterargument": "...",
  "analysis": {"fallacies": [], "unsupported_claims": ["We should expand nuclear because it is low carbon"], "strengths": ["logical_connectors"], "score": 0.55},
  "coach_feedback": "...",
  "score": 62.0
}
```

GET `http://localhost:8000/api/sessions/?limit=10` returns recent session summaries.

## Testing
- Run `python manage.py check` to validate project config.
- Run `python manage.py test` for Django tests (none defined yet).

## Notes
- The agent falls back to a deterministic template when no API key or internet is available.
- Session logs are stored in SQLite for basic skill tracking.

