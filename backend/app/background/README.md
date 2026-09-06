## Run

```bash
cd backend/app/background
python -m app.background.worker_process
```

## Run With Control

```bash
cd backend/app/background
BACKGROUND_WORKERS=8 python -m app.background.worker_process
```
