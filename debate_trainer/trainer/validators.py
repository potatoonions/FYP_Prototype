"""
Input validation utilities for API endpoints.

Provides reusable validation functions for common input types including
JSON payloads, string fields, and enumerated values.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse


def validate_json_payload(request: HttpRequest) -> tuple[Dict[str, Any] | None, JsonResponse | None]:
    """
    Validate and parse JSON payload from request.
    
    Returns:
        Tuple of (payload_dict, error_response). If valid, error_response is None.
    """
    try:
        payload: Dict[str, Any] = json.loads(request.body.decode("utf-8"))
        return payload, None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON payload"}, status=400)
    except UnicodeDecodeError:
        return None, JsonResponse({"error": "Invalid request encoding"}, status=400)


def validate_string_field(
    value: Any,
    field_name: str,
    max_length: int | None = None,
    min_length: int = 1,
    required: bool = True,
) -> tuple[str | None, JsonResponse | None]:
    """
    Validate a string field.
    
    Returns:
        Tuple of (validated_value, error_response). If valid, error_response is None.
    """
    if value is None:
        if required:
            return None, JsonResponse(
                {"error": f"`{field_name}` is required"}, status=400
            )
        return None, None
    
    if not isinstance(value, str):
        return None, JsonResponse(
            {"error": f"`{field_name}` must be a string"}, status=400
        )
    
    value = value.strip()
    
    if len(value) < min_length:
        return None, JsonResponse(
            {"error": f"`{field_name}` must be at least {min_length} characters"}, status=400
        )
    
    if max_length and len(value) > max_length:
        return None, JsonResponse(
            {"error": f"`{field_name}` must not exceed {max_length} characters"}, status=400
        )
    
    return value, None


def validate_difficulty(value: Any) -> tuple[str | None, JsonResponse | None]:
    """Validate difficulty level."""
    valid_difficulties = {"easy", "medium", "hard"}
    if value not in valid_difficulties:
        return None, JsonResponse(
            {"error": f"`difficulty` must be one of: {', '.join(valid_difficulties)}"}, status=400
        )
    return value, None


def validate_limit(value: Any, default: int = 20, max_limit: int = 100) -> int:
    """Validate and sanitize limit parameter."""
    try:
        limit = int(value)
        if limit < 1:
            return default
        if limit > max_limit:
            return max_limit
        return limit
    except (ValueError, TypeError):
        return default

