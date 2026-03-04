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

    def _format_sources_for_prompt(self, sources: list) -> str:
        """Format sources for inclusion in prompts."""
        if not sources:
            return ""
        source_text = "Available sources to cite:\n"
        for i, source in enumerate(sources[:3], 1):
            source_text += f"{i}. {source.get('title', 'Unknown')} ({source.get('year', 'N/A')}) - {source.get('type', 'source')}\n"
        return source_text

    def generate_opening_position(self, topic: str, research_summary: str, difficulty: str = "medium", personality: str = "balanced", sources: list = None) -> Dict[str, object]:
        """Generate an opening debate position based on research context with source citations."""
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        sources = sources or []
        source_instruction = ""
        if sources:
            source_instruction = (
                "When making claims, reference which source supports your point using format: "
                "'According to [Source Title]...' or 'Research from [Source] shows...'. "
                "Include at least one source reference. "
            )
        
        system = (
            f"{style} "
            f"Topic: '{topic}'. Difficulty: {difficulty}. "
            f"{source_instruction}"
            "State your position in 3-4 sentences MAX (under 70 words). "
            "Be bold and specific. No preamble."
        )
        sources_text = self._format_sources_for_prompt(sources)
        user_prompt = (
            f"Topic: {topic}\n"
            f"Context: {research_summary[:300]}\n"
            f"{sources_text}\n"
            "Your position (70 words max, cite sources):"
        )
        response = self._call_model(system, user_prompt)
        
        # Return structured response with both text and cited sources
        return {
            "text": response,
            "sources_used": sources[:3] if sources else [],
            "personality": personality,
            "difficulty": difficulty
        }

    def generate_counter_response(
        self, 
        topic: str, 
        ai_opening: str, 
        user_argument: str, 
        round_number: int,
        difficulty: str = "medium",
        personality: str = "balanced",
        sources: list = None
    ) -> Dict[str, object]:
        """Generate a counter-response to the user's argument in the debate with source citations."""
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        sources = sources or []
        source_instruction = ""
        if sources:
            source_instruction = (
                "When making factual claims, reference sources using format: "
                "'According to [Source]...' or 'As [Source] demonstrates...'. "
            )
        
        system = (
            f"{style} "
            f"Round {round_number} debate. Difficulty: {difficulty}. "
            f"{source_instruction}"
            "Reply in MAX 80 words: 1) Challenge their weakest point with evidence, "
            "2) End with ONE sharp question. No fluff or greetings."
        )
        sources_text = self._format_sources_for_prompt(sources)
        user_prompt = (
            f"Topic: {topic}\n"
            f"My position: {ai_opening[:150]}\n"
            f"They said: {user_argument}\n"
            f"{sources_text}\n"
            "Counter (80 words max, cite sources if making factual claims):"
        )
        counter = self._call_model(system, user_prompt)
        return {
            "counter_argument": counter, 
            "round": round_number, 
            "personality": personality,
            "sources_used": sources[:3] if sources else []
        }

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

    def analyze_argument_issues(self, argument: str, topic: str = "") -> Dict:
        """
        AI-powered analysis to identify fallacies, weak points, and unsupported claims.
        Returns detailed critique with specific issues highlighted.
        """
        system = (
            "You are a debate coach analyzing an argument for logical issues. "
            "Identify specific problems in the argument. For EACH issue found, provide:\n"
            "1. The exact quote/phrase that has the issue\n"
            "2. The type of issue (fallacy, weak argument, or unsupported claim)\n"
            "3. A brief explanation of why it's problematic\n"
            "4. A specific suggestion for improvement\n\n"
            "Format your response as:\n"
            "ISSUE 1:\n"
            "- Quote: \"[exact text]\"\n"
            "- Type: [Fallacy/Weak Argument/Unsupported Claim]\n"
            "- Problem: [explanation]\n"
            "- Fix: [suggestion]\n\n"
            "If the argument is strong, say 'NO MAJOR ISSUES FOUND' and list 1-2 strengths.\n"
            "Be thorough but fair. Maximum 4 issues."
        )
        prompt = (
            f"Topic: {topic}\n\n"
            f"Argument to analyze:\n\"{argument}\"\n\n"
            "Analyze this argument for fallacies, weak points, and unsupported claims:"
        )
        
        response = self._call_model(system, prompt, timeout=20)
        
        # Parse the AI response into structured issues
        issues = []
        current_issue = {}
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('ISSUE') or line.startswith('Issue'):
                if current_issue:
                    issues.append(current_issue)
                current_issue = {}
            elif line.startswith('- Quote:') or line.startswith('Quote:'):
                quote = line.split(':', 1)[1].strip().strip('"\'')
                current_issue['matched_text'] = quote
            elif line.startswith('- Type:') or line.startswith('Type:'):
                issue_type = line.split(':', 1)[1].strip().lower()
                if 'fallacy' in issue_type:
                    current_issue['issue_type'] = 'fallacy'
                elif 'weak' in issue_type:
                    current_issue['issue_type'] = 'weak_argument'
                else:
                    current_issue['issue_type'] = 'unsupported_claim'
                current_issue['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Problem:') or line.startswith('Problem:'):
                current_issue['description'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Fix:') or line.startswith('Fix:'):
                current_issue['suggestion'] = line.split(':', 1)[1].strip()
        
        if current_issue and 'matched_text' in current_issue:
            issues.append(current_issue)
        
        # Find positions in original text
        for issue in issues:
            if 'matched_text' in issue:
                pos = argument.lower().find(issue['matched_text'].lower()[:30])
                if pos != -1:
                    issue['position'] = {'start': pos, 'end': pos + len(issue.get('matched_text', ''))}
                else:
                    issue['position'] = {'start': 0, 'end': 0}
                issue['severity'] = 'high' if issue.get('issue_type') == 'fallacy' else 'medium'
        
        # Determine if no issues found
        no_issues = 'no major issues' in response.lower() or 'no issues found' in response.lower()
        
        return {
            "ai_issues": issues[:4],  # Limit to 4 issues
            "raw_analysis": response,
            "has_issues": not no_issues and len(issues) > 0,
            "argument_preview": argument[:100] + "..." if len(argument) > 100 else argument
        }


def from_settings(settings) -> AgenticDebateAgent:
    """Create agent instance from Django settings."""
    return AgenticDebateAgent(
        model=getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini"),
        api_key=getattr(settings, "AI_API_KEY", os.environ.get("AI_API_KEY", "")),
        provider=getattr(settings, "AI_MODEL_PROVIDER", "openai"),
        trace=getattr(settings, "AI_TRACE", False),
    )
