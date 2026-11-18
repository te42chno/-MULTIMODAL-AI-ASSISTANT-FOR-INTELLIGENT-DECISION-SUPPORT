import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SAMPLE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_data", "clinical")
)


def test_01_health_check():
    """Verify system health endpoint returns 200 OK and valid provider info."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "llm_provider" in data
    assert "embedding_provider" in data


def test_02_text_only_question():
    """Verify text-only conversation and session initialization."""
    payload = {
        "message": "What is multimodal evidence-grounded clinical decision support?",
        "modality": "text",
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert "content" in data
    assert data["role"] == "assistant"


def test_03_document_upload_and_rag():
    """Verify clinical note ingestion, chunking, indexing and grounded citations."""
    doc_path = os.path.join(SAMPLE_DIR, "clinical_note.txt")
    assert os.path.exists(doc_path), f"File {doc_path} not found"

    with open(doc_path, "rb") as f:
        res = client.post(
            "/api/upload/document",
            files={"file": ("clinical_note.txt", f, "text/plain")},
        )

    assert res.status_code == 200
    upload_data = res.json()
    file_id = upload_data["file_id"]
    assert upload_data["chunk_count"] > 0

    query_payload = {
        "query": "What does the plan say about the thyroid panel and palpitations?",
        "file_ids": [file_id],
        "top_k": 3,
    }
    q_res = client.post("/api/documents/query", json=query_payload)
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["grounded"] is True
    assert len(q_data["sources"]) > 0
    assert "clinical_note.txt" in q_data["sources"][0]["filename"]


def test_04_image_upload_and_analysis():
    """Verify clinical chart upload, palette extraction and local visual fallback."""
    img_path = os.path.join(SAMPLE_DIR, "vitals_chart.png")
    assert os.path.exists(img_path)

    with open(img_path, "rb") as f:
        res = client.post(
            "/api/upload/image",
            files={"file": ("vitals_chart.png", f, "image/png")},
            data={"prompt": "Identify any visible clinical trend or text."},
        )

    assert res.status_code == 200
    data = res.json()
    assert "file_id" in data
    analysis = data["analysis"]
    assert analysis["width"] == 400
    assert analysis["height"] == 300
    assert len(analysis["color_palette"]) > 0


def test_05_audio_upload_and_transcription():
    """Verify synthetic consultation audio ingestion and transcription fallback."""
    audio_path = os.path.join(SAMPLE_DIR, "consultation_audio.wav")
    assert os.path.exists(audio_path)

    with open(audio_path, "rb") as f:
        res = client.post(
            "/api/upload/audio",
            files={"file": ("consultation_audio.wav", f, "audio/wav")},
        )

    assert res.status_code == 200
    data = res.json()
    assert "file_id" in data
    assert "duration_seconds" in data
    assert data["status"] == "processed"


def test_06_dataset_upload_and_safe_query():
    """Verify synthetic lab CSV upload, schema inference and safe calculation."""
    csv_path = os.path.join(SAMPLE_DIR, "lab_results.csv")
    assert os.path.exists(csv_path)

    with open(csv_path, "rb") as f:
        res = client.post(
            "/api/upload/dataset",
            files={"file": ("lab_results.csv", f, "text/csv")},
        )

    assert res.status_code == 200
    ds_data = res.json()
    assert ds_data["row_count"] == 8
    assert ds_data["column_count"] == 5
    assert len(ds_data["columns"]) == 5
    assert len(ds_data["recommended_charts"]) > 0

    file_id = ds_data["file_id"]
    q_res = client.post(
        "/api/datasets/query",
        json={
            "file_id": file_id,
            "question": "What is the highest Hemoglobin_g_dL in this dataset?",
        },
    )
    assert q_res.status_code == 200
    q_ans = q_res.json()
    assert "14.8" in q_ans["answer"]
    assert "df['Hemoglobin_g_dL'].max()" in q_ans["calculation_summary"]


def test_07_video_upload_and_frame_extraction():
    """Verify synthetic video upload and OpenCV interval frame extraction."""
    vid_path = os.path.join(SAMPLE_DIR, "procedure_clip.mp4")
    assert os.path.exists(vid_path)

    with open(vid_path, "rb") as f:
        res = client.post(
            "/api/upload/video",
            files={"file": ("procedure_clip.mp4", f, "video/mp4")},
        )

    assert res.status_code == 200
    v_data = res.json()
    assert v_data["duration_seconds"] > 0
    assert v_data["extracted_frames_count"] > 0
    assert len(v_data["timeline_events"]) > 0


def test_08_intelligent_decision_support_report():
    """Verify evidence-aware structured clinical decision report generation."""
    payload = {
        "query": "Should DEMO-001 continue monitoring, pursue targeted workup, or escalate?",
        "criteria": ["Evidence strength", "Risk", "Feasibility"],
    }
    res = client.post("/api/decision-support", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "report_id" in data
    report = data["report"]
    assert "executive_summary" in report
    assert len(report["alternatives"]) >= 2
    assert len(report["risks_and_limitations"]) >= 2
    assert len(report["actionable_next_steps"]) >= 2
    assert "final_recommendation" in report
    assert "academic demonstration only" in report["executive_summary"].lower()


def test_09_unsupported_file_format_rejection():
    """Verify security validation rejects unsupported or dangerous extensions."""
    res = client.post(
        "/api/upload/document",
        files={"file": ("malicious.exe", b"MZ...", "application/octet-stream")},
    )
    assert res.status_code == 400
    err = res.json()
    assert "not supported" in err["detail"].lower()
