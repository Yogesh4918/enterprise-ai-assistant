"""Tests for RAG pipeline components."""

import pytest

from app.rag.chunking import TextChunker
from app.rag.prompts import RAG_SYSTEM_PROMPT, QUERY_REWRITE_PROMPT
from app.nlp.language import detect_language
from app.nlp.keywords import extract_keywords
from app.nlp.sentiment import analyze_sentiment, SentimentLabel


class TestTextChunker:
    """Tests for the TextChunker."""

    def test_chunk_short_text(self):
        """Short text should produce a single chunk."""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk_text("Hello world. This is a test.")
        assert len(chunks) >= 1
        assert chunks[0]["text"].strip() != ""

    def test_chunk_long_text(self):
        """Long text should produce multiple chunks."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        long_text = "This is a test sentence. " * 100
        chunks = chunker.chunk_text(long_text)
        assert len(chunks) > 1

    def test_chunk_metadata_preserved(self):
        """Metadata should be attached to each chunk."""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk_text(
            "Test content here.",
            metadata={"source": "test.pdf", "page": 1},
        )
        assert len(chunks) >= 1
        assert "metadata" in chunks[0]
        assert chunks[0]["metadata"]["source"] == "test.pdf"

    def test_chunk_empty_text(self):
        """Empty text should return empty list."""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0


class TestPrompts:
    """Tests for prompt templates."""

    def test_rag_prompt_exists(self):
        """RAG system prompt should be defined."""
        assert RAG_SYSTEM_PROMPT is not None
        assert len(RAG_SYSTEM_PROMPT) > 50

    def test_query_rewrite_prompt_exists(self):
        """Query rewrite prompt should be defined."""
        assert QUERY_REWRITE_PROMPT is not None
        assert len(QUERY_REWRITE_PROMPT) > 20


class TestLanguageDetection:
    """Tests for language detection."""

    def test_detect_english(self):
        """English text should be detected."""
        result = detect_language("This is a test sentence in English.")
        assert result.language == "en"
        assert result.confidence > 0.5

    def test_detect_short_text(self):
        """Very short text should return default."""
        result = detect_language("Hi")
        assert result.language is not None


class TestKeywordExtraction:
    """Tests for keyword extraction."""

    def test_extract_keywords(self):
        """Should extract relevant keywords from text."""
        text = "Machine learning and artificial intelligence are transforming the technology industry."
        keywords = extract_keywords(text, top_k=5)
        assert len(keywords) > 0
        assert keywords[0].score > 0

    def test_extract_keywords_empty(self):
        """Empty text should return empty list."""
        keywords = extract_keywords("", top_k=5)
        assert len(keywords) == 0


class TestSentimentAnalysis:
    """Tests for sentiment analysis."""

    def test_positive_sentiment(self):
        """Positive text should be detected."""
        result = analyze_sentiment("This is amazing and wonderful!")
        assert result.label == SentimentLabel.POSITIVE

    def test_negative_sentiment(self):
        """Negative text should be detected."""
        result = analyze_sentiment("This is terrible and horrible!")
        assert result.label == SentimentLabel.NEGATIVE

    def test_empty_text(self):
        """Empty text should return neutral."""
        result = analyze_sentiment("")
        assert result.label == SentimentLabel.NEUTRAL
