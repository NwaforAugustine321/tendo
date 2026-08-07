# Tendo Voice Agent

Real-time voice AI assistant for Tendo, built with [LiveKit Agents](https://docs.livekit.io/agents/).

## Architecture

The agent uses a **voice pipeline** approach:

```
User Speech → STT (Deepgram Nova 3) → LLM (Gemma 4 31B) → TTS (Cartesia Sonic 3) → Audio Response
```

Key components:
- **STT**: Deepgram Nova 3 — multilingual speech-to-text
- **LLM**: Google Gemma 4 31B — reasoning and response generation (via LiveKit Inference)
- **TTS**: Cartesia Sonic 3 — natural voice synthesis
- **Turn Detection**: LiveKit Turn Detector — acoustic + semantic end-of-turn detection
- **Noise Cancellation**: ai_coustics QUAIL — background noise removal

## Prerequisites

1. A [LiveKit Cloud](https://cloud.livekit.io/) account (free tier available)
2. Python 3.10+
3. [uv](https://docs.astral.sh/uv/) package manager (recommended)

## Setup

1. Copy the environment template and add your LiveKit credentials:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your credentials from [LiveKit Cloud](https://cloud.livekit.io/):

```
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

2. Install dependencies:

```bash
uv sync
```

## Running

### Console mode (talk directly in terminal)

```bash
uv run python src/agent.py console
```

### Development mode (for use with frontend)

```bash
uv run python src/agent.py dev
```

### Production mode

```bash
uv run python src/agent.py start
```

## Frontend Integration

Connect any LiveKit frontend to this agent:

- **Web (React)**: [agent-starter-react](https://github.com/livekit-examples/agent-starter-react)
- **iOS/macOS**: [agent-starter-swift](https://github.com/livekit-examples/agent-starter-swift)
- **Flutter**: [agent-starter-flutter](https://github.com/livekit-examples/agent-starter-flutter)
- **Android**: [agent-starter-android](https://github.com/livekit-examples/agent-starter-android)

Or use the [LiveKit Playground](https://cloud.livekit.io/) to test immediately.

## Customization

### Change the LLM

Edit `src/agent.py` and swap the model:

```python
# Use OpenAI
llm=inference.LLM(model="openai/gpt-4o-mini")

# Use Anthropic
llm=inference.LLM(model="anthropic/claude-sonnet-4-20250514")
```

### Change the Voice

Browse voices at [LiveKit TTS docs](https://docs.livekit.io/agents/models/tts/) and update the voice ID:

```python
tts=inference.TTS(
    model="cartesia/sonic-3",
    voice="your-voice-id",
)
```

### Use a Realtime Model (instead of pipeline)

For lower latency with OpenAI's Realtime API:

```python
from livekit.plugins import openai

# Replace the llm argument in TendoAssistant.__init__:
llm=openai.realtime.RealtimeModel(voice="marin")

# And remove stt/tts from AgentSession (the realtime model handles both)
```

### Add Tools

Add methods to `TendoAssistant` with the `@function_tool` decorator:

```python
@function_tool
async def my_tool(self, context: RunContext, param: str):
    """Description of what this tool does.

    Args:
        param: Description of the parameter
    """
    # Your implementation
    return "result"
```

## Deployment

### Docker

```bash
docker build -t tendo-voice-agent .
docker run --env-file .env.local tendo-voice-agent
```

### LiveKit Cloud

See the [deployment guide](https://docs.livekit.io/deploy/agents/).

## Documentation

- [LiveKit Agents Overview](https://docs.livekit.io/agents/)
- [Voice AI Quickstart](https://docs.livekit.io/agents/start/voice-ai-quickstart)
- [Available Models](https://docs.livekit.io/agents/models/)
- [Building with Tools](https://docs.livekit.io/agents/build/tools/)
- [Turn Detection](https://docs.livekit.io/agents/build/turns/)
