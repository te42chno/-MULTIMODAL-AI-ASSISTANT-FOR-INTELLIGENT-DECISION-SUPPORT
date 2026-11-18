# Deploying MedReason to Vercel

This guide deploys the **entire application** to Vercel: the React UI as a static site and the FastAPI backend as a Python serverless function, both on one domain.

> **Academic demonstration only — not for clinical use.**

---

## How it works on Vercel

| Concern | Local development | Vercel deployment |
| :--- | :--- | :--- |
| Frontend | Vite dev server on `:5173` | Static build served by Vercel |
| API | Uvicorn on `:8000` | Python function via Mangum at `/api/*` |
| Database | SQLite file on disk | **Hosted Postgres** (required) |
| Uploads | Files written to `backend/data/uploads` | Bytes stored in Postgres; staged to `/tmp` per request |
| API URL | `http://127.0.0.1:8000/api` | Same-origin `/api` (automatic) |

The relevant files are:

- `vercel.json` — build command, `/api` rewrite, function settings
- `api/index.py` — Mangum ASGI adapter (Vercel function entrypoint)
- `requirements.txt` — Python dependencies for the Vercel function
- `backend/app/services/storage_service.py` — local/database storage abstraction
- `.vercelignore` — keeps `node_modules`, local data and docs out of the upload

### Function size (kept under Vercel's 500 MB limit)

The root `requirements.txt` deliberately installs only lightweight packages (about 97 MB installed). Heavy ML wheels — NumPy, pandas, scikit-learn, SciPy, OpenCV and SpeechRecognition — are **not bundled**. Each affected service detects whether those libraries are present:

- **Locally** (full `backend/requirements.txt` installed): the original scikit-learn embeddings, pandas analytics, OpenCV vision/frame extraction and SpeechRecognition run exactly as before — no change in answers or behaviour.
- **On Vercel**: dependency-free fallbacks activate automatically (hashing embeddings, CSV/Excel analytics with `statistics`, Pillow colour palette, metadata-only video/speech results).

If Vercel reports a bundle-size error again, confirm the root `requirements.txt` has not been expanded and that `.vercelignore` is present.

> **Deployment check:** the fix is in commit `336101f`. In Vercel → Deployments, the newest deployment must show this commit hash (or a later one). If it shows `afb2b6c` or `40243fd`, you are looking at an old deployment — redeploy from `main`.

---

## Important: read this before deploying

Vercel **Hobby** functions are limited to about **10 seconds** per request. Groq and Gemini calls can take up to 45 seconds, so live API calls will time out on Hobby.

- On **Hobby**, use the offline providers (`LLM_PROVIDER=mock`, `VISION_PROVIDER=mock`). The whole app — uploads, retrieval, dataset analytics, citations and offline decision reports — works instantly and reliably.
- On **Pro**, set the providers to `groq` / `gemini`, add your keys, and raise `maxDuration` in `vercel.json` from `10` to `60`.

There is no workaround for this on Hobby; it is a platform limit.

---

## Step 1 — Create a free Postgres database

The SQLite file cannot survive serverless invocations, so you need a hosted Postgres database.

