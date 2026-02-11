"""
Formal debate flow engine with timing, speaker management, and POI handling.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger("trainer.services.debate_flow")


@dataclass
class TimeSignal:
    """Time signal (bell) notification."""
    time_seconds: int
    signal_type: str  # "protected_end" | "speech_end"
    bell_count: int  # 1 for protected end, 2 for speech end


@dataclass
class POIRequest:
    """Point of Information request."""
    from_speaker: str  # "user" | "ai"
    timestamp: datetime
    question: str
    accepted: Optional[bool] = None
    response: Optional[str] = None


class DebateFlowEngine:
    """Manages formal debate flow, timing, and rules."""
    
    def __init__(self, config):
        """Initialize debate flow engine with configuration."""
        self.config = config
        self.speech_order = config.get_speech_order()
        self.current_speech_index = 0
        self.current_speaker = None
        self.speech_start_time = None
        self.time_warnings_given = set()
    
    def get_current_speech_info(self) -> Dict:
        """Get information about current speech."""
        if self.current_speech_index >= len(self.speech_order):
            return None
        return self.speech_order[self.current_speech_index]
    
    def get_next_speaker(self, user_side: str) -> str:
        """Get whose turn it is (user or ai)."""
        current = self.get_current_speech_info()
        if not current:
            return None
        speaker_side = current["side"]
        return "user" if speaker_side == user_side else "ai"
    
    def get_time_signals(self, elapsed_seconds: int) -> List[TimeSignal]:
        """Get time signals for elapsed time in current speech."""
        current = self.get_current_speech_info()
        if not current:
            return []
        
        signals = []
        protected_end = self.config.protected_time
        total_time = current["duration"]
        
        # Signal at end of protected time (once)
        if elapsed_seconds == protected_end and protected_end not in self.time_warnings_given:
            signals.append(TimeSignal(
                time_seconds=elapsed_seconds,
                signal_type="protected_end",
                bell_count=1
            ))
            self.time_warnings_given.add(protected_end)
        
        # Signal at end of speech (twice)
        if elapsed_seconds == total_time and total_time not in self.time_warnings_given:
            signals.append(TimeSignal(
                time_seconds=elapsed_seconds,
                signal_type="speech_end",
                bell_count=2
            ))
            self.time_warnings_given.add(total_time)
        
        return signals
    
    def can_accept_poi(self, elapsed_seconds: int) -> bool:
        """Check if POI can be accepted at current time."""
        current = self.get_current_speech_info()
        if not current:
            return False
        
        # POI not allowed if AI disabled it
        if not self.config.allow_poi:
            return False
        
        # POI not allowed in protected time (first minute)
        if elapsed_seconds < self.config.protected_time:
            return False
        
        # POI not allowed in last minute
        remaining_time = current["duration"] - elapsed_seconds
        if remaining_time < 60:
            return False
        
        return True
    
    def advance_speech(self):
        """Move to next speech in the debate."""
        self.current_speech_index += 1
        self.time_warnings_given.clear()
    
    def get_remaining_time(self, elapsed_seconds: int) -> int:
        """Get remaining time in current speech."""
        current = self.get_current_speech_info()
        if not current:
            return 0
        return max(0, current["duration"] - elapsed_seconds)
    
    def get_debate_progress(self) -> Dict:
        """Get overall debate progress."""
        total_speeches = len(self.speech_order)
        current = self.current_speech_index + 1  # 1-indexed
        percent = (current / total_speeches) * 100 if total_speeches > 0 else 0
        
        return {
            "current_speech": current,
            "total_speeches": total_speeches,
            "progress_percent": round(percent, 1),
            "is_complete": self.current_speech_index >= total_speeches
        }
    
    def validate_new_arguments(self, speech_type: str, speech_content: str) -> Dict:
        """
        Validate that new arguments aren't introduced in rebuttal.
        Returns dict with 'valid': bool, 'issues': [list of issues]
        """
        if not self.config.no_new_arguments_in_rebuttal:
            return {"valid": True, "issues": []}
        
        if speech_type != "reply":
            return {"valid": True, "issues": []}
        
        # Simple heuristic: look for markers of new arguments
        # In a real system, this would use NLP
        issues = []
        new_arg_markers = [
            "furthermore, i propose",
            "my new position",
            "i also think that",
            "another reason is",
        ]
        
        lower_content = speech_content.lower()
        for marker in new_arg_markers:
            if marker in lower_content:
                issues.append(f"Possible new argument detected: '{marker}'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }


class SpeechAnalyzer:
    """Analyzes speeches for formal debate requirements."""
    
    @staticmethod
    def analyze_formality(speech_text: str) -> Dict:
        """Analyze speech for formal debate language."""
        analysis = {
            "formality_score": 0.0,
            "issues": [],
            "strengths": []
        }
        
        # Check for formal greeting
        if any(greeting in speech_text.lower() for greeting in ["honorable", "mr.", "madam", "chair"]):
            analysis["strengths"].append("Uses formal greeting/address")
        else:
            analysis["issues"].append("Missing formal address")
        
        # Check for logical structure
        structure_markers = ["firstly", "secondly", "finally", "therefore", "thus", "in conclusion"]
        marker_count = sum(1 for marker in structure_markers if marker in speech_text.lower())
        if marker_count >= 2:
            analysis["strengths"].append("Logical structure with clear transitions")
        else:
            analysis["issues"].append("Weak logical structure")
        
        # Check for evidence citations
        if any(marker in speech_text for marker in ["according to", "data shows", "research indicates", "statistics"]):
            analysis["strengths"].append("Cites evidence/research")
        else:
            analysis["issues"].append("No evidence cited")
        
        # Calculate formality score
        score = len(analysis["strengths"]) * 0.33 - len(analysis["issues"]) * 0.2
        analysis["formality_score"] = max(0, min(100, score * 25))
        
        return analysis
    
    @staticmethod
    def check_rebuttal_focus(current_speech: str, previous_opponent_speech: str) -> Dict:
        """Check if rebuttal focuses on opponent's arguments."""
        # Extract key terms from previous speech
        opponent_keywords = set()
        words = previous_opponent_speech.lower().split()
        for word in words:
            if len(word) > 5:  # Focus on significant words
                opponent_keywords.add(word)
        
        # Check if current speech addresses opponent's points
        current_lower = current_speech.lower()
        current_words = current_lower.split()
        
        addressed_keywords = sum(1 for word in current_words if word in opponent_keywords)
        total_keywords = len(opponent_keywords)
        
        focus_percentage = (addressed_keywords / total_keywords * 100) if total_keywords > 0 else 0
        
        return {
            "rebuttal_focus": focus_percentage,
            "addressed_keywords": addressed_keywords,
            "total_opponent_keywords": total_keywords,
            "adequately_rebuts": focus_percentage > 30
        }
