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

