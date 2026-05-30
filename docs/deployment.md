# Deployment Guide

## Local Development (Docker Compose)

### Prerequisites
- Docker Desktop 4.x+
- Docker Compose v2.x+
- OpenAI API key

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — set OPENAI_API_KEY at minimum

# 2. Build and launch
docker-compose up --build -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f
```

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Chat UI |
| Backend | http://localhost:8000 | API Server |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Qdrant | http://localhost:6333/dashboard | Vector DB UI |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |

### Development Mode

For hot-reloading during development:

```bash
# Start infrastructure only
docker-compose up -d postgres redis qdrant

# Run backend with hot reload
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Run frontend with hot reload
cd frontend
npm install
npm run dev
```

---

## Google Cloud Platform (GCP) Deployment

### Architecture on GCP

```
Cloud Run (Backend) ← Cloud SQL (PostgreSQL)
     ↕                    
Cloud Run (Frontend) ← Memorystore (Redis)
     ↕
Qdrant Cloud or GKE ← Cloud Storage (Files)
```

### Step 1: Setup GCP Project

```bash
# Create project
gcloud projects create rag-assistant --name="RAG Assistant"
gcloud config set project rag-assistant

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### Step 2: Create Infrastructure

```bash
# Cloud SQL (PostgreSQL)
gcloud sql instances create rag-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_DB_PASSWORD

gcloud sql databases create ragchat --instance=rag-db

# Memorystore (Redis)
gcloud redis instances create rag-cache \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

### Step 3: Build & Push Images

```bash
# Backend
docker build -t gcr.io/rag-assistant/backend ./backend
docker push gcr.io/rag-assistant/backend

# Frontend
docker build -t gcr.io/rag-assistant/frontend ./frontend
docker push gcr.io/rag-assistant/frontend
```

### Step 4: Deploy to Cloud Run

```bash
# Deploy backend
gcloud run deploy rag-backend \
  --image gcr.io/rag-assistant/backend \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=sk-...,DATABASE_URL=postgresql+asyncpg://..."

# Deploy frontend
gcloud run deploy rag-frontend \
  --image gcr.io/rag-assistant/frontend \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_API_URL=https://rag-backend-xxxxx.run.app"
```

### Step 5: Qdrant Deployment

**Option A: Qdrant Cloud (Recommended)**
1. Sign up at https://cloud.qdrant.io
2. Create a cluster
3. Set `QDRANT_HOST` and `QDRANT_API_KEY` in Cloud Run env vars

**Option B: GKE Self-hosted**
```bash
# Create GKE cluster
gcloud container clusters create qdrant-cluster \
  --num-nodes=2 \
  --machine-type=e2-standard-2

# Deploy Qdrant via Helm
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm install qdrant qdrant/qdrant
```

---

## Production Checklist

### Security
- [ ] Change JWT_SECRET_KEY to a strong random value
- [ ] Set DEBUG=false
- [ ] Restrict CORS_ORIGINS to your domain
- [ ] Enable HTTPS (handled by Cloud Run)
- [ ] Use GCP Secret Manager for API keys
- [ ] Set up VPC connector for private database access

### Performance
- [ ] Set appropriate Cloud Run min/max instances
- [ ] Configure Redis maxmemory policy
- [ ] Create PostgreSQL indexes on frequently queried columns
- [ ] Enable Qdrant HNSW index optimization
- [ ] Set up CDN for frontend static assets

### Monitoring
- [ ] Enable Cloud Run metrics
- [ ] Set up Cloud Logging filters
- [ ] Configure uptime checks
- [ ] Set up alerting for error rates
- [ ] Enable LangSmith tracing for RAG pipeline

### Backup
- [ ] Configure Cloud SQL automated backups
- [ ] Set up Qdrant snapshot scheduling
- [ ] Export Redis data periodically
