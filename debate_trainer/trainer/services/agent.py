"""
Agentic orchestration for generating counterarguments and feedback.
Supports multiple LLM providers: OpenAI, Google Gemini, and more.
Falls back to heuristic responses if no API is available.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

try:
    from openai import OpenAI, APITimeoutError as OpenAITimeoutError, APIError as OpenAIError
except ImportError:  # pragma: no cover
    OpenAI = None
    OpenAITimeoutError = Exception
    OpenAIError = Exception

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

logger = logging.getLogger("trainer.services.agent")

# Base API error class
class APIError(Exception):
    """Base exception for API errors"""
    pass

class APITimeoutError(APIError):
    """API timeout exception"""
    pass


# AI Personality Modes
AI_PERSONALITIES = {
    "balanced": {
        "name": "Balanced",
        "description": "Fair and measured debate style",
        "style": "You are a balanced, fair debater. Use measured language, acknowledge valid points from the opposition, and present logical arguments without aggression.",
    },
    "aggressive": {
        "name": "Aggressive",
        "description": "Sharp, direct attacks on weak points",
        "style": "You are an aggressive debater. Be sharp, direct, and relentless in attacking weak points. Use strong language and rhetorical questions. Challenge every assumption.",
    },
    "diplomatic": {
        "name": "Diplomatic",
        "description": "Polite and respectful, seeks common ground",
        "style": "You are a diplomatic debater. Be polite and respectful, acknowledge the opponent's perspective, seek common ground while firmly presenting your case. Use phrases like 'I understand your point, however...'",
    },
    "academic": {
        "name": "Academic",
        "description": "Evidence-focused, cites studies and data",
        "style": "You are an academic debater. Focus heavily on evidence, cite studies and statistics (hypothetical if needed), use formal language, and structure arguments with clear premises and conclusions.",
    },
    "socratic": {
        "name": "Socratic",
        "description": "Questions everything, leads with inquiry",
        "style": "You are a Socratic debater. Lead with probing questions, challenge assumptions through inquiry, make the opponent justify their reasoning. Ask 'why' and 'how do you know' frequently.",
    },
}


class AgenticDebateAgent:
    """Multi-provider LLM agent for debate training."""
    
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        provider: str = "openai", 
        trace: bool = False
    ) -> None:
        """Initialize debate agent with specified provider."""
        self.model = model
        self.api_key = api_key
        self.provider = provider
        self.trace = trace
        self.client = None
        
        if api_key in {"", "set-me"}:
            logger.debug(f"API key not set for {provider}")
            return
            
        if provider == "openai" and OpenAI:
            self.client = OpenAI(api_key=api_key)
            logger.debug("OpenAI client initialized")
        elif provider == "google" and genai:
            genai.configure(api_key=api_key)
            self.client = genai  # Store module reference
            logger.debug("Google Gemini client initialized")
        elif provider == "groq" and Groq:
            self.client = Groq(api_key=api_key)
            logger.debug("Groq client initialized")
        else:
            logger.debug(f"Provider '{provider}' not available or unsupported")

    def _call_model(self, system: str, user: str, timeout: int = 30) -> str:
        """
        Call the configured LLM provider.
        
        Args:
            system: System prompt/instructions
            user: User prompt/query
            timeout: Request timeout in seconds
        
        Returns:
            Generated text response or fallback message
        """
        if not self.client:
            logger.debug("No AI client available, using fallback response")
            return (
                "Counterargument (fallback): Consider questioning the evidence, "
                "present an alternative cause, and invite the opponent to justify their claims."
            )
        
        try:
            if self.provider == "openai":
                return self._call_openai(system, user, timeout)
            elif self.provider == "google":
                return self._call_gemini(system, user)
            elif self.provider == "groq":
                return self._call_groq(system, user, timeout)
            else:
                return self._fallback_response("Provider not supported")
        except OpenAITimeoutError:
            logger.warning(f"API timeout after {timeout}s")
            return self._fallback_response("Request timed out. Please try again.")
        except (OpenAIError, APIError) as e:
            logger.error(f"API error: {str(e)}", exc_info=True)
            return self._fallback_response("API error. Please try again.")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return self._fallback_response("An error occurred. Please try again.")
    
    def _call_openai(self, system: str, user: str, timeout: int) -> str:
        """Call OpenAI API."""
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.6,
            timeout=timeout,
        )
        return completion.choices[0].message.content or ""
    
    def _call_gemini(self, system: str, user: str) -> str:
        """Call Google Gemini API."""
        model = self.client.GenerativeModel(self.model)
        combined_prompt = f"{system}\n\n{user}"
        response = model.generate_content(combined_prompt)
        return response.text or ""
    
    def _call_groq(self, system: str, user: str, timeout: int) -> str:
        """Call Groq API."""
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.6,
            timeout=timeout,
        )
        return completion.choices[0].message.content or ""
    
    @staticmethod
    def _fallback_response(error_msg: str = "") -> str:
        """Return fallback response when API unavailable."""
        return (
            "Response (fallback): Consider questioning the evidence, "
            "present an alternative cause, and invite the opponent to justify their claims."
        )

    def generate_counterargument(self, topic: str, user_argument: str, difficulty: str = "medium", personality: str = "balanced") -> Dict[str, str]:
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        system = (
            f"{style} "
            "Generate a SHORT counterargument (max 80 words). "
            "Be direct: 1 key rebuttal + 1 probing question. No fluff. "
            f"Difficulty: {difficulty}."
        )
        plan = (
            f"Topic: {topic}\nUser argument: {user_argument}\n"
            "Rebuttal (80 words max):"
        )
        content = self._call_model(system, plan)
        return {"topic": topic, "counterargument": content, "difficulty": difficulty, "personality": personality}

    def critique_and_feedback(self, user_argument: str) -> str:
        system = (
            "You are an argument analyst. Give BRIEF feedback (max 60 words total):\n"
            "• Strength: [1 sentence]\n"
            "• Weakness: [1 sentence]\n"
            "• Tip: [1 sentence]"
        )
        return self._call_model(system, user_argument)

    def generate_opening_position(self, topic: str, research_summary: str, difficulty: str = "medium", personality: str = "balanced") -> str:
        """Generate an opening debate position based on research context."""
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        system = (
            f"{style} "
            f"Topic: '{topic}'. Difficulty: {difficulty}. "
            "State your position in 2 sentences MAX (under 50 words). "
            "Be bold and specific. No preamble."
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"Context: {research_summary[:300]}\n\n"
            "Your position (50 words max):"
        )
        return self._call_model(system, user_prompt)

    def generate_counter_response(
        self, 
        topic: str, 
        ai_opening: str, 
        user_argument: str, 
        round_number: int,
        difficulty: str = "medium",
        personality: str = "balanced"
    ) -> Dict[str, str]:
        """Generate a counter-response to the user's argument in the debate."""
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        system = (
            f"{style} "
            f"Round {round_number} debate. Difficulty: {difficulty}. "
            "Reply in MAX 60 words: 1) Challenge their weakest point, "
            "2) End with ONE sharp question. No fluff or greetings."
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"My position: {ai_opening[:150]}\n"
            f"They said: {user_argument}\n\n"
            "Counter (60 words max):"
        )
        counter = self._call_model(system, user_prompt)
        return {"counter_argument": counter, "round": round_number, "personality": personality}

    def generate_debate_feedback(self, user_argument: str, round_number: int, difficulty: str = "medium") -> Dict[str, object]:
        """Generate comprehensive feedback on user's argument in a debate round."""
        system = (
            f"Debate coach, round {round_number}. Give feedback in MAX 50 words:\n"
            "✓ What worked | ✗ Fix this | → Next step\n"
            f"Difficulty: {difficulty}."
        )
        feedback = self._call_model(system, user_argument)
        return {
            "round": round_number,
            "feedback": feedback,
            "difficulty": difficulty,
        }

    def generate_formal_speech(
        self,
        motion: str,
        side: str,
        speech_type: str,
        previous_speeches: list = None,
        opponent_position: str = None,
        difficulty: str = "medium",
        personality: str = "balanced"
    ) -> str:
        """Generate a formal debate speech."""
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        
        if speech_type == "substantive":
            system = (
                f"{style} "
                f"Formal debate speech on: '{motion}'. Side: {side.upper()}.\n"
                "Structure (MAX 200 words):\n"
                "1. Brief formal opening\n"
                "2. Define 1 key term\n"
                "3. Present 2 arguments with evidence\n"
                "4. Conclude\n"
                f"Difficulty: {difficulty}. Be punchy, not verbose."
            )
            prompt = f"Motion: {motion}\nSide: {side.upper()}\n\nSpeech (200 words max):"
        
        elif speech_type == "reply":
            system = (
                f"{style} "
                f"REPLY speech (rebuttal). Motion: '{motion}', Side: {side.upper()}\n"
                "MAX 120 words:\n"
                "1. Attack opponent's weakest point\n"
                "2. Defend your best argument\n"
                "3. Conclude why you won\n"
                "NO new arguments. Be sharp."
            )
            prev_speeches_text = ""
            if previous_speeches:
                for speech in previous_speeches[-2:]:  # Last 2 speeches for context
                    prev_speeches_text += f"\n{speech['side'].upper()}: {speech['text'][:300]}..."
            
            prompt = (
                f"Motion: {motion}\n"
                f"Your side: {side.upper()}\n"
                f"Opponent's position: {opponent_position or 'See previous speeches'}\n"
                f"Previous speeches:{prev_speeches_text}\n\n"
                "Deliver your reply speech attacking opponent's points."
            )
        else:
            return ""
        
        return self._call_model(system, prompt)
    
    def respond_to_poi(self, question: str, current_argument: str) -> str:
        """Generate a response to a Point of Information."""
        system = (
            "You are an expert debater responding to a Point of Information (POI) challenge.\n"
            "Keep your response to 15-20 seconds of speaking (~40-50 words).\n"
            "Be respectful but assertive in defending your argument."
        )
        prompt = (
            f"Question from opponent: {question}\n"
            f"Your argument: {current_argument}\n\n"
            "Respond briefly to this POI."
        )
        return self._call_model(system, prompt)
    
    def evaluate_formal_speech(
        self,
        speech_text: str,
        speech_type: str,
        side: str,
        opponent_context: str = ""
    ) -> Dict:
        """Evaluate a formal debate speech."""
        system = (
            f"You are evaluating a formal debate {speech_type} speech delivered by the {side.upper()} side.\n"
            "Rate the speech on:\n"
            "1. Formal structure and language (0-25)\n"
            "2. Argument strength (0-25)\n"
            "3. Evidence quality (0-25)\n"
            "4. Delivery effectiveness (0-25)\n"
            "Total: 0-100\n\n"
            "Provide specific feedback on strengths and areas for improvement."
        )
        prompt = (
            f"Speech type: {speech_type}\n"
            f"Side: {side.upper()}\n"
            f"Speech text:\n{speech_text[:1000]}\n\n"
            f"Opponent context: {opponent_context[:500] if opponent_context else 'N/A'}\n\n"
            "Evaluate this speech and provide a score and feedback."
        )
        
        response = self._call_model(system, prompt)
        
        # Extract score if possible (simple heuristic)
        score = 60.0  # Default
        for line in response.split('\n'):
            if 'score' in line.lower() and any(char.isdigit() for char in line):
                words = line.split()
                for i, word in enumerate(words):
                    if word.isdigit():
                        try:
                            score = float(word)
                            if score <= 100:
                                break
                        except:
                            pass
        
        return {
            "score": min(100, score),
            "feedback": response,
            "speech_type": speech_type,
            "side": side
        }

    def suggest_rebuttals(self, opponent_argument: str, topic: str = "") -> Dict:
        """Generate real-time rebuttal suggestions as user types."""
        system = (
            "You are a debate assistant. Given the opponent's argument, "
            "suggest 3 SHORT rebuttal angles (max 15 words each). "
            "Format: numbered list, no explanations."
        )
        prompt = (
            f"Topic: {topic}\n"
            f"Opponent says: {opponent_argument}\n\n"
            "3 rebuttal angles (15 words each max):"
        )
        response = self._call_model(system, prompt, timeout=10)
        
        # Parse suggestions
        suggestions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-•) ').strip()
                if clean:
                    suggestions.append(clean)
        
        return {"suggestions": suggestions[:3], "opponent_argument": opponent_argument[:100]}


def from_settings(settings) -> AgenticDebateAgent:
    """Create agent instance from Django settings."""
    return AgenticDebateAgent(
        model=getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini"),
        api_key=getattr(settings, "AI_API_KEY", os.environ.get("AI_API_KEY", "")),
        provider=getattr(settings, "AI_MODEL_PROVIDER", "openai"),
        trace=getattr(settings, "AI_TRACE", False),
    )
