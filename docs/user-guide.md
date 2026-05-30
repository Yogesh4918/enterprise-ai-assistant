# User Guide

## Getting Started

### 1. Register an Account

1. Navigate to http://localhost:3000/register
2. Fill in your name, email, and password
3. Click "Create Account"
4. You'll be redirected to the chat interface

### 2. Upload Documents

Before you can ask questions about your documents, you need to upload them:

1. Click the **Documents** link in the sidebar
2. Drag and drop files (PDF, DOCX, TXT) onto the upload area, or click to browse
3. Wait for processing — the status will change from "Processing" to "Indexed"
4. Once indexed, your documents are searchable!

**Supported formats:**
- PDF files (including scanned documents with OCR)
- DOCX (Microsoft Word)
- TXT (plain text)

**Size limit:** 50 MB per file

### 3. Chat with Your Documents

1. Click **New Chat** in the sidebar
2. Type a question about your uploaded documents
3. The AI will search your documents, find relevant passages, and generate an answer
4. Look for **citations** [1][2] in the response — click them to see the source

### 4. Understanding the Interface

#### Chat Area
- **User messages** appear on the right in accent-colored bubbles
- **AI responses** appear on the left with markdown formatting
- **Citations** are shown as numbered badges — click to see the source
- **Confidence score** is shown below each AI response

#### Sidebar
- **New Chat** — Start a fresh conversation
- **Chat History** — Click any conversation to continue it
- **Search** — Find past conversations
- **Delete** — Remove conversations you no longer need

#### Input Bar
- **Text Input** — Type your message and press Enter to send
- **Shift+Enter** — New line without sending
- **Microphone** — Click for voice input
- **Paperclip** — Attach a file to your message

### 5. Voice Features

#### Voice Input
1. Click the microphone icon in the input bar
2. Speak your question
3. Click again to stop recording
4. Your speech will be transcribed and sent as a message

#### Voice Output
- AI responses can be played back as audio
- Click the speaker icon on any AI response to hear it

### 6. Advanced Features

#### Agent Types
The AI automatically routes your queries to specialized agents:

- **Research Agent** — For complex questions requiring multi-step research
- **Summarization Agent** — When you ask to summarize a document
- **Translation Agent** — When you need content in a different language
- **General Chat** — For casual conversation without document retrieval

#### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Shift+Enter | New line |
| Ctrl+N | New conversation |
| Ctrl+/ | Focus search |

---

## FAQ

**Q: How accurate are the responses?**
A: The AI always cites its sources. Check the confidence score — green (>80%) means high confidence, yellow (50-80%) means moderate, red (<50%) means the AI is less certain.

**Q: Can I upload multiple documents?**
A: Yes! Upload as many documents as you need. The AI will search across all your indexed documents.

**Q: What languages are supported?**
A: The system supports multilingual queries. You can ask questions in English, Spanish, French, German, Chinese, Japanese, and many more languages.

**Q: How is my data stored?**
A: Documents are chunked and stored as vectors in Qdrant. Original files are stored securely on the server. All data is isolated per user.

**Q: Can I delete my data?**
A: Yes. Delete individual documents from the Documents page, or delete conversations from the sidebar.
