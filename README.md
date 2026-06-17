# Tendo

AI Business Operating System — an adaptive intelligence platform that learns how your business operates through natural voice and text conversations.

## Setup

### Backend

```bash
cd backend
conda env create -f environment.yml
conda activate tendo
cp .env.example .env
# Fill in your API keys in .env
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`.

**Endpoints:**
- `GET /health` — health check
- `POST /events` — unified event ingress
- `WS /ws/voice` — real-time voice-to-voice

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

### Environment Variables (backend/.env)

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
MEM0_API_KEY=
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=
GOOGLE_VOICE_API_KEY=
SPEC_HOT_RELOAD=true
```

## Project Structure

```
tendo/
├── frontend/          # React + TypeScript + Vite + Tailwind v4
├── backend/           # Python + FastAPI + LangGraph
│   ├── app/
│   │   ├── ws/            # WebSocket service module
│   │   ├── communication/ # Voice + delivery + layer
│   │   ├── db/            # Database access layer
│   │   ├── memory/        # Conversation memory
│   │   ├── redis/         # Cache + checkpointer
│   │   ├── llm/           # LLM client + spec loader
│   │   ├── agents/        # Agent specs (.md files)
│   │   └── graph/         # LangGraph workflow + nodes
│   └── environment.yml
└── README.md
```
