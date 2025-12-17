from __future__ import annotations

import json
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings
from django.views.decorators.http import require_GET, require_http_methods

from .models import DebateSession
from .services.agent import from_settings
from .services.analysis import analyze_argument


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@require_GET
def home_view(request: HttpRequest) -> HttpResponse:
    """Home page view with API information."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Debate Trainer</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                margin-top: 0;
                font-size: 2.5em;
            }
            h2 {
                color: #764ba2;
                margin-top: 30px;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
            }
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.9em;
                margin-right: 10px;
            }
            .method.post {
                background: #28a745;
                color: white;
            }
            .method.get {
                background: #007bff;
                color: white;
            }
            code {
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }
            .links {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 2px solid #eee;
            }
            .links a {
                color: #667eea;
                text-decoration: none;
                margin-right: 20px;
                font-weight: 500;
            }
            .links a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 AI Debate Trainer</h1>
            <p>Welcome to the AI Debate Trainer API. Use this service to practice your debate skills with AI-powered feedback and counterarguments.</p>
            
            <h2>API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/debate/</strong>
                <p>Submit a debate argument and receive AI feedback, counterarguments, and analysis.</p>
                <p><strong>Request Body:</strong></p>
                <pre><code>{
  "topic": "Climate Change",
  "argument": "Your argument here",
  "user_name": "John Doe",
  "difficulty": "medium"
}</code></pre>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/sessions/</strong>
                <p>Retrieve debate session history.</p>
                <p><strong>Query Parameters:</strong> <code>?limit=20</code></p>
            </div>
            
            <div class="links">
                <a href="/admin/">Admin Panel</a>
                <a href="/debate/">Try Debate Trainer</a>
                <a href="/api/sessions/">Session History</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)


@require_http_methods(["GET"])
def debate_form_view(request: HttpRequest) -> HttpResponse:
    """Web interface for debate training."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Debate Trainer - Practice</title>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                margin-top: 0;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #555;
            }
            input[type="text"], textarea, select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            input[type="text"]:focus, textarea:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            textarea {
                min-height: 150px;
                resize: vertical;
            }
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #667eea;
            }
            .loading.active {
                display: block;
            }
            .result {
                display: none;
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .result.active {
                display: block;
            }
            .result h3 {
                color: #667eea;
                margin-top: 0;
            }
            .score {
                font-size: 2em;
                font-weight: bold;
                color: #28a745;
                margin: 10px 0;
            }
            .section {
                margin: 20px 0;
                padding: 15px;
                background: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            .section h4 {
                margin-top: 0;
                color: #764ba2;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                border-left: 4px solid #dc3545;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #667eea;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-link">← Back to Home</a>
            <h1>🎯 Practice Your Debate Skills</h1>
            <p>Enter your argument and get AI-powered feedback, counterarguments, and analysis.</p>
            
            <form id="debateForm">
                <div class="form-group">
                    <label for="user_name">Your Name</label>
                    <input type="text" id="user_name" name="user_name" placeholder="Enter your name" value="Anonymous">
                </div>
                
                <div class="form-group">
                    <label for="topic">Debate Topic</label>
                    <input type="text" id="topic" name="topic" placeholder="e.g., Climate Change, Education Reform" value="General">
                </div>
                
                <div class="form-group">
                    <label for="difficulty">Difficulty Level</label>
                    <select id="difficulty" name="difficulty">
                        <option value="easy">Easy</option>
                        <option value="medium" selected>Medium</option>
                        <option value="hard">Hard</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="argument">Your Argument</label>
                    <textarea id="argument" name="argument" placeholder="Enter your debate argument here..." required></textarea>
                </div>
                
                <button type="submit">Submit Argument</button>
            </form>
            
            <div class="loading" id="loading">
                <p>🤔 Analyzing your argument and generating feedback...</p>
            </div>
            
            <div class="error" id="error" style="display: none;"></div>
            
            <div class="result" id="result">
                <h3>📊 Your Results</h3>
                <div class="score" id="score"></div>
                
                <div class="section">
                    <h4>🎯 Counterargument</h4>
                    <p id="counterargument"></p>
                </div>
                
                <div class="section">
                    <h4>📈 Analysis</h4>
                    <div id="analysis"></div>
                </div>
                
                <div class="section">
                    <h4>💡 Coach Feedback</h4>
                    <p id="feedback"></p>
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('debateForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const form = e.target;
                const loading = document.getElementById('loading');
                const result = document.getElementById('result');
                const error = document.getElementById('error');
                const submitBtn = form.querySelector('button[type="submit"]');
                
                // Hide previous results
                result.classList.remove('active');
                error.style.display = 'none';
                
                // Show loading
                loading.classList.add('active');
                submitBtn.disabled = true;
                
                const formData = {
                    user_name: document.getElementById('user_name').value || 'Anonymous',
                    topic: document.getElementById('topic').value || 'General',
                    difficulty: document.getElementById('difficulty').value || 'medium',
                    argument: document.getElementById('argument').value
                };
                
                try {
                    const response = await fetch('/api/debate/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(formData)
                    });
                    
                    const data = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(data.error || 'An error occurred');
                    }
                    
                    // Display results
                    document.getElementById('score').textContent = `Score: ${data.score}/100`;
                    document.getElementById('counterargument').textContent = data.counterargument || 'No counterargument provided';
                    
                    // Display analysis
                    const analysisDiv = document.getElementById('analysis');
                    if (data.analysis) {
                        let analysisHtml = '';
                        if (data.analysis.strengths && data.analysis.strengths.length > 0) {
                            analysisHtml += '<p><strong>Strengths:</strong> ' + data.analysis.strengths.join(', ') + '</p>';
                        }
                        if (data.analysis.weaknesses && data.analysis.weaknesses.length > 0) {
                            analysisHtml += '<p><strong>Weaknesses:</strong> ' + data.analysis.weaknesses.join(', ') + '</p>';
                        }
                        analysisDiv.innerHTML = analysisHtml || '<p>Analysis data not available</p>';
                    }
                    
                    document.getElementById('feedback').textContent = data.coach_feedback || 'No feedback provided';
                    
                    result.classList.add('active');
                    result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    
                } catch (err) {
                    error.textContent = 'Error: ' + err.message;
                    error.style.display = 'block';
                } finally {
                    loading.classList.remove('active');
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)


@csrf_exempt
def debate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _json_error("Only POST is allowed", status=405)

    try:
        payload: Dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return _json_error("Invalid JSON payload")

    topic = payload.get("topic") or "General"
    user_argument = payload.get("argument")
    user_name = payload.get("user_name") or "anonymous"
    difficulty = payload.get("difficulty") or "medium"

    if not user_argument:
        return _json_error("`argument` is required")

    agent = from_settings(settings)
    analysis = analyze_argument(user_argument).as_dict()
    counter = agent.generate_counterargument(topic, user_argument, difficulty)
    feedback = agent.critique_and_feedback(user_argument)

    combined_score = round((analysis["score"] + (0.1 if "logical_connectors" in analysis["strengths"] else 0)) * 100, 1)

    session = DebateSession.objects.create(
        user_name=user_name,
        topic=topic,
        user_argument=user_argument,
        ai_feedback={"analysis": analysis, "counter": counter, "coach_feedback": feedback},
        score=combined_score,
    )

    response = {
        "session_id": session.id,
        "topic": topic,
        "counterargument": counter["counterargument"],
        "analysis": analysis,
        "coach_feedback": feedback,
        "score": combined_score,
    }
    return JsonResponse(response)


@require_GET
def session_history(request: HttpRequest) -> JsonResponse:
    limit = int(request.GET.get("limit", "20"))
    sessions = DebateSession.objects.all()[: limit or 20]
    data = [
        {
            "id": s.id,
            "user_name": s.user_name,
            "topic": s.topic,
            "score": s.score,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
    return JsonResponse({"sessions": data})

