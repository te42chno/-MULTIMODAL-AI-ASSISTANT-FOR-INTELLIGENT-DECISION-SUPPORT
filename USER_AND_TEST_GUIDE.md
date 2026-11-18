# MedReason — User & Testing Guide

> **Academic demonstration only — not for clinical use.** All records in this project are synthetic. Use this guide to exercise the app safely and consistently.

The app is currently running at:

- Frontend: <http://127.0.0.1:5173>
- Backend health: <http://127.0.0.1:8000/api/health>
- API docs: <http://127.0.0.1:8000/docs>

---

## 1. Quick-start: your first 5 minutes

1. Open <http://127.0.0.1:5173>.
2. Click **New clinical case** in the left sidebar.
3. Upload `data/sample_data/clinical/clinical_note.txt` using the paperclip in the composer.
4. Paste this prompt and press **Enter**:

   > What does the plan say about the thyroid panel and palpitations?

5. Confirm that:
   - the answer mentions the thyroid panel, repeat heart-rate monitoring and escalation if palpitations persist;
   - citation chips such as `[E1]` appear;
   - the **Evidence** panel on the right shows the retrieved note snippet.

If that works, the core RAG loop is functioning.

---

## 2. UI tour

| Area | What it does | What to check |
| :--- | :--- | :--- |
| **Left sidebar** | Case history, search, new case, Evidence Hub, Analytics, Settings. | `New clinical case` resets the workspace. Case titles appear after the first message. |
| **Top bar** | Shows active case title, academic-use badge and Evidence panel toggle. | Badge should always read **Academic use only**. |
| **Welcome screen** | Four starter cards for decision brief, note RAG, lab tables and media. | Clicking a card inserts a prepared prompt. |
| **Composer** | Attach files, record voice, toggle **Decision Brief**, send messages. | Active files appear as chips above/near the input. |
| **Chat area** | Markdown answers, charts, citation chips and structured reports. | Answers should contain `[E1]`-style references when files are attached. |
| **Evidence Inspector** | Model pipeline, VLM/embedding providers, active files, citations, disclaimer. | Should show `groq`, `gemini`, `hashing_cosine`. |
| **Analytics modal** | Modality counts, upload volume, charts. | Counts must reflect real uploads; no fake demo data. |
| **Evidence Hub** | Searchable file catalog. | Uploaded files should appear with type and summary. |
| **Settings modal** | Read-only provider status. | Changes are made in `backend/.env`, then restart backend. |

---

## 3. How to use the app

### 3.1 Start a case

- Click **New clinical case**.
- Give it a meaningful first prompt; the app uses the prompt text as the case title.

### 3.2 Upload evidence

Supported inputs:

| Modality | Extensions | Sample file |
| :--- | :--- | :--- |
| Clinical notes | `.pdf`, `.docx`, `.doc`, `.txt`, `.md` | `clinical_note.txt` |
| Lab tables | `.csv`, `.xlsx`, `.xls` | `lab_results.csv` |
| Images | `.png`, `.jpg`, `.jpeg`, `.webp` | `vitals_chart.png` |
| Audio | `.wav`, `.mp3`, `.m4a`, `.webm` | `consultation_audio.wav` |
| Video | `.mp4`, `.mov`, `.avi`, `.webm` | `procedure_clip.mp4` |

Use the paperclip button in the composer. Wait for the file chip to appear before asking a question.

### 3.3 Ask a grounded question

- Type a question and press **Enter**.
- The app retrieves the most relevant evidence chunks, then sends them to Groq as `[E1]`, `[E2]`, etc.
- Every medical claim in the answer should be traceable to a citation.

### 3.4 Inspect evidence

- Click the **Evidence** button in the top bar.
- Check:
  - **Model pipeline** → text provider and active model
  - **VLM** / **Embeddings** provider tiles
  - **Citations** → filename, source reference, snippet and score
  - **Active files** → uploaded media inventory

### 3.5 Generate a decision brief

