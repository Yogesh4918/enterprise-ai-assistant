"""Sentiment analysis service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

_sentiment_pipeline = None


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    label: SentimentLabel
    polarity: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0


def _get_pipeline():
    """Lazy-load the sentiment analysis pipeline."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            from transformers import pipeline
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                truncation=True,
                max_length=512,
            )
        except Exception as e:
            logger.warning(f"Failed to load sentiment model: {e}")
            _sentiment_pipeline = None
    return _sentiment_pipeline


def analyze_sentiment(text: str) -> SentimentResult:
    """
    Analyze the sentiment of the given text.

    Args:
        text: Input text to analyze.

    Returns:
        SentimentResult with label, polarity score, and confidence.
    """
    if not text or len(text.strip()) < 2:
        return SentimentResult(
            label=SentimentLabel.NEUTRAL,
            polarity=0.0,
            confidence=0.0,
        )

    pipe = _get_pipeline()
    if pipe is None:
        return _fallback_sentiment(text)

    try:
        result = pipe(text[:512])[0]
        hf_label = result["label"].upper()
        score = result["score"]

        if hf_label == "POSITIVE":
            label = SentimentLabel.POSITIVE
            polarity = score
        elif hf_label == "NEGATIVE":
            label = SentimentLabel.NEGATIVE
            polarity = -score
        else:
            label = SentimentLabel.NEUTRAL
            polarity = 0.0

        return SentimentResult(label=label, polarity=polarity, confidence=score)

    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {e}")
        return _fallback_sentiment(text)


def _fallback_sentiment(text: str) -> SentimentResult:
    """Simple keyword-based fallback sentiment analysis."""
    text_lower = text.lower()

    positive_words = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "love", "happy", "best", "awesome", "perfect", "brilliant",
        "thank", "thanks", "helpful", "useful", "nice",
    }
    negative_words = {
        "bad", "terrible", "awful", "horrible", "hate", "worst", "poor",
        "wrong", "error", "fail", "broken", "useless", "annoying",
        "frustrating", "disappointed", "ugly",
    }

    words = set(text_lower.split())
    pos_count = len(words & positive_words)
    neg_count = len(words & negative_words)
    total = pos_count + neg_count

    if total == 0:
        return SentimentResult(label=SentimentLabel.NEUTRAL, polarity=0.0, confidence=0.3)

    polarity = (pos_count - neg_count) / total
    if polarity > 0.1:
        label = SentimentLabel.POSITIVE
    elif polarity < -0.1:
        label = SentimentLabel.NEGATIVE
    else:
        label = SentimentLabel.NEUTRAL

    return SentimentResult(label=label, polarity=polarity, confidence=0.5)
