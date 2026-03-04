"""
REST API endpoints for gamification, analytics, and leaderboard.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.db.models import Avg, Count, Sum, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import json
import logging

from .models import UserProfile, DebateRound, FormalDebateSession
from .validators import validate_json_payload, validate_string_field
from .rate_limit import rate_limit
from .services.agent import AI_PERSONALITIES

logger = logging.getLogger("trainer.gamification")


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


# ============================================================================
# Gamification Endpoints
# ============================================================================

@require_GET
def get_user_profile(request):
    """Get or create user profile with XP, level, badges."""
    user_name = request.GET.get("user_name", "Anonymous")
    
    profile, created = UserProfile.objects.get_or_create(
        user_name=user_name,
        defaults={"xp": 0, "level": 1}
    )
    
    # Check for new badges
    new_badges = profile.check_and_award_badges()
    
    # Calculate XP for next level
    next_level_xp = profile.xp_for_level(profile.level + 1)
    current_level_xp = profile.xp_for_level(profile.level)
    xp_progress = profile.xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    
    return JsonResponse({
        "user_name": profile.user_name,
        "xp": profile.xp,
        "level": profile.level,
        "xp_progress": xp_progress,
        "xp_needed": xp_needed,
        "progress_percent": round((xp_progress / xp_needed) * 100, 1) if xp_needed > 0 else 100,
        "total_debates": profile.total_debates,
        "debates_won": profile.debates_won,
        "win_rate": profile.win_rate,
        "average_score": profile.average_score,
        "highest_score": profile.highest_score,
        "current_streak": profile.current_streak,
        "longest_streak": profile.longest_streak,
        "badges": profile.badges,
        "new_badges": new_badges,
        "daily_challenge_completed": profile.daily_challenge_completed and profile.daily_challenge_date == timezone.now().date(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def award_xp(request):
    """Award XP to user after completing a debate."""
    payload, error = validate_json_payload(request)
    if error:
        return error
    
    user_name = payload.get("user_name", "Anonymous")
    xp_amount = payload.get("xp", 0)
    score = payload.get("score", 0)
    won = payload.get("won", False)
    
    profile, _ = UserProfile.objects.get_or_create(
        user_name=user_name,
        defaults={"xp": 0, "level": 1}
    )
    
    # Update stats
    profile.total_debates += 1
    if won:
        profile.debates_won += 1
    profile.total_score += score
    if score > profile.highest_score:
        profile.highest_score = score
    
    # Update streak
    today = timezone.now().date()
    if profile.last_debate_date:
        if profile.last_debate_date == today - timedelta(days=1):
            profile.current_streak += 1
        elif profile.last_debate_date != today:
            profile.current_streak = 1
    else:
        profile.current_streak = 1
    
    if profile.current_streak > profile.longest_streak:
        profile.longest_streak = profile.current_streak
    
    profile.last_debate_date = today
    
    # Calculate and add XP
    base_xp = xp_amount if xp_amount > 0 else 50
    streak_bonus = min(profile.current_streak * 5, 25)  # Max 25 bonus
    win_bonus = 20 if won else 0
    total_xp = base_xp + streak_bonus + win_bonus
    
    old_level = profile.level
    profile.add_xp(total_xp)
    
    # Check for new badges
    new_badges = profile.check_and_award_badges()
    
    return JsonResponse({
        "user_name": profile.user_name,
        "xp_awarded": total_xp,
        "breakdown": {
            "base": base_xp,
            "streak_bonus": streak_bonus,
            "win_bonus": win_bonus,
        },
        "new_xp": profile.xp,
        "level": profile.level,
        "leveled_up": profile.level > old_level,
        "new_badges": new_badges,
        "current_streak": profile.current_streak,
    })


@require_GET
def get_daily_challenge(request):
    """Get today's daily challenge topic."""
    # Rotating daily challenges
    DAILY_CHALLENGES = [
        {"topic": "Social media does more harm than good", "difficulty": "medium"},
        {"topic": "Artificial intelligence will replace most jobs", "difficulty": "hard"},
        {"topic": "Climate change is the biggest threat to humanity", "difficulty": "medium"},
        {"topic": "Universal basic income should be implemented", "difficulty": "hard"},
        {"topic": "Education should be free for everyone", "difficulty": "easy"},
        {"topic": "Space exploration is worth the cost", "difficulty": "medium"},
        {"topic": "Genetic engineering should be regulated", "difficulty": "hard"},
    ]
    
    # Use day of year to rotate
    day_index = timezone.now().timetuple().tm_yday % len(DAILY_CHALLENGES)
    challenge = DAILY_CHALLENGES[day_index]
    
    user_name = request.GET.get("user_name")
    completed = False
    if user_name:
        try:
            profile = UserProfile.objects.get(user_name=user_name)
            completed = profile.daily_challenge_completed and profile.daily_challenge_date == timezone.now().date()
        except UserProfile.DoesNotExist:
            pass
    
    return JsonResponse({
        "challenge": challenge,
        "bonus_xp": 50,
        "completed": completed,
        "date": timezone.now().date().isoformat(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def complete_daily_challenge(request):
    """Mark daily challenge as completed."""
    payload, error = validate_json_payload(request)
    if error:
        return error
    
    user_name = payload.get("user_name", "Anonymous")
    
    profile, _ = UserProfile.objects.get_or_create(
        user_name=user_name,
        defaults={"xp": 0, "level": 1}
    )
    
    today = timezone.now().date()
    if profile.daily_challenge_completed and profile.daily_challenge_date == today:
        return JsonResponse({"already_completed": True, "xp_awarded": 0})
    
    profile.daily_challenge_completed = True
    profile.daily_challenge_date = today
    profile.add_xp(50)  # Daily challenge bonus
    profile.save()
    
    return JsonResponse({
        "completed": True,
        "xp_awarded": 50,
        "new_xp": profile.xp,
        "level": profile.level,
    })


# ============================================================================
# Leaderboard Endpoints
# ============================================================================

@require_GET
def get_leaderboard(request):
    """Get global leaderboard."""
    timeframe = request.GET.get("timeframe", "all")  # all, week, month
    limit = int(request.GET.get("limit", 10))
    
    profiles = UserProfile.objects.all()
    
    if timeframe == "week":
        week_ago = timezone.now().date() - timedelta(days=7)
        profiles = profiles.filter(last_debate_date__gte=week_ago)
    elif timeframe == "month":
        month_ago = timezone.now().date() - timedelta(days=30)
        profiles = profiles.filter(last_debate_date__gte=month_ago)
    
    # Order by XP
    profiles = profiles.order_by("-xp")[:limit]
    
    leaderboard = []
    for rank, profile in enumerate(profiles, 1):
        leaderboard.append({
            "rank": rank,
            "user_name": profile.user_name,
            "xp": profile.xp,
            "level": profile.level,
            "total_debates": profile.total_debates,
            "win_rate": profile.win_rate,
            "current_streak": profile.current_streak,
            "badges_count": len(profile.badges),
        })
    
    return JsonResponse({"leaderboard": leaderboard, "timeframe": timeframe})


@require_GET
def get_user_rank(request):
    """Get specific user's rank on leaderboard."""
    user_name = request.GET.get("user_name")
    if not user_name:
        return _json_error("user_name is required")
    
    try:
        profile = UserProfile.objects.get(user_name=user_name)
    except UserProfile.DoesNotExist:
        return _json_error("User not found", status=404)
    
    # Count users with more XP
    rank = UserProfile.objects.filter(xp__gt=profile.xp).count() + 1
    total_users = UserProfile.objects.count()
    
    return JsonResponse({
        "user_name": profile.user_name,
        "rank": rank,
        "total_users": total_users,
        "percentile": round((1 - (rank / total_users)) * 100, 1) if total_users > 0 else 100,
        "xp": profile.xp,
        "level": profile.level,
    })


# ============================================================================
# Analytics Endpoints
# ============================================================================

@require_GET
def get_user_analytics(request):
    """Get detailed analytics for a user."""
    user_name = request.GET.get("user_name")
    if not user_name:
        return _json_error("user_name is required")
    
    # Get all user's debate rounds
    debates = DebateRound.objects.filter(user_name=user_name).order_by("-created_at")
    
    if not debates.exists():
        return JsonResponse({
            "user_name": user_name,
            "has_data": False,
            "message": "No debate history found"
        })
    
    # Score progression over time
    score_history = []
    for debate in debates[:20]:  # Last 20 debates
        score_history.append({
            "date": debate.created_at.isoformat(),
            "topic": debate.topic[:30],
            "score": debate.overall_score,
            "difficulty": debate.difficulty,
        })
    
    # Aggregate stats
    total_debates = debates.count()
    avg_score = debates.aggregate(avg=Avg("overall_score"))["avg"] or 0
    
    # Fallacy analysis from conversation data
    fallacy_counts = {}
    for debate in debates:
        for msg in debate.conversation:
            if msg.get("role") == "user" and msg.get("analysis"):
                for fallacy in msg["analysis"].get("fallacies", []):
                    fallacy_counts[fallacy] = fallacy_counts.get(fallacy, 0) + 1
    
    # Scores by difficulty
    difficulty_stats = {}
    for difficulty in ["easy", "medium", "hard"]:
        diff_debates = debates.filter(difficulty=difficulty)
        if diff_debates.exists():
            difficulty_stats[difficulty] = {
                "count": diff_debates.count(),
                "avg_score": round(diff_debates.aggregate(avg=Avg("overall_score"))["avg"] or 0, 1),
            }
    
    # Activity heatmap (debates per day for last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    activity = debates.filter(created_at__gte=thirty_days_ago).annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(count=Count("id")).order_by("date")
    
    return JsonResponse({
        "user_name": user_name,
        "has_data": True,
        "summary": {
            "total_debates": total_debates,
            "average_score": round(avg_score, 1),
            "best_score": debates.order_by("-overall_score").first().overall_score if debates.exists() else 0,
        },
        "score_history": score_history,
        "fallacy_counts": fallacy_counts,
        "difficulty_stats": difficulty_stats,
        "activity_heatmap": list(activity),
    })


@require_GET
def get_skill_radar(request):
    """Get skill radar data for visualization."""
    user_name = request.GET.get("user_name")
    if not user_name:
        return _json_error("user_name is required")
    
    debates = DebateRound.objects.filter(user_name=user_name)
    
    if not debates.exists():
        # Return default values
        return JsonResponse({
            "user_name": user_name,
            "skills": {
                "logic": 50,
                "evidence": 50,
                "clarity": 50,
                "persuasion": 50,
                "counter_arguments": 50,
            }
        })
    
    # Analyze skills from debate history
    total_scores = {"logic": 0, "evidence": 0, "clarity": 0, "persuasion": 0, "counter_arguments": 0}
    count = 0
    
    for debate in debates[:20]:
        for msg in debate.conversation:
            if msg.get("role") == "user" and msg.get("analysis"):
                analysis = msg["analysis"]
                count += 1
                
                # Base score from overall
                base = analysis.get("score", 0.5) * 100
                
                # Adjust based on strengths and weaknesses
                strengths = analysis.get("strengths", [])
                fallacies = analysis.get("fallacies", [])
                unsupported = analysis.get("unsupported_claims", [])
                
                total_scores["logic"] += base - (len(fallacies) * 10)
                total_scores["evidence"] += base - (len(unsupported) * 5) + (10 if "uses_examples" in strengths else 0)
                total_scores["clarity"] += base + (10 if "detailed_argument" in strengths else 0)
                total_scores["persuasion"] += base + (5 if "logical_connectors" in strengths else 0)
                total_scores["counter_arguments"] += base
    
    if count > 0:
        skills = {k: min(100, max(0, round(v / count, 1))) for k, v in total_scores.items()}
    else:
        skills = {k: 50 for k in total_scores}
    
    return JsonResponse({
        "user_name": user_name,
        "skills": skills,
    })


# ============================================================================
# Session Replay Endpoints
# ============================================================================

@require_GET
def get_session_list(request):
    """Get list of sessions for replay."""
    user_name = request.GET.get("user_name")
    limit = int(request.GET.get("limit", 10))
    
    debates = DebateRound.objects.all()
    if user_name:
        debates = debates.filter(user_name=user_name)
    
    debates = debates.order_by("-created_at")[:limit]
    
    sessions = []
    for debate in debates:
        sessions.append({
            "session_id": debate.session_id,
            "topic": debate.topic,
            "user_name": debate.user_name,
            "score": debate.overall_score,
            "rounds": debate.current_round - 1,
            "difficulty": debate.difficulty,
            "date": debate.created_at.isoformat(),
            "is_active": debate.is_active,
        })
    
    return JsonResponse({"sessions": sessions})


@require_GET
def get_session_replay(request):
    """Get full session data for replay."""
    session_id = request.GET.get("session_id")
    if not session_id:
        return _json_error("session_id is required")
    
    try:
        debate = DebateRound.objects.get(session_id=session_id)
    except DebateRound.DoesNotExist:
        return _json_error("Session not found", status=404)
    
    return JsonResponse({
        "session_id": debate.session_id,
        "topic": debate.topic,
        "user_name": debate.user_name,
        "ai_position": debate.ai_position,
        "difficulty": debate.difficulty,
        "overall_score": debate.overall_score,
        "conversation": debate.conversation,
        "feedbacks": debate.ai_feedbacks,
        "scores": debate.scores,
        "research_summary": debate.research_summary,
        "created_at": debate.created_at.isoformat(),
    })


# ============================================================================
# AI Personality Endpoints
# ============================================================================

@require_GET
def get_ai_personalities(request):
    """Get list of available AI personality modes."""
    personalities = []
    for pid, pdata in AI_PERSONALITIES.items():
        personalities.append({
            "id": pid,
            "name": pdata["name"],
            "description": pdata["description"],
        })
    
    return JsonResponse({"personalities": personalities})


# ============================================================================
# Real-time Rebuttal Suggestions
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
@rate_limit(requests_per_minute=30)
def get_rebuttal_suggestions(request):
    """Get real-time rebuttal suggestions as user types."""
    from django.conf import settings
    from .services.agent import from_settings
    
    payload, error = validate_json_payload(request)
    if error:
        return error
    
    opponent_argument = payload.get("opponent_argument", "")
    topic = payload.get("topic", "")
    
    if len(opponent_argument) < 20:
        return JsonResponse({"suggestions": [], "message": "Need more text for suggestions"})
    
    agent = from_settings(settings)
    result = agent.suggest_rebuttals(opponent_argument, topic)
    
    return JsonResponse(result)
