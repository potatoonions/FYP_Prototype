"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from trainer.views import home_view
from trainer.debate_chat import debate_chat_view
from trainer.formal_debate_ui_enhanced import formal_debate_view

urlpatterns = [
    path("", formal_debate_view, name="home"),  # Enhanced debate trainer
    path("chat/", debate_chat_view, name="chat"),  # Old chat view
    path("api-docs/", home_view, name="api-docs"),  # API documentation
    path("admin/", admin.site.urls),
    path("api/", include("trainer.urls")),
]