1. Upload at least one note and one lab table.
2. Enable **Decision Brief** in the composer.
3. Ask a comparative question, e.g.:

   > For DEMO-001 with fatigue and palpitations, compare continued monitoring, targeted workup, and specialist review, then recommend the safest next step.

4. Expect a structured report card with:
   - executive summary
   - key findings and quantitative metrics
   - alternatives with pros/cons and feasibility scores
   - risks and mitigations
   - final recommendation
   - actionable next steps
   - evidence sources

### 3.6 Use voice input

- Click the microphone button in the composer.
- Allow browser microphone access.
- Speak, stop recording, then send.
- The browser records audio, uploads it, and the backend transcribes it.

### 3.7 Read an answer correctly

- `[E1]`, `[E2]`, … are evidence IDs.
- A source reference may be a **page**, **row**, **timestamp** or **timeline marker**.
- If the evidence is insufficient, the correct behaviour is an inconclusive answer — not an invented one.

---

## 4. Copy-paste prompt pack

Use these after uploading the corresponding files.

### Clinical note RAG

```text
Summarize the clinical note for DEMO-001 with exact source references.
```

```text
What does the plan say about the thyroid panel and palpitations?
```

```text
List the examination findings and separate them from the assessment.
```

### Lab table analytics

```text
What is the highest Hemoglobin_g_dL in this dataset?
```

```text
What is the average TSH_mIU_L in this dataset?
```

```text
How many rows does the lab table contain, and which columns are present?
```

```text
Are there any missing values in the lab table?
```

### Image / VLM

```text
Describe the chart and report its visible title and the two trends.
```

```text
Which line represents heart rate and which line represents hemoglobin?
```

### Audio / video

```text
Summarize the consultation transcript and list any timestamped segments.
```

```text
Summarize the video timeline events with their timestamps.
```

### Cross-modal

```text
Summarize all available evidence for DEMO-001 across the note, lab table, chart, audio and video.
```

### Decision brief

```text
For DEMO-001 with fatigue and palpitations, compare continued monitoring, targeted workup, and specialist review. Recommend the safest next step using only the uploaded evidence.
```

### Negative tests

```text
What is the capital of France?
```

```text
What is the recommended chemotherapy regimen for this patient?
```

The app should say the uploaded evidence does not contain the answer; it must not invent facts.

---

## 5. Manual test matrix

Run these in order. Mark **Pass / Fail**.

| ID | Scenario | Steps | Expected result | Pass? |
| :--- | :--- | :--- | :--- | :--- |
| TC-01 | App loads | Open frontend URL | Welcome screen, no blank page, no console errors | ☐ |
| TC-02 | Backend health | Open `/api/health` | `status: healthy`, `llm_provider: groq`, `vision_provider: gemini` | ☐ |
| TC-03 | New case | Click **New clinical case** | Chat clears, welcome cards return | ☐ |
| TC-04 | Note upload | Upload `clinical_note.txt` | File chip appears; upload success | ☐ |
| TC-05 | Note RAG | Ask thyroid/palpitations prompt | Answer mentions thyroid panel, monitoring, escalation; `[E1]` citation present | ☐ |
| TC-06 | Citation check | Click/open Evidence panel | Note snippet and source reference visible | ☐ |
| TC-07 | Lab upload | Upload `lab_results.csv` | 8 rows, 5 columns, charts recommended | ☐ |
| TC-08 | Lab max | Ask highest `Hemoglobin_g_dL` | Answer contains **14.8** and `df['Hemoglobin_g_dL'].max()` | ☐ |
| TC-09 | Lab mean | Ask average `TSH_mIU_L` | Answer contains about **3.513** | ☐ |
| TC-10 | Image VLM | Upload `vitals_chart.png`, ask for description | Gemini caption mentions synthetic vitals trend; no `Provider Mode: Local` text | ☐ |
| TC-11 | Audio | Upload `consultation_audio.wav` | Duration about 4s, status processed, transcript evidence created | ☐ |
| TC-12 | Video | Upload `procedure_clip.mp4` | Duration about 6s, extracted frames > 0, timeline events present | ☐ |
| TC-13 | Decision brief | Upload note + lab, enable Decision Brief, ask comparative prompt | Structured report with ≥2 alternatives, risks, recommendation, citations | ☐ |
| TC-14 | Cross-modal | Upload all modalities, ask cross-modal summary | Citations from more than one modality appear | ☐ |
| TC-15 | Evidence Inspector | Toggle Evidence panel | Pipeline shows `groq`, `gemini`, `hashing_cosine` | ☐ |
| TC-16 | Knowledge Hub | Open Evidence Hub, search `lab` | `lab_results.csv` appears | ☐ |
| TC-17 | Analytics | Open Analytics | Counts match uploaded files; no fabricated default pie chart | ☐ |
| TC-18 | Irrelevant question | Ask capital of France with files attached | App states evidence does not contain answer | ☐ |
| TC-19 | Unsupported file | Try uploading `malicious.exe` | Upload rejected with unsupported-format error | ☐ |
| TC-20 | Disclaimer | Inspect any answer/report | `Academic demonstration only — not for clinical use.` present | ☐ |

