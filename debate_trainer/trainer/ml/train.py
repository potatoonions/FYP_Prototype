"""
Training script for the Argument Quality Classifier.
Uses HuggingFace datasets and PyTorch for training.
"""

import os
import logging
import argparse
from datetime import datetime
from typing import Dict, Tuple

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

from .classifier import ArgumentQualityClassifier, MODEL_DIR
from .dataset import load_argument_quality_data, create_dataloaders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Trainer:
    """
    Trainer class for ArgumentQualityClassifier.
    Handles training loop, validation, and checkpointing.
    """
    
    def __init__(
        self,
        model: ArgumentQualityClassifier,
        train_loader,
        val_loader,
        learning_rate: float = 2e-5,
        weight_decay: float = 0.01,
        num_epochs: int = 5,
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.num_epochs = num_epochs
        self.device = model.device
        
        # Loss functions
        self.classification_loss = nn.CrossEntropyLoss()
        self.regression_loss = nn.MSELoss()
        
        # Optimizer
        self.optimizer = AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        
        # Learning rate scheduler
        total_steps = len(train_loader) * num_epochs
        self.scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=total_steps,
            eta_min=1e-7,
        )
        
        # Training history
        self.history = {
            "train_loss": [],
            "val_loss": [],
            "val_accuracy": [],
            "val_mae": [],
        }
        
        self.best_val_loss = float("inf")
    
    def train_epoch(self) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        
        progress_bar = tqdm(self.train_loader, desc="Training")
        
        for batch in progress_bar:
            # Move batch to device
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch["label"].to(self.device)
            scores = batch["score"].to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            class_logits, pred_scores = self.model(input_ids, attention_mask)
            
            # Calculate combined loss
            cls_loss = self.classification_loss(class_logits, labels)
            reg_loss = self.regression_loss(pred_scores, scores)
            loss = cls_loss + 0.5 * reg_loss  # Weight regression less
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            self.scheduler.step()
            
            total_loss += loss.item()
            progress_bar.set_postfix({"loss": f"{loss.item():.4f}"})
        
        return total_loss / len(self.train_loader)
    
    def validate(self) -> Tuple[float, float, float]:
        """Validate the model."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        total_mae = 0.0
        
        with torch.no_grad():
            for batch in tqdm(self.val_loader, desc="Validating"):
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["label"].to(self.device)
                scores = batch["score"].to(self.device)
                
                class_logits, pred_scores = self.model(input_ids, attention_mask)
                
                # Calculate loss
                cls_loss = self.classification_loss(class_logits, labels)
                reg_loss = self.regression_loss(pred_scores, scores)
                loss = cls_loss + 0.5 * reg_loss
                total_loss += loss.item()
                
                # Calculate accuracy
                predictions = torch.argmax(class_logits, dim=-1)
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
                
                # Calculate MAE for regression
                total_mae += torch.abs(pred_scores - scores).sum().item()
        
        avg_loss = total_loss / len(self.val_loader)
        accuracy = correct / total
        mae = total_mae / total
        
        return avg_loss, accuracy, mae
    
    def train(self) -> Dict:
        """
        Full training loop.
        
        Returns:
            Training history dictionary
        """
        logger.info(f"Starting training for {self.num_epochs} epochs")
        logger.info(f"Training samples: {len(self.train_loader.dataset)}")
        logger.info(f"Validation samples: {len(self.val_loader.dataset)}")
        logger.info(f"Device: {self.device}")
        
        for epoch in range(self.num_epochs):
            logger.info(f"\n{'='*50}")
            logger.info(f"Epoch {epoch + 1}/{self.num_epochs}")
            logger.info(f"{'='*50}")
            
            # Train
            train_loss = self.train_epoch()
            self.history["train_loss"].append(train_loss)
            
            # Validate
            val_loss, val_acc, val_mae = self.validate()
            self.history["val_loss"].append(val_loss)
            self.history["val_accuracy"].append(val_acc)
            self.history["val_mae"].append(val_mae)
            
            logger.info(f"Train Loss: {train_loss:.4f}")
            logger.info(f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f} | Val MAE: {val_mae:.4f}")
            
            # Save best model
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.model.save()
                logger.info("✓ Saved best model checkpoint")
        
        logger.info("\nTraining complete!")
        logger.info(f"Best validation loss: {self.best_val_loss:.4f}")
        
        return self.history


def train_model(
    num_epochs: int = 5,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    freeze_bert: bool = False,
) -> Dict:
    """
    Main training function.
    
    Args:
        num_epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate for optimizer
        freeze_bert: Whether to freeze BERT layers
        
    Returns:
        Training history
    """
    # Load data
    logger.info("Loading training data from HuggingFace...")
    train_samples, val_samples = load_argument_quality_data()
    
    if not train_samples:
        logger.error("No training data available!")
        return {}
    
    # Create model
    logger.info("Initializing model...")
    model = ArgumentQualityClassifier(freeze_bert=freeze_bert)
    
    # Create dataloaders
    train_loader, val_loader = create_dataloaders(
        train_samples,
        val_samples,
        model.tokenizer,
        batch_size=batch_size,
    )
    
    # Create trainer and train
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        learning_rate=learning_rate,
        num_epochs=num_epochs,
    )
    
    history = trainer.train()
    
    return history


def main():
    """CLI entry point for training."""
    parser = argparse.ArgumentParser(description="Train Argument Quality Classifier")
    parser.add_argument("--epochs", type=int, default=5, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--freeze-bert", action="store_true", help="Freeze BERT layers")
    
    args = parser.parse_args()
    
    history = train_model(
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        freeze_bert=args.freeze_bert,
    )
    
    if history:
        logger.info(f"\nFinal Results:")
        logger.info(f"  Final Train Loss: {history['train_loss'][-1]:.4f}")
        logger.info(f"  Final Val Loss: {history['val_loss'][-1]:.4f}")
        logger.info(f"  Final Val Accuracy: {history['val_accuracy'][-1]:.4f}")


if __name__ == "__main__":
    main()
