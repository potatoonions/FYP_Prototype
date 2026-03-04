"""
Rule-based lightweight analyzers that run alongside the LLM.
These provide transparent signals (structure, fallacies, persuasiveness)
to combine with the model's feedback.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


# Extended fallacy detection with descriptions and examples
FALLACY_PATTERNS: Dict[str, Dict] = {
    "ad_hominem": {
        "keywords": ["idiot", "stupid", "fool", "nonsense about you", "you're just", "you people", "typical of someone like"],
        "description": "Attacking the person rather than their argument",
        "example": "You're just saying that because you're biased",
        "severity": "high"
    },
    "appeal_to_emotion": {
        "keywords": ["everyone knows", "think of the children", "heartbreaking", "tragic", "how could anyone", "any decent person"],
        "description": "Using emotional manipulation instead of logical reasoning",
        "example": "Think of the children who will suffer!",
        "severity": "medium"
    },
    "slippery_slope": {
        "keywords": ["will inevitably", "leads to", "domino effect", "next thing you know", "slippery slope", "where does it end"],
        "description": "Assuming one event will lead to extreme consequences without evidence",
        "example": "If we allow X, soon we'll have Y and Z",
        "severity": "medium"
    },
    "hasty_generalization": {
        "keywords": ["always", "never", "everyone", "no one", "all people", "nobody ever"],
        "description": "Drawing broad conclusions from limited examples",
        "example": "Everyone knows that...",
        "severity": "medium"
    },
    "straw_man": {
        "keywords": ["so you're saying", "what you really mean", "you think that", "your argument is basically"],
        "description": "Misrepresenting someone's argument to make it easier to attack",
        "example": "So you're saying we should just ignore the problem entirely?",
        "severity": "high"
    },
    "false_dichotomy": {
        "keywords": ["either...or", "only two options", "you're either with us", "if not...then", "the only choice"],
        "description": "Presenting only two options when more exist",
        "example": "You're either with us or against us",
        "severity": "medium"
    },
    "appeal_to_authority": {
        "keywords": ["experts say", "scientists believe", "studies show", "research proves"],
        "description": "Citing authority without specific evidence (can be valid if properly sourced)",
        "example": "Scientists say this is true (without citation)",
        "severity": "low"
    },
    "circular_reasoning": {
        "keywords": ["because it is", "that's just how it is", "it's true because", "self-evident"],
        "description": "Using the conclusion as a premise",
        "example": "It's true because it's obviously true",
        "severity": "high"
    },
    "red_herring": {
        "keywords": ["but what about", "the real issue is", "speaking of which", "that reminds me"],
        "description": "Introducing irrelevant information to distract from the main argument",
        "example": "But what about this completely different issue?",
        "severity": "medium"
    },
    "bandwagon": {
        "keywords": ["everyone is doing", "most people believe", "popular opinion", "the majority thinks"],
        "description": "Arguing something is true because many people believe it",
        "example": "Most people agree with me, so I must be right",
        "severity": "medium"
    },
}

# Patterns for weak arguments
WEAK_ARGUMENT_PATTERNS: Dict[str, Dict] = {
    "vague_language": {
        "patterns": [r"\bsomehow\b", r"\bsort of\b", r"\bkind of\b", r"\bmaybe\b", r"\bprobably\b", r"\bsomething like\b"],
        "description": "Using imprecise language that weakens your point",
        "suggestion": "Be more specific and definitive in your claims"
    },
    "unsupported_assertion": {
        "patterns": [r"\bit's obvious\b", r"\bclearly\b", r"\bof course\b", r"\bobviously\b"],
        "description": "Asserting something is obvious without explanation",
        "suggestion": "Explain WHY it's obvious or provide evidence"
    },
    "weak_hedging": {
        "patterns": [r"\bi think\b", r"\bi believe\b", r"\bin my opinion\b", r"\bi feel\b"],
        "description": "Over-qualifying statements reduces persuasive power",
        "suggestion": "State your position more confidently with evidence"
    },
    "missing_evidence": {
        "patterns": [r"\bshould\b.*\.", r"\bmust\b.*\.", r"\bneed to\b.*\."],
        "description": "Making prescriptive claims without supporting evidence",
        "suggestion": "Add data, examples, or logical reasoning to support claims"
    },
}


@dataclass
class DetailedIssue:
    """Represents a detected issue in the argument."""
    issue_type: str  # 'fallacy', 'weak_argument', 'unsupported_claim'
    name: str
    description: str
    matched_text: str
    position: Tuple[int, int]  # start and end position in text
    severity: str  # 'high', 'medium', 'low'
    suggestion: str

    def as_dict(self) -> Dict:
        return {
            "issue_type": self.issue_type,
            "name": self.name,
            "description": self.description,
            "matched_text": self.matched_text,
            "position": {"start": self.position[0], "end": self.position[1]},
            "severity": self.severity,
            "suggestion": self.suggestion,
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


@dataclass
class DetailedAnalysisResult:
    """Comprehensive analysis result with positions for highlighting."""
    issues: List[DetailedIssue]
    strengths: List[str]
    overall_score: float
    summary: str

    def as_dict(self) -> Dict:
        return {
            "issues": [issue.as_dict() for issue in self.issues],
            "strengths": self.strengths,
            "overall_score": round(self.overall_score, 2),
            "summary": self.summary,
            "issue_counts": {
                "fallacies": len([i for i in self.issues if i.issue_type == "fallacy"]),
                "weak_arguments": len([i for i in self.issues if i.issue_type == "weak_argument"]),
                "unsupported_claims": len([i for i in self.issues if i.issue_type == "unsupported_claim"]),
            }
        }


def detect_fallacies(text: str) -> List[str]:
    detected: List[str] = []
    lowered = text.lower()
    for fallacy, info in FALLACY_PATTERNS.items():
        if any(cue in lowered for cue in info["keywords"]):
            detected.append(fallacy)
    return detected


def detect_fallacies_detailed(text: str) -> List[DetailedIssue]:
    """Detect fallacies with position information for highlighting."""
    issues: List[DetailedIssue] = []
    lowered = text.lower()
    
    for fallacy_name, info in FALLACY_PATTERNS.items():
        for keyword in info["keywords"]:
            # Find all occurrences
            start = 0
            while True:
                pos = lowered.find(keyword, start)
                if pos == -1:
                    break
                
                # Get surrounding context (the sentence containing this)
                sentence_start = text.rfind('.', 0, pos)
                sentence_start = 0 if sentence_start == -1 else sentence_start + 1
                sentence_end = text.find('.', pos)
                sentence_end = len(text) if sentence_end == -1 else sentence_end + 1
                
                matched_text = text[sentence_start:sentence_end].strip()
                
                issues.append(DetailedIssue(
                    issue_type="fallacy",
                    name=fallacy_name.replace("_", " ").title(),
                    description=info["description"],
                    matched_text=matched_text,
                    position=(sentence_start, sentence_end),
                    severity=info["severity"],
                    suggestion=f"Avoid {info['description'].lower()}. Example to avoid: '{info['example']}'"
                ))
                start = pos + len(keyword)
                break  # Only report once per fallacy type per text
    
    return issues


def detect_weak_arguments(text: str) -> List[DetailedIssue]:
    """Detect weak argument patterns with positions."""
    issues: List[DetailedIssue] = []
    
    for pattern_name, info in WEAK_ARGUMENT_PATTERNS.items():
        for pattern in info["patterns"]:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches[:2]:  # Limit to 2 per pattern type
                # Get the sentence containing this match
                sentence_start = text.rfind('.', 0, match.start())
                sentence_start = 0 if sentence_start == -1 else sentence_start + 1
                sentence_end = text.find('.', match.end())
                sentence_end = len(text) if sentence_end == -1 else sentence_end + 1
                
                matched_text = text[sentence_start:sentence_end].strip()
                
                issues.append(DetailedIssue(
                    issue_type="weak_argument",
                    name=pattern_name.replace("_", " ").title(),
                    description=info["description"],
                    matched_text=matched_text,
                    position=(sentence_start, sentence_end),
                    severity="medium",
                    suggestion=info["suggestion"]
                ))
                break  # Only report once per pattern type
    
    return issues


def detect_unsupported_claims(text: str) -> List[str]:
    unsupported: List[str] = []
    sentences = [s.strip() for s in text.replace("?", ".").split(".") if s.strip()]
    for sentence in sentences:
        has_confidence = any(word in sentence.lower() for word in ["should", "must", "certainly", "undeniably"])
        has_evidence = any(marker in sentence.lower() for marker in ["because", "for example", "according to", "data", "study"])
        if has_confidence and not has_evidence:
            unsupported.append(sentence)
    return unsupported


def detect_unsupported_claims_detailed(text: str) -> List[DetailedIssue]:
    """Detect unsupported claims with position information."""
    issues: List[DetailedIssue] = []
    sentences = [s.strip() for s in text.replace("?", ".").split(".") if s.strip()]
    
    current_pos = 0
    for sentence in sentences:
        # Find the position of this sentence in the original text
        sentence_pos = text.find(sentence, current_pos)
        if sentence_pos == -1:
            continue
        
        has_confidence = any(word in sentence.lower() for word in 
            ["should", "must", "certainly", "undeniably", "definitely", "always", "never", "absolutely"])
        has_evidence = any(marker in sentence.lower() for marker in 
            ["because", "for example", "according to", "data", "study", "research", "evidence", "shows that", "demonstrates"])
        
        if has_confidence and not has_evidence:
            issues.append(DetailedIssue(
                issue_type="unsupported_claim",
                name="Unsupported Claim",
                description="Strong assertion made without supporting evidence",
                matched_text=sentence,
                position=(sentence_pos, sentence_pos + len(sentence)),
                severity="medium",
                suggestion="Add evidence, examples, data, or citations to support this claim"
            ))
        
        current_pos = sentence_pos + len(sentence)
    
    return issues


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


def analyze_argument_detailed(text: str) -> DetailedAnalysisResult:
    """
    Perform comprehensive analysis of an argument with detailed issue tracking.
    Returns issues with positions for UI highlighting.
    """
    # Collect all issues
    all_issues: List[DetailedIssue] = []
    
    # Detect fallacies
    fallacy_issues = detect_fallacies_detailed(text)
    all_issues.extend(fallacy_issues)
    
    # Detect weak arguments
    weak_issues = detect_weak_arguments(text)
    all_issues.extend(weak_issues)
    
    # Detect unsupported claims
    unsupported_issues = detect_unsupported_claims_detailed(text)
    all_issues.extend(unsupported_issues)
    
    # Remove duplicates (same position range)
    seen_positions = set()
    unique_issues = []
    for issue in all_issues:
        pos_key = (issue.position[0], issue.position[1])
        if pos_key not in seen_positions:
            seen_positions.add(pos_key)
            unique_issues.append(issue)
    
    # Sort by position
    unique_issues.sort(key=lambda x: x.position[0])
    
    # Detect strengths
    strengths = detect_strengths(text)
    
    # Calculate score
    high_severity = len([i for i in unique_issues if i.severity == "high"])
    medium_severity = len([i for i in unique_issues if i.severity == "medium"])
    low_severity = len([i for i in unique_issues if i.severity == "low"])
    
    base = 0.7
    penalty = (0.15 * high_severity) + (0.08 * medium_severity) + (0.03 * low_severity)
    bonus = 0.1 * len(strengths)
    overall_score = max(0.0, min(1.0, base - penalty + bonus))
    
    # Generate summary
    issue_count = len(unique_issues)
    if issue_count == 0:
        summary = "Strong argument with no major issues detected."
    elif issue_count <= 2:
        summary = f"Good argument with {issue_count} minor issue(s) to address."
    elif issue_count <= 4:
        summary = f"Moderate argument with {issue_count} issues that could be improved."
    else:
        summary = f"Argument needs work - {issue_count} issues detected that weaken your position."
    
    return DetailedAnalysisResult(
        issues=unique_issues,
        strengths=strengths,
        overall_score=overall_score,
        summary=summary
    )


# Mapping for human-readable fallacy names
FALLACY_DISPLAY_NAMES = {
    "ad_hominem": "Ad Hominem Attack",
    "appeal_to_emotion": "Appeal to Emotion",
    "slippery_slope": "Slippery Slope",
    "hasty_generalization": "Hasty Generalization",
    "straw_man": "Straw Man",
    "false_dichotomy": "False Dichotomy",
    "appeal_to_authority": "Appeal to Authority",
    "circular_reasoning": "Circular Reasoning",
    "red_herring": "Red Herring",
    "bandwagon": "Bandwagon Fallacy",
}

