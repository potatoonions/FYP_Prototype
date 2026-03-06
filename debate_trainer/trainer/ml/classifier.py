"""
PyTorch-based Argument Quality Classifier using DistilBERT.
Fine-tuned on argument quality datasets from HuggingFace.
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any

import torch
import torch.nn as nn
from transformers import DistilBertModel, DistilBertTokenizer

logger = logging.getLogger(__name__)

# Model save path
MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(MODEL_DIR, "argument_classifier.pt")


class ArgumentQualityClassifier(nn.Module):
    """
    Neural network for classifying argument quality.
    
    Architecture:
    - DistilBERT encoder for text understanding
    - Dropout for regularization
    - Linear layers for classification
    
    Output: Quality score (0-1) and quality class (weak/medium/strong)
    """
    
    def __init__(
        self,
        num_classes: int = 3,  # weak, medium, strong
        dropout_rate: float = 0.3,
        freeze_bert: bool = False,
    ):
        super().__init__()
        
        self.num_classes = num_classes
        self.bert = DistilBertModel.from_pretrained("distilbert-base-uncased")
        self.tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
        
        # Optionally freeze BERT layers for faster training
        if freeze_bert:
            for param in self.bert.parameters():
                param.requires_grad = False
        
        # Classification head
        hidden_size = self.bert.config.hidden_size  # 768
        
        self.classifier = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )
        
        # Regression head for continuous quality score
        self.regressor = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),  # Output between 0-1
        )
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)
        
        logger.info(f"ArgumentQualityClassifier initialized on {self.device}")
    
    def forward(
        self, 
        input_ids: torch.Tensor, 
        attention_mask: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the model.
        
        Args:
            input_ids: Tokenized input tensor
            attention_mask: Attention mask tensor
            
        Returns:
            Tuple of (class_logits, quality_score)
        """
        # Get BERT embeddings
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        # Use [CLS] token representation
        pooled_output = outputs.last_hidden_state[:, 0, :]
        
        # Get classification logits and quality score
        class_logits = self.classifier(pooled_output)
        quality_score = self.regressor(pooled_output)
        
        return class_logits, quality_score.squeeze(-1)
    
    def tokenize(
        self, 
        texts: list, 
        max_length: int = 512
    ) -> Dict[str, torch.Tensor]:
        """
        Tokenize input texts for the model.
        
        Args:
            texts: List of argument texts
            max_length: Maximum sequence length
            
        Returns:
            Dictionary with input_ids and attention_mask
        """
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"].to(self.device),
            "attention_mask": encoded["attention_mask"].to(self.device),
        }
    
    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predict argument quality for a single text.
        
        Args:
            text: Argument text to analyze
            
        Returns:
            Dictionary with quality_score, quality_class, and confidence
        """
        self.eval()
        
        with torch.no_grad():
            inputs = self.tokenize([text])
            class_logits, quality_score = self.forward(
                inputs["input_ids"], 
                inputs["attention_mask"]
            )
            
            # Get predicted class
            probabilities = torch.softmax(class_logits, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0, predicted_class].item()
            
            class_labels = ["weak", "medium", "strong"]
            
            return {
                "quality_score": quality_score.item(),
                "quality_class": class_labels[predicted_class],
                "confidence": confidence,
                "class_probabilities": {
                    label: prob.item() 
                    for label, prob in zip(class_labels, probabilities[0])
                },
            }
    
    def save(self, path: Optional[str] = None):
        """Save model weights to disk."""
        save_path = path or MODEL_PATH
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save(self.state_dict(), save_path)
        logger.info(f"Model saved to {save_path}")
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> "ArgumentQualityClassifier":
        """Load model weights from disk."""
        load_path = path or MODEL_PATH
        model = cls()
        if os.path.exists(load_path):
            model.load_state_dict(torch.load(load_path, map_location=model.device))
            logger.info(f"Model loaded from {load_path}")
        else:
            logger.warning(f"No saved model found at {load_path}, using untrained model")
        return model


# Singleton instance for inference
_classifier_instance: Optional[ArgumentQualityClassifier] = None


def get_classifier() -> ArgumentQualityClassifier:
    """Get or create the singleton classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ArgumentQualityClassifier.load()
    return _classifier_instance
