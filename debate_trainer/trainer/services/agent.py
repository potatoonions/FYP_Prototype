"""
Agentic orchestration for generating counterarguments and feedback.
Falls back to heuristic responses if an LLM provider is unavailable.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None


class AgenticDebateAgent:
    def __init__(self, model: str, api_key: str, provider: str = "openai", trace: bool = False) -> None:
        self.model = model
        self.api_key = api_key
        self.provider = provider
        self.trace = trace
        self.client = None
        if provider == "openai" and OpenAI and api_key not in {"", "set-me"}:
            self.client = OpenAI(api_key=api_key)

    def _call_model(self, system: str, user: str) -> str:
        """Call the provider and return text; fallback to deterministic text."""
        if self.client:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.6,
            )
            return completion.choices[0].message.content

        # Fallback: simple template to avoid hard failure without network.
        return (
            "Counterargument (fallback): consider questioning the evidence, "
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


def from_settings(settings) -> AgenticDebateAgent:
    return AgenticDebateAgent(
        model=getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini"),
        api_key=getattr(settings, "AI_API_KEY", os.environ.get("AI_API_KEY", "")),
        provider=getattr(settings, "AI_MODEL_PROVIDER", "openai"),
        trace=getattr(settings, "AI_TRACE", False),
    )
