from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_GET, require_http_methods
from django.core.cache import cache

from .models import DebateSession, DebateRound
from .services import from_settings, analyze_argument, analyze_argument_detailed, analyze_argument_with_ml, get_research_context, get_reference_sources
from .validators import (
    validate_json_payload,
    validate_string_field,
    validate_difficulty,
    validate_limit,
)
from .rate_limit import rate_limit

logger = logging.getLogger("trainer")


def _json_error(message: str, status: int = 400) -> JsonResponse:
    """Helper to return JSON errors."""
    return JsonResponse({"error": message}, status=status)


@require_GET
def home_view(request: HttpRequest) -> HttpResponse:
    """API documentation page (accessible at /api-docs/)."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Debate Trainer API</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }
            .container { background: white; border-radius: 12px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            h1 { color: #667eea; margin-top: 0; font-size: 2.2em; }
            h2 { color: #764ba2; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #667eea; }
            .method { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85em; margin-right: 10px; color: white; }
            .method.post { background: #28a745; }
            .method.get { background: #007bff; }
            code { background: #e9ecef; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
            pre { background: #f8f9fa; padding: 12px; border-radius: 6px; overflow-x: auto; }
            .links { margin-top: 30px; padding-top: 20px; border-top: 2px solid #eee; }
            .links a { color: #667eea; text-decoration: none; margin-right: 20px; font-weight: 500; }
            .links a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 AI Debate Trainer API</h1>
            <p>Multi-turn debate with AI research integration and real-time scoring.</p>
            
            <h2>Core Endpoints</h2>
            
            <div class="endpoint">
                <span class="method post">POST</span> <strong>/api/debate/start/</strong>
                <p>Initialize a debate session with research and AI opening position.</p>
                <pre><code>{ "topic": "AI Ethics", "user_name": "John", "difficulty": "medium" }</code></pre>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span> <strong>/api/debate/response/</strong>
                <p>Submit your response and get AI counter-argument with feedback.</p>
                <pre><code>{ "session_id": "...", "response": "Your argument..." }</code></pre>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span> <strong>/api/debate/end/</strong>
                <p>End debate and get final summary.</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/api/debate/history/?session_id=...</strong>
                <p>Retrieve complete debate history and scores.</p>
            </div>
            
            <div class="links">
                <strong>Quick Links:</strong>
                <a href="/">🎮 Start Debate</a>
                <a href="/admin/">⚙️ Admin</a>
                <a href="/api/formal/">🏆 Formal Debate</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)


# ============================================================================
# Multi-turn Debate Flow Endpoints (Core API)
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@rate_limit(requests_per_minute=10)  # 10 debates per minute (research is expensive)
def start_debate(request: HttpRequest) -> JsonResponse:
    """Start a new multi-turn debate with AI research and opening position."""
    payload, error = validate_json_payload(request)
    if error:
        logger.warning("Invalid JSON payload in start_debate")
        return error

    topic, error = validate_string_field(
        payload.get("topic"), "topic", max_length=255, min_length=3
    )
    if error:
        return error

    user_name, error = validate_string_field(
        payload.get("user_name"), "user_name", max_length=100, required=False
    )
    if error:
        return error
    user_name = user_name or "anonymous"

    difficulty, error = validate_difficulty(payload.get("difficulty", "medium"))
    if error:
        return error

    # Create a unique session ID
    session_id = str(uuid.uuid4())

    try:
        # Check cache for research (lightweight caching)
        cache_key = f"research:{topic.lower()}"
        research = cache.get(cache_key)
        
        if research is None:
            logger.info(f"Fetching research for topic: {topic}")
            research = get_research_context(topic, max_results=5)
            # Cache for 1 hour (research is expensive)
            cache.set(cache_key, research, timeout=3600)
        else:
            logger.debug(f"Using cached research for topic: {topic}")

        # Get curated reference sources for the topic
        reference_sources = get_reference_sources(topic)
        
        research_summary = research.get("summary", "")

        # Generate AI's opening position with sources
        agent = from_settings(settings)
        ai_position_result = agent.generate_opening_position(
            topic, 
            research_summary, 
            difficulty,
            sources=reference_sources
        )
        
        # Handle both old string return and new dict return for backwards compatibility
        if isinstance(ai_position_result, dict):
            ai_position = ai_position_result.get("text", str(ai_position_result))
            sources_used = ai_position_result.get("sources_used", reference_sources)
        else:
            ai_position = ai_position_result
            sources_used = reference_sources

        # Create debate round record
        debate_round = DebateRound.objects.create(
            session_id=session_id,
            user_name=user_name,
            topic=topic,
            ai_position=ai_position,
            research_summary=research,
            round_type="ai_opening",
            difficulty=difficulty,
            conversation=[
                {
                    "role": "ai",
                    "content": ai_position,
                    "round": 1,
                    "type": "opening",
                    "sources": sources_used
                }
            ],
        )
        
        # Store reference sources in the session for later use
        debate_round.research_summary["reference_sources"] = reference_sources
        debate_round.save()

        logger.info(f"Started debate session {session_id} for user {user_name} on topic {topic}")

        response = {
            "session_id": session_id,
            "topic": topic,
            "ai_opening_position": ai_position,
            "research_context": {
                "papers_found": research.get("papers_found", 0),
                "summary": research_summary,
            },
            "reference_sources": sources_used,
            "difficulty": difficulty,
            "current_round": 1,
        }
        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Error starting debate: {str(e)}", exc_info=True)
        return _json_error("An error occurred starting the debate", status=500)


@csrf_exempt
@require_http_methods(["POST"])
@rate_limit(requests_per_minute=60)  # 60 responses per minute
def submit_user_response(request: HttpRequest) -> JsonResponse:
    """Submit user response and get AI counter-argument."""
    payload, error = validate_json_payload(request)
    if error:
        logger.warning("Invalid JSON payload in submit_user_response")
        return error

    session_id, error = validate_string_field(
        payload.get("session_id"), "session_id", max_length=100
    )
    if error:
        return error

    user_response, error = validate_string_field(
        payload.get("response"), "response", max_length=5000, min_length=10
    )
    if error:
        return error

    try:
        # Get the debate round - fetch only needed fields for performance
        try:
            debate_round = DebateRound.objects.only(
                'session_id', 'topic', 'ai_position', 'research_summary',
                'current_round', 'difficulty', 'conversation', 'is_active',
                'ai_feedbacks', 'scores', 'overall_score'
            ).get(session_id=session_id)
        except DebateRound.DoesNotExist:
            logger.warning(f"Debate session not found: {session_id}")
            return _json_error("Debate session not found", status=404)

        if not debate_round.is_active:
            logger.info(f"Attempted response to ended debate session: {session_id}")
            return _json_error("Debate session has ended", status=400)

        # Analyze user's argument (rule-based)
        analysis = analyze_argument(user_response).as_dict()
        
        # Perform detailed analysis for highlighting issues
        detailed_analysis = analyze_argument_detailed(user_response).as_dict()
        
        # ML-enhanced analysis (combines rule-based + neural network)
        # Wrapped in try-except to not break debate if ML fails
        try:
            ml_analysis = analyze_argument_with_ml(user_response, use_ml=True)
        except Exception as ml_error:
            logger.warning(f"ML analysis failed: {ml_error}")
            ml_analysis = {
                "ml_available": False,
                "combined_score": analysis["score"],
                "error": str(ml_error)
            }

        # Add user response to conversation
        current_round = debate_round.current_round
        debate_round.conversation.append({
            "role": "user",
            "content": user_response,
            "round": current_round,
            "analysis": analysis,
            "detailed_analysis": detailed_analysis,
        })

        # Get reference sources from the session
        reference_sources = debate_round.research_summary.get("reference_sources", [])

        # Generate AI counter-argument with sources
        agent = from_settings(settings)
        counter_response = agent.generate_counter_response(
            debate_round.topic,
            debate_round.ai_position,
            user_response,
            current_round,
            debate_round.difficulty,
            sources=reference_sources
        )

        # Get feedback on user's argument
        feedback = agent.generate_debate_feedback(
            user_response,
            current_round,
            debate_round.difficulty
        )
        
        # Get AI-powered issue analysis (optional - can be slow)
        ai_critique = {}
        try:
            ai_critique = agent.analyze_argument_issues(user_response, debate_round.topic)
        except Exception as e:
            logger.debug(f"AI critique failed: {str(e)}")
            ai_critique = {"ai_issues": [], "has_issues": False}

        # Extract counter argument text (handle both dict and string returns)
        counter_text = counter_response.get("counter_argument", str(counter_response)) if isinstance(counter_response, dict) else counter_response
        sources_used = counter_response.get("sources_used", reference_sources) if isinstance(counter_response, dict) else reference_sources

        # Add AI counter to conversation
        debate_round.conversation.append({
            "role": "ai",
            "content": counter_text,
            "round": current_round + 1,
            "type": "counter",
            "sources": sources_used
        })

        # Store feedback and scores
        debate_round.ai_feedbacks[str(current_round)] = feedback
        debate_round.scores[str(current_round)] = analysis["score"]

        # Update round
        debate_round.current_round = current_round + 1
        debate_round.round_type = "ai_counter"
        debate_round.save()

        # Calculate running average score
        scores = [float(s) for s in debate_round.scores.values()]
        overall_score = round(sum(scores) / len(scores) * 100, 1) if scores else 0.0
        debate_round.overall_score = overall_score
        debate_round.save()

        logger.info(
            f"Processed response for session {session_id}, round {current_round}, score: {overall_score}"
        )

        response = {
            "session_id": session_id,
            "round": current_round,
            "user_analysis": analysis,
            "detailed_analysis": detailed_analysis,
            "ml_analysis": ml_analysis,
            "ai_critique": ai_critique,
            "ai_counter_argument": counter_text,
            "coach_feedback": feedback["feedback"],
            "current_score": round(analysis["score"] * 100, 1),
            "ml_score": round(ml_analysis.get("combined_score", analysis["score"]) * 100, 1),
            "overall_score": overall_score,
            "next_round": current_round + 1,
            "sources_cited": sources_used,
        }
        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Error processing response: {str(e)}", exc_info=True)
        return _json_error("An error occurred processing your response", status=500)


@csrf_exempt
@require_http_methods(["POST"])
def end_debate(request: HttpRequest) -> JsonResponse:
    """End a debate session and get final summary."""
    payload, error = validate_json_payload(request)
    if error:
        logger.warning("Invalid JSON payload in end_debate")
        return error

    session_id, error = validate_string_field(
        payload.get("session_id"), "session_id", max_length=100
    )
    if error:
        return error

    try:
        try:
            debate_round = DebateRound.objects.only(
                'session_id', 'is_active', 'current_round', 'overall_score',
                'topic', 'user_name', 'difficulty', 'conversation', 'research_summary'
            ).get(session_id=session_id)
        except DebateRound.DoesNotExist:
            logger.warning(f"Attempted to end non-existent debate session: {session_id}")
            return _json_error("Debate session not found", status=404)

        debate_round.is_active = False
        debate_round.save()

        logger.info(
            f"Ended debate session {session_id}, rounds: {debate_round.current_round - 1}, "
            f"score: {debate_round.overall_score}"
        )

        # Prepare final summary
        response = {
            "session_id": session_id,
            "topic": debate_round.topic,
            "user_name": debate_round.user_name,
            "total_rounds": debate_round.current_round - 1,
            "overall_score": debate_round.overall_score,
            "difficulty": debate_round.difficulty,
            "conversation_length": len(debate_round.conversation),
            "research_used": {
                "papers_found": debate_round.research_summary.get("papers_found", 0),
                "sources": len(debate_round.research_summary.get("papers", [])),
            }
        }
        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Error ending debate: {str(e)}", exc_info=True)
        return _json_error("An error occurred ending the debate", status=500)


@require_GET
def get_debate_history(request: HttpRequest) -> JsonResponse:
    """Get debate round history for a session."""
    session_id = request.GET.get("session_id")

    if not session_id:
        return _json_error("`session_id` is required")

    try:
        try:
            debate_round = DebateRound.objects.only(
                'session_id', 'topic', 'user_name', 'difficulty',
                'overall_score', 'current_round', 'conversation',
                'ai_feedbacks', 'scores', 'is_active', 'created_at'
            ).get(session_id=session_id)
        except DebateRound.DoesNotExist:
            logger.warning(f"History requested for non-existent session: {session_id}")
            return _json_error("Debate session not found", status=404)

        response = {
            "session_id": session_id,
            "topic": debate_round.topic,
            "user_name": debate_round.user_name,
            "difficulty": debate_round.difficulty,
            "overall_score": debate_round.overall_score,
            "total_rounds": debate_round.current_round - 1,
            "conversation": debate_round.conversation,
            "feedbacks": debate_round.ai_feedbacks,
            "scores": {k: round(float(v) * 100, 1) for k, v in debate_round.scores.items()},
            "is_active": debate_round.is_active,
            "created_at": debate_round.created_at.isoformat(),
        }
        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}", exc_info=True)
        return _json_error("An error occurred retrieving debate history", status=500)


