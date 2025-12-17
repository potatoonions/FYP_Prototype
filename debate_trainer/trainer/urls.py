from django.urls import path

from .views import (
    debate_view, 
    session_history,
    start_debate,
    submit_user_response,
    end_debate,
    get_debate_history,
    debate_chat_view,
)

urlpatterns = [
    # Legacy endpoints
    path("debate/", debate_view, name="debate"),
    path("sessions/", session_history, name="sessions"),
    
    # Multi-turn debate flow endpoints
    path("debate/start/", start_debate, name="start_debate"),
    path("debate/response/", submit_user_response, name="submit_response"),
    path("debate/end/", end_debate, name="end_debate"),
    path("debate/history/", get_debate_history, name="debate_history"),
    
    # Interactive debate UI
    path("debate/chat/", debate_chat_view, name="debate_chat"),
]
