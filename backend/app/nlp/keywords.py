"""Keyword extraction service using RAKE algorithm."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from",
    "further", "get", "got", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "its", "itself", "just", "let's", "me", "might", "more", "most",
    "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "shan't", "she", "should", "shouldn't",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "upon", "us", "very",
    "was", "wasn't", "we", "were", "weren't", "what", "when", "where",
    "which", "while", "who", "whom", "why", "will", "with", "won't",
    "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves",
}


@dataclass
class Keyword:
    """An extracted keyword with its score."""
    text: str
    score: float


def extract_keywords(text: str, top_k: int = 10) -> list[Keyword]:
    """
    Extract keywords from text using a RAKE-inspired algorithm.

    Args:
        text: Input text to analyze.
        top_k: Maximum number of keywords to return.

    Returns:
        List of Keyword objects sorted by score (descending).
    """
    if not text or len(text.strip()) < 5:
        return []

    # Split text into candidate phrases using stop words and punctuation
    phrase_delimiters = re.compile(r"[.!?,;:\t\n\r\(\)\[\]\{\}\"'`/\\|@#$%^&*+=<>~]")
    sentences = phrase_delimiters.split(text.lower())

    phrases: list[list[str]] = []
    for sentence in sentences:
        words = sentence.strip().split()
        current_phrase: list[str] = []
        for word in words:
            clean_word = re.sub(r"[^a-zA-Z0-9\-]", "", word)
            if not clean_word:
                continue
            if clean_word in STOP_WORDS:
                if current_phrase:
                    phrases.append(current_phrase)
                    current_phrase = []
            else:
                current_phrase.append(clean_word)
        if current_phrase:
            phrases.append(current_phrase)

    # Calculate word scores based on degree and frequency
    word_freq: dict[str, int] = defaultdict(int)
    word_degree: dict[str, int] = defaultdict(int)

    for phrase in phrases:
        degree = len(phrase) - 1
        for word in phrase:
            word_freq[word] += 1
            word_degree[word] += degree

    word_scores: dict[str, float] = {}
    for word in word_freq:
        word_scores[word] = (word_degree[word] + word_freq[word]) / word_freq[word]

    # Score phrases
    phrase_scores: dict[str, float] = {}
    for phrase in phrases:
        phrase_text = " ".join(phrase)
        if len(phrase_text) < 2:
            continue
        score = sum(word_scores.get(w, 0.0) for w in phrase)
        if phrase_text in phrase_scores:
            phrase_scores[phrase_text] = max(phrase_scores[phrase_text], score)
        else:
            phrase_scores[phrase_text] = score

    # Sort and return top-k
    sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)

    # Normalize scores
    max_score = sorted_phrases[0][1] if sorted_phrases else 1.0
    if max_score == 0:
        max_score = 1.0

    return [
        Keyword(text=phrase, score=round(score / max_score, 4))
        for phrase, score in sorted_phrases[:top_k]
    ]
