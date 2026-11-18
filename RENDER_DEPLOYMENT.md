# Deploying MedReason to Render (single service)

> **Academic demonstration only — not for clinical use.**

One Render **Web Service** runs both the React UI and the FastAPI backend.

## Form values

| Field | Value |
| :--- | :--- |
| **Root Directory** | `.` (leave the default — do **not** set `frontend` or `backend`) |
| **Runtime / Language** | Python |
| **Build Command** | `pip install -r backend/requirements.txt && npm --prefix frontend install && npm --prefix frontend run build` |
| **Start Command** | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free (512 MB RAM) is enough |

The **Start Command is required** — leaving it empty produces `Required` and
`There are errors above. Please fix them to continue.`

The app serves the built React app from `frontend/dist` at `/`, the API at
`/api`, and Swagger docs at `/docs`. Routes registered by the API always take
priority, so there is no conflict with the SPA fallback.

## Environment Variables (Render → Environment)

### Simplest, guaranteed-working setup (no external database)

| Name | Value |
| :--- | :--- |
| `LLM_PROVIDER` | `mock` |
| `VISION_PROVIDER` | `mock` |
| `SPEECH_PROVIDER` | `local` |
| `EMBEDDING_PROVIDER` | `hashing_cosine` |
| `STORAGE_BACKEND` | `local` |

With these values the app uses local SQLite and a local uploads folder. Uploads,
retrieval, dataset analytics, citations and decision reports all work. **Data is
reset on each redeploy/restart** — fine for a demo.

### Persistent setup (hosted Postgres)

Add these instead, using the **real** Neon connection string (never the
`USER:PASSWORD@EP-HOST` placeholder):

| Name | Value |
| :--- | :--- |
| `DATABASE_URL` | `postgresql+pg8000://<user>:<password>@<real-host>/medreason?sslmode=require` |
| `STORAGE_BACKEND` | `database` |

Keep `?sslmode=require` — the app converts it to pg8000's `ssl_context`
automatically. Tables are created on startup. Never put keys or DB passwords
in `render.yaml` or committed files; use Render's Environment tab.

### Optional live providers (paid instance recommended)

| Name | Value |
| :--- | :--- |
| `LLM_PROVIDER` | `groq` |
| `LLM_MODEL` | `qwen/qwen3.8-27b` |
| `LLM_API_KEY` | your Groq key |
| `VISION_PROVIDER` | `gemini` |
| `VISION_MODEL` | `gemini-flash-lite-latest` |
| `VISION_API_KEY` | your Gemini key |

## Verify

After the deploy is **Live**:

1. `https://<your-service>.onrender.com/api/health` → JSON with `"status": "healthy"`.
2. The site root → MedReason welcome screen.
3. Upload a note or CSV, then ask a question — answers include grounded citations.

If you changed environment variables, use **Manual Deploy → Deploy latest commit**
(or restart the service) so they take effect.
