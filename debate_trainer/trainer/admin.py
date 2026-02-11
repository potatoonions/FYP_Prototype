"""Admin configuration for debate trainer models."""
from django.contrib import admin

from .models import DebateRound, DebateSession


@admin.register(DebateSession)
class DebateSessionAdmin(admin.ModelAdmin):
    """Admin interface for DebateSession model."""
    
    list_display = ["id", "user_name", "topic", "score", "created_at"]
    list_filter = ["created_at", "score"]
    search_fields = ["user_name", "topic", "user_argument"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]


@admin.register(DebateRound)
class DebateRoundAdmin(admin.ModelAdmin):
    """Admin interface for DebateRound model."""
    
    list_display = [
        "session_id",
        "user_name",
        "topic",
        "current_round",
        "overall_score",
        "difficulty",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "difficulty",
        "round_type",
        "created_at",
    ]
    search_fields = ["session_id", "user_name", "topic"]
    readonly_fields = ["session_id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    
    fieldsets = (
        ("Session Info", {
            "fields": ("session_id", "user_name", "topic", "difficulty")
        }),
        ("Debate State", {
            "fields": ("current_round", "round_type", "is_active")
        }),
        ("Content", {
            "fields": ("ai_position", "research_summary", "conversation")
        }),
        ("Scoring", {
            "fields": ("scores", "ai_feedbacks", "overall_score")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

