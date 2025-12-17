"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from trainer.views import debate_form_view, home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("debate/", debate_form_view, name="debate-form"),
    path("admin/", admin.site.urls),
    path("api/", include("trainer.urls")),
]

