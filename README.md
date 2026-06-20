# Tendo

AI Business Operating System — an adaptive intelligence platform that learns how your business operates through natural voice and text conversations.

## Setup

### Backend

```bash
cd backend

# Create conda environment 
conda env create -f environment.yml

# Activate the environment
conda activate tendo

# Copy env file and fill in your API keys
cp .env.example .env

# Run the server
uvicorn app.main:asgi_app --reload
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
