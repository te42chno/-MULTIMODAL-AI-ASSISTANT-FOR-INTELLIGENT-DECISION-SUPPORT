# MedReason Frontend

This is the React + TypeScript + Vite interface for **MedReason**, the clinical multimodal RAG assistant.

It provides:

- a clinical chat workspace with evidence citations,
- a multimodal composer for notes, labs, images, audio and video,
- a structured decision-report renderer,
- an evidence inspector with provider status and source snippets,
- analytics and evidence-hub views.

## Run locally

```powershell
cd "D:\pbl ly\frontend"
npm install
npm run dev
```

Open <http://localhost:5173>. The app expects the backend at `http://127.0.0.1:8000/api`.

Copy `.env.example` to `.env` if you need to override the backend URL.

## Documentation

See the repository root [`README.md`](../README.md) for project overview and setup, and [`USER_AND_TEST_GUIDE.md`](../USER_AND_TEST_GUIDE.md) for a guided demo and manual test matrix.
