"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from trainer.views import home_view, debate_chat_view, formal_debate_enhanced_view

urlpatterns = [
    path("", formal_debate_enhanced_view, name="home"),
    path("debate/", debate_chat_view, name="chat"),
    path("api-docs/", home_view, name="api-docs"),
    path("admin/", admin.site.urls),
    path("api/", include("trainer.urls")),
]

