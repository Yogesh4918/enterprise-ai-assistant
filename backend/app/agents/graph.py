"""LangGraph state graph — orchestrates the full agent pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.agents.research import ResearchAgent
from app.agents.router import Intent, IntentRouter
from app.agents.summarizer import SummarizationAgent
from app.agents.translator import TranslationAgent
from app.rag.chain import RAGChain, RAGResponse
from app.rag.retrieval import HybridRetriever
from app.rag.vectorstore import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """State object flowing through the LangGraph nodes."""
    # Input
    query: str = ""
    collection: str = "default"
    chat_history: str = ""
    # Routing
    intent: str = ""
    # Retrieval
    documents: list[SearchResult] = field(default_factory=list)
    # Output
    response: RAGResponse | None = None
    error: str | None = None


# ── Node functions ──────────────────────────────────────────────────────────

async def classify_intent(state: dict[str, Any]) -> dict[str, Any]:
    """Classify the user's intent."""
    router = IntentRouter()
    intent = await router.classify(state["query"])
    logger.info("Intent classified as: %s", intent.value)
    return {"intent": intent.value}


async def retrieve_context(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant documents from the vector store."""
    retriever = HybridRetriever()
    try:
        docs = await retriever.retrieve(
            query=state["query"],
            collection=state.get("collection", "default"),
            chat_history=state.get("chat_history", ""),
        )
        return {"documents": docs}
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        return {"documents": [], "error": f"Retrieval failed: {exc}"}


async def research_node(state: dict[str, Any]) -> dict[str, Any]:
    """Handle complex research queries with decomposition."""
    agent = ResearchAgent()
    try:
        response = await agent.research(
            query=state["query"],
            collection=state.get("collection", "default"),
            chat_history=state.get("chat_history", ""),
        )
        return {"response": response}
    except Exception as exc:
        logger.error("Research failed: %s", exc)
        return {
            "response": RAGResponse(answer=f"Research failed: {exc}", confidence=0.0)
        }


async def summarize_node(state: dict[str, Any]) -> dict[str, Any]:
    """Summarize retrieved documents."""
    agent = SummarizationAgent()
    docs = state.get("documents", [])

    if docs:
        texts = [{"text": d.text, "source": d.metadata.get("source", "doc")} for d in docs]
        result = await agent.summarize_documents(texts)
    else:
        result = await agent.summarize(state["query"])

    return {
        "response": RAGResponse(
            answer=result.summary,
            confidence=0.8,
            metadata={"word_count": result.word_count, "source_length": result.source_length},
        )
    }


async def translate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Translate text."""
    agent = TranslationAgent()
    result = await agent.translate(state["query"])
    return {
        "response": RAGResponse(
            answer=result.translated_text,
            confidence=0.9,
            metadata={
                "source_language": result.source_language,
                "target_language": result.target_language,
            },
        )
    }


async def generate_response(state: dict[str, Any]) -> dict[str, Any]:
    """Generate a RAG response from retrieved context."""
    chain = RAGChain()
    docs = state.get("documents", [])
    response = await chain.generate(
        query=state["query"],
        context_docs=docs,
        chat_history=state.get("chat_history", ""),
    )
    return {"response": response}


async def chat_response(state: dict[str, Any]) -> dict[str, Any]:
    """Handle casual chat without document retrieval."""
    import openai as oai
    from app.config import get_settings

    settings = get_settings()
    client = oai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly and helpful Enterprise AI Assistant. "
                        "Respond naturally to greetings and casual conversation. "
                        "If the user seems to have a document-related question, "
                        "suggest they ask it clearly so you can search the knowledge base."
                    ),
                },
                {"role": "user", "content": state["query"]},
            ],
            temperature=0.7,
            max_tokens=512,
        )
        answer = response.choices[0].message.content or ""
        return {
            "response": RAGResponse(answer=answer, confidence=1.0)
        }
    except Exception as exc:
        return {
            "response": RAGResponse(answer=f"Sorry, I encountered an error: {exc}", confidence=0.0)
        }


# ── Routing logic ───────────────────────────────────────────────────────────

def route_by_intent(state: dict[str, Any]) -> str:
    """Route to the correct handler based on classified intent."""
    intent = state.get("intent", "question")
    route_map = {
        "question": "retrieve_context",
        "summarize": "retrieve_context",
        "translate": "translate",
        "chat": "chat_response",
    }
    return route_map.get(intent, "retrieve_context")


def route_after_retrieval(state: dict[str, Any]) -> str:
    """After retrieval, route to the appropriate generator."""
    intent = state.get("intent", "question")
    if intent == "summarize":
        return "summarize"
    # Check if this looks like a complex query needing research
    docs = state.get("documents", [])
    if docs and len(docs) >= 8:
        return "generate_response"
    return "generate_response"


# ── Graph construction ──────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph state graph.

    Returns
    -------
    StateGraph
        A compiled graph ready for invocation.
    """
    graph = StateGraph(dict)

    # Add nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("research", research_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("translate", translate_node)
    graph.add_node("generate_response", generate_response)
    graph.add_node("chat_response", chat_response)

    # Entry point
    graph.set_entry_point("classify_intent")

    # Conditional routing from intent classifier
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "retrieve_context": "retrieve_context",
            "translate": "translate",
            "chat_response": "chat_response",
        },
    )

    # After retrieval, route to generator or summarizer
    graph.add_conditional_edges(
        "retrieve_context",
        route_after_retrieval,
        {
            "summarize": "summarize",
            "generate_response": "generate_response",
        },
    )

    # Terminal nodes
    graph.add_edge("generate_response", END)
    graph.add_edge("summarize", END)
    graph.add_edge("translate", END)
    graph.add_edge("chat_response", END)
    graph.add_edge("research", END)

    return graph.compile()


# Module-level compiled graph
agent_graph = build_agent_graph()
