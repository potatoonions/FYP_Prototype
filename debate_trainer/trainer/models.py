from django.db import models


class DebateSession(models.Model):
    """Simple session log to support skill tracking."""

    user_name = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    user_argument = models.TextField()
    ai_feedback = models.JSONField(default=dict)
    score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - convenience
        return f"{self.user_name} on {self.topic} @ {self.created_at:%Y-%m-%d}"


class DebateRound(models.Model):
    """Tracks multi-turn debate rounds with research context."""
    
    ROUND_CHOICES = [
        ("ai_opening", "AI Opening Position"),
        ("user_response", "User Response"),
        ("ai_counter", "AI Counter Argument"),
    ]
    
    session_id = models.CharField(max_length=100, unique=True)  # Unique identifier for debate session
    user_name = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    ai_position = models.TextField()  # AI's initial position
    research_summary = models.JSONField(default=dict)  # Summary of Google Scholar research
    
    # Round tracking
    current_round = models.IntegerField(default=1)
    round_type = models.CharField(max_length=20, choices=ROUND_CHOICES, default="ai_opening")
    
    # Conversation history
    conversation = models.JSONField(default=list)  # List of {role: "ai"/"user", content: text, round: int}
    
    # Scoring and feedback
    ai_feedbacks = models.JSONField(default=dict)  # {round_number: feedback}
    scores = models.JSONField(default=dict)  # {round_number: score}
    overall_score = models.FloatField(default=0.0)
    
    difficulty = models.CharField(max_length=20, default="medium")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_name} - {self.topic} (Round {self.current_round})"
