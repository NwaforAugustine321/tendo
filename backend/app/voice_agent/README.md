# Voice Agent

## Setup

```bash
conda env create -f environment.yml
conda activate voice-agent
```

## Run

```bash
cd backend/app/voice_agent
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```
