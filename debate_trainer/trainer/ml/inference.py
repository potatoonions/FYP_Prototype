"""
Inference service for argument quality prediction.
Provides easy-to-use functions for integrating ML predictions into the debate trainer.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Lazy loading of classifier to avoid slow startup
_classifier = None


def _get_classifier():
    """Lazy load the classifier."""
    global _classifier
    if _classifier is None:
        try:
            from .classifier import get_classifier
            _classifier = get_classifier()
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            return None
    return _classifier


def predict_argument_quality(text: str) -> Dict[str, Any]:
    """
    Predict the quality of an argument using the ML model.
    
    Args:
        text: The argument text to analyze
        
    Returns:
        Dictionary containing:
        - quality_score: Float between 0-1
        - quality_class: "weak", "medium", or "strong"
        - confidence: Model confidence in the prediction
        - class_probabilities: Probabilities for each class
        - ml_available: Whether ML prediction was successful
    """
    classifier = _get_classifier()
    
    if classifier is None:
        logger.warning("ML classifier not available, returning default prediction")
        return {
            "quality_score": 0.5,
            "quality_class": "medium",
            "confidence": 0.0,
            "class_probabilities": {"weak": 0.33, "medium": 0.34, "strong": 0.33},
            "ml_available": False,
        }
    
    try:
        prediction = classifier.predict(text)
        prediction["ml_available"] = True
        return prediction
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {
            "quality_score": 0.5,
            "quality_class": "medium",
            "confidence": 0.0,
            "class_probabilities": {"weak": 0.33, "medium": 0.34, "strong": 0.33},
            "ml_available": False,
            "error": str(e),
        }


def get_ml_analysis(text: str) -> Dict[str, Any]:
    """
    Get comprehensive ML-based analysis of an argument.
    
    This provides a more detailed analysis including:
    - Quality prediction
    - Strength indicators
    - Suggested improvements based on quality class
    
    Args:
        text: The argument text to analyze
        
    Returns:
        Comprehensive analysis dictionary
    """
    # Get base prediction
    prediction = predict_argument_quality(text)
    
    # Add analysis details
    analysis = {
        **prediction,
        "analysis": {},
    }
    
    quality_class = prediction.get("quality_class", "medium")
    quality_score = prediction.get("quality_score", 0.5)
    
    # Generate feedback based on quality
    if quality_class == "strong":
        analysis["analysis"] = {
            "summary": "This is a well-constructed argument.",
            "strengths": [
                "Clear and logical structure",
                "Evidence-based reasoning",
                "Persuasive language",
            ],
            "suggestions": [
                "Consider addressing potential counterarguments",
                "Add specific examples or data if not present",
            ],
        }
    elif quality_class == "medium":
        analysis["analysis"] = {
            "summary": "This argument has potential but could be strengthened.",
            "strengths": [
                "Presents a clear position",
            ],
            "suggestions": [
                "Add supporting evidence or citations",
                "Strengthen logical connections between claims",
                "Consider addressing opposing viewpoints",
                "Use more specific examples",
            ],
        }
    else:  # weak
        analysis["analysis"] = {
            "summary": "This argument needs significant improvement.",
            "strengths": [],
            "suggestions": [
                "Provide concrete evidence for your claims",
                "Avoid logical fallacies (ad hominem, appeals to emotion)",
                "Structure your argument with clear premises and conclusion",
                "Use objective language instead of subjective assertions",
                "Address the specific topic rather than making general statements",
            ],
        }
    
    # Add quality score interpretation
    if quality_score >= 0.8:
        analysis["score_interpretation"] = "Excellent"
    elif quality_score >= 0.6:
        analysis["score_interpretation"] = "Good"
    elif quality_score >= 0.4:
        analysis["score_interpretation"] = "Fair"
    elif quality_score >= 0.2:
        analysis["score_interpretation"] = "Needs Work"
    else:
        analysis["score_interpretation"] = "Poor"
    
    return analysis


def batch_predict(texts: list) -> list:
    """
    Predict quality for multiple arguments.
    
    Args:
        texts: List of argument texts
        
    Returns:
        List of prediction dictionaries
    """
    return [predict_argument_quality(text) for text in texts]
