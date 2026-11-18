import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.file_repo import FileRepository
from app.repositories.vector_repo import VectorRepository
from app.services.llm_service import llm_service
from app.services.data_analysis_service import data_analysis_service
from app.services.decision_support_service import DecisionSupportService
from app.schemas.chat import ChatResponse, Citation

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Central Orchestration Hub unifying text, documents, images, audio, video, datasets, and decision support."""

    def __init__(self, db: Session):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.file_repo = FileRepository(db)
        self.vector_repo = VectorRepository(db)
        self.decision_service = DecisionSupportService(db)

    async def handle_user_message(
        self,
        conversation_id: Optional[str],
        message: str,
        modality: str = "text",
        file_ids: Optional[List[str]] = None,
        is_decision_support: bool = False,
        system_instruction: Optional[str] = None
    ) -> ChatResponse:
        """Route user input to appropriate modality pipeline and return a unified response."""
        file_ids = file_ids or []

        # 1. Ensure conversation exists
        if not conversation_id:
            conv = self.conv_repo.create_conversation(title=message[:40] or "New Multimodal Chat")
            conversation_id = conv.id
        else:
            conv = self.conv_repo.get_conversation(conversation_id)
            if not conv:
                conv = self.conv_repo.create_conversation(title=message[:40] or "New Multimodal Chat")
                conversation_id = conv.id

        # 2. Persist user message
        user_msg = self.conv_repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
            modality=modality,
            file_ids=file_ids
        )

        # 3. Decision Support Routing
        lower_message = message.lower()
        wants_decision = (
            is_decision_support
            or "decision support" in lower_message
            or "clinical decision" in lower_message
            or ("recommend" in lower_message and "support" in lower_message)
        )
        if wants_decision:
            report_schema = await self.decision_service.generate_decision_report(
                query=message,
                conversation_id=conversation_id,
                file_ids=file_ids
            )
            # Format report into rich Markdown
            md_content = self._format_decision_report_markdown(report_schema)
            
            assistant_msg = self.conv_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=md_content,
                modality="decision",
                file_ids=file_ids,
                sources=[c.model_dump() for c in report_schema.evidence_sources],
                metadata_json={"report": report_schema.model_dump()}
            )

            return ChatResponse(
                conversation_id=conversation_id,
                message_id=assistant_msg.id,
                role="assistant",
                content=md_content,
                modality="decision",
                sources=report_schema.evidence_sources,
                metadata={"report": report_schema.model_dump()},
                created_at=assistant_msg.created_at
            )

        # 4. Retrieve unified multimodal evidence first. Every modality — notes,
        # tables, images, audio and video — shares the same evidence index.
        chunks = self.vector_repo.search_similar_chunks(
            query=message,
            file_ids=file_ids if file_ids else None,
            top_k=4,
        )
        citations = self.vector_repo.build_citations(chunks)
        context_blocks = [
            f"[E{i}] {c['filename']} ({c.get('source_ref') or 'source'}, {c.get('modality', 'document')}): {c['text']}"
            for i, c in enumerate(chunks, start=1)
        ]

        # 5. Deterministic tabular computations are added as evidence too, so a
        # dataset never short-circuits retrieval or bypasses the LLM synthesis.
        metadata: Dict[str, Any] = {"grounded": bool(chunks)}
        computation_notes: List[str] = []
        dataset_files = []
        for fid in file_ids:
            ds = self.file_repo.get_file(fid)
            if ds and ds.file_type == "dataset":
                dataset_files.append(ds)

        for ds in dataset_files[:2]:
            ans_dict = data_analysis_service.answer_question(
                ds.file_path, ds.filename, message
            )
            context_blocks.append(
                f"[E{len(context_blocks) + 1}] {ds.filename} (dataset computation): "
                f"{ans_dict['answer']} Basis: {ans_dict['calculation_summary']}"
            )
            citations.append(
                Citation(
                    source_id=ds.id,
                    filename=ds.filename,
                    row_or_item="Dataset computation",
                    snippet=ans_dict["calculation_summary"],
                    relevance_score=1.0,
                )
            )
            computation_notes.append(
                f"**{ds.filename}:** {ans_dict['answer']} "
                f"`{ans_dict['calculation_summary']}`"
            )
            if not metadata.get("chart") and ans_dict.get("chart"):
                metadata["chart"] = ans_dict["chart"]
            if not metadata.get("data_table") and ans_dict.get("data_table"):
                metadata["data_table"] = ans_dict["data_table"]

        context_str = "\n".join(context_blocks)

        # 6. Generate answer using LLM with all retrieved evidence in context.
        generated_answer = await llm_service.generate_response(
            prompt=message,
            system_instruction=system_instruction,
            context=context_str if context_str else None,
        )

        if computation_notes:
            generated_answer += (
                "\n\n### Deterministic tabular results\n"
                + "\n\n".join(computation_notes)
            )

        metadata["grounded"] = bool(context_str)
        response_modality = "dataset" if dataset_files else modality

        # 7. Persist assistant response
        assistant_msg = self.conv_repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=generated_answer,
            modality=response_modality,
            file_ids=file_ids,
            sources=[c.model_dump() for c in citations],
            metadata_json=metadata,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            message_id=assistant_msg.id,
            role="assistant",
            content=generated_answer,
            modality=response_modality,
            sources=citations,
            metadata=metadata,
            created_at=assistant_msg.created_at,
        )

    def _format_decision_report_markdown(self, report: Any) -> str:
        """Format decision report into professional structured markdown."""
        md = []
        md.append(f"## 📋 {report.title}\n")
        md.append(f"**Objective:** *{report.objective}*\n")
        md.append(f"### 1. Executive Summary\n{report.executive_summary}\n")
        
        md.append("### 2. Key Findings & Quantitative Metrics")
        for kf in report.key_findings:
            md.append(f"- {kf}")
        
        if report.quantitative_metrics:
            md.append("\n**Computed Metrics:**")
            for k, v in report.quantitative_metrics.items():
                md.append(f"- **{k}:** `{v}`")
        
        md.append("\n### 3. Alternative Options & Trade-Off Analysis")
        for alt in report.alternatives:
            md.append(f"#### {alt.name} (Feasibility: {alt.feasibility_score}/10, Risk: {alt.risk_level})")
            md.append(f"{alt.description}")
            md.append(f"- **Pros:** {', '.join(alt.pros)}")
            md.append(f"- **Cons:** {', '.join(alt.cons)}")
            md.append(f"- **Estimated Impact:** {alt.estimated_impact}\n")

        md.append("### 4. Risks, Limitations & Mitigations")
        for r in report.risks_and_limitations:
            md.append(f"- **{r.risk}** `[{r.severity}]`: {r.mitigation_strategy}")

        md.append(f"\n### 5. Final Recommendation\n{report.final_recommendation}\n")

        md.append("### 6. Actionable Next Steps")
        for step in report.actionable_next_steps:
            md.append(f"1. {step}")

        return "\n".join(md)
