# Tendo

AI Business Operating System — an adaptive intelligence platform that learns how your business operates through natural voice and text conversations.

## Setup

### Backend

```bash
cd backend

# Create conda environment
conda env create -f environment.yml

# Activate the environment
conda activate tendo_v2

# Copy env file and fill in your API keys
cp .env.example .env

# Run the server
uvicorn app.main:asgi_app --reload
python -m uvicorn app.main:asgi_app --reload


# kill running app
kill -9 $(lsof -t -i:8000)
cloudflared tunnel --protocol quic --url http://localhost:5173
python3  voice_worker.py dev
python -m app.livekit.worker dev
https://merchandise-ranges-methods-lots.trycloudflare.com/api/integrations/webhook/whatsapp
```

To update the environment after changes to `environment.yml`:

```bash
conda env update -f environment.yml --prune
```

The backend runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

# Important doc - https://docs.nvidia.com/rag/latest/?utm_source=chatgpt.com

https://docs.nvidia.com/rag/latest/api-key.html
