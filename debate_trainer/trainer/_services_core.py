"""
Consolidated services module for the AI Debate Trainer.
Combines: AI Agent, Analysis, Research, and Debate Flow functionality.
"""
from __future__ import annotations

import logging
import math
import os
import re
import signal
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# LLM Provider imports
try:
    from openai import OpenAI, APITimeoutError as OpenAITimeoutError, APIError as OpenAIError
except ImportError:
    OpenAI = None
    OpenAITimeoutError = Exception
    OpenAIError = Exception

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False

logger = logging.getLogger("trainer.services")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class APIError(Exception):
    """Base exception for API errors"""
    pass

class APITimeoutError(APIError):
    """API timeout exception"""
    pass

class ResearchTimeoutError(Exception):
    """Custom timeout exception for research operations."""
    pass


# =============================================================================
# AI PERSONALITIES
# =============================================================================

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


# =============================================================================
# ANALYSIS PATTERNS (Precompiled for performance)
# =============================================================================

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

# Precompiled weak argument patterns for performance
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

# Precompile regex patterns at module load for performance
COMPILED_WEAK_PATTERNS = {
    name: [re.compile(p, re.IGNORECASE) for p in info["patterns"]]
    for name, info in WEAK_ARGUMENT_PATTERNS.items()
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DetailedIssue:
    """Represents a detected issue in the argument."""
    issue_type: str
    name: str
    description: str
    matched_text: str
    position: Tuple[int, int]
    severity: str
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

@dataclass
class TimeSignal:
    """Time signal (bell) notification."""
    time_seconds: int
    signal_type: str
    bell_count: int

@dataclass
class POIRequest:
    """Point of Information request."""
    from_speaker: str
    timestamp: datetime
    question: str
    accepted: Optional[bool] = None
    response: Optional[str] = None


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

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
            pos = lowered.find(keyword)
            if pos != -1:
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
                break
    return issues


def detect_weak_arguments(text: str) -> List[DetailedIssue]:
    """Detect weak argument patterns with positions using precompiled regex."""
    issues: List[DetailedIssue] = []
    
    for pattern_name, compiled_patterns in COMPILED_WEAK_PATTERNS.items():
        info = WEAK_ARGUMENT_PATTERNS[pattern_name]
        for pattern in compiled_patterns:
            match = pattern.search(text)
            if match:
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
                break
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
    """Comprehensive analysis with detailed issue tracking."""
    all_issues: List[DetailedIssue] = []
    all_issues.extend(detect_fallacies_detailed(text))
    all_issues.extend(detect_weak_arguments(text))
    all_issues.extend(detect_unsupported_claims_detailed(text))
    
    # Remove duplicates
    seen_positions = set()
    unique_issues = []
    for issue in all_issues:
        pos_key = (issue.position[0], issue.position[1])
        if pos_key not in seen_positions:
            seen_positions.add(pos_key)
            unique_issues.append(issue)
    
    unique_issues.sort(key=lambda x: x.position[0])
    strengths = detect_strengths(text)
    
    high_severity = len([i for i in unique_issues if i.severity == "high"])
    medium_severity = len([i for i in unique_issues if i.severity == "medium"])
    low_severity = len([i for i in unique_issues if i.severity == "low"])
    
    base = 0.7
    penalty = (0.15 * high_severity) + (0.08 * medium_severity) + (0.03 * low_severity)
    bonus = 0.1 * len(strengths)
    overall_score = max(0.0, min(1.0, base - penalty + bonus))
    
    issue_count = len(unique_issues)
    if issue_count == 0:
        summary = "Strong argument with no major issues detected."
    elif issue_count <= 2:
        summary = f"Good argument with {issue_count} minor issue(s) to address."
    elif issue_count <= 4:
        summary = f"Moderate argument with {issue_count} issues that could be improved."
    else:
        summary = f"Argument needs work - {issue_count} issues detected that weaken your position."
    
    return DetailedAnalysisResult(unique_issues, strengths, overall_score, summary)


def analyze_argument_with_ml(text: str, use_ml: bool = True) -> Dict:
    """
    Enhanced argument analysis combining rule-based and ML approaches.
    
    Args:
        text: The argument text to analyze
        use_ml: Whether to include ML-based analysis
        
    Returns:
        Combined analysis dictionary with both rule-based and ML scores
    """
    # Get rule-based analysis
    rule_based = analyze_argument_detailed(text)
    
    result = {
        "rule_based": {
            "issues": [
                {
                    "type": issue.issue_type,
                    "description": issue.description,
                    "text": issue.text_snippet,
                    "severity": issue.severity,
                    "suggestion": issue.suggestion,
                }
                for issue in rule_based.issues
            ],
            "strengths": rule_based.strengths,
            "score": rule_based.overall_score,
            "summary": rule_based.summary,
        },
        "combined_score": rule_based.overall_score,
    }
    
    # Add ML analysis if enabled
    if use_ml:
        try:
            from .ml import get_ml_analysis
            ml_result = get_ml_analysis(text)
            result["ml_based"] = ml_result
            
            # Combine scores (weighted average: 60% ML, 40% rule-based)
            if ml_result.get("ml_available", False):
                ml_score = ml_result.get("quality_score", 0.5)
                rule_score = rule_based.overall_score
                result["combined_score"] = (0.6 * ml_score) + (0.4 * rule_score)
                result["ml_available"] = True
            else:
                result["ml_available"] = False
        except ImportError:
            result["ml_based"] = None
            result["ml_available"] = False
    else:
        result["ml_based"] = None
        result["ml_available"] = False
    
    return result


# =============================================================================
# RESEARCH SOURCES
# =============================================================================

REFERENCE_SOURCES = {
    "artificial intelligence": [
        {"title": "Artificial Intelligence: A Modern Approach", "authors": ["Stuart Russell", "Peter Norvig"], "year": "2020", "type": "book", "url": "https://aima.cs.berkeley.edu/", "description": "The definitive textbook on AI covering machine learning, reasoning, planning, and ethics."},
        {"title": "Ethics of Artificial Intelligence and Robotics", "authors": ["Stanford Encyclopedia of Philosophy"], "year": "2023", "type": "article", "url": "https://plato.stanford.edu/entries/ethics-ai/", "description": "Comprehensive philosophical analysis of AI ethics, bias, and accountability."},
        {"title": "UNESCO Recommendation on the Ethics of AI", "authors": ["UNESCO"], "year": "2021", "type": "report", "url": "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics", "description": "First global standard on AI ethics adopted by 193 countries."},
    ],
    "climate": [
        {"title": "IPCC Sixth Assessment Report", "authors": ["Intergovernmental Panel on Climate Change"], "year": "2023", "type": "report", "url": "https://www.ipcc.ch/assessment-report/ar6/", "description": "Authoritative scientific assessment of climate change causes, impacts, and solutions."},
        {"title": "The Economics of Climate Change", "authors": ["Nicholas Stern"], "year": "2007", "type": "book", "url": "https://www.lse.ac.uk/granthaminstitute/publication/the-economics-of-climate-change-the-stern-review/", "description": "Landmark economic analysis of climate change and policy responses."},
    ],
    "healthcare": [
        {"title": "World Health Organization Reports", "authors": ["WHO"], "year": "2023", "type": "report", "url": "https://www.who.int/publications", "description": "Global health statistics, guidelines, and policy recommendations."},
        {"title": "The Lancet", "authors": ["Various"], "year": "2023", "type": "journal", "url": "https://www.thelancet.com/", "description": "Leading peer-reviewed medical journal with high-impact research."},
    ],
    "education": [
        {"title": "OECD Education at a Glance", "authors": ["OECD"], "year": "2023", "type": "report", "url": "https://www.oecd.org/education/education-at-a-glance/", "description": "Comprehensive international statistics on education systems worldwide."},
        {"title": "Visible Learning", "authors": ["John Hattie"], "year": "2008", "type": "book", "url": "https://visible-learning.org/", "description": "Meta-analysis of educational research identifying effective teaching strategies."},
    ],
    "default": [
        {"title": "Stanford Encyclopedia of Philosophy", "authors": ["Stanford University"], "year": "2023", "type": "encyclopedia", "url": "https://plato.stanford.edu/", "description": "Authoritative reference for philosophical topics and ethical debates."},
        {"title": "Academic databases (JSTOR, Google Scholar)", "authors": ["Various"], "year": "2023", "type": "database", "url": "https://scholar.google.com/", "description": "Search peer-reviewed academic papers on your topic."},
        {"title": "Pew Research Center", "authors": ["Pew Research"], "year": "2023", "type": "report", "url": "https://www.pewresearch.org/", "description": "Non-partisan data and analysis on social issues and public opinion."},
    ],
}


def get_reference_sources(topic: str) -> List[Dict]:
    """Get curated reference sources relevant to the debate topic."""
    topic_lower = topic.lower()
    sources = []
    
    for keyword, keyword_sources in REFERENCE_SOURCES.items():
        if keyword != "default" and keyword in topic_lower:
            sources.extend(keyword_sources)
    
    if len(sources) < 3:
        sources.extend(REFERENCE_SOURCES["default"])
    
    seen_titles = set()
    unique_sources = []
    for source in sources:
        if source["title"] not in seen_titles:
            seen_titles.add(source["title"])
            unique_sources.append(source)
    
    return unique_sources[:5]


class ScholarResearcher:
    """Fetches research papers from Google Scholar."""
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
    
    def search_topic(self, topic: str, timeout: int = 15) -> Dict[str, object]:
        if not SCHOLARLY_AVAILABLE:
            return self._fallback_research(topic)
        
        try:
            # Use ThreadPoolExecutor for timeout on Windows
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._do_search, topic)
                try:
                    return future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Research timeout for topic: {topic}")
                    return self._fallback_research(topic)
        except Exception as e:
            logger.error(f"Error searching for topic '{topic}': {str(e)}")
            return self._fallback_research(topic)
    
    def _do_search(self, topic: str) -> Dict:
        search_query = scholarly.search_pubs(topic)
        papers = []
        
        for i, paper in enumerate(search_query):
            if i >= self.max_results:
                break
            try:
                papers.append({
                    "title": paper.get("bib", {}).get("title", "Unknown"),
                    "authors": paper.get("bib", {}).get("author", ["Unknown"]),
                    "year": paper.get("bib", {}).get("pub_year", "Unknown"),
                    "abstract": paper.get("bib", {}).get("abstract", "No abstract available"),
                    "url": paper.get("eprint_url", "") or paper.get("pub_url", ""),
                })
            except Exception:
                continue
        
        return {
            "topic": topic,
            "papers_found": len(papers),
            "papers": papers,
            "summary": self._summarize_papers(papers),
        }
    
    def _summarize_papers(self, papers: List[Dict]) -> str:
        if not papers:
            return "No research papers found."
        
        summary = f"Found {len(papers)} relevant research papers:\n\n"
        for i, paper in enumerate(papers, 1):
            summary += f"{i}. {paper['title']}\n"
            summary += f"   Authors: {', '.join(paper['authors'][:3])}\n"
            summary += f"   Year: {paper['year']}\n"
            if paper['abstract']:
                summary += f"   Summary: {paper['abstract'][:200]}...\n\n"
        return summary
    
    def _fallback_research(self, topic: str) -> Dict[str, object]:
        return {
            "topic": topic,
            "papers_found": 0,
            "papers": [],
            "summary": f"Research context: This is a debate on '{topic}'. Use your knowledge and critical thinking to construct arguments.",
            "note": "Scholarly search unavailable - using fallback mode",
        }


