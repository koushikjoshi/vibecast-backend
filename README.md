# VibeCast — Backend

FastAPI service that orchestrates the VibeCast newsroom-of-agents and publishes
finished episodes to an RSS feed. See [`PRD.md`](../PRD.md) in the parent
workspace for the product spec.

## Stack

- **FastAPI** + Uvicorn (async HTTP + SSE for live trace streaming)
- **SQLAlchemy** (async) + **SQLite** for persistence and observability
- **OpenAI / Anthropic** SDKs for agent LLM calls
- **ElevenLabs** (primary) + OpenAI TTS (fallback) for host voices
- **feedgen** for RSS 2.0 / iTunes-tagged podcast feed
- **ffmpeg** (via Docker base image) for audio mixing and 30s clip export

## Layout

```
vibecast-backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # pydantic-settings env
│   ├── routes/              # HTTP routers
│   ├── agents/              # agent definitions (editor, researcher, …)
│   ├── services/            # TTS, RSS, memory, media
│   ├── observability/       # SQLite trace writer
│   └── models/              # ORM + pydantic models
├── prompts/                 # version-controlled prompt templates
├── hosts/                   # host persona files (md + yaml frontmatter)
├── evals/                   # 10-topic eval set + runner
├── public/stings/           # royalty-free audio stings
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Local dev

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in OPENAI_API_KEY + ELEVENLABS_API_KEY
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health`

## Docker

```bash
docker build -t vibecast-backend .
docker run -p 8000:8000 --env-file .env vibecast-backend
```

## Deployment

Deployed on a Hostinger VPS via **Coolify**. Coolify pulls this repo, builds the
`Dockerfile`, injects env vars, and exposes the service behind its built-in
Traefik reverse proxy with auto-issued Let's Encrypt certs.

See [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for the full deploy playbook.

## API surface (stubs)

| Method | Path                    | Purpose                                 |
|-------:|-------------------------|-----------------------------------------|
| GET    | `/health`               | Liveness / readiness                    |
| GET    | `/feed.xml`             | Public podcast RSS (Spotify/Apple/…)    |
| GET    | `/api/episodes`         | List episodes                           |
| GET    | `/api/episodes/{id}`    | Episode detail (audio, transcript, …)   |
| POST   | `/api/runs`             | Kick off a new Make-Your-Own run        |
| GET    | `/api/runs/{id}/stream` | SSE live trace of an in-flight run      |
| GET    | `/api/hosts`            | List hosts in the roster                |
| GET    | `/api/traces`           | List past runs                          |
| GET    | `/api/traces/{id}`      | Full step tree of one run               |
