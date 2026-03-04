# Re-export from consolidated services module for backwards compatibility
# This allows existing imports like:
#   from .services.agent import from_settings
#   from .services.analysis import analyze_argument
# to continue working

# The main services are now in trainer/_services_core.py
# These files are kept for backwards compatibility but may be removed in future

from .._services_core import (
    # Agent
    AgenticDebateAgent,
    from_settings,
    AI_PERSONALITIES,
    # Analysis
    analyze_argument,
    analyze_argument_detailed,
    detect_fallacies,
    detect_strengths,
    AnalysisResult,
    DetailedAnalysisResult,
    FALLACY_PATTERNS,
    FALLACY_DISPLAY_NAMES,
    # Research
    get_research_context,
    get_reference_sources,
    ScholarResearcher,
    REFERENCE_SOURCES,
    # Debate Flow
    DebateFlowEngine,
    SpeechAnalyzer,
    TimeSignal,
    POIRequest,
)

__all__ = [
    'AgenticDebateAgent',
    'from_settings',
    'AI_PERSONALITIES',
    'analyze_argument',
    'analyze_argument_detailed',
    'detect_fallacies',
    'detect_strengths',
    'AnalysisResult',
    'DetailedAnalysisResult',
    'FALLACY_PATTERNS',
    'FALLACY_DISPLAY_NAMES',
    'get_research_context',
    'get_reference_sources',
    'ScholarResearcher',
    'REFERENCE_SOURCES',
    'DebateFlowEngine',
    'SpeechAnalyzer',
    'TimeSignal',
    'POIRequest',
]


