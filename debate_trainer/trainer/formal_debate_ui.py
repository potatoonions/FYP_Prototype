from django.http import HttpResponse
from django.views.decorators.http import require_GET
import logging

logger = logging.getLogger("trainer")


@require_GET
def formal_debate_view(request):
    """Interactive formal debate interface with customizable settings."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Formal Debate Competition</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .header p {
                font-size: 1.1em;
                opacity: 0.9;
            }
            .content {
                padding: 40px;
            }
            .setup-section {
                display: none;
            }
            .setup-section.active {
                display: block;
            }
            .debate-section {
                display: none;
            }
            .debate-section.active {
                display: block;
            }
            .form-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }
            .form-grid.full {
                grid-template-columns: 1fr;
            }
            .form-group {
                display: flex;
                flex-direction: column;
            }
            label {
                font-weight: 600;
                margin-bottom: 8px;
                color: #333;
            }
            input, select, textarea {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 1em;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            input:focus, select:focus, textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            button {
                flex: 1;
                padding: 14px;
                border: none;
                border-radius: 8px;
                font-size: 1em;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            .btn-secondary {
                background: #f0f0f0;
                color: #333;
            }
            .btn-secondary:hover {
                background: #e0e0e0;
            }
            
            /* Debate Interface */
            .debate-header {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .debate-info {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
            }
            .info-card {
                background: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                border-left: 4px solid #667eea;
            }
            .info-card h3 {
                font-size: 0.9em;
                color: #666;
                margin-bottom: 8px;
            }
            .info-card .value {
                font-size: 1.5em;
                font-weight: bold;
                color: #333;
            }
            
            .speaker-turn {
                background: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                text-align: center;
            }
            .speaker-turn h2 {
                color: #333;
                margin-bottom: 10px;
            }
            .speaker-turn .speaker-name {
                font-size: 1.3em;
                font-weight: bold;
                color: #667eea;
            }
            
            .timer {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 20px;
            }
            .timer .time-display {
                font-size: 3em;
                font-weight: bold;
                font-family: 'Courier New', monospace;
            }
            .timer .time-label {
                font-size: 0.9em;
                opacity: 0.9;
                margin-top: 5px;
            }
            .timer.warning {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            }
            
            .speech-history {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                max-height: 400px;
                overflow-y: auto;
            }
            .speech-item {
                background: white;
                padding: 15px;
                border-left: 4px solid #667eea;
                margin-bottom: 10px;
                border-radius: 4px;
            }
            .speech-item.ai {
                border-left-color: #764ba2;
            }
            .speech-item.user {
                border-left-color: #667eea;
            }
            .speech-meta {
                font-size: 0.9em;
                color: #666;
                margin-bottom: 8px;
            }
            .speech-meta strong {
                color: #333;
            }
            .speech-content {
                color: #333;
                line-height: 1.6;
            }
            
            .speech-input {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .speech-input textarea {
                min-height: 150px;
                resize: vertical;
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
            .spinner {
                display: inline-block;
                width: 30px;
                height: 30px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: none;
            }
            .error.active {
                display: block;
            }
            
            .scores {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-top: 20px;
            }
            .score-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .score-card h3 {
                color: #666;
                margin-bottom: 10px;
            }
            .score-card .score {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 10px;
            }
            .progress-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                width: 0%;
                transition: width 0.3s;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎤 Formal Debate Competition</h1>
                <p>Back-and-forth debate with real-time feedback</p>
            </div>
            
            <div class="content">
                <!-- Setup Section -->
                <div class="setup-section active" id="setupSection">
                    <h2>Configure Your Debate</h2>
                    <form id="setupForm">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="motion">Debate Motion</label>
                                <textarea id="motion" placeholder="e.g., Social media is beneficial to society" required></textarea>
                            </div>
                        </div>
                        
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="userName">Your Name</label>
                                <input type="text" id="userName" placeholder="Anonymous" value="Anonymous">
                            </div>
                            <div class="form-group">
                                <label for="userSide">Your Side</label>
                                <select id="userSide">
                                    <option value="affirmative">Affirmative (For)</option>
                                    <option value="negative">Negative (Against)</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="speakersPerSide">Speakers Per Side</label>
                                <input type="number" id="speakersPerSide" value="2" min="1" max="10">
                            </div>
                            <div class="form-group">
                                <label for="substantiveTime">Substantive Speech Time (minutes)</label>
                                <input type="number" id="substantiveTime" value="8" min="1" max="30">
                            </div>
                        </div>
                        
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="replyTime">Reply Speech Time (minutes)</label>
                                <input type="number" id="replyTime" value="4" min="1" max="15">
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="includeReplies" checked>
                                    Include Reply Speeches
                                </label>
                            </div>
                        </div>
                        
                        <div class="form-grid">
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="allowPOI" checked>
                                    Allow Points of Information (POI)
                                </label>
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="noNewArgs" checked>
                                    Enforce: No New Arguments in Rebuttals
                                </label>
                            </div>
                        </div>
                        
                        <div class="button-group">
                            <button type="submit" class="btn-primary">Start Debate</button>
                        </div>
                    </form>
                </div>
                
                <!-- Debate Section -->
                <div class="debate-section" id="debateSection">
                    <div class="debate-header">
                        <div class="debate-info">
                            <div class="info-card">
                                <h3>Motion</h3>
                                <div class="value" id="motionDisplay"></div>
                            </div>
                            <div class="info-card">
                                <h3>Your Side</h3>
                                <div class="value" id="userSideDisplay"></div>
                            </div>
                            <div class="info-card">
                                <h3>Progress</h3>
                                <div class="value" id="progressDisplay">0/0</div>
                            </div>
                            <div class="info-card">
                                <h3>Status</h3>
                                <div class="value" id="statusDisplay">Starting...</div>
                            </div>
                        </div>
                        <div class="progress-bar" style="margin-top: 15px;">
                            <div class="progress-bar-fill" id="progressBar"></div>
                        </div>
                    </div>
                    
                    <div id="errorDiv" class="error"></div>
                    
                    <div class="speaker-turn" id="speakerTurn"></div>
                    
                    <div class="timer" id="timer">
                        <div class="time-display" id="timeDisplay">0:00</div>
                        <div class="time-label" id="timeLabel">Time remaining</div>
                    </div>
                    
                    <div class="speech-history" id="speechHistory">
                        <p style="color: #999; text-align: center;">Debate history will appear here...</p>
                    </div>
                    
                    <div id="inputSection"></div>
                    
                    <div class="loading" id="loading">
                        <div class="spinner"></div>
                        <p>AI is preparing their speech...</p>
                    </div>
                    
                    <div class="scores" id="scores" style="display: none;">
                        <div class="score-card">
                            <h3>Your Score</h3>
                            <div class="score" id="userScore">0</div>
                        </div>
                        <div class="score-card">
                            <h3>AI Score</h3>
                            <div class="score" id="aiScore">0</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let currentSession = null;
            let debateConfig = null;
            let timeRemaining = 0;
            let timerInterval = null;
            
            // Setup form submission
            document.getElementById('setupForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const motion = document.getElementById('motion').value;
                const userName = document.getElementById('userName').value || 'Anonymous';
                const userSide = document.getElementById('userSide').value;
                const speakersPerSide = parseInt(document.getElementById('speakersPerSide').value);
                const substantiveTime = parseInt(document.getElementById('substantiveTime').value) * 60;
                const replyTime = parseInt(document.getElementById('replyTime').value) * 60;
                const includeReplies = document.getElementById('includeReplies').checked;
                const allowPOI = document.getElementById('allowPOI').checked;
                const noNewArgs = document.getElementById('noNewArgs').checked;
                
                try {
                    // Create debate
                    const createRes = await fetch('/api/formal/create/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            motion,
                            user_name: userName,
                            format_type: 'custom',
                            speakers_per_side: speakersPerSide,
                            substantive_time: substantiveTime,
                            reply_time: replyTime,
                            include_replies: includeReplies,
                            allow_poi: allowPOI,
                            no_new_arguments: noNewArgs,
                            user_side: userSide
                        })
                    });
                    
                    if (!createRes.ok) throw new Error('Failed to create debate');
                    const createData = await createRes.json();
                    
                    currentSession = createData.session_id;
                    debateConfig = createData;
                    
                    // Display setup info
                    document.getElementById('motionDisplay').textContent = motion.substring(0, 30);
                    document.getElementById('userSideDisplay').textContent = userSide;
                    document.getElementById('progressDisplay').textContent = `0/${createData.total_speeches}`;
                    
                    // Start debate
                    const startRes = await fetch('/api/formal/start/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: currentSession })
                    });
                    
                    if (!startRes.ok) throw new Error('Failed to start debate');
                    const startData = await startRes.json();
                    
                    // Show AI opening speech
                    addSpeechToHistory('ai', startData.current_speaker_side, 'substantive', startData.ai_opening_speech);
                    
                    // Switch to debate view
                    document.getElementById('setupSection').classList.remove('active');
                    document.getElementById('debateSection').classList.add('active');
                    
                    updateDebateStatus();
                } catch (error) {
                    showError('Error starting debate: ' + error.message);
                }
            });
            
            function addSpeechToHistory(speaker, side, type, content) {
                const history = document.getElementById('speechHistory');
                if (history.querySelector('p')) {
                    history.innerHTML = '';
                }
                
                const item = document.createElement('div');
                item.className = `speech-item ${speaker}`;
                item.innerHTML = `
                    <div class="speech-meta">
                        <strong>${speaker === 'ai' ? 'AI' : 'You'}</strong> (${side}, ${type})
                    </div>
                    <div class="speech-content">${content}</div>
                `;
                history.appendChild(item);
                history.scrollTop = history.scrollHeight;
            }
            
            function updateDebateStatus() {
                document.getElementById('speakerTurn').innerHTML = `
                    <h2>⏱️ Your Turn to Speak</h2>
                    <p>Prepare your <strong>substantive speech</strong> (${debateConfig.timing.substantive_seconds / 60} minutes)</p>
                `;
                
                // Create speech input
                const inputSection = document.getElementById('inputSection');
                inputSection.innerHTML = `
                    <div class="speech-input">
                        <textarea id="userSpeech" placeholder="Enter your speech here..." style="min-height: 200px;"></textarea>
                        <button class="btn-primary" onclick="submitSpeech()">Submit Speech</button>
                    </div>
                `;
            }
            
            async function submitSpeech() {
                const speech = document.getElementById('userSpeech').value;
                if (!speech.trim()) {
                    showError('Please enter your speech');
                    return;
                }
                
                try {
                    document.getElementById('loading').classList.add('active');
                    
                    const res = await fetch('/api/formal/speech/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: currentSession,
                            speech: speech,
                            time_taken: 300,
                            pois_received: []
                        })
                    });
                    
                    if (!res.ok) throw new Error('Failed to submit speech');
                    const data = await res.json();
                    
                    // Add user speech
                    addSpeechToHistory('user', 'user', 'substantive', speech);
                    
                    if (data.status === 'completed') {
                        // Debate completed
                        document.getElementById('inputSection').innerHTML = `
                            <div style="text-align: center; padding: 20px;">
                                <h2>🎉 Debate Completed!</h2>
                                <p>Final Scores:</p>
                                <p><strong>Your Score:</strong> ${data.scores.user_score}/100</p>
                                <p><strong>AI Score:</strong> ${data.scores.ai_score}/100</p>
                                <button class="btn-primary" onclick="location.reload()">Start New Debate</button>
                            </div>
                        `;
                    } else {
                        // Show AI speech
                        addSpeechToHistory('ai', data.next_speaker_side, data.next_speech_type, data.ai_speech);
                        updateDebateStatus();
                    }
                    
                    // Update scores
                    document.getElementById('userScore').textContent = Math.round(data.current_scores.user_score);
                    document.getElementById('aiScore').textContent = Math.round(data.current_scores.ai_score);
                    document.getElementById('scores').style.display = 'grid';
                    
                    // Update progress
                    document.getElementById('progressDisplay').textContent = `${data.progress.completed_speeches}/${data.progress.total_speeches}`;
                    document.getElementById('progressBar').style.width = data.progress.percent_complete + '%';
                    
                } catch (error) {
                    showError('Error: ' + error.message);
                } finally {
                    document.getElementById('loading').classList.remove('active');
                }
            }
            
            function showError(message) {
                const errorDiv = document.getElementById('errorDiv');
                errorDiv.textContent = message;
                errorDiv.classList.add('active');
                setTimeout(() => errorDiv.classList.remove('active'), 5000);
            }
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)