def get_research_context(topic: str, max_results: int = 5) -> Dict[str, object]:
    """Fetch research for a debate topic."""
    researcher = ScholarResearcher(max_results=max_results)
    return researcher.search_topic(topic)


# =============================================================================
# AI DEBATE AGENT (with async support)
# =============================================================================

class AgenticDebateAgent:
    """Multi-provider LLM agent for debate training with async support."""
    
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    
    def __init__(self, model: str, api_key: str, provider: str = "openai", trace: bool = False) -> None:
        self.model = model
        self.api_key = api_key
        self.provider = provider
        self.trace = trace
        self._client = None
        self._initialized = False
        
    @property
    def client(self):
        """Lazy initialization of AI client."""
        if not self._initialized:
            self._init_client()
            self._initialized = True
        return self._client
    
    def _init_client(self):
        if self.api_key in {"", "set-me"}:
            logger.debug(f"API key not set for {self.provider}")
            return
            
        if self.provider == "openai" and OpenAI:
            self._client = OpenAI(api_key=self.api_key)
        elif self.provider == "google" and genai:
            genai.configure(api_key=self.api_key)
            self._client = genai
        elif self.provider == "groq" and Groq:
            self._client = Groq(api_key=self.api_key)

    def _call_model(self, system: str, user: str, timeout: int = 30) -> str:
        """Call LLM with timeout support."""
        if not self.client:
            return self._fallback_response()
        
        try:
            if self.provider == "openai":
                return self._call_openai(system, user, timeout)
            elif self.provider == "google":
                return self._call_gemini(system, user)
            elif self.provider == "groq":
                return self._call_groq(system, user, timeout)
            return self._fallback_response()
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            return self._fallback_response()
    
    def _call_model_async(self, system: str, user: str, timeout: int = 30) -> concurrent.futures.Future:
        """Call LLM asynchronously using thread pool."""
        return self._executor.submit(self._call_model, system, user, timeout)
    
    def _call_openai(self, system: str, user: str, timeout: int) -> str:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.6,
            timeout=timeout,
        )
        return completion.choices[0].message.content or ""
    
    def _call_gemini(self, system: str, user: str) -> str:
        model = self._client.GenerativeModel(self.model)
        response = model.generate_content(f"{system}\n\n{user}")
        return response.text or ""
    
    def _call_groq(self, system: str, user: str, timeout: int) -> str:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.6,
            timeout=timeout,
        )
        return completion.choices[0].message.content or ""
    
    @staticmethod
    def _fallback_response(error_msg: str = "") -> str:
        return "Response (fallback): Consider questioning the evidence, present an alternative cause, and invite the opponent to justify their claims."

    def _format_sources_for_prompt(self, sources: list) -> str:
        if not sources:
            return ""
        source_text = "Available sources to cite:\n"
        for i, source in enumerate(sources[:3], 1):
            source_text += f"{i}. {source.get('title', 'Unknown')} ({source.get('year', 'N/A')}) - {source.get('type', 'source')}\n"
        return source_text

    def generate_counterargument(self, topic: str, user_argument: str, difficulty: str = "medium", personality: str = "balanced") -> Dict[str, str]:
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        system = f"{style} Generate a SHORT counterargument (max 80 words). Be direct: 1 key rebuttal + 1 probing question. No fluff. Difficulty: {difficulty}."
        plan = f"Topic: {topic}\nUser argument: {user_argument}\nRebuttal (80 words max):"
        content = self._call_model(system, plan)
        return {"topic": topic, "counterargument": content, "difficulty": difficulty, "personality": personality}

    def critique_and_feedback(self, user_argument: str) -> str:
        system = "You are an argument analyst. Give BRIEF feedback (max 60 words total):\n• Strength: [1 sentence]\n• Weakness: [1 sentence]\n• Tip: [1 sentence]"
        return self._call_model(system, user_argument)

    def generate_opening_position(self, topic: str, research_summary: str, difficulty: str = "medium", personality: str = "balanced", sources: list = None) -> Dict[str, object]:
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        sources = sources or []
        source_instruction = ""
        if sources:
            source_instruction = "When making claims, reference which source supports your point using format: 'According to [Source Title]...' or 'Research from [Source] shows...'. Include at least one source reference. "
        
        system = f"{style} Topic: '{topic}'. Difficulty: {difficulty}. {source_instruction}State your position in 3-4 sentences MAX (under 70 words). Be bold and specific. No preamble."
        sources_text = self._format_sources_for_prompt(sources)
        user_prompt = f"Topic: {topic}\nContext: {research_summary[:300]}\n{sources_text}\nYour position (70 words max, cite sources):"
        response = self._call_model(system, user_prompt)
        
        return {"text": response, "sources_used": sources[:3] if sources else [], "personality": personality, "difficulty": difficulty}

    def generate_counter_response(self, topic: str, ai_opening: str, user_argument: str, round_number: int, difficulty: str = "medium", personality: str = "balanced", sources: list = None) -> Dict[str, object]:
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        sources = sources or []
        source_instruction = ""
        if sources:
            source_instruction = "When making factual claims, reference sources using format: 'According to [Source]...' or 'As [Source] demonstrates...'. "
        
        system = f"{style} Round {round_number} debate. Difficulty: {difficulty}. {source_instruction}Reply in MAX 80 words: 1) Challenge their weakest point with evidence, 2) End with ONE sharp question. No fluff or greetings."
        sources_text = self._format_sources_for_prompt(sources)
        user_prompt = f"Topic: {topic}\nMy position: {ai_opening[:150]}\nThey said: {user_argument}\n{sources_text}\nCounter (80 words max, cite sources if making factual claims):"
        counter = self._call_model(system, user_prompt)
        return {"counter_argument": counter, "round": round_number, "personality": personality, "sources_used": sources[:3] if sources else []}

    def generate_debate_feedback(self, user_argument: str, round_number: int, difficulty: str = "medium") -> Dict[str, object]:
        system = f"Debate coach, round {round_number}. Give feedback in MAX 50 words:\n✓ What worked | ✗ Fix this | → Next step\nDifficulty: {difficulty}."
        feedback = self._call_model(system, user_argument)
        return {"round": round_number, "feedback": feedback, "difficulty": difficulty}

    def generate_formal_speech(self, motion: str, side: str, speech_type: str, previous_speeches: list = None, opponent_position: str = None, difficulty: str = "medium", personality: str = "balanced") -> str:
        style = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["balanced"])["style"]
        
        if speech_type == "substantive":
            system = f"{style} Formal debate speech on: '{motion}'. Side: {side.upper()}.\nStructure (MAX 200 words):\n1. Brief formal opening\n2. Define 1 key term\n3. Present 2 arguments with evidence\n4. Conclude\nDifficulty: {difficulty}. Be punchy, not verbose."
            prompt = f"Motion: {motion}\nSide: {side.upper()}\n\nSpeech (200 words max):"
        elif speech_type == "reply":
            system = f"{style} REPLY speech (rebuttal). Motion: '{motion}', Side: {side.upper()}\nMAX 120 words:\n1. Attack opponent's weakest point\n2. Defend your best argument\n3. Conclude why you won\nNO new arguments. Be sharp."
            prev_speeches_text = ""
            if previous_speeches:
                for speech in previous_speeches[-2:]:
                    prev_speeches_text += f"\n{speech['side'].upper()}: {speech['text'][:300]}..."
            prompt = f"Motion: {motion}\nYour side: {side.upper()}\nOpponent's position: {opponent_position or 'See previous speeches'}\nPrevious speeches:{prev_speeches_text}\n\nDeliver your reply speech attacking opponent's points."
        else:
            return ""
        
        return self._call_model(system, prompt)
    
    def respond_to_poi(self, question: str, current_argument: str) -> str:
        system = "You are an expert debater responding to a Point of Information (POI) challenge.\nKeep your response to 15-20 seconds of speaking (~40-50 words).\nBe respectful but assertive in defending your argument."
        prompt = f"Question from opponent: {question}\nYour argument: {current_argument}\n\nRespond briefly to this POI."
        return self._call_model(system, prompt)
    
    def evaluate_formal_speech(self, speech_text: str, speech_type: str, side: str, opponent_context: str = "") -> Dict:
        system = f"You are evaluating a formal debate {speech_type} speech delivered by the {side.upper()} side.\nRate the speech on:\n1. Formal structure and language (0-25)\n2. Argument strength (0-25)\n3. Evidence quality (0-25)\n4. Delivery effectiveness (0-25)\nTotal: 0-100\n\nProvide specific feedback on strengths and areas for improvement."
        prompt = f"Speech type: {speech_type}\nSide: {side.upper()}\nSpeech text:\n{speech_text[:1000]}\n\nOpponent context: {opponent_context[:500] if opponent_context else 'N/A'}\n\nEvaluate this speech and provide a score and feedback."
        
        response = self._call_model(system, prompt)
        score = 60.0
        for line in response.split('\n'):
            if 'score' in line.lower() and any(char.isdigit() for char in line):
                for word in line.split():
                    if word.isdigit():
                        try:
                            score = float(word)
                            if score <= 100:
                                break
                        except:
                            pass
        
        return {"score": min(100, score), "feedback": response, "speech_type": speech_type, "side": side}

    def suggest_rebuttals(self, opponent_argument: str, topic: str = "") -> Dict:
        system = "You are a debate assistant. Given the opponent's argument, suggest 3 SHORT rebuttal angles (max 15 words each). Format: numbered list, no explanations."
        prompt = f"Topic: {topic}\nOpponent says: {opponent_argument}\n\n3 rebuttal angles (15 words each max):"
        response = self._call_model(system, prompt, timeout=10)
        
        suggestions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                clean = line.lstrip('0123456789.-•) ').strip()
                if clean:
                    suggestions.append(clean)
        
        return {"suggestions": suggestions[:3], "opponent_argument": opponent_argument[:100]}

    def analyze_argument_issues(self, argument: str, topic: str = "") -> Dict:
        system = "You are a debate coach analyzing an argument for logical issues. Identify specific problems. For EACH issue found, provide:\n1. The exact quote/phrase that has the issue\n2. The type of issue (fallacy, weak argument, or unsupported claim)\n3. A brief explanation of why it's problematic\n4. A specific suggestion for improvement\n\nFormat:\nISSUE 1:\n- Quote: \"[exact text]\"\n- Type: [Fallacy/Weak Argument/Unsupported Claim]\n- Problem: [explanation]\n- Fix: [suggestion]\n\nIf strong, say 'NO MAJOR ISSUES FOUND' and list 1-2 strengths. Maximum 4 issues."
        prompt = f"Topic: {topic}\n\nArgument to analyze:\n\"{argument}\"\n\nAnalyze this argument for fallacies, weak points, and unsupported claims:"
        
        response = self._call_model(system, prompt, timeout=20)
        
        issues = []
        current_issue = {}
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('ISSUE') or line.startswith('Issue'):
                if current_issue:
                    issues.append(current_issue)
                current_issue = {}
            elif line.startswith('- Quote:') or line.startswith('Quote:'):
                current_issue['matched_text'] = line.split(':', 1)[1].strip().strip('"\'')
            elif line.startswith('- Type:') or line.startswith('Type:'):
                issue_type = line.split(':', 1)[1].strip().lower()
                current_issue['issue_type'] = 'fallacy' if 'fallacy' in issue_type else ('weak_argument' if 'weak' in issue_type else 'unsupported_claim')
                current_issue['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Problem:') or line.startswith('Problem:'):
                current_issue['description'] = line.split(':', 1)[1].strip()
            elif line.startswith('- Fix:') or line.startswith('Fix:'):
                current_issue['suggestion'] = line.split(':', 1)[1].strip()
        
        if current_issue and 'matched_text' in current_issue:
            issues.append(current_issue)
        
        for issue in issues:
            if 'matched_text' in issue:
                pos = argument.lower().find(issue['matched_text'].lower()[:30])
                issue['position'] = {'start': pos, 'end': pos + len(issue.get('matched_text', ''))} if pos != -1 else {'start': 0, 'end': 0}
                issue['severity'] = 'high' if issue.get('issue_type') == 'fallacy' else 'medium'
        
        return {
            "ai_issues": issues[:4],
            "raw_analysis": response,
            "has_issues": 'no major issues' not in response.lower() and len(issues) > 0,
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


# =============================================================================
# DEBATE FLOW ENGINE
# =============================================================================

class DebateFlowEngine:
    """Manages formal debate flow, timing, and rules."""
    
    def __init__(self, config):
        self.config = config
        self.speech_order = config.get_speech_order()
        self.current_speech_index = 0
        self.current_speaker = None
        self.speech_start_time = None
        self.time_warnings_given = set()
    
    def get_current_speech_info(self) -> Dict:
        if self.current_speech_index >= len(self.speech_order):
            return None
        return self.speech_order[self.current_speech_index]
    
    def get_next_speaker(self, user_side: str) -> str:
        current = self.get_current_speech_info()
        if not current:
            return None
        return "user" if current["side"] == user_side else "ai"
    
    def get_time_signals(self, elapsed_seconds: int) -> List[TimeSignal]:
        current = self.get_current_speech_info()
        if not current:
            return []
        
        signals = []
        protected_end = self.config.protected_time
        total_time = current["duration"]
        
        if elapsed_seconds == protected_end and protected_end not in self.time_warnings_given:
            signals.append(TimeSignal(elapsed_seconds, "protected_end", 1))
            self.time_warnings_given.add(protected_end)
        
        if elapsed_seconds == total_time and total_time not in self.time_warnings_given:
            signals.append(TimeSignal(elapsed_seconds, "speech_end", 2))
            self.time_warnings_given.add(total_time)
        
        return signals
    
    def can_accept_poi(self, elapsed_seconds: int) -> bool:
        current = self.get_current_speech_info()
        if not current or not self.config.allow_poi:
            return False
        return elapsed_seconds >= self.config.protected_time
    
    def advance_speech(self) -> Dict:
        self.current_speech_index += 1
        self.time_warnings_given = set()
        self.speech_start_time = datetime.now()
        return self.get_current_speech_info()
    
    def is_debate_complete(self) -> bool:
        return self.current_speech_index >= len(self.speech_order)
    
    def get_debate_progress(self) -> Dict:
        return {
            "current_speech": self.current_speech_index + 1,
            "total_speeches": len(self.speech_order),
            "progress_percent": round((self.current_speech_index / len(self.speech_order)) * 100, 1) if self.speech_order else 0
        }


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


class SpeechAnalyzer:
    """Analyzes speeches for formal debate requirements."""
    
    @staticmethod
    def analyze_formality(speech_text: str) -> Dict:
        """Analyze speech for formal debate language."""
        analysis = {"formality_score": 0.0, "issues": [], "strengths": []}
        
        if any(greeting in speech_text.lower() for greeting in ["honorable", "mr.", "madam", "chair"]):
            analysis["strengths"].append("Uses formal greeting/address")
        else:
            analysis["issues"].append("Missing formal address")
        
        structure_markers = ["firstly", "secondly", "finally", "therefore", "thus", "in conclusion"]
        marker_count = sum(1 for marker in structure_markers if marker in speech_text.lower())
        if marker_count >= 2:
            analysis["strengths"].append("Logical structure with clear transitions")
        else:
            analysis["issues"].append("Weak logical structure")
        
        if any(marker in speech_text for marker in ["according to", "data shows", "research indicates", "statistics"]):
            analysis["strengths"].append("Cites evidence/research")
        else:
            analysis["issues"].append("No evidence cited")
        
        score = len(analysis["strengths"]) * 0.33 - len(analysis["issues"]) * 0.2
        analysis["formality_score"] = max(0, min(100, score * 25))
        return analysis
    
    @staticmethod
    def check_rebuttal_focus(current_speech: str, previous_opponent_speech: str) -> Dict:
        """Check if rebuttal focuses on opponent's arguments."""
        opponent_keywords = {word for word in previous_opponent_speech.lower().split() if len(word) > 5}
        current_words = current_speech.lower().split()
        
        addressed_keywords = sum(1 for word in current_words if word in opponent_keywords)
        total_keywords = len(opponent_keywords)
        focus_percentage = (addressed_keywords / total_keywords * 100) if total_keywords > 0 else 0
        
        return {
            "rebuttal_focus": focus_percentage,
            "addressed_keywords": addressed_keywords,
            "total_opponent_keywords": total_keywords,
            "adequately_rebuts": focus_percentage > 30
        }
