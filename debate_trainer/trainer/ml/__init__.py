"""
Machine Learning module for argument quality classification.
Uses PyTorch and HuggingFace transformers for deep learning-based analysis.
"""

from .classifier import ArgumentQualityClassifier, get_classifier
from .inference import predict_argument_quality, get_ml_analysis

__all__ = [
    "ArgumentQualityClassifier",
    "get_classifier", 
    "predict_argument_quality",
    "get_ml_analysis",
]
