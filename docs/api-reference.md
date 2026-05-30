# API Reference

## Base URL

- **Local Development:** `http://localhost:8000`
- **Production:** `https://your-domain.com`

## Authentication

All endpoints except `/api/auth/register` and `/api/auth/login` require a JWT token.

Include the token in the `Authorization` header:
```
Authorization: Bearer <your-jwt-token>
```

---

## Auth Endpoints

### POST `/api/auth/register`

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST `/api/auth/login`

Authenticate and receive JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST `/api/auth/refresh`

Refresh an expired access token.

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

### GET `/api/auth/me`

Get current authenticated user profile.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Chat Endpoints

### POST `/api/chat`

Create a new conversation.

**Request Body:**
```json
{
  "title": "My Research Question"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "title": "My Research Question",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### GET `/api/chat`

List all conversations for the current user.

**Query Parameters:**
- `skip` (int, default: 0) — Pagination offset
- `limit` (int, default: 50) — Max results

**Response (200):**
```json
[
  {
    "id": "uuid",
    "title": "My Research Question",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "message_count": 5
  }
]
```

### GET `/api/chat/{id}`

Get a conversation with all messages.

**Response (200):**
```json
{
  "id": "uuid",
  "title": "My Research Question",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "What does the report say about revenue?",
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "According to the report [1], revenue increased by 15%...",
      "citations": [
        {
          "index": 1,
          "source": "annual-report.pdf",
          "page": 12,
          "chunk_text": "Revenue for Q4 2024 showed a 15% increase...",
          "relevance_score": 0.92
        }
      ],
      "confidence_score": 0.89,
      "created_at": "2024-01-01T00:00:01Z"
    }
  ]
}
```

### POST `/api/chat/{id}/message`

Send a message and get AI response (non-streaming).

**Request Body:**
```json
{
  "content": "What does the report say about revenue?"
}
```

### DELETE `/api/chat/{id}`

Delete a conversation and all its messages.

### PATCH `/api/chat/{id}`

Update conversation title.

**Request Body:**
```json
{
  "title": "Revenue Analysis Chat"
}
```

---

## WebSocket Chat

### WS `/ws/chat/{conversation_id}`

Real-time streaming chat via WebSocket.

**Connection:**
```
ws://localhost:8000/ws/chat/{conversation_id}?token={jwt_token}
```

**Send Message:**
```json
{
  "type": "message",
  "content": "What does the report say?"
}
```

**Receive Events:**
```json
{"type": "token", "data": "According"}
{"type": "token", "data": " to"}
{"type": "token", "data": " the report"}
{"type": "citation", "data": {"index": 1, "source": "report.pdf", "page": 5}}
{"type": "confidence", "data": 0.89}
{"type": "done", "data": null}
```

---

## Document Endpoints

### POST `/api/documents/upload`

Upload a document for processing.

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `file` — The document file (PDF, DOCX, TXT)

**Response (201):**
```json
{
  "id": "uuid",
  "filename": "report.pdf",
  "file_type": "pdf",
  "file_size": 1048576,
  "status": "processing",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### GET `/api/documents`

List all documents for the current user.

### GET `/api/documents/{id}/status`

Check document processing status.

**Response (200):**
```json
{
  "id": "uuid",
  "filename": "report.pdf",
  "status": "indexed",
  "chunk_count": 42,
  "language": "en"
}
```

### DELETE `/api/documents/{id}`

Delete a document and its vector data.

---

## Voice Endpoints

### POST `/api/voice/transcribe`

Transcribe audio to text.

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `audio` — Audio file (WAV, MP3, WebM)

**Response (200):**
```json
{
  "text": "What does the report say about revenue?",
  "language": "en",
  "confidence": 0.95
}
```

### POST `/api/voice/synthesize`

Convert text to speech audio.

**Request Body:**
```json
{
  "text": "According to the report, revenue increased by 15%.",
  "language": "en"
}
```

**Response:** Audio file (MP3)

---

## Health Check

### GET `/api/health`

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "qdrant": "connected"
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request — Invalid input |
| 401 | Unauthorized — Missing or invalid token |
| 403 | Forbidden — Insufficient permissions |
| 404 | Not Found — Resource doesn't exist |
| 413 | Payload Too Large — File exceeds limit |
| 422 | Unprocessable Entity — Validation error |
| 429 | Too Many Requests — Rate limit exceeded |
| 500 | Internal Server Error — Server-side failure |
