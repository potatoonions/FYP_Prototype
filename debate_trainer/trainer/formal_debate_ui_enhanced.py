from django.http import HttpResponse
from django.views.decorators.http import require_GET
import logging

logger = logging.getLogger("trainer")


@require_GET
def formal_debate_view(request):
    """Interactive formal debate interface with all enhanced features."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Debate Trainer - Enhanced</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            :root {
                --primary: #667eea;
                --secondary: #764ba2;
                --success: #28a745;
                --warning: #ffc107;
                --danger: #dc3545;
                --dark: #333;
                --light: #f8f9fa;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            
            /* Navigation Tabs */
            .nav-tabs {
                display: flex;
                background: var(--dark);
                overflow-x: auto;
            }
            .nav-tab {
                padding: 15px 25px;
                color: #aaa;
                cursor: pointer;
                border: none;
                background: none;
                font-size: 1em;
                white-space: nowrap;
                transition: all 0.3s;
            }
            .nav-tab:hover { color: white; }
            .nav-tab.active {
                color: white;
                background: var(--primary);
            }
            
            /* Sections */
            .section { display: none; padding: 30px; }
            .section.active { display: block; }
            
            /* Header */
            .header {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                padding: 25px;
                text-align: center;
            }
            .header h1 { font-size: 2em; margin-bottom: 5px; }
            
            /* User Profile Card */
            .profile-card {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
            }
            .profile-header { display: flex; justify-content: space-between; align-items: center; }
            .level-badge {
                background: rgba(255,255,255,0.2);
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
            }
            .xp-bar {
                background: rgba(255,255,255,0.3);
                border-radius: 10px;
                height: 12px;
                margin-top: 15px;
                overflow: hidden;
            }
            .xp-fill {
                background: var(--success);
                height: 100%;
                transition: width 0.5s;
            }
            .streak-badge {
                display: inline-block;
                background: var(--warning);
                color: var(--dark);
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                margin-top: 10px;
            }
            
            /* Form Elements */
            .form-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .form-group { display: flex; flex-direction: column; }
            label { font-weight: 600; margin-bottom: 6px; color: var(--dark); font-size: 0.9em; }
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
                border-color: var(--primary);
            }
            
            /* Buttons */
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 1em;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }
            .btn-primary {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102,126,234,0.4);
            }
            .btn-secondary { background: #e0e0e0; color: var(--dark); }
            .btn-success { background: var(--success); color: white; }
            .btn-danger { background: var(--danger); color: white; }
            .btn-sm { padding: 8px 16px; font-size: 0.9em; }
            .btn-group { display: flex; gap: 10px; flex-wrap: wrap; }
            
            /* Timer */
            .timer-display {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                margin: 20px 0;
            }
            .timer-display .time {
                font-size: 3.5em;
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }
            .timer-display.warning { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); }
            .timer-controls { margin-top: 15px; }
            
            /* Speech History */
            .speech-history {
                background: var(--light);
                border-radius: 12px;
                padding: 20px;
                max-height: 400px;
                overflow-y: auto;
                margin: 20px 0;
            }
            .speech-item {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 10px;
                border-left: 4px solid var(--primary);
            }
            .speech-item.ai { border-left-color: var(--secondary); }
            .speech-meta { font-size: 0.85em; color: #666; margin-bottom: 8px; }
            .speech-content { line-height: 1.6; }
            
            /* Voice Controls */
            .voice-controls {
                background: var(--light);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                display: flex;
                gap: 10px;
                align-items: center;
                flex-wrap: wrap;
            }
            .voice-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #ccc;
            }
            .voice-indicator.listening { background: var(--danger); animation: pulse 1s infinite; }
            .voice-indicator.speaking { background: var(--success); animation: pulse 1s infinite; }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            /* Personality Cards */
            .personality-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .personality-card {
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 15px;
                cursor: pointer;
                transition: all 0.3s;
                text-align: center;
            }
            .personality-card:hover { border-color: var(--primary); }
            .personality-card.selected {
                border-color: var(--primary);
                background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
            }
            .personality-card h4 { margin-bottom: 5px; }
            .personality-card p { font-size: 0.85em; color: #666; }
            
            /* Suggestions Panel */
            .suggestions-panel {
                background: #fff3cd;
                border: 1px solid var(--warning);
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }
            .suggestions-panel h4 { margin-bottom: 10px; color: #856404; }
            .suggestion-item {
                background: white;
                padding: 8px 12px;
                border-radius: 6px;
                margin: 5px 0;
                cursor: pointer;
                transition: background 0.2s;
            }
            .suggestion-item:hover { background: #ffeeba; }
            
            /* Stats Cards */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .stat-card .value {
                font-size: 2em;
                font-weight: bold;
                color: var(--primary);
            }
            .stat-card .label {
                font-size: 0.85em;
                color: #666;
                margin-top: 5px;
            }
            
            /* Charts */
            .chart-container {
                background: white;
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .chart-container h3 { margin-bottom: 15px; }
            
            /* Leaderboard */
            .leaderboard-table {
                width: 100%;
                border-collapse: collapse;
            }
            .leaderboard-table th, .leaderboard-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            .leaderboard-table tr:hover { background: var(--light); }
            .rank-1 { background: linear-gradient(90deg, #ffd700 0%, #fff 50%); }
            .rank-2 { background: linear-gradient(90deg, #c0c0c0 0%, #fff 50%); }
            .rank-3 { background: linear-gradient(90deg, #cd7f32 0%, #fff 50%); }
            
            /* Badges */
            .badges-grid {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .badge {
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.85em;
            }
            .badge.locked {
                background: #ccc;
                opacity: 0.6;
            }
            
            /* Session Replay */
            .replay-controls {
                display: flex;
                gap: 10px;
                align-items: center;
                margin: 15px 0;
            }
            .replay-progress {
                flex: 1;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
            }
            .replay-progress-fill {
                height: 100%;
                background: var(--primary);
                transition: width 0.3s;
            }
            
            /* Loading */
            .loading { text-align: center; padding: 30px; color: var(--primary); }
            .spinner {
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            }
            @keyframes spin { 100% { transform: rotate(360deg); } }
            
            /* Daily Challenge Banner */
            .challenge-banner {
                background: linear-gradient(90deg, #ff6b6b 0%, #feca57 100%);
                color: white;
                padding: 15px 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .challenge-banner.completed {
                background: linear-gradient(90deg, var(--success) 0%, #20c997 100%);
            }
            
            /* Toast Notifications */
            .toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
            }
            .toast {
                background: var(--dark);
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 10px;
                animation: slideIn 0.3s ease;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }
            .toast.success { background: var(--success); }
            .toast.error { background: var(--danger); }
            .toast.xp { background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            /* Mobile Responsive */
            @media (max-width: 768px) {
                .container { margin: 10px; }
                .section { padding: 15px; }
                .timer-display .time { font-size: 2.5em; }
                .form-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Navigation -->
            <nav class="nav-tabs">
                <button class="nav-tab active" onclick="showSection('debate')">🎤 Debate</button>
                <button class="nav-tab" onclick="showSection('analytics')">📊 Analytics</button>
                <button class="nav-tab" onclick="showSection('leaderboard')">🏆 Leaderboard</button>
                <button class="nav-tab" onclick="showSection('replay')">📼 Replay</button>
                <button class="nav-tab" onclick="showSection('settings')">⚙️ Settings</button>
            </nav>
            
            <!-- Toast Container -->
            <div class="toast-container" id="toastContainer"></div>
            
            <!-- DEBATE SECTION -->
            <div class="section active" id="debateSection">
                <div class="header">
                    <h1>🎯 AI Debate Trainer</h1>
                    <p>Practice debating with AI opponents • Earn XP • Climb the ranks</p>
                </div>
                
                <!-- User Profile Card -->
                <div class="profile-card" id="profileCard">
                    <div class="profile-header">
                        <div>
                            <h3 id="profileName">Loading...</h3>
                            <span class="streak-badge" id="streakBadge">🔥 0 day streak</span>
                        </div>
                        <div class="level-badge" id="levelBadge">Level 1</div>
                    </div>
                    <div class="xp-bar">
                        <div class="xp-fill" id="xpFill" style="width: 0%"></div>
                    </div>
                    <small id="xpText">0 / 100 XP</small>
                </div>
                
                <!-- Daily Challenge -->
                <div class="challenge-banner" id="challengeBanner">
                    <div>
                        <strong>📅 Daily Challenge:</strong>
                        <span id="challengeTopic">Loading...</span>
                    </div>
                    <button class="btn btn-sm" onclick="startDailyChallenge()">+50 XP →</button>
                </div>
                
                <!-- Setup Form -->
                <div id="setupForm">
                    <h2 style="margin-bottom: 20px;">Configure Your Debate</h2>
                    
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Your Name</label>
                            <input type="text" id="userName" value="Anonymous" placeholder="Enter your name">
                        </div>
                        <div class="form-group">
                            <label>Difficulty</label>
                            <select id="difficulty">
                                <option value="easy">Easy</option>
                                <option value="medium" selected>Medium</option>
                                <option value="hard">Hard</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Debate Motion / Topic</label>
                        <textarea id="motion" rows="2" placeholder="e.g., Social media does more harm than good"></textarea>
                    </div>
                    
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Your Side</label>
                            <select id="userSide">
                                <option value="affirmative">Affirmative (For)</option>
                                <option value="negative">Negative (Against)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Speech Time (minutes)</label>
                            <input type="number" id="speechTime" value="5" min="1" max="15">
                        </div>
                    </div>
                    
                    <!-- AI Personality Selection -->
                    <label style="margin-top: 15px;">AI Opponent Style</label>
                    <div class="personality-grid" id="personalityGrid">
                        <!-- Populated by JS -->
                    </div>
                    
                    <div class="btn-group" style="margin-top: 20px;">
                        <button class="btn btn-primary" onclick="startDebate()">🚀 Start Debate</button>
                    </div>
                </div>
                
                <!-- Active Debate Interface -->
                <div id="debateInterface" style="display: none;">
                    <!-- Timer -->
                    <div class="timer-display" id="timerDisplay">
                        <div class="time" id="timerTime">5:00</div>
                        <div>Time Remaining</div>
                        <div class="timer-controls">
                            <button class="btn btn-sm btn-secondary" onclick="pauseTimer()">⏸️ Pause</button>
                            <button class="btn btn-sm btn-secondary" onclick="resetTimer()">🔄 Reset</button>
                        </div>
                    </div>
                    
                    <!-- Voice Controls -->
                    <div class="voice-controls">
                        <div class="voice-indicator" id="voiceIndicator"></div>
                        <button class="btn btn-sm" id="sttBtn" onclick="toggleSpeechToText()">🎤 Speak</button>
                        <button class="btn btn-sm" id="ttsBtn" onclick="toggleTextToSpeech()">🔊 Read Aloud</button>
                        <label style="margin-left: auto;">
                            <input type="checkbox" id="autoTTS"> Auto-read AI responses
                        </label>
                    </div>
                    
                    <!-- Speech History -->
                    <div class="speech-history" id="speechHistory">
                        <p style="text-align: center; color: #999;">Debate will appear here...</p>
                    </div>
                    
                    <!-- Real-time Suggestions -->
                    <div class="suggestions-panel" id="suggestionsPanel" style="display: none;">
                        <h4>💡 Rebuttal Suggestions</h4>
                        <div id="suggestionsList"></div>
                    </div>
                    
                    <!-- User Input -->
                    <div class="form-group">
                        <label>Your Response</label>
                        <textarea id="userSpeech" rows="4" placeholder="Type your argument or click 🎤 to speak..."
                            oninput="handleTyping()"></textarea>
                    </div>
                    
                    <div class="btn-group">
                        <button class="btn btn-primary" onclick="submitSpeech()">Submit Speech</button>
                        <button class="btn btn-danger" onclick="endDebate()">End Debate</button>
                    </div>
                    
                    <!-- Current Scores -->
                    <div class="stats-grid" id="liveScores" style="margin-top: 20px;">
                        <div class="stat-card">
                            <div class="value" id="userScoreDisplay">0</div>
                            <div class="label">Your Score</div>
                        </div>
                        <div class="stat-card">
                            <div class="value" id="aiScoreDisplay">0</div>
                            <div class="label">AI Score</div>
                        </div>
                        <div class="stat-card">
                            <div class="value" id="roundDisplay">1</div>
                            <div class="label">Round</div>
                        </div>
                    </div>
                </div>
                
                <!-- Loading Overlay -->
                <div class="loading" id="loadingOverlay" style="display: none;">
                    <div class="spinner"></div>
                    <p>AI is thinking...</p>
                </div>
            </div>
            
            <!-- ANALYTICS SECTION -->
            <div class="section" id="analyticsSection">
                <h2>📊 Your Analytics</h2>
                
                <div class="stats-grid" id="analyticsStats">
                    <div class="stat-card">
                        <div class="value" id="totalDebates">0</div>
                        <div class="label">Total Debates</div>
                    </div>
                    <div class="stat-card">
                        <div class="value" id="avgScore">0</div>
                        <div class="label">Avg Score</div>
                    </div>
                    <div class="stat-card">
                        <div class="value" id="winRate">0%</div>
                        <div class="label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="value" id="bestScore">0</div>
                        <div class="label">Best Score</div>
                    </div>
                </div>
                
                <!-- Skill Radar Chart -->
                <div class="chart-container">
                    <h3>Skill Breakdown</h3>
                    <canvas id="skillRadar" width="400" height="300"></canvas>
                </div>
                
                <!-- Score History Chart -->
                <div class="chart-container">
                    <h3>Score History</h3>
                    <canvas id="scoreHistory" width="400" height="200"></canvas>
                </div>
                
                <!-- Fallacy Heatmap -->
                <div class="chart-container">
                    <h3>Common Fallacies to Avoid</h3>
                    <canvas id="fallacyChart" width="400" height="200"></canvas>
                </div>
                
                <!-- Badges -->
                <div class="chart-container">
                    <h3>🏅 Your Badges</h3>
                    <div class="badges-grid" id="badgesGrid">
                        <!-- Populated by JS -->
                    </div>
                </div>
            </div>
            
            <!-- LEADERBOARD SECTION -->
            <div class="section" id="leaderboardSection">
                <h2>🏆 Leaderboard</h2>
                
                <div class="btn-group" style="margin-bottom: 20px;">
                    <button class="btn btn-primary" onclick="loadLeaderboard('all')">All Time</button>
                    <button class="btn btn-secondary" onclick="loadLeaderboard('week')">This Week</button>
                    <button class="btn btn-secondary" onclick="loadLeaderboard('month')">This Month</button>
                </div>
                
                <div class="stat-card" id="yourRank" style="margin-bottom: 20px;">
                    <p>Your Rank: <strong id="rankDisplay">#--</strong> (Top <span id="percentileDisplay">--%</span>)</p>
                </div>
                
                <table class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Name</th>
                            <th>Level</th>
                            <th>XP</th>
                            <th>Win Rate</th>
                            <th>Streak</th>
                        </tr>
                    </thead>
                    <tbody id="leaderboardBody">
                        <!-- Populated by JS -->
                    </tbody>
                </table>
            </div>
            
            <!-- REPLAY SECTION -->
            <div class="section" id="replaySection">
                <h2>📼 Session Replay</h2>
                
                <div class="form-group">
                    <label>Select a Session to Replay</label>
                    <select id="replaySelect" onchange="loadReplay()">
                        <option value="">-- Select Session --</option>
                    </select>
                </div>
                
                <div id="replayViewer" style="display: none;">
                    <div class="replay-controls">
                        <button class="btn btn-sm" onclick="replayPrev()">⏮️</button>
                        <button class="btn btn-sm" onclick="replayPlay()">▶️ Play</button>
                        <button class="btn btn-sm" onclick="replayNext()">⏭️</button>
                        <div class="replay-progress">
                            <div class="replay-progress-fill" id="replayProgress"></div>
                        </div>
                        <span id="replayStep">0/0</span>
                    </div>
                    
                    <div class="speech-history" id="replayHistory">
                        <!-- Replay content -->
                    </div>
                    
                    <div class="stat-card">
                        <h4>Session Summary</h4>
                        <p>Topic: <span id="replayTopic"></span></p>
                        <p>Final Score: <span id="replayScore"></span></p>
                    </div>
                </div>
            </div>
            
            <!-- SETTINGS SECTION -->
            <div class="section" id="settingsSection">
                <h2>⚙️ Settings</h2>
                
                <div class="form-group">
                    <label>Text-to-Speech Voice</label>
                    <select id="ttsVoice">
                        <!-- Populated by JS -->
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Speech Rate</label>
                    <input type="range" id="ttsRate" min="0.5" max="2" step="0.1" value="1">
                    <span id="ttsRateValue">1.0x</span>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="soundEffects" checked>
                        Enable Sound Effects (timer bells)
                    </label>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="autoSuggestions" checked>
                        Show Real-time Rebuttal Suggestions
                    </label>
                </div>
            </div>
        </div>
        
        <script>
            // ============================================
            // STATE
            // ============================================
            let state = {
                userName: 'Anonymous',
                sessionId: null,
                currentRound: 1,
                timerSeconds: 300,
                timerInterval: null,
                timerPaused: false,
                selectedPersonality: 'balanced',
                isListening: false,
                isSpeaking: false,
                recognition: null,
                synthesis: window.speechSynthesis,
                replayData: null,
                replayIndex: 0,
                lastOpponentText: '',
            };
            
            // ============================================
            // INITIALIZATION
            // ============================================
            document.addEventListener('DOMContentLoaded', async () => {
                state.userName = localStorage.getItem('debateUserName') || 'Anonymous';
                document.getElementById('userName').value = state.userName;
                
                await loadPersonalities();
                await loadUserProfile();
                await loadDailyChallenge();
                loadVoices();
                initSpeechRecognition();
                loadSessionList();
            });
            
            // ============================================
            // NAVIGATION
            // ============================================
            function showSection(sectionName) {
                document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                
                document.getElementById(sectionName + 'Section').classList.add('active');
                event.target.classList.add('active');
                
                if (sectionName === 'analytics') loadAnalytics();
                if (sectionName === 'leaderboard') loadLeaderboard('all');
            }
            
            // ============================================
            // USER PROFILE & GAMIFICATION
            // ============================================
            async function loadUserProfile() {
                try {
                    const res = await fetch(`/api/profile/?user_name=${encodeURIComponent(state.userName)}`);
                    const data = await res.json();
                    
                    document.getElementById('profileName').textContent = data.user_name;
                    document.getElementById('levelBadge').textContent = `Level ${data.level}`;
                    document.getElementById('streakBadge').textContent = `🔥 ${data.current_streak} day streak`;
                    document.getElementById('xpFill').style.width = `${data.progress_percent}%`;
                    document.getElementById('xpText').textContent = `${data.xp_progress} / ${data.xp_needed} XP`;
                    
                    // Show new badges
                    if (data.new_badges && data.new_badges.length > 0) {
                        data.new_badges.forEach(badge => {
                            showToast(`🏅 New Badge: ${badge.name}!`, 'success');
                        });
                    }
                } catch (e) {
                    console.error('Failed to load profile:', e);
                }
            }
            
            async function awardXP(score, won) {
                try {
                    const res = await fetch('/api/profile/xp/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_name: state.userName,
                            score: score,
                            won: won,
                        })
                    });
                    const data = await res.json();
                    
                    showToast(`+${data.xp_awarded} XP earned!`, 'xp');
                    if (data.leveled_up) {
                        showToast(`🎉 Level Up! You're now Level ${data.level}!`, 'success');
                    }
                    
                    await loadUserProfile();
                } catch (e) {
                    console.error('Failed to award XP:', e);
                }
            }
            
            // ============================================
            // DAILY CHALLENGE
            // ============================================
            async function loadDailyChallenge() {
                try {
                    const res = await fetch(`/api/challenge/?user_name=${encodeURIComponent(state.userName)}`);
                    const data = await res.json();
                    
                    document.getElementById('challengeTopic').textContent = data.challenge.topic;
                    
                    if (data.completed) {
                        document.getElementById('challengeBanner').classList.add('completed');
                        document.getElementById('challengeBanner').querySelector('button').textContent = '✓ Completed';
                        document.getElementById('challengeBanner').querySelector('button').disabled = true;
                    }
                } catch (e) {
                    console.error('Failed to load daily challenge:', e);
                }
            }
            
            async function startDailyChallenge() {
                const res = await fetch(`/api/challenge/?user_name=${encodeURIComponent(state.userName)}`);
                const data = await res.json();
                document.getElementById('motion').value = data.challenge.topic;
                document.getElementById('difficulty').value = data.challenge.difficulty;
                showToast('Daily Challenge loaded! Complete it for +50 XP bonus.', 'success');
            }
            
            // ============================================
            // AI PERSONALITIES
            // ============================================
            async function loadPersonalities() {
                try {
                    const res = await fetch('/api/personalities/');
                    const data = await res.json();
                    
                    const grid = document.getElementById('personalityGrid');
                    grid.innerHTML = data.personalities.map(p => `
                        <div class="personality-card ${p.id === state.selectedPersonality ? 'selected' : ''}"
                             onclick="selectPersonality('${p.id}')">
                            <h4>${p.name}</h4>
                            <p>${p.description}</p>
                        </div>
                    `).join('');
                } catch (e) {
                    console.error('Failed to load personalities:', e);
                }
            }
            
            function selectPersonality(id) {
                state.selectedPersonality = id;
                document.querySelectorAll('.personality-card').forEach(c => c.classList.remove('selected'));
                event.target.closest('.personality-card').classList.add('selected');
            }
            
            // ============================================
            // DEBATE FLOW
            // ============================================
            async function startDebate() {
                state.userName = document.getElementById('userName').value || 'Anonymous';
                localStorage.setItem('debateUserName', state.userName);
                
                const motion = document.getElementById('motion').value;
                if (!motion.trim()) {
                    showToast('Please enter a debate topic', 'error');
                    return;
                }
                
                showLoading(true);
                
                try {
                    const res = await fetch('/api/debate/start/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            topic: motion,
                            user_name: state.userName,
                            difficulty: document.getElementById('difficulty').value,
                            personality: state.selectedPersonality,
                        })
                    });
                    
                    const data = await res.json();
                    if (data.error) throw new Error(data.error);
                    
                    state.sessionId = data.session_id;
                    state.currentRound = 1;
                    state.timerSeconds = parseInt(document.getElementById('speechTime').value) * 60;
                    
                    document.getElementById('setupForm').style.display = 'none';
                    document.getElementById('debateInterface').style.display = 'block';
                    
                    addToHistory('ai', data.ai_opening_position);
                    state.lastOpponentText = data.ai_opening_position;
                    
                    startTimer();
                    
                    if (document.getElementById('autoTTS').checked) {
                        speakText(data.ai_opening_position);
                    }
                    
                } catch (e) {
                    showToast('Error starting debate: ' + e.message, 'error');
                } finally {
                    showLoading(false);
                }
            }
            
            async function submitSpeech() {
                const speech = document.getElementById('userSpeech').value;
                if (!speech.trim()) {
                    showToast('Please enter your response', 'error');
                    return;
                }
                
                showLoading(true);
                pauseTimer();
                
                try {
                    const res = await fetch('/api/debate/response/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: state.sessionId,
                            response: speech,
                            personality: state.selectedPersonality,
                        })
                    });
                    
                    const data = await res.json();
                    if (data.error) throw new Error(data.error);
                    
                    addToHistory('user', speech);
                    addToHistory('ai', data.ai_counter_argument);
                    state.lastOpponentText = data.ai_counter_argument;
                    
                    document.getElementById('userSpeech').value = '';
                    document.getElementById('suggestionsPanel').style.display = 'none';
                    
                    state.currentRound = data.next_round;
                    document.getElementById('roundDisplay').textContent = state.currentRound;
                    document.getElementById('userScoreDisplay').textContent = Math.round(data.overall_score);
                    
                    // Show feedback toast
                    showToast(data.coach_feedback.substring(0, 100) + '...', 'success');
                    
                    if (document.getElementById('autoTTS').checked) {
                        speakText(data.ai_counter_argument);
                    }
                    
                    resetTimer();
                    startTimer();
                    
                } catch (e) {
                    showToast('Error: ' + e.message, 'error');
                } finally {
                    showLoading(false);
                }
            }
            
            async function endDebate() {
                if (!confirm('End this debate?')) return;
                
                showLoading(true);
                
                try {
                    const res = await fetch('/api/debate/end/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: state.sessionId })
                    });
                    
                    const data = await res.json();
                    
                    pauseTimer();
                    
                    const won = data.overall_score >= 60;
                    await awardXP(data.overall_score, won);
                    
                    showToast(`Debate ended! Final score: ${data.overall_score}`, won ? 'success' : 'error');
                    
                    // Reset UI
                    document.getElementById('setupForm').style.display = 'block';
                    document.getElementById('debateInterface').style.display = 'none';
                    document.getElementById('speechHistory').innerHTML = '<p style="text-align: center; color: #999;">Debate will appear here...</p>';
                    
                    state.sessionId = null;
                    
                    await loadUserProfile();
                    
                } catch (e) {
                    showToast('Error ending debate: ' + e.message, 'error');
                } finally {
                    showLoading(false);
                }
            }
            
            function addToHistory(role, content) {
                const history = document.getElementById('speechHistory');
                if (history.querySelector('p')) history.innerHTML = '';
                
                const item = document.createElement('div');
                item.className = `speech-item ${role}`;
                item.innerHTML = `
                    <div class="speech-meta">
                        <strong>${role === 'ai' ? '🤖 AI' : '👤 You'}</strong>
                        <span style="float: right;">Round ${state.currentRound}</span>
                    </div>
                    <div class="speech-content">${content}</div>
                `;
                history.appendChild(item);
                history.scrollTop = history.scrollHeight;
            }
            
            // ============================================
            // TIMER
            // ============================================
            function startTimer() {
                state.timerPaused = false;
                state.timerInterval = setInterval(() => {
                    if (!state.timerPaused && state.timerSeconds > 0) {
                        state.timerSeconds--;
                        updateTimerDisplay();
                        
                        // Warning at 1 minute
                        if (state.timerSeconds === 60 && document.getElementById('soundEffects').checked) {
                            playBell(1);
                            document.getElementById('timerDisplay').classList.add('warning');
                        }
                        // End
                        if (state.timerSeconds === 0 && document.getElementById('soundEffects').checked) {
                            playBell(2);
                        }
                    }
                }, 1000);
            }
            
            function pauseTimer() {
                state.timerPaused = true;
            }
            
            function resetTimer() {
                state.timerSeconds = parseInt(document.getElementById('speechTime').value) * 60;
                document.getElementById('timerDisplay').classList.remove('warning');
                updateTimerDisplay();
            }
            
            function updateTimerDisplay() {
                const mins = Math.floor(state.timerSeconds / 60);
                const secs = state.timerSeconds % 60;
                document.getElementById('timerTime').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            }
            
            function playBell(count) {
                // Simple bell sound using Web Audio API
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                for (let i = 0; i < count; i++) {
                    setTimeout(() => {
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.frequency.value = 800;
                        osc.type = 'sine';
                        gain.gain.setValueAtTime(0.3, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                        osc.start(ctx.currentTime);
                        osc.stop(ctx.currentTime + 0.5);
                    }, i * 600);
                }
            }
            
            // ============================================
            // TEXT-TO-SPEECH
            // ============================================
            function loadVoices() {
                const voices = state.synthesis.getVoices();
                const select = document.getElementById('ttsVoice');
                select.innerHTML = voices.map((v, i) => 
                    `<option value="${i}">${v.name} (${v.lang})</option>`
                ).join('');
            }
            
            if (speechSynthesis.onvoiceschanged !== undefined) {
                speechSynthesis.onvoiceschanged = loadVoices;
            }
            
            function speakText(text) {
                if (state.isSpeaking) {
                    state.synthesis.cancel();
                }
                
                const utterance = new SpeechSynthesisUtterance(text);
                const voices = state.synthesis.getVoices();
                const voiceIndex = document.getElementById('ttsVoice').value;
                if (voices[voiceIndex]) utterance.voice = voices[voiceIndex];
                utterance.rate = parseFloat(document.getElementById('ttsRate').value);
                
                utterance.onstart = () => {
                    state.isSpeaking = true;
                    document.getElementById('voiceIndicator').classList.add('speaking');
                };
                utterance.onend = () => {
                    state.isSpeaking = false;
                    document.getElementById('voiceIndicator').classList.remove('speaking');
                };
                
                state.synthesis.speak(utterance);
            }
            
            function toggleTextToSpeech() {
                if (state.isSpeaking) {
                    state.synthesis.cancel();
                    state.isSpeaking = false;
                    document.getElementById('voiceIndicator').classList.remove('speaking');
                } else {
                    speakText(state.lastOpponentText);
                }
            }
            
            document.getElementById('ttsRate').addEventListener('input', (e) => {
                document.getElementById('ttsRateValue').textContent = e.target.value + 'x';
            });
            
            // ============================================
            // SPEECH-TO-TEXT
            // ============================================
            function initSpeechRecognition() {
                if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                    document.getElementById('sttBtn').disabled = true;
                    document.getElementById('sttBtn').title = 'Speech recognition not supported';
                    return;
                }
                
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                state.recognition = new SpeechRecognition();
                state.recognition.continuous = true;
                state.recognition.interimResults = true;
                
                state.recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    document.getElementById('userSpeech').value = transcript;
                };
                
                state.recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    stopListening();
                };
                
                state.recognition.onend = () => {
                    if (state.isListening) {
                        state.recognition.start(); // Restart if still listening
                    }
                };
            }
            
            function toggleSpeechToText() {
                if (state.isListening) {
                    stopListening();
                } else {
                    startListening();
                }
            }
            
            function startListening() {
                if (!state.recognition) return;
                state.isListening = true;
                state.recognition.start();
                document.getElementById('voiceIndicator').classList.add('listening');
                document.getElementById('sttBtn').textContent = '⏹️ Stop';
            }
            
            function stopListening() {
                if (!state.recognition) return;
                state.isListening = false;
                state.recognition.stop();
                document.getElementById('voiceIndicator').classList.remove('listening');
                document.getElementById('sttBtn').textContent = '🎤 Speak';
            }
            
            // ============================================
            // REAL-TIME SUGGESTIONS
            // ============================================
            let suggestionTimeout = null;
            
            function handleTyping() {
                if (!document.getElementById('autoSuggestions').checked) return;
                
                clearTimeout(suggestionTimeout);
                suggestionTimeout = setTimeout(async () => {
                    const text = document.getElementById('userSpeech').value;
                    if (text.length < 20) {
                        document.getElementById('suggestionsPanel').style.display = 'none';
                        return;
                    }
                    
                    try {
                        const res = await fetch('/api/suggestions/', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                opponent_argument: state.lastOpponentText,
                                topic: document.getElementById('motion').value,
                            })
                        });
                        const data = await res.json();
                        
                        if (data.suggestions && data.suggestions.length > 0) {
                            document.getElementById('suggestionsPanel').style.display = 'block';
                            document.getElementById('suggestionsList').innerHTML = data.suggestions.map(s =>
                                `<div class="suggestion-item" onclick="useSuggestion('${s.replace(/'/g, "\\'")}')">💡 ${s}</div>`
                            ).join('');
                        }
                    } catch (e) {
                        console.error('Failed to get suggestions:', e);
                    }
                }, 1500); // Debounce 1.5s
            }
            
            function useSuggestion(suggestion) {
                const textarea = document.getElementById('userSpeech');
                textarea.value += ' ' + suggestion;
                document.getElementById('suggestionsPanel').style.display = 'none';
            }
            
            // ============================================
            // ANALYTICS
            // ============================================
            async function loadAnalytics() {
                try {
                    // Load profile stats
                    const profileRes = await fetch(`/api/profile/?user_name=${encodeURIComponent(state.userName)}`);
                    const profile = await profileRes.json();
                    
                    document.getElementById('totalDebates').textContent = profile.total_debates;
                    document.getElementById('avgScore').textContent = profile.average_score;
                    document.getElementById('winRate').textContent = profile.win_rate + '%';
                    document.getElementById('bestScore').textContent = profile.highest_score;
                    
                    // Load badges
                    renderBadges(profile.badges);
                    
                    // Load skill radar
                    const skillRes = await fetch(`/api/analytics/skills/?user_name=${encodeURIComponent(state.userName)}`);
                    const skillData = await skillRes.json();
                    renderSkillRadar(skillData.skills);
                    
                    // Load analytics
                    const analyticsRes = await fetch(`/api/analytics/?user_name=${encodeURIComponent(state.userName)}`);
                    const analytics = await analyticsRes.json();
                    
                    if (analytics.has_data) {
                        renderScoreHistory(analytics.score_history);
                        renderFallacyChart(analytics.fallacy_counts);
                    }
                    
                } catch (e) {
                    console.error('Failed to load analytics:', e);
                }
            }
            
            function renderSkillRadar(skills) {
                const ctx = document.getElementById('skillRadar').getContext('2d');
                new Chart(ctx, {
                    type: 'radar',
                    data: {
                        labels: ['Logic', 'Evidence', 'Clarity', 'Persuasion', 'Counter-Arguments'],
                        datasets: [{
                            label: 'Your Skills',
                            data: [skills.logic, skills.evidence, skills.clarity, skills.persuasion, skills.counter_arguments],
                            backgroundColor: 'rgba(102, 126, 234, 0.2)',
                            borderColor: 'rgba(102, 126, 234, 1)',
                            pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                        }]
                    },
                    options: {
                        scales: {
                            r: { beginAtZero: true, max: 100 }
                        }
                    }
                });
            }
            
            function renderScoreHistory(history) {
                const ctx = document.getElementById('scoreHistory').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: history.map(h => h.date.split('T')[0]),
                        datasets: [{
                            label: 'Score',
                            data: history.map(h => h.score),
                            borderColor: 'rgba(102, 126, 234, 1)',
                            tension: 0.3,
                            fill: true,
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        }]
                    },
                    options: {
                        scales: { y: { beginAtZero: true, max: 100 } }
                    }
                });
            }
            
            function renderFallacyChart(fallacies) {
                const ctx = document.getElementById('fallacyChart').getContext('2d');
                const labels = Object.keys(fallacies);
                const data = Object.values(fallacies);
                
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels.map(l => l.replace(/_/g, ' ')),
                        datasets: [{
                            label: 'Times Detected',
                            data: data,
                            backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        scales: { x: { beginAtZero: true } }
                    }
                });
            }
            
            function renderBadges(userBadges) {
                const ALL_BADGES = {
                    first_debate: { name: 'First Steps', icon: '👣' },
                    '10_debates': { name: 'Debater', icon: '🎯' },
                    '50_debates': { name: 'Veteran', icon: '⭐' },
                    first_win: { name: 'Victor', icon: '🏆' },
                    '10_wins': { name: 'Champion', icon: '👑' },
                    perfect_score: { name: 'Perfectionist', icon: '💯' },
                    streak_3: { name: 'On Fire', icon: '🔥' },
                    streak_7: { name: 'Unstoppable', icon: '⚡' },
                    level_5: { name: 'Rising Star', icon: '🌟' },
                    level_10: { name: 'Master Debater', icon: '🎓' },
                };
                
                const grid = document.getElementById('badgesGrid');
                grid.innerHTML = Object.entries(ALL_BADGES).map(([id, badge]) => {
                    const earned = userBadges.includes(id);
                    return `<div class="badge ${earned ? '' : 'locked'}">${badge.icon} ${badge.name}</div>`;
                }).join('');
            }
            
            // ============================================
            // LEADERBOARD
            // ============================================
            async function loadLeaderboard(timeframe) {
                try {
                    const res = await fetch(`/api/leaderboard/?timeframe=${timeframe}&limit=20`);
                    const data = await res.json();
                    
                    const tbody = document.getElementById('leaderboardBody');
                    tbody.innerHTML = data.leaderboard.map((entry, i) => `
                        <tr class="${i < 3 ? 'rank-' + (i + 1) : ''}">
                            <td>${entry.rank}</td>
                            <td>${entry.user_name}</td>
                            <td>Lv.${entry.level}</td>
                            <td>${entry.xp}</td>
                            <td>${entry.win_rate}%</td>
                            <td>🔥 ${entry.current_streak}</td>
                        </tr>
                    `).join('');
                    
                    // Load user rank
                    const rankRes = await fetch(`/api/leaderboard/rank/?user_name=${encodeURIComponent(state.userName)}`);
                    const rankData = await rankRes.json();
                    
                    if (!rankData.error) {
                        document.getElementById('rankDisplay').textContent = '#' + rankData.rank;
                        document.getElementById('percentileDisplay').textContent = rankData.percentile + '%';
                    }
                    
                } catch (e) {
                    console.error('Failed to load leaderboard:', e);
                }
            }
            
            // ============================================
            // SESSION REPLAY
            // ============================================
            async function loadSessionList() {
                try {
                    const res = await fetch(`/api/sessions/?user_name=${encodeURIComponent(state.userName)}&limit=20`);
                    const data = await res.json();
                    
                    const select = document.getElementById('replaySelect');
                    select.innerHTML = '<option value="">-- Select Session --</option>' +
                        data.sessions.map(s => 
                            `<option value="${s.session_id}">${s.topic.substring(0, 30)} - Score: ${s.score} (${s.date.split('T')[0]})</option>`
                        ).join('');
                } catch (e) {
                    console.error('Failed to load sessions:', e);
                }
            }
            
            async function loadReplay() {
                const sessionId = document.getElementById('replaySelect').value;
                if (!sessionId) {
                    document.getElementById('replayViewer').style.display = 'none';
                    return;
                }
                
                try {
                    const res = await fetch(`/api/sessions/replay/?session_id=${sessionId}`);
                    state.replayData = await res.json();
                    state.replayIndex = 0;
                    
                    document.getElementById('replayViewer').style.display = 'block';
                    document.getElementById('replayTopic').textContent = state.replayData.topic;
                    document.getElementById('replayScore').textContent = state.replayData.overall_score;
                    
                    renderReplayStep();
                } catch (e) {
                    console.error('Failed to load replay:', e);
                }
            }
            
            function renderReplayStep() {
                if (!state.replayData) return;
                
                const history = document.getElementById('replayHistory');
                history.innerHTML = '';
                
                const conversation = state.replayData.conversation;
                for (let i = 0; i <= state.replayIndex && i < conversation.length; i++) {
                    const msg = conversation[i];
                    const item = document.createElement('div');
                    item.className = `speech-item ${msg.role}`;
                    item.innerHTML = `
                        <div class="speech-meta"><strong>${msg.role === 'ai' ? '🤖 AI' : '👤 You'}</strong></div>
                        <div class="speech-content">${msg.content}</div>
                    `;
                    history.appendChild(item);
                }
                
                document.getElementById('replayStep').textContent = `${state.replayIndex + 1}/${conversation.length}`;
                document.getElementById('replayProgress').style.width = `${((state.replayIndex + 1) / conversation.length) * 100}%`;
            }
            
            function replayPrev() {
                if (state.replayIndex > 0) {
                    state.replayIndex--;
                    renderReplayStep();
                }
            }
            
            function replayNext() {
                if (state.replayData && state.replayIndex < state.replayData.conversation.length - 1) {
                    state.replayIndex++;
                    renderReplayStep();
                }
            }
            
            let replayInterval = null;
            function replayPlay() {
                if (replayInterval) {
                    clearInterval(replayInterval);
                    replayInterval = null;
                    return;
                }
                
                replayInterval = setInterval(() => {
                    if (state.replayData && state.replayIndex < state.replayData.conversation.length - 1) {
                        state.replayIndex++;
                        renderReplayStep();
                    } else {
                        clearInterval(replayInterval);
                        replayInterval = null;
                    }
                }, 2000);
            }
            
            // ============================================
            // UTILITIES
            // ============================================
            function showLoading(show) {
                document.getElementById('loadingOverlay').style.display = show ? 'block' : 'none';
            }
            
            function showToast(message, type = '') {
                const container = document.getElementById('toastContainer');
                const toast = document.createElement('div');
                toast.className = `toast ${type}`;
                toast.textContent = message;
                container.appendChild(toast);
                
                setTimeout(() => toast.remove(), 4000);
            }
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)
