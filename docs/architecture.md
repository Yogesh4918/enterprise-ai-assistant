# Architecture Documentation

## System Overview

The Enterprise AI Assistant is a multi-service application built as a monorepo with three main layers:

1. **Frontend** — Next.js 15 with Claude-style conversational UI
2. **Backend** — FastAPI with RAG pipeline, LangGraph agents, and NLP services
3. **Infrastructure** — Qdrant, PostgreSQL, Redis in Docker containers

## Data Flow

### Document Ingestion Flow
```
User uploads file → FastAPI receives multipart → DocumentLoader parses file
→ TextChunker splits into chunks → EmbeddingService generates vectors
→ QdrantVectorStore upserts chunks + vectors → PostgreSQL stores metadata
→ Status updated to "indexed"
```

### Query Processing Flow
```
User sends message → WebSocket receives → Router Agent classifies intent
→ HybridRetriever fetches relevant chunks (dense + sparse search)
→ Reranker scores and filters results → RAGChain generates response
→ Citations extracted → Confidence score calculated
→ Response streamed back token-by-token via WebSocket
→ Message saved to PostgreSQL → Memory updated in Redis
```

### Agent Orchestration (LangGraph)
```
User query → Router Node (classify intent)
  ├─ "question" → Research Agent → Retrieve → Rerank → Generate
  ├─ "summarize" → Summarization Agent → Retrieve all docs → Summarize
  ├─ "translate" → Translation Agent → Detect lang → Retrieve → Translate → Respond
  └─ "chat" → Direct LLM → Generate response
```

## Key Design Decisions

### Why Qdrant over ChromaDB/FAISS?
- Native hybrid search with Reciprocal Rank Fusion (RRF)
- Production-ready with horizontal scaling
- Built-in multi-tenancy via collections
- Excellent Docker support with persistence

### Why OpenAI text-embedding-3-small?
- Best cost/performance ratio for production
- 1536 dimensions, strong multilingual support
- Native integration with LangChain

### Why LangGraph over simple LangChain chains?
- Stateful agent orchestration with cycles
- Conditional routing based on intent
- Self-correction loops (retrieve → grade → rewrite → retrieve)
- Built-in persistence and checkpointing

### Why WebSocket over SSE for streaming?
- Bidirectional communication (send messages while receiving)
- Lower overhead for long-running conversations
- Better support for real-time features (typing indicators)

## Security Model

- JWT tokens with HS256 signing
- Access tokens expire in 30 minutes
- Refresh tokens expire in 7 days
- Passwords hashed with bcrypt (12 rounds)
- RBAC with admin/user roles
- WebSocket authentication via query parameter token
- CORS restricted to frontend origin
- Rate limiting per IP/user
