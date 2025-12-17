from django.urls import path

from .views import debate_view, session_history

urlpatterns = [
    path("debate/", debate_view, name="debate"),
    path("sessions/", session_history, name="sessions"),
]

