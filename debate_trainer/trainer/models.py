from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json


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
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user_name", "-created_at"]),
        ]

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
        indexes = [
            models.Index(fields=["session_id"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user_name", "-created_at"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]
    
    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user_name} - {self.topic} (Round {self.current_round})"


class FormalDebateConfig(models.Model):
    """Configuration for formal debate competitions."""
    
    FORMAT_CHOICES = [
        ("custom", "Custom"),
        ("parliamentary", "Parliamentary (4v4)"),
        ("public_forum", "Public Forum (2v2)"),
        ("world_schools", "World Schools (3v3)"),
    ]
    
    # Basic config
    format_type = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="custom")
    motion = models.TextField()  # Debate topic/motion
    is_affirmative = models.BooleanField(default=True)  # Is user taking affirmative side?
    
    # Speaker configuration
    speakers_per_side = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    # Timing configuration (in seconds)
    substantive_speech_time = models.IntegerField(
        default=480,  # 8 minutes default
        validators=[MinValueValidator(60), MaxValueValidator(3600)],
        help_text="Duration of substantive speeches in seconds"
    )
    reply_speech_time = models.IntegerField(
        default=240,  # 4 minutes default
        validators=[MinValueValidator(30), MaxValueValidator(1200)],
        help_text="Duration of reply speeches in seconds"
    )
    protected_time = models.IntegerField(
        default=60,  # 1st minute protected
        validators=[MinValueValidator(30), MaxValueValidator(600)],
        help_text="Protected time at start (no POI) in seconds"
    )
    
    # Debate structure
    include_replies = models.BooleanField(default=True)
    allow_poi = models.BooleanField(default=True, help_text="Allow Points of Information")
    poi_duration = models.IntegerField(
        default=15,  # 15 seconds per POI
        validators=[MinValueValidator(5), MaxValueValidator(60)],
        help_text="Duration of each POI in seconds"
    )
    max_pois_per_speech = models.IntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    
    # Rules
    no_new_arguments_in_rebuttal = models.BooleanField(default=True)
    require_definitions = models.BooleanField(default=False)
    require_respect = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self) -> str:
        return f"{self.motion[:50]} ({self.get_format_type_display()})"
    
    def get_speech_order(self) -> list:
        """Generate the order of speeches for the debate."""
        order = []
        for round_num in range(1, self.speakers_per_side + 1):
            # Affirmative speaker
            order.append({
                "round": round_num,
                "side": "affirmative",
                "speaker": round_num,
                "type": "substantive",
                "duration": self.substantive_speech_time
            })
            # Negative speaker
            order.append({
                "round": round_num,
                "side": "negative",
                "speaker": round_num,
                "type": "substantive",
                "duration": self.substantive_speech_time
            })
        
        # Add reply speeches if enabled
        if self.include_replies:
            order.append({
                "round": self.speakers_per_side + 1,
                "side": "negative",
                "speaker": 1,
                "type": "reply",
                "duration": self.reply_speech_time
            })
            order.append({
                "round": self.speakers_per_side + 1,
                "side": "affirmative",
                "speaker": 1,
                "type": "reply",
                "duration": self.reply_speech_time
            })
        
        return order
    
    def validate_new_arguments(self, speech_type: str, speech_text: str) -> dict:
        """Validate if rebuttal contains new arguments (when rule is enabled)."""
        if not self.no_new_arguments_in_rebuttal or speech_type != "reply":
            return {"valid": True, "issues": []}
        
        # Simple heuristic: check if speech introduces new topics/claims
        new_arg_indicators = ["furthermore", "additionally", "in addition", "also", "another point"]
        has_new_args = any(indicator in speech_text.lower() for indicator in new_arg_indicators)
        
        return {
            "valid": not has_new_args,
            "issues": ["Rebuttal contains potential new arguments"] if has_new_args else []
        }


class FormalDebateSession(models.Model):
    """Tracks a formal debate competition."""
    
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("paused", "Paused"),
    ]
    
    config = models.ForeignKey(FormalDebateConfig, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    
    # Participants
    user_name = models.CharField(max_length=100)
    user_side = models.CharField(max_length=20, choices=[("affirmative", "Affirmative"), ("negative", "Negative")])
    ai_side = models.CharField(max_length=20, choices=[("affirmative", "Affirmative"), ("negative", "Negative")])
    
    # Progress tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")
    current_speaker_index = models.IntegerField(default=0)  # Index in speech order
    current_speech_time_elapsed = models.IntegerField(default=0)  # Seconds elapsed in current speech
    
    # Speech history
    speeches = models.JSONField(default=list)
    """
    [
        {
            "speaker": "user|ai",
            "side": "affirmative|negative",
            "type": "substantive|reply",
            "content": "speech text",
            "time_taken": seconds,
            "pois_received": [],
            "timestamp": ISO datetime
        },
        ...
    ]
    """
    
    # Points of information
    pois_given = models.JSONField(default=list)  # POIs given by user
    pois_received = models.JSONField(default=list)  # POIs received by user
    
    # Scoring
    user_score = models.FloatField(default=0.0)
    ai_score = models.FloatField(default=0.0)
    feedback = models.JSONField(default=dict)  # {speaker_side: "feedback text"}
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session_id"]),
            models.Index(fields=["user_name", "-created_at"]),
            models.Index(fields=["status"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.user_name} vs AI - {self.config.motion[:30]}"
    
    def get_current_speech(self) -> dict:
        """Get the current speech details."""
        order = self.config.get_speech_order()
        if self.current_speaker_index < len(order):
            return order[self.current_speaker_index]
        return None
    
    def get_next_speaker(self) -> str:
        """Get whose turn it is (user or ai)."""
        current = self.get_current_speech()
        if not current:
            return None
        speaker_side = current["side"]
        return "user" if speaker_side == self.user_side else "ai"
    
    def advance_to_next_speech(self):
        """Move to next speech in sequence."""
        self.current_speaker_index += 1
        self.current_speech_time_elapsed = 0
