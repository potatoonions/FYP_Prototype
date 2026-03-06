"""
Dataset handling for argument quality classification.
Loads and preprocesses data from HuggingFace datasets.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset, DataLoader

logger = logging.getLogger(__name__)

# Try to import datasets
try:
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False
    logger.warning("HuggingFace datasets not installed. Run: pip install datasets")


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
    Load argument quality data from HuggingFace.
    
    Uses multiple datasets and combines them:
    1. UKP Sentential Argument Mining
    2. IBM Claim Stance Dataset  
    3. Argument Quality Ranking
    
    Returns:
        Tuple of (train_samples, val_samples)
    """
    if not DATASETS_AVAILABLE:
        logger.error("HuggingFace datasets not available")
        return [], []
    
    all_samples = []
    
    # Dataset 1: UKP Sentential Argument Mining Corpus
    try:
        logger.info("Loading UKP Argument Mining dataset...")
        dataset = load_dataset("ukp/ampersand", trust_remote_code=True)
        
        for split in ["train", "validation"]:
            if split in dataset:
                for item in dataset[split]:
                    text = item.get("premise", "") or item.get("text", "")
                    if text and len(text) > 20:
                        # Map annotation to quality (simplified)
                        label = item.get("label", 1)
                        if isinstance(label, int):
                            quality = min(2, max(0, label))
                        else:
                            quality = 1  # default to medium
                        
                        score = (quality + 0.5) / 3.0
                        all_samples.append(ArgumentSample(text, quality, score))
        
        logger.info(f"Loaded {len(all_samples)} samples from UKP dataset")
    except Exception as e:
        logger.warning(f"Could not load UKP dataset: {e}")
    
    # Dataset 2: Argument Quality Ranking (ArgQ)
    try:
        logger.info("Loading ArgQ dataset...")
        dataset = load_dataset("webis/args-me", trust_remote_code=True)
        
        count = 0
        for split in dataset:
            for item in dataset[split]:
                if count >= 5000:  # Limit samples
                    break
                    
                text = item.get("argument", "") or item.get("premise", "")
                if text and len(text) > 30:
                    # Use stance confidence as quality proxy
                    stance = item.get("stance", "")
                    if stance in ["pro", "con"]:
                        quality = 2  # Clear stance = strong
                        score = 0.8
                    else:
                        quality = 1  # Unclear = medium
                        score = 0.5
                    
                    all_samples.append(ArgumentSample(text, quality, score))
                    count += 1
        
        logger.info(f"Total samples after ArgQ: {len(all_samples)}")
    except Exception as e:
        logger.warning(f"Could not load ArgQ dataset: {e}")
    
    # Dataset 3: Persuasive Essays (argument components)
    try:
        logger.info("Loading Persuasive Essays dataset...")
        dataset = load_dataset("tasksource/persuasive-essays", trust_remote_code=True)
        
        count = 0
        for split in dataset:
            for item in dataset[split]:
                if count >= 3000:
                    break
                
                text = item.get("text", "")
                label = item.get("label", "")
                
                if text and len(text) > 20:
                    # Map component types to quality
                    if label in ["MajorClaim", "Claim"]:
                        quality = 2
                        score = 0.85
                    elif label == "Premise":
                        quality = 1
                        score = 0.6
                    else:
                        quality = 0
                        score = 0.3
                    
                    all_samples.append(ArgumentSample(text, quality, score))
                    count += 1
        
        logger.info(f"Total samples after Essays: {len(all_samples)}")
    except Exception as e:
        logger.warning(f"Could not load Persuasive Essays dataset: {e}")
    
    # If no datasets loaded, use synthetic fallback
    if len(all_samples) < 100:
        logger.warning("Insufficient data from HuggingFace, using synthetic data")
        all_samples = _generate_synthetic_samples()
    
    # Shuffle and split
    import random
    random.shuffle(all_samples)
    
    split_idx = int(len(all_samples) * 0.85)
    train_samples = all_samples[:split_idx]
    val_samples = all_samples[split_idx:]
    
    logger.info(f"Final dataset: {len(train_samples)} train, {len(val_samples)} val")
    
    return train_samples, val_samples


def _generate_synthetic_samples() -> List[ArgumentSample]:
    """Generate synthetic argument samples as fallback."""
    samples = []
    
    # Strong arguments
    strong_templates = [
        "Research conducted by leading universities demonstrates that {topic} leads to measurable improvements in {outcome}, with studies showing a {percent}% increase in effectiveness.",
        "Multiple peer-reviewed studies have consistently shown that {topic} is essential for {outcome}. The evidence is clear: implementing {topic} results in significant benefits.",
        "According to data from international organizations, countries that implement {topic} see substantial improvements in {outcome}, proving its effectiveness.",
    ]
    
    # Medium arguments
    medium_templates = [
        "{topic} is important because it helps achieve {outcome}. Many experts believe this approach is beneficial.",
        "There are good reasons to support {topic}. It can lead to improvements in {outcome} when properly implemented.",
        "Supporting {topic} makes sense because it addresses key issues related to {outcome}.",
    ]
    
    # Weak arguments
    weak_templates = [
        "{topic} is obviously the best option. Anyone can see that.",
        "Everyone knows {topic} is true. It's just common sense.",
        "{topic} is good because I think it is. That's my opinion.",
        "You're wrong if you don't support {topic}. It's clearly better.",
    ]
    
    topics = [
        ("renewable energy", "environmental sustainability"),
        ("education funding", "student outcomes"),
        ("healthcare access", "public health"),
        ("technology regulation", "consumer protection"),
        ("urban planning", "quality of life"),
    ]
    
    import random
    
    for topic, outcome in topics:
        # Generate strong samples
        for template in strong_templates:
            text = template.format(topic=topic, outcome=outcome, percent=random.randint(15, 45))
            samples.append(ArgumentSample(text, 2, random.uniform(0.75, 0.95)))
        
        # Generate medium samples
        for template in medium_templates:
            text = template.format(topic=topic, outcome=outcome)
            samples.append(ArgumentSample(text, 1, random.uniform(0.4, 0.65)))
        
        # Generate weak samples
        for template in weak_templates:
            text = template.format(topic=topic)
            samples.append(ArgumentSample(text, 0, random.uniform(0.1, 0.35)))
    
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
