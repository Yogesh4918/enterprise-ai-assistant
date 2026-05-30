# 🤖 Enterprise Multilingual AI Assistant

> A production-ready Retrieval-Augmented Generation (RAG) chatbot with multilingual NLP, voice AI, LangGraph agents, hybrid search, and a Claude/ChatGPT-style interface.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-0.3-orange)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)

---

## ✨ Features

### 🧠 RAG Pipeline
- **Document Ingestion** — Upload PDF, DOCX, TXT files or crawl websites
- **Hybrid Search** — Dense (semantic) + Sparse (BM25) vector retrieval via Qdrant
- **Re-ranking** — Cross-encoder reranking for precision
- **Citations** — Source attribution with page numbers and confidence scores
- **Query Rewriting** — LLM-powered query optimization for better retrieval
- **MMR Retrieval** — Maximal Marginal Relevance for diverse results

### 🤖 LangGraph Agents
- **Router Agent** — Intent classification and query routing
- **Research Agent** — Multi-step research with iterative retrieval
- **Summarization Agent** — Document summarization (extractive + abstractive)
- **Translation Agent** — Cross-language query and response handling

### 💬 Claude-Style Chat UI
- **Streaming Responses** — Real-time token-by-token streaming via WebSocket
- **Markdown Rendering** — Full markdown + syntax highlighting + LaTeX
- **Dark Mode** — Premium dark theme with glassmorphism effects
- **Sidebar** — Chat history, search, conversation management
- **Responsive** — Works on desktop and mobile

### 🎤 Voice Intelligence
- **Speech-to-Text** — Faster-Whisper for audio transcription
- **Text-to-Speech** — ElevenLabs/Coqui for audio responses
- **Language Detection** — Auto-detect spoken language

### 🌍 Multilingual NLP
- **Language Detection** — Automatic language identification
- **NER** — Named Entity Recognition across languages
- **Sentiment Analysis** — Polarity and subjectivity scoring
- **Keyword Extraction** — Automatic key term identification

### 🔒 Enterprise Security
- **JWT Authentication** — Secure token-based auth
- **Role-Based Access Control** — Admin and user roles
- **Rate Limiting** — API request throttling

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│            Next.js 15 + Tailwind v4              │
│            + ShadCN/UI Components                │
└──────────────┬──────────────┬───────────────────┘
               │ REST API     │ WebSocket
┌──────────────▼──────────────▼───────────────────┐
│                   Backend                        │
│              FastAPI + LangGraph                 │
│         ┌────────────────────────┐               │
│         │    RAG Pipeline        │               │
│         │  Ingest→Chunk→Embed    │               │
│         │  →Retrieve→Rerank      │               │
│         │  →Generate w/ Citations│               │
│         └────────────────────────┘               │
└───────┬──────────┬──────────┬───────────────────┘
        │          │          │
   ┌────▼────┐ ┌───▼───┐ ┌───▼────┐
   │ Qdrant  │ │Postgres│ │ Redis  │
   │ Vectors │ │Metadata│ │ Cache  │
   └─────────┘ └───────┘ └────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [OpenAI API Key](https://platform.openai.com/api-keys)

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd Gpt

# Copy environment template
cp .env.example .env

# Edit .env and set your API keys
# At minimum, set OPENAI_API_KEY
```

### 2. Launch with Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Access the Application

| Service | URL |
|---------|-----|
| **Frontend (Chat UI)** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **Qdrant Dashboard** | http://localhost:6333/dashboard |

### 4. First Steps

1. Register an account at http://localhost:3000/register
2. Upload documents via the Documents page
3. Start chatting! Ask questions about your documents
4. Try voice input with the microphone button

---

## 🛠️ Development Setup

### Backend (Python)

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Node.js)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Infrastructure (Docker)

```bash
# Start only infrastructure services
docker-compose up -d postgres redis qdrant
```

---

## 📁 Project Structure

```
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py             # App entry point
│   │   ├── config.py           # Environment config
│   │   ├── database.py         # PostgreSQL setup
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── api/                # REST & WebSocket routes
│   │   ├── services/           # Business logic
│   │   ├── rag/                # RAG pipeline
│   │   ├── agents/             # LangGraph agents
│   │   └── nlp/                # NLP services
│   ├── tests/                  # Test suite
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/                # Pages (App Router)
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom hooks
│   │   ├── stores/             # Zustand state
│   │   ├── lib/                # Utilities
│   │   └── types/              # TypeScript types
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml          # Full stack orchestration
├── .env.example                # Config template
└── docs/                       # Documentation
```

---

## 🔌 API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Get current user |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Create conversation |
| GET | `/api/chat` | List conversations |
| GET | `/api/chat/{id}` | Get conversation |
| DELETE | `/api/chat/{id}` | Delete conversation |
| POST | `/api/chat/{id}/message` | Send message |
| WS | `/ws/chat/{id}` | Streaming chat |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload document |
| GET | `/api/documents` | List documents |
| GET | `/api/documents/{id}/status` | Check status |
| DELETE | `/api/documents/{id}` | Delete document |

### Voice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voice/transcribe` | Audio → Text |
| POST | `/api/voice/synthesize` | Text → Audio |

---

## ☁️ Cloud Deployment (GCP)

### Google Cloud Run

```bash
# Build and push images
docker build -t gcr.io/PROJECT_ID/rag-backend ./backend
docker build -t gcr.io/PROJECT_ID/rag-frontend ./frontend
docker push gcr.io/PROJECT_ID/rag-backend
docker push gcr.io/PROJECT_ID/rag-frontend

# Deploy backend
gcloud run deploy rag-backend \
  --image gcr.io/PROJECT_ID/rag-backend \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=..." \
  --memory 2Gi

# Deploy frontend
gcloud run deploy rag-frontend \
  --image gcr.io/PROJECT_ID/rag-frontend \
  --platform managed \
  --allow-unauthenticated
```

### Managed Services (Recommended for Production)
- **PostgreSQL** → Cloud SQL
- **Redis** → Memorystore for Redis
- **Qdrant** → Qdrant Cloud or GKE deployment
- **File Storage** → Cloud Storage

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v --cov=app

# Frontend tests
cd frontend
npm test

# E2E tests
npx playwright test
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ using LangChain, FastAPI, Next.js, and OpenAI
</p>