1. Create a free account at [Neon](https://neon.tech) (or Supabase / any Postgres host).
2. Create a database, e.g. `medreason`.
3. Copy the **connection string**. It looks like:

   ```text
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/medreason
   ```

4. Convert it to the pg8000 dialect Vercel will use:

   ```text
   postgresql+pg8000://user:password@ep-xxx.us-east-2.aws.neon.tech/medreason?sslmode=require
   ```

   Replace `postgres://` / `postgresql://` with `postgresql+pg8000://` and keep `sslmode=require`.

> **Keep `?sslmode=require` in the string.** The app now translates it into pg8000's `ssl_context` automatically, so older `TypeError: connect() got an unexpected keyword argument 'sslmode'` errors are resolved.
>
> **Use the real Neon string — not a placeholder.** Values such as `USER:PASSWORD@EP-HOST` are examples only. If the host is literally `EP-HOST`, the app cannot resolve it and every request will fail with `getaddrinfo failed` / `Can't create a connection to host EP-HOST`. Copy the actual connection string from your Neon dashboard.

> Tables are created automatically on the first request via `Base.metadata.create_all()`. No manual migration is needed.

---

## Step 2 — Import the repository into Vercel

1. Go to [Vercel → Add New → Project](https://vercel.com/new).
2. Import `https://github.com/te42chno/-MULTIMODAL-AI-ASSISTANT-FOR-INTELLIGENT-DECISION-SUPPORT.git`.
3. Use these settings:
   - **Framework Preset:** Other
   - **Root Directory:** leave as the repository root (`.`)
   - **Build Command:** `npm --prefix frontend install && npm --prefix frontend run build`
   - **Output Directory:** `frontend/dist`
   - **Install Command:** leave default

   These are already declared in `vercel.json`, so Vercel should fill them in automatically. Do **not** set the root directory to `frontend`, or the `/api` function will not be included.

4. Add the environment variables below before deploying.

---

## Step 3 — Environment variables

In **Project Settings → Environment Variables**, add:

### Required

| Name | Value |
| :--- | :--- |
| `DATABASE_URL` | The `postgresql+pg8000://...` string from Step 1 |
| `STORAGE_BACKEND` | `database` |
| `LLM_PROVIDER` | `mock` on Hobby, `groq` on Pro |
| `VISION_PROVIDER` | `mock` on Hobby, `gemini` on Pro |
| `SPEECH_PROVIDER` | `local` |
| `EMBEDDING_PROVIDER` | `hashing_cosine` |

### Only when using live providers (Pro)

| Name | Value |
| :--- | :--- |
| `LLM_MODEL` | `qwen/qwen3.8-27b` |
| `LLM_API_KEY` | your Groq key |
| `VISION_MODEL` | `gemini-flash-lite-latest` |
| `VISION_API_KEY` | your Gemini key |

### Optional

| Name | Value | Purpose |
| :--- | :--- | :--- |
| `TEMP_DIR` | `/tmp/medreason` | Where upload bytes are staged within a request |
| `MAX_UPLOAD_SIZE_BYTES` | `52428800` | Upload size cap |
| `CORS_ORIGINS` | JSON array | Not needed — UI and API share one origin |

> Never put API keys in `vercel.json` or in committed files. Use Vercel's encrypted environment variables.

If you switch to live providers on Pro, also change `maxDuration` in `vercel.json`:

```json
"functions": {
  "api/index.py": { "maxDuration": 60, "memory": 1024 }
}
```

Then commit and push for Vercel to rebuild.

---

## Step 4 — Deploy and verify

Click **Deploy**. After the build finishes:

1. Open `https://<your-project>.vercel.app/api/health`. Expected:

   ```json
   {
     "status": "healthy",
     "database": "PostgreSQL (initialized)",
     "storage_backend": "database"
   }
   ```

2. Open the site root. You should see the MedReason welcome screen.

3. Run a quick smoke test in the UI:
   - Click **New clinical case**
   - Upload `data/sample_data/clinical/lab_results.csv`
   - Ask: “What is the highest Hemoglobin_g_dL in this dataset?”
   - Expect **14.8** with citations

4. Upload `clinical_note.txt` and ask about the thyroid panel. You should see `[E1]` citations with the note snippet in the Evidence panel.

---

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Function Timeout` / 504 | Hobby 10s limit with live LLM | Use mock providers, or upgrade to Pro and raise `maxDuration` |
| `relation "files" does not exist` | Database not reachable or wrong URL | Check `DATABASE_URL` includes `+pg8000` and `sslmode=require`; redeploy |
| `ModuleNotFoundError: mangum` | Root `requirements.txt` not used | Ensure Root Directory is `.` and `api/index.py` is at repo root |
| Blank UI / 404 on page refresh | Rewrite misconfigured | Confirm the two rewrites in `vercel.json` |
| Uploads fail with `FileNotFoundError` | `STORAGE_BACKEND` not `database` | Set it to `database` in Vercel env vars and redeploy |
| Image shows “Provider Mode: Local” | `VISION_PROVIDER=mock` | Expected on Hobby; set `gemini` only on Pro |
| `model_not_found` | Retired provider model | Check provider `/models` endpoint and update `LLM_MODEL` / `VISION_MODEL` |

---

## Known limitations on Vercel

- Hobby timeouts prevent live Groq/Gemini calls (see above).
- `/tmp` is per-invocation; extracted evidence is persisted in Postgres, but raw media previews are not served from `/static/uploads`.
- Video processing is frame sampling, not continuous temporal understanding.
- SQLite-specific local features are unavailable; use Postgres.
- This is an academic prototype, not a production medical system.

---

## Cost notes

- Vercel Hobby and Neon free tier are sufficient for the offline-provider demo.
- Live LLM calls require Vercel Pro for the longer function duration; API usage itself is on the free tiers of Groq and Gemini, subject to their rate limits.
