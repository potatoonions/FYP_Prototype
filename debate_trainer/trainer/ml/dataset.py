"""
Dataset handling for argument quality classification.
Loads data from a CSV file (argument_dataset.csv).
"""

import os
import csv
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset, DataLoader

logger = logging.getLogger(__name__)

# Path to local CSV dataset
DATASET_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DATASET_PATH = os.path.join(DATASET_DIR, "argument_dataset.csv")


@dataclass
class ArgumentSample:
    """Single argument sample with label."""
    text: str
    quality_label: int  # 0=weak, 1=medium, 2=strong
    quality_score: float  # 0.0 to 1.0


class ArgumentQualityDataset(Dataset):
    """
    PyTorch Dataset for argument quality classification.
    """
    
    def __init__(
        self,
        samples: List[ArgumentSample],
        tokenizer,
        max_length: int = 512,
    ):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]
        
        # Tokenize
        encoded = self.tokenizer(
            sample.text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "label": torch.tensor(sample.quality_label, dtype=torch.long),
            "score": torch.tensor(sample.quality_score, dtype=torch.float),
        }


def load_argument_quality_data() -> Tuple[List[ArgumentSample], List[ArgumentSample]]:
    """
    Load argument quality data from CSV file.
    
    The CSV file should be located at: trainer/ml/argument_dataset.csv
    Format: text,quality_label,quality_score
    - quality_label: 0=weak, 1=medium, 2=strong
    - quality_score: 0.0 to 1.0
    
    Returns:
        Tuple of (train_samples, val_samples)
    """
    import random
    
    # Load from CSV file
    all_samples = _load_from_csv()
    
    if len(all_samples) == 0:
        logger.error(f"No data found! Please add data to: {CSV_DATASET_PATH}")
        logger.error("CSV format: text,quality_label,quality_score")
        logger.error("  quality_label: 0=weak, 1=medium, 2=strong")
        logger.error("  quality_score: 0.0 to 1.0")
        return [], []
    
    if len(all_samples) < 50:
        logger.warning(f"Only {len(all_samples)} samples found. Consider adding more data for better training.")
    
    # Shuffle and split (85% train, 15% validation)
    random.shuffle(all_samples)
    
    split_idx = int(len(all_samples) * 0.85)
    train_samples = all_samples[:split_idx]
    val_samples = all_samples[split_idx:]
    
    # Ensure at least 1 validation sample
    if len(val_samples) == 0 and len(train_samples) > 1:
        val_samples = [train_samples.pop()]
    
    logger.info(f"Dataset loaded: {len(train_samples)} train, {len(val_samples)} val samples")
    
    return train_samples, val_samples


def _load_from_csv() -> List[ArgumentSample]:
    """Load samples from local CSV file."""
    samples = []
    
    if not os.path.exists(CSV_DATASET_PATH):
        logger.info(f"CSV file not found at {CSV_DATASET_PATH}")
        return samples
    
    try:
        logger.info(f"Loading dataset from CSV: {CSV_DATASET_PATH}")
        with open(CSV_DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('text', '').strip()
                if text and len(text) > 10:
                    quality_label = int(row.get('quality_label', 1))
                    quality_score = float(row.get('quality_score', 0.5))
                    samples.append(ArgumentSample(text, quality_label, quality_score))
        
        logger.info(f"Loaded {len(samples)} samples from CSV")
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
    
    return samples


def create_dataloaders(
    train_samples: List[ArgumentSample],
    val_samples: List[ArgumentSample],
    tokenizer,
    batch_size: int = 16,
    max_length: int = 256,
) -> Tuple[DataLoader, DataLoader]:
    """
    Create PyTorch DataLoaders for training and validation.
    """
    train_dataset = ArgumentQualityDataset(train_samples, tokenizer, max_length)
    val_dataset = ArgumentQualityDataset(val_samples, tokenizer, max_length)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,  # Windows compatibility
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    
    return train_loader, val_loader
