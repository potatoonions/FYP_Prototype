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

    def generate_counterargument(self, topic: str, user_argument: str, difficulty: str = "medium") -> Dict[str, str]:
        system = (
            "You are a concise debate coach generating focused counterarguments. "
            "Use clear logic, cite hypothetical evidence briefly, and suggest probing questions. "
            f"Difficulty: {difficulty}."
        )
        plan = (
            f"Topic: {topic}\nUser argument: {user_argument}\n"
            "Draft a rebuttal that highlights logical gaps and offers an alternative framing."
        )
        content = self._call_model(system, plan)
        return {"topic": topic, "counterargument": content, "difficulty": difficulty}

    def critique_and_feedback(self, user_argument: str) -> str:
        system = (
            "You are an argument analyst. Provide concise feedback in three bullet points: "
            "1) strongest element, 2) biggest logical vulnerability, 3) one improvement suggestion."
        )
        return self._call_model(system, user_argument)

    def generate_opening_position(self, topic: str, research_summary: str, difficulty: str = "medium") -> str:
        """Generate an opening debate position based on research context."""
        system = (
            f"You are an expert debater initiating a structured debate on '{topic}'. "
            f"Difficulty level: {difficulty}. "
            "Generate a clear, compelling opening position (2-3 sentences) that will challenge the user. "
            "Be specific and take a definitive stance."
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"Research Context:\n{research_summary}\n\n"
            "Create an opening position that the user should debate against."
        )
        return self._call_model(system, user_prompt)

    def generate_counter_response(
        self, 
        topic: str, 
        ai_opening: str, 
        user_argument: str, 
        round_number: int,
        difficulty: str = "medium"
    ) -> Dict[str, str]:
        """Generate a counter-response to the user's argument in the debate."""
        system = (
            f"You are an expert debater in round {round_number} of a debate. "
            f"Difficulty: {difficulty}. "
            "Provide a thoughtful counter-argument that:\n"
            "1. Directly addresses the user's points\n"
            "2. Identifies logical gaps or assumptions\n"
            "3. Presents an alternative perspective\n"
            "4. Asks a probing question to deepen the debate\n"
            "Keep your response concise (3-4 sentences)."
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"My opening position: {ai_opening}\n"
            f"User's response: {user_argument}\n\n"
            "Generate a counter-argument."
        )
        counter = self._call_model(system, user_prompt)
        return {"counter_argument": counter, "round": round_number}

    def generate_debate_feedback(self, user_argument: str, round_number: int, difficulty: str = "medium") -> Dict[str, object]:
        """Generate comprehensive feedback on user's argument in a debate round."""
        system = (
            f"You are a debate coach evaluating round {round_number}. "
            f"Analyze this argument for:\n"
            "1. Clarity and coherence\n"
            "2. Logical strength\n"
            "3. Use of evidence\n"
            "4. Counter to opponent's points\n"
            f"Difficulty: {difficulty}. "
            "Provide actionable feedback."
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
        difficulty: str = "medium"
    ) -> str:
        """Generate a formal debate speech."""
        if speech_type == "substantive":
            system = (
                f"You are an expert debater delivering a substantive speech on formal debate motion: '{motion}'.\n"
                f"You are speaking for the {side.upper()} side.\n"
                f"Your speech should:\n"
                "1. Open with formal address (e.g., 'Honorable judges, worthy opposition')\n"
                "2. Define key terms\n"
                "3. Present 2-3 main arguments with evidence\n"
                "4. Use logical connectives (firstly, secondly, therefore, etc.)\n"
                "5. Conclude with a summary of your case\n"
                f"Difficulty: {difficulty}.\n"
                "Keep speech concise (aim for ~400 words to fit 7-8 minute delivery)."
            )
            prompt = f"Motion: {motion}\nSide: {side.upper()}\n\nDeliver your substantive speech."
        
        elif speech_type == "reply":
            system = (
                f"You are an expert debater delivering a REPLY speech (rebuttal).\n"
                f"Motion: '{motion}', Side: {side.upper()}\n"
                "Your reply speech should:\n"
                "1. Address the opponent's main arguments\n"
                "2. Point out logical flaws or weak evidence\n"
                "3. Reinforce your side's strongest points\n"
                "4. DO NOT introduce new arguments\n"
                "5. Conclude with why your side won the debate\n"
                "Keep it focused and concise (~200 words for 4-minute delivery)."
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


def from_settings(settings) -> AgenticDebateAgent:
    """Create agent instance from Django settings."""
    return AgenticDebateAgent(
        model=getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini"),
        api_key=getattr(settings, "AI_API_KEY", os.environ.get("AI_API_KEY", "")),
        provider=getattr(settings, "AI_MODEL_PROVIDER", "openai"),
        trace=getattr(settings, "AI_TRACE", False),
    )
