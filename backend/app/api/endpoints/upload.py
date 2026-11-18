import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.config import settings, UPLOAD_DIR
from app.database import get_db
from app.core.security import sanitize_filename, validate_file_extension, determine_modality
from app.repositories.file_repo import FileRepository
from app.repositories.vector_repo import VectorRepository
from app.services.document_service import document_service
from app.services.vision_service import vision_service
from app.services.speech_service import speech_service
from app.services.video_service import video_service
from app.services.data_analysis_service import data_analysis_service

router = APIRouter()


async def _save_uploaded_file(file: UploadFile, subfolder: str) -> str:
    """Save upload to isolated directory with sanitized unique filename."""
    clean_name = sanitize_filename(file.filename or "uploaded_file")
    ext = validate_file_extension(clean_name)
    
    unique_name = f"{uuid.uuid4().hex[:8]}_{clean_name}"
    dest_dir = UPLOAD_DIR / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir / unique_name

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_BYTES//(1024*1024)}MB.")

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path), clean_name, len(content)


def _index_multimodal_evidence(
    vector_repo: VectorRepository,
    file_id: str,
    file_type: str,
    filename: str,
    payload: dict,
) -> None:
    """Convert each modality's derived data into retrievable evidence chunks."""
    chunks = []

    if file_type == "image":
        parts = [f"Image: {filename}.", f"VLM findings: {payload.get('description', '')}"]
        if payload.get("extracted_text"):
            parts.append(f"Visible text: {payload['extracted_text']}")
        chunks.append(
            {
                "modality": "image",
                "source_ref": "Image findings",
                "text": " ".join(parts),
                "metadata": {"palette": payload.get("color_palette", [])},
            }
        )

    elif file_type == "audio":
        for i, seg in enumerate(payload.get("segments", [])):
            chunks.append(
                {
                    "chunk_index": i,
                    "modality": "audio",
                    "source_ref": f"{seg.get('start', 0):.0f}s-{seg.get('end', 0):.0f}s",
                    "text": f"Consultation transcript: {seg.get('text', '')}",
                    "metadata": {"start": seg.get("start"), "end": seg.get("end")},
                }
            )
        if not chunks:
            chunks.append(
                {
                    "modality": "audio",
                    "source_ref": "Transcript",
                    "text": f"Consultation transcript for {filename}: {payload.get('transcription', '')}",
                }
            )

    elif file_type == "video":
        for i, event in enumerate(payload.get("timeline_events", [])):
            chunks.append(
                {
                    "chunk_index": i,
                    "modality": "video",
                    "source_ref": event.get("time", ""),
                    "text": f"Video timeline: {event.get('event', '')}",
                    "metadata": {"seconds": event.get("seconds")},
                }
            )
        chunks.append(
            {
                "chunk_index": len(chunks),
                "modality": "video",
                "source_ref": "Summary",
                "text": f"Video summary for {filename}: {payload.get('overall_summary', '')}",
            }
        )

    elif file_type == "dataset":
        col_names = ", ".join(c["name"] for c in payload.get("columns", []))
        chunks.append(
            {
                "modality": "dataset",
                "source_ref": "Schema",
                "text": (
                    f"Dataset {filename}: {payload.get('row_count')} rows and "
                    f"{payload.get('column_count')} columns. Columns: {col_names}. "
                    f"Missing values: {payload.get('missing_value_count')}. "
                    f"Duplicate rows: {payload.get('duplicate_row_count')}."
                ),
            }
        )
        for i, row in enumerate(payload.get("preview_rows", [])[:10]):
            chunks.append(
                {
                    "chunk_index": i + 1,
                    "modality": "dataset",
                    "source_ref": f"Row {i + 1}",
                    "text": "Lab/table record: " + ", ".join(f"{k}={v}" for k, v in row.items()),
                }
            )

    if chunks:
        vector_repo.add_evidence_chunks(file_id, chunks)


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        file_path, original_name, file_size = await _save_uploaded_file(file, "documents")
        
        # Process document (extract text & chunks)
        doc_result = document_service.process_document(file_path, original_name)
        
        # Save file record in DB
        file_repo = FileRepository(db)
        record = file_repo.save_file(
            filename=original_name,
            file_type="document",
            file_size=file_size,
            file_path=file_path,
            conversation_id=conversation_id,
            summary=doc_result.get("summary"),
            metadata_dict={
                "page_count": doc_result.get("page_count"),
                "chunk_count": len(doc_result.get("chunks", [])),
                "total_words": doc_result.get("total_words")
            }
        )

        # Index chunks into vector store
        vector_repo = VectorRepository(db)
        vector_repo.add_document_chunks(record.id, doc_result["chunks"])

        return {
            "file_id": record.id,
            "filename": original_name,
            "file_size": file_size,
            "page_count": doc_result.get("page_count"),
            "chunk_count": len(doc_result["chunks"]),
            "summary": doc_result.get("summary"),
            "status": "processed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        file_path, original_name, file_size = await _save_uploaded_file(file, "images")
        
        # Process image with vision service
        analysis = await vision_service.analyze_image(file_path, prompt)

        file_repo = FileRepository(db)
        record = file_repo.save_file(
            filename=original_name,
            file_type="image",
            file_size=file_size,
            file_path=file_path,
            conversation_id=conversation_id,
            summary=analysis.get("description"),
            metadata_dict=analysis
        )
        _index_multimodal_evidence(VectorRepository(db), record.id, "image", original_name, analysis)

        return {
            "file_id": record.id,
            "filename": original_name,
            "file_size": file_size,
            "analysis": analysis,
            "status": "processed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/audio")
async def upload_audio(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        file_path, original_name, file_size = await _save_uploaded_file(file, "audio")
        
        transcription_result = speech_service.transcribe_audio(file_path)

        file_repo = FileRepository(db)
        record = file_repo.save_file(
            filename=original_name,
            file_type="audio",
            file_size=file_size,
            file_path=file_path,
            conversation_id=conversation_id,
            summary=transcription_result.get("transcription"),
            metadata_dict=transcription_result
        )
        _index_multimodal_evidence(
            VectorRepository(db), record.id, "audio", original_name, transcription_result
        )

        return {
            "file_id": record.id,
            "filename": original_name,
            "file_size": file_size,
            "transcription": transcription_result.get("transcription"),
            "duration_seconds": transcription_result.get("duration_seconds"),
            "status": "processed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/video")
async def upload_video(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        file_path, original_name, file_size = await _save_uploaded_file(file, "videos")
        
        video_analysis = video_service.process_video(file_path, original_name)

        file_repo = FileRepository(db)
        record = file_repo.save_file(
            filename=original_name,
            file_type="video",
            file_size=file_size,
            file_path=file_path,
            conversation_id=conversation_id,
            summary=video_analysis.get("overall_summary"),
            metadata_dict=video_analysis
        )
        _index_multimodal_evidence(
            VectorRepository(db), record.id, "video", original_name, video_analysis
        )

        return {
            "file_id": record.id,
            "filename": original_name,
            "file_size": file_size,
            "duration_seconds": video_analysis.get("duration_seconds"),
            "fps": video_analysis.get("fps"),
            "extracted_frames_count": len(video_analysis.get("extracted_frames", [])),
            "summary": video_analysis.get("overall_summary"),
            "timeline_events": video_analysis.get("timeline_events", []),
            "status": "processed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        file_path, original_name, file_size = await _save_uploaded_file(file, "datasets")
        
        dataset_meta = data_analysis_service.analyze_dataset(file_path, original_name)

        file_repo = FileRepository(db)
        record = file_repo.save_file(
            filename=original_name,
            file_type="dataset",
            file_size=file_size,
            file_path=file_path,
            conversation_id=conversation_id,
            summary=f"Dataset with {dataset_meta['row_count']} rows and {dataset_meta['column_count']} columns.",
            metadata_dict=dataset_meta
        )
        _index_multimodal_evidence(
            VectorRepository(db), record.id, "dataset", original_name, dataset_meta
        )

        return {
            "file_id": record.id,
            "filename": original_name,
            "file_size": file_size,
            "row_count": dataset_meta["row_count"],
            "column_count": dataset_meta["column_count"],
            "missing_value_count": dataset_meta["missing_value_count"],
            "duplicate_row_count": dataset_meta["duplicate_row_count"],
            "columns": dataset_meta["columns"],
            "summary_statistics": dataset_meta["summary_statistics"],
            "recommended_charts": dataset_meta["recommended_charts"],
            "status": "processed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
