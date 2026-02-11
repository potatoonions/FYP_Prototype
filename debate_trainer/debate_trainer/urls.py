"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from trainer.views import home_view
from trainer.debate_chat import debate_chat_view

urlpatterns = [
    path("", debate_chat_view, name="home"),  # Direct to debate trainer
    path("api-docs/", home_view, name="api-docs"),  # API documentation
    path("admin/", admin.site.urls),
    path("api/", include("trainer.urls")),
]

