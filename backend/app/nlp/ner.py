"""Named Entity Recognition service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_nlp_model = None


def _get_nlp():
    """Lazy-load spaCy model."""
    global _nlp_model
    if _nlp_model is None:
        try:
            import spacy
            _nlp_model = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
            _nlp_model = None
    return _nlp_model


@dataclass
class Entity:
    """A recognized named entity."""
    text: str
    label: str
    start: int
    end: int
    description: str = ""


ENTITY_DESCRIPTIONS: dict[str, str] = {
    "PERSON": "People, including fictional",
    "NORP": "Nationalities, religious, or political groups",
    "FAC": "Buildings, airports, highways, bridges, etc.",
    "ORG": "Companies, agencies, institutions, etc.",
    "GPE": "Countries, cities, states",
    "LOC": "Non-GPE locations, mountain ranges, bodies of water",
    "PRODUCT": "Objects, vehicles, foods, etc.",
    "EVENT": "Named hurricanes, battles, wars, sports events, etc.",
    "WORK_OF_ART": "Titles of books, songs, etc.",
    "LAW": "Named documents made into laws",
    "LANGUAGE": "Any named language",
    "DATE": "Absolute or relative dates or periods",
    "TIME": "Times smaller than a day",
    "PERCENT": "Percentage",
    "MONEY": "Monetary values, including unit",
    "QUANTITY": "Measurements, as of weight or distance",
    "ORDINAL": "\"first\", \"second\", etc.",
    "CARDINAL": "Numerals that do not fall under another type",
}


def extract_entities(text: str) -> list[Entity]:
    """
    Extract named entities from text using spaCy.

    Args:
        text: Input text to analyze.

    Returns:
        List of Entity objects with text, label, position, and description.
    """
    nlp = _get_nlp()
    if nlp is None:
        return []

    doc = nlp(text[:100_000])  # Limit text length for performance

    entities = []
    seen = set()

    for ent in doc.ents:
        key = (ent.text.strip(), ent.label_)
        if key in seen:
            continue
        seen.add(key)

        entities.append(Entity(
            text=ent.text.strip(),
            label=ent.label_,
            start=ent.start_char,
            end=ent.end_char,
            description=ENTITY_DESCRIPTIONS.get(ent.label_, ""),
        ))

    return entities


def extract_entities_grouped(text: str) -> dict[str, list[str]]:
    """
    Extract entities and group them by label.

    Returns:
        Dictionary mapping entity labels to lists of entity texts.
    """
    entities = extract_entities(text)
    grouped: dict[str, list[str]] = {}
    for entity in entities:
        grouped.setdefault(entity.label, []).append(entity.text)
    return grouped