---

## 6. Automated tests

Run the backend integration suite:

```powershell
cd "D:\pbl ly\backend"
python -m pytest tests/test_system.py -v
```

Expected: **9 passed**.

These tests are forced offline by `tests/conftest.py`, so they do not spend your Groq/Gemini quota.

Build the frontend:

```powershell
cd "D:\pbl ly\frontend"
npm run build
```

Expected: successful build. A Vite chunk-size warning is acceptable.

---

## 7. Acceptance criteria

A test passes only if all of these hold:

1. **Grounded:** every clinical claim is supported by a visible citation.
2. **No fabrication:** the app never invents lab values, diagnoses or guidelines.
3. **Traceable:** citations show filename and source reference.
4. **Honest uncertainty:** insufficient evidence produces an inconclusive answer.
5. **Disclaimer present:** academic-use warning appears in answers/reports.
6. **Providers active:** health/Evidence Inspector show Groq and Gemini.
7. **No errors:** no HTTP 500 in terminal and no uncaught browser console errors.
8. **Real data only from fixtures:** no fabricated analytics numbers in UI.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| Frontend cannot reach backend | Backend stopped or wrong API URL | Check `/api/health`; frontend defaults to `http://127.0.0.1:8000/api` |
| Image shows local fallback | Gemini key/model issue | Restart backend after `.env` changes; check `VISION_MODEL` |
| Groq `model_not_found` | Provider retired model | Query `https://api.groq.com/openai/v1/models` with your key and update `LLM_MODEL` |
| Answer has no citations | No evidence retrieved | Upload a relevant file or rephrase query using terms from the file |
| Audio transcript is placeholder | Whisper not installed or audio is synthetic tone | Install `faster-whisper` and set `SPEECH_PROVIDER=whisper` |
| Video timeline missing | Codec/duration issue | Re-encode to H.264 MP4 under 180 seconds |
| Test suite uses mock providers | Expected | `backend/tests/conftest.py` intentionally forces offline mode |

---

## 9. Bug report template

If something fails, record:

```text
Test ID:
Prompt used:
Files uploaded:
Expected result:
Actual result:
Citation IDs shown:
Provider shown in Evidence Inspector:
Browser console error (if any):
Backend terminal error (if any):
Screenshot:
```

---

## 10. Sample files reference

All synthetic fixtures are in `data/sample_data/clinical/`:

| File | Known facts for testing |
| :--- | :--- |
| `clinical_note.txt` | DEMO-001, fatigue/palpitations, HR 96, plan includes thyroid panel and escalation |
| `lab_results.csv` | 8 rows, 5 columns; max `Hemoglobin_g_dL` = 14.8; mean `TSH_mIU_L` ≈ 3.513 |
| `vitals_chart.png` | 400×300, title `SYNTHETIC VITALS TREND`, teal HR and violet hemoglobin lines |
| `consultation_audio.wav` | 4-second synthetic audio placeholder |
| `procedure_clip.mp4` | 6-second synthetic timeline clip |

The top-level `data/sample_data/` copies use older generic filenames but contain the same clinical data.
