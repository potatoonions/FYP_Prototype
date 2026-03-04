from django.urls import path

from .views import (
    start_debate,
    submit_user_response,
    end_debate,
    get_debate_history,
)
from .formal_debate_api import (
    create_formal_debate,
    start_formal_debate,
    submit_formal_speech,
    get_formal_debate_status,
)
from .formal_debate_ui import formal_debate_view as formal_debate_basic
from .formal_debate_ui_enhanced import formal_debate_view as formal_debate_enhanced
from .gamification_api import (
    get_user_profile,
    award_xp,
    get_daily_challenge,
    complete_daily_challenge,
    get_leaderboard,
    get_user_rank,
    get_user_analytics,
    get_skill_radar,
    get_session_list,
    get_session_replay,
    get_ai_personalities,
    get_rebuttal_suggestions,
)

urlpatterns = [
    # Multi-turn debate flow - Core API
    path("debate/start/", start_debate, name="start_debate"),
    path("debate/response/", submit_user_response, name="submit_response"),
    path("debate/end/", end_debate, name="end_debate"),
    path("debate/history/", get_debate_history, name="debate_history"),
    
    # Formal debate competition interface (enhanced is default)
    path("formal/", formal_debate_enhanced, name="formal_debate"),
    path("formal/basic/", formal_debate_basic, name="formal_debate_basic"),
    path("formal/create/", create_formal_debate, name="create_formal_debate"),
    path("formal/start/", start_formal_debate, name="start_formal_debate"),
    path("formal/speech/", submit_formal_speech, name="submit_formal_speech"),
    path("formal/status/", get_formal_debate_status, name="get_formal_debate_status"),
    
    # Gamification
    path("profile/", get_user_profile, name="user_profile"),
    path("profile/xp/", award_xp, name="award_xp"),
    path("challenge/", get_daily_challenge, name="daily_challenge"),
    path("challenge/complete/", complete_daily_challenge, name="complete_challenge"),
    
    # Leaderboard
    path("leaderboard/", get_leaderboard, name="leaderboard"),
    path("leaderboard/rank/", get_user_rank, name="user_rank"),
    
    # Analytics
    path("analytics/", get_user_analytics, name="user_analytics"),
    path("analytics/skills/", get_skill_radar, name="skill_radar"),
    
    # Session replay
    path("sessions/", get_session_list, name="session_list"),
    path("sessions/replay/", get_session_replay, name="session_replay"),
    
    # AI Personalities
    path("personalities/", get_ai_personalities, name="ai_personalities"),
    
    # Real-time suggestions
    path("suggestions/", get_rebuttal_suggestions, name="rebuttal_suggestions"),
]