"""
Rule-based lightweight analyzers that run alongside the LLM.
These provide transparent signals (structure, fallacies, persuasiveness)
to combine with the model's feedback.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List


FALLACY_KEYWORDS: Dict[str, List[str]] = {
    "ad_hominem": ["idiot", "stupid", "fool", "nonsense about you"],
    "appeal_to_emotion": ["everyone knows", "think of the children", "heartbreaking"],
    "slippery_slope": ["will inevitably", "leads to", "domino effect"],
    "hasty_generalization": ["always", "never", "everyone", "no one"],
}


@dataclass
class AnalysisResult:
    fallacies: List[str]
    unsupported_claims: List[str]
    strengths: List[str]
    score: float

    def as_dict(self) -> Dict[str, object]:
        return {
            "fallacies": self.fallacies,
            "unsupported_claims": self.unsupported_claims,
            "strengths": self.strengths,
            "score": round(self.score, 2),
        }


def detect_fallacies(text: str) -> List[str]:
    detected: List[str] = []
    lowered = text.lower()
    for fallacy, cues in FALLACY_KEYWORDS.items():
        if any(cue in lowered for cue in cues):
            detected.append(fallacy)
    return detected


def detect_unsupported_claims(text: str) -> List[str]:
    unsupported: List[str] = []
    sentences = [s.strip() for s in text.replace("?", ".").split(".") if s.strip()]
    for sentence in sentences:
        has_confidence = any(word in sentence.lower() for word in ["should", "must", "certainly", "undeniably"])
        has_evidence = any(marker in sentence.lower() for marker in ["because", "for example", "according to", "data", "study"])
        if has_confidence and not has_evidence:
            unsupported.append(sentence)
    return unsupported


def detect_strengths(text: str) -> List[str]:
    strengths: List[str] = []
    if len(text.split()) > 80:
        strengths.append("detailed_argument")
    if any(phrase in text.lower() for phrase in ["for example", "for instance", "according to"]):
        strengths.append("uses_examples")
    if any(conn in text.lower() for conn in ["therefore", "thus", "hence"]):
        strengths.append("logical_connectors")
    return strengths


def score_argument(fallacies: List[str], unsupported: List[str], strengths: List[str]) -> float:
    base = 0.6
    penalty = 0.1 * len(fallacies) + 0.05 * len(unsupported)
    bonus = 0.08 * len(strengths)
    return max(0.0, min(1.0, base - penalty + bonus))


def analyze_argument(text: str) -> AnalysisResult:
    fallacies = detect_fallacies(text)
    unsupported = detect_unsupported_claims(text)
    strengths = detect_strengths(text)
    score = score_argument(fallacies, unsupported, strengths)
    return AnalysisResult(fallacies, unsupported, strengths, score)

