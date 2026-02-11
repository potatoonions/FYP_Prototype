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
from .formal_debate_ui import formal_debate_view

urlpatterns = [
    # Multi-turn debate flow - Core API
    path("debate/start/", start_debate, name="start_debate"),
    path("debate/response/", submit_user_response, name="submit_response"),
    path("debate/end/", end_debate, name="end_debate"),
    path("debate/history/", get_debate_history, name="debate_history"),
    
    # Formal debate competition interface
    path("formal/", formal_debate_view, name="formal_debate"),
    path("formal/create/", create_formal_debate, name="create_formal_debate"),
    path("formal/start/", start_formal_debate, name="start_formal_debate"),
    path("formal/speech/", submit_formal_speech, name="submit_formal_speech"),
    path("formal/status/", get_formal_debate_status, name="get_formal_debate_status"),
]