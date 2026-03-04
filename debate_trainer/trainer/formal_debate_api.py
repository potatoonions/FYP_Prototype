"""
REST API endpoints for formal debate competitions.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import uuid
import logging

from .models import FormalDebateConfig, FormalDebateSession
from .services import from_settings, DebateFlowEngine, SpeechAnalyzer
from .validators import validate_json_payload, validate_string_field
from .rate_limit import rate_limit

logger = logging.getLogger("trainer.formal_debate_api")


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@csrf_exempt
@rate_limit(requests_per_minute=20)
@require_http_methods(["POST"])
def create_formal_debate(request):
    """Create a new formal debate configuration and session."""
    payload, error = validate_json_payload(request)
    if error:
        return error
    
    try:
        # Parse motion
        motion, error = validate_string_field(payload.get("motion"), "motion", required=True)
        if error:
            return error
        
        user_name, error = validate_string_field(payload.get("user_name"), "user_name", required=False)
        user_name = user_name or "Anonymous"
        
        # Parse config
        format_type = payload.get("format_type", "custom")
        speakers_per_side = payload.get("speakers_per_side", 2)
        substantive_time = payload.get("substantive_time", 480)  # 8 min
        reply_time = payload.get("reply_time", 240)  # 4 min
        include_replies = payload.get("include_replies", True)
        allow_poi = payload.get("allow_poi", True)
        no_new_args = payload.get("no_new_arguments", True)
        
        # Validate numbers
        if not isinstance(speakers_per_side, int) or speakers_per_side < 1 or speakers_per_side > 10:
            return _json_error("speakers_per_side must be 1-10")
        if not isinstance(substantive_time, int) or substantive_time < 60:
            return _json_error("substantive_time must be >= 60 seconds")
        if not isinstance(reply_time, int) or reply_time < 30:
            return _json_error("reply_time must be >= 30 seconds")
        
        # Create config
        config = FormalDebateConfig.objects.create(
            format_type=format_type,
            motion=motion,
            speakers_per_side=speakers_per_side,
            substantive_speech_time=substantive_time,
            reply_speech_time=reply_time,
            include_replies=include_replies,
            allow_poi=allow_poi,
            no_new_arguments_in_rebuttal=no_new_args
        )
        
        # Determine sides
        user_side = payload.get("user_side", "affirmative")
        if user_side not in ["affirmative", "negative"]:
            user_side = "affirmative"
        ai_side = "negative" if user_side == "affirmative" else "affirmative"
        
        # Create session
        session_id = str(uuid.uuid4())
        session = FormalDebateSession.objects.create(
            config=config,
            session_id=session_id,
            user_name=user_name,
            user_side=user_side,
            ai_side=ai_side,
            status="not_started"
        )
        
        logger.info(f"Created formal debate session {session_id} for {user_name}")
        
        return JsonResponse({
            "session_id": session_id,
            "motion": motion,
            "user_side": user_side,
            "ai_side": ai_side,
            "speakers_per_side": speakers_per_side,
            "total_speeches": len(config.get_speech_order()),
            "speech_order_summary": {
                "substantive_per_side": speakers_per_side,
                "reply_speeches": 2 if include_replies else 0,
                "total": len(config.get_speech_order())
            },
            "timing": {
                "substantive_seconds": substantive_time,
                "reply_seconds": reply_time,
                "total_estimated_minutes": round((substantive_time * speakers_per_side * 2 + (reply_time * 2 if include_replies else 0)) / 60, 1)
            }
        }, status=201)
    
    except Exception as e:
        logger.error(f"Error creating formal debate: {str(e)}", exc_info=True)
        return _json_error(f"Server error: {str(e)}", status=500)


@csrf_exempt
@rate_limit(requests_per_minute=100)
@require_http_methods(["POST"])
def start_formal_debate(request):
    """Start a formal debate session (AI gives first speech)."""
    payload, error = validate_json_payload(request)
    if error:
        return error
    
    try:
        session_id = payload.get("session_id")
        if not session_id:
            return _json_error("session_id required")
        
        try:
            session = FormalDebateSession.objects.get(session_id=session_id)
        except FormalDebateSession.DoesNotExist:
            return _json_error("Session not found", status=404)
        
        if session.status != "not_started":
            return _json_error(f"Cannot start debate with status: {session.status}")
        
        # Get AI agent
        from django.conf import settings
        agent = from_settings(settings)
        
        # Generate opening speech for AI
        current_speech_info = session.config.get_speech_order()[0]
        ai_speaker_side = current_speech_info["side"]
        
        # AI gives first speech
        opening_speech = agent.generate_formal_speech(
            motion=session.config.motion,
            side=ai_speaker_side,
            speech_type="substantive",
            difficulty="medium"
        )
        
        # Update session
        session.status = "in_progress"
        session.started_at = timezone.now()
        session.speeches.append({
            "speaker": "ai",
            "side": ai_speaker_side,
            "type": "substantive",
            "content": opening_speech,
            "time_taken": 0,
            "pois_received": [],
            "timestamp": timezone.now().isoformat()
        })
        session.current_speaker_index = 0
        session.save()
        
        logger.info(f"Started formal debate session {session_id}")
        
        return JsonResponse({
            "session_id": session_id,
            "status": "in_progress",
            "current_speaker": "ai",
            "current_speaker_side": ai_speaker_side,
            "ai_opening_speech": opening_speech,
            "timing": {
                "speech_duration_seconds": session.config.substantive_speech_time,
                "speech_duration_readable": f"{session.config.substantive_speech_time // 60} minutes"
            },
            "next_speaker": "user",
            "message": "AI has delivered opening speech. Prepare your response."
        })
    
    except Exception as e:
        logger.error(f"Error starting formal debate: {str(e)}", exc_info=True)
        return _json_error(f"Server error: {str(e)}", status=500)


@csrf_exempt
@rate_limit(requests_per_minute=100)
@require_http_methods(["POST"])
def submit_formal_speech(request):
    """Submit a user speech and get AI evaluation + next speech."""
    payload, error = validate_json_payload(request)
    if error:
        return error
    
    try:
        session_id = payload.get("session_id")
        speech_text, error = validate_string_field(payload.get("speech"), "speech", required=True)
        if error:
            return error
        
        time_taken = payload.get("time_taken", 0)  # seconds
        pois_received = payload.get("pois_received", [])
        
        try:
            session = FormalDebateSession.objects.get(session_id=session_id)
        except FormalDebateSession.DoesNotExist:
            return _json_error("Session not found", status=404)
        
        if session.status != "in_progress":
            return _json_error(f"Debate not in progress (status: {session.status})")
        
        # Get current speech info
        current_index = session.current_speaker_index
        speech_order = session.config.get_speech_order()
        
        if current_index >= len(speech_order):
            return _json_error("Debate already completed")
        
        current_speech_info = speech_order[current_index]
        
        # Validate this is user's turn
        expected_side = current_speech_info["side"]
        if expected_side != session.user_side:
            return _json_error(f"It's not your turn! Expected {current_speech_info['side']} speaker.")
        
        # Get AI agent
        from django.conf import settings
        agent = from_settings(settings)
        
        # Analyze user's speech
        analyzer = SpeechAnalyzer()
        formality = analyzer.analyze_formality(speech_text)
        
        # For rebuttal speeches, check if new arguments were introduced
        validation = session.config.validate_new_arguments(current_speech_info["type"], speech_text)
        
        # Record user speech
        user_speech_record = {
            "speaker": "user",
            "side": session.user_side,
            "type": current_speech_info["type"],
            "content": speech_text,
            "time_taken": time_taken,
            "pois_received": pois_received,
            "timestamp": timezone.now().isoformat(),
            "formality_score": formality["formality_score"],
            "issues": formality["issues"],
            "argument_validation": validation
        }
        session.speeches.append(user_speech_record)
        session.user_score += formality["formality_score"] * 0.5  # Formality counts for 50%
        
        # Move to next speech
        session.current_speaker_index += 1
        
        # Check if debate is complete
        if session.current_speaker_index >= len(speech_order):
            session.status = "completed"
            session.ended_at = timezone.now()
            session.save()
            
            return JsonResponse({
                "session_id": session_id,
                "status": "completed",
                "message": "Debate completed!",
                "scores": {
                    "user_score": round(session.user_score, 1),
                    "ai_score": round(session.ai_score, 1)
                },
                "user_speech_feedback": {
                    "formality": formality,
                    "validation": validation,
                    "time_used": time_taken
                }
            })
        
        # Get next speech info
        next_speech_info = speech_order[session.current_speaker_index]
        next_speaker_side = next_speech_info["side"]
        is_user_next = next_speaker_side == session.user_side
        
        # Generate AI speech if it's AI's turn
        ai_speech = ""
        if not is_user_next:
            # Get opponent's most recent speech for context
            opponent_speeches = [s["content"] for s in session.speeches if s["speaker"] != "ai"]
            opponent_context = opponent_speeches[-1] if opponent_speeches else ""
            
            ai_speech = agent.generate_formal_speech(
                motion=session.config.motion,
                side=next_speaker_side,
                speech_type=next_speech_info["type"],
                previous_speeches=session.speeches,
                opponent_position=opponent_context,
                difficulty="medium"
            )
            
            # Evaluate the speech
            ai_eval = agent.evaluate_formal_speech(
                ai_speech,
                next_speech_info["type"],
                next_speaker_side,
                opponent_context
            )
            session.ai_score += ai_eval["score"] * 0.5
            
            # Record AI speech
            session.speeches.append({
                "speaker": "ai",
                "side": next_speaker_side,
                "type": next_speech_info["type"],
                "content": ai_speech,
                "time_taken": 0,
                "pois_received": [],
                "timestamp": timezone.now().isoformat(),
                "evaluation": ai_eval
            })
            
            session.current_speaker_index += 1
        
        session.save()
        
        # Prepare response
        progress = session.config.get_speech_order()
        current_progress = (session.current_speaker_index / len(progress)) * 100
        
        return JsonResponse({
            "session_id": session_id,
            "status": "in_progress",
            "user_speech_feedback": {
                "formality": formality,
                "validation": validation,
                "time_used": time_taken
            },
            "next_speaker": "user" if is_user_next else "ai",
            "next_speaker_side": next_speaker_side if is_user_next else session.ai_side,
            "next_speech_type": next_speech_info["type"],
            "ai_speech": ai_speech if not is_user_next else None,
            "progress": {
                "completed_speeches": session.current_speaker_index,
                "total_speeches": len(progress),
                "percent_complete": round(current_progress, 1)
            },
            "current_scores": {
                "user_score": round(session.user_score, 1),
                "ai_score": round(session.ai_score, 1)
            }
        })
    
    except Exception as e:
        logger.error(f"Error submitting formal speech: {str(e)}", exc_info=True)
        return _json_error(f"Server error: {str(e)}", status=500)


@csrf_exempt
@rate_limit(requests_per_minute=50)
@require_http_methods(["GET"])
def get_formal_debate_status(request):
    """Get current status of a formal debate session."""
    session_id = request.GET.get("session_id")
    if not session_id:
        return _json_error("session_id required")
    
    try:
        session = FormalDebateSession.objects.get(session_id=session_id)
    except FormalDebateSession.DoesNotExist:
        return _json_error("Session not found", status=404)
    
    speech_order = session.config.get_speech_order()
    
    return JsonResponse({
        "session_id": session_id,
        "motion": session.config.motion,
        "status": session.status,
        "user_side": session.user_side,
        "ai_side": session.ai_side,
        "progress": {
            "completed_speeches": session.current_speaker_index,
            "total_speeches": len(speech_order),
            "percent_complete": round((session.current_speaker_index / len(speech_order)) * 100, 1)
        },
        "scores": {
            "user_score": round(session.user_score, 1),
            "ai_score": round(session.ai_score, 1)
        },
        "speech_count": len(session.speeches),
        "created_at": session.created_at.isoformat(),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None
    })
