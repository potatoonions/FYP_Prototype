"""Multi-turn debate interface with research integration."""
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def debate_chat_view(request: HttpRequest) -> HttpResponse:
    """Interactive multi-turn debate interface."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Debate Trainer - Multi-turn Debate</title>
        <style>
            * { box-sizing: border-box; }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: 1fr 300px;
                gap: 20px;
            }
            
            .main {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                display: flex;
                flex-direction: column;
            }
            
            .sidebar {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                height: fit-content;
            }
            
            h1 {
                color: #667eea;
                margin: 0 0 10px 0;
                font-size: 1.8em;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 20px;
                font-size: 0.95em;
            }
            
            .status {
                background: #f0f4ff;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #667eea;
            }
            
            .status.loading {
                background: #fff3cd;
                border-left-color: #ffc107;
            }
            
            .status.error {
                background: #f8d7da;
                border-left-color: #dc3545;
                color: #721c24;
            }
            
            .topic-input {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
            }
            
            .topic-input input {
                flex: 1;
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
            
            .topic-input select {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }
            
            .topic-input button {
                padding: 10px 20px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .topic-input button:hover {
                background: #764ba2;
            }
            
            .conversation {
                flex: 1;
                overflow-y: auto;
                margin-bottom: 20px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                min-height: 300px;
                max-height: 500px;
            }
            
            .message {
                margin-bottom: 15px;
                padding: 12px;
                border-radius: 8px;
                animation: slideIn 0.3s ease;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .message.ai {
                background: #e7f0ff;
                border-left: 4px solid #667eea;
            }
            
            .message.user {
                background: #e8f5e9;
                border-left: 4px solid #28a745;
                margin-left: 20px;
            }
            
            .message.system {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
            }
            
            .message-role {
                font-weight: 600;
                font-size: 0.85em;
                color: #555;
                margin-bottom: 5px;
            }
            
            .message-content {
                color: #333;
                line-height: 1.5;
            }
            
            .response-input {
                display: flex;
                gap: 10px;
            }
            
            textarea {
                flex: 1;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-family: inherit;
                font-size: 14px;
                resize: vertical;
                min-height: 80px;
                transition: border-color 0.3s;
            }
            
            textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .input-buttons {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            
            button {
                padding: 12px 20px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            button:hover {
                background: #764ba2;
            }
            
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            button.secondary {
                background: #6c757d;
            }
            
            button.secondary:hover {
                background: #5a6268;
            }
            
            .sidebar h3 {
                color: #667eea;
                margin-top: 0;
                font-size: 1.1em;
            }
            
            .sidebar-section {
                margin-bottom: 20px;
                padding-bottom: 20px;
                border-bottom: 1px solid #eee;
            }
            
            .sidebar-section:last-child {
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }
            
            .info-item {
                font-size: 0.9em;
                margin-bottom: 8px;
                color: #555;
            }
            
            .info-label {
                font-weight: 600;
                color: #333;
            }
            
            .score {
                font-size: 2em;
                font-weight: bold;
                color: #28a745;
                text-align: center;
                margin: 10px 0;
            }
            
            .research-papers {
                max-height: 300px;
                overflow-y: auto;
                font-size: 0.85em;
            }
            
            .paper {
                background: #f0f4ff;
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 8px;
                border-left: 3px solid #667eea;
            }
            
            .paper-title {
                font-weight: 600;
                color: #667eea;
                margin-bottom: 2px;
            }
            
            @media (max-width: 768px) {
                .container {
                    grid-template-columns: 1fr;
                }
                
                .sidebar {
                    order: -1;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="main">
                <h1>🎯 AI Debate Trainer</h1>
                <p class="subtitle">Multi-turn debate with AI research integration</p>
                
                <div id="status" class="status" style="display: none;"></div>
                
                <!-- Topic Input -->
                <div class="topic-input" id="topicSection">
                    <input type="text" id="topicInput" placeholder="Enter a debate topic (e.g., AI Ethics, Climate Policy)..." value="Artificial Intelligence Ethics">
                    <select id="difficulty">
                        <option value="easy">Easy</option>
                        <option value="medium" selected>Medium</option>
                        <option value="hard">Hard</option>
                    </select>
                    <button onclick="startDebate()">Start Debate</button>
                </div>
                
                <!-- Conversation Area -->
                <div class="conversation" id="conversation" style="display: none;"></div>
                
                <!-- Response Input -->
                <div id="responseSection" style="display: none;">
                    <div class="response-input">
                        <textarea id="userResponse" placeholder="Type your response here..."></textarea>
                        <div class="input-buttons">
                            <button onclick="submitResponse()">Submit Response</button>
                            <button class="secondary" onclick="endDebate()">End Debate</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Sidebar -->
            <div class="sidebar" id="sidebar" style="display: none;">
                <h3>📊 Debate Info</h3>
                
                <div class="sidebar-section">
                    <div class="info-item">
                        <span class="info-label">Topic:</span>
                        <span id="sidebarTopic"></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Difficulty:</span>
                        <span id="sidebarDifficulty"></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Round:</span>
                        <span id="sidebarRound">1</span>
                    </div>
                </div>
                
                <div class="sidebar-section">
                    <div class="info-label">Current Score</div>
                    <div class="score" id="currentScore">-</div>
                </div>
                
                <div class="sidebar-section">
                    <div class="info-label">📚 Research Found</div>
                    <div class="info-item" id="papersCount">Papers: 0</div>
                    <div class="research-papers" id="researchPapers"></div>
                </div>
            </div>
        </div>
        
        <script>
            let sessionId = null;
            let currentRound = 1;
            let isWaitingForAI = false;
            let researchData = null;
            
            function showStatus(message, type = 'info') {
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = message;
                statusDiv.className = 'status ' + type;
                statusDiv.style.display = 'block';
            }
            
            function hideStatus() {
                document.getElementById('status').style.display = 'none';
            }
            
            function addMessage(role, content, round = null) {
                const conv = document.getElementById('conversation');
                const msg = document.createElement('div');
                msg.className = 'message ' + role;
                
                let roleText = role === 'ai' ? '🤖 AI Debate Opponent' : '👤 You';
                msg.innerHTML = `
                    <div class="message-role">${roleText}</div>
                    <div class="message-content">${content}</div>
                `;
                
                conv.appendChild(msg);
                conv.scrollTop = conv.scrollHeight;
            }
            
            async function startDebate() {
                const topic = document.getElementById('topicInput').value.trim();
                const difficulty = document.getElementById('difficulty').value;
                
                if (!topic) {
                    showStatus('Please enter a debate topic', 'error');
                    return;
                }
                
                showStatus('🔍 Researching topic and generating opening position...', 'loading');
                document.getElementById('topicSection').style.display = 'none';
                
                try {
                    const response = await fetch('/api/debate/start/', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            topic: topic,
                            user_name: 'Debater',
                            difficulty: difficulty
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.error || 'Failed to start debate');
                    }
                    
                    const data = await response.json();
                    sessionId = data.session_id;
                    currentRound = 1;
                    researchData = data.research_context;
                    
                    // Show conversation and sidebar
                    document.getElementById('conversation').style.display = 'block';
                    document.getElementById('responseSection').style.display = 'block';
                    document.getElementById('sidebar').style.display = 'block';
                    
                    // Update sidebar
                    document.getElementById('sidebarTopic').textContent = topic;
                    document.getElementById('sidebarDifficulty').textContent = difficulty;
                    document.getElementById('papersCount').textContent = 'Papers: ' + data.research_context.papers_found;
                    
                    // Display research papers
                    if (researchData.summary) {
                        addMessage('system', researchData.summary);
                    }
                    
                    // Add AI opening
                    addMessage('ai', data.ai_opening_position, 1);
                    
                    hideStatus();
                    document.getElementById('userResponse').focus();
                    
                } catch (err) {
                    showStatus('Error: ' + err.message, 'error');
                    document.getElementById('topicSection').style.display = 'flex';
                }
            }
            
            async function submitResponse() {
                const response = document.getElementById('userResponse').value.trim();
                
                if (!response) {
                    showStatus('Please enter a response', 'error');
                    return;
                }
                
                if (!sessionId) {
                    showStatus('No active debate session', 'error');
                    return;
                }
                
                showStatus('⏳ Processing your response...', 'loading');
                document.getElementById('userResponse').disabled = true;
                isWaitingForAI = true;
                
                try {
                    const res = await fetch('/api/debate/response/', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            session_id: sessionId,
                            response: response
                        })
                    });
                    
                    if (!res.ok) {
                        const error = await res.json();
                        throw new Error(error.error || 'Failed to process response');
                    }
                    
                    const data = await res.json();
                    
                    // Add user message
                    addMessage('user', response, data.round);
                    
                    // Add AI counter
                    addMessage('ai', data.ai_counter_argument, data.round + 1);
                    
                    // Update score
                    document.getElementById('currentScore').textContent = data.overall_score;
                    document.getElementById('sidebarRound').textContent = data.next_round;
                    
                    // Show feedback
                    showStatus('💡 Feedback: ' + data.coach_feedback, 'info');
                    
                    // Clear input
                    document.getElementById('userResponse').value = '';
                    document.getElementById('userResponse').focus();
                    
                    currentRound = data.next_round;
                    
                } catch (err) {
                    showStatus('Error: ' + err.message, 'error');
                } finally {
                    document.getElementById('userResponse').disabled = false;
                    isWaitingForAI = false;
                }
            }
            
            async function endDebate() {
                if (!sessionId) return;
                
                try {
                    const response = await fetch('/api/debate/end/', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ session_id: sessionId })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        showStatus(`Debate ended! Final score: ${data.overall_score} over ${data.total_rounds} rounds`, 'info');
                        document.getElementById('responseSection').style.display = 'none';
                        
                        setTimeout(() => {
                            location.reload();
                        }, 2000);
                    }
                } catch (err) {
                    showStatus('Error ending debate: ' + err.message, 'error');
                }
            }
            
            // Allow Enter+Shift to submit
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('userResponse').addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && e.shiftKey && !isWaitingForAI) {
                        submitResponse();
                    }
                });
            });
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)
