import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.repositories.file_repo import FileRepository
from app.repositories.vector_repo import VectorRepository
from app.schemas.chat import Citation
from app.schemas.decision import AlternativeOption, DecisionReportSchema, RiskFactor
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

DISCLAIMER = "Academic demonstration only — not for clinical use."


class DecisionSupportService:
    """Evidence-driven clinical decision report generation."""

    def __init__(self, db: Session):
        self.db = db
        self.vector_repo = VectorRepository(db)
        self.file_repo = FileRepository(db)

    async def generate_decision_report(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        criteria: Optional[List[str]] = None,
    ) -> DecisionReportSchema:
        criteria = criteria or ["evidence strength", "risk", "feasibility"]

        chunks = self.vector_repo.search_evidence(
            query=query, file_ids=file_ids, top_k=6, score_threshold=0.06
        )
        citations = self.vector_repo.build_citations(chunks)

        dataset_metrics: Dict[str, Any] = {}
        active_files = self.file_repo.list_files(conversation_id) if conversation_id else []
        if file_ids:
            active_files = [f for f in active_files if f.id in file_ids]
        for f in active_files:
            if f.file_type == "dataset" and f.metadata_json:
                try:
                    meta = json.loads(f.metadata_json)
                    dataset_metrics[f.filename] = {
                        "rows": meta.get("row_count"),
                        "columns": meta.get("column_count"),
                        "missing_values": meta.get("missing_value_count"),
                    }
                except Exception:
                    pass

        evidence_lines = []
        for i, c in enumerate(chunks[:6], start=1):
            evidence_lines.append(
                f"[E{i}] {c['filename']} ({c.get('source_ref') or 'source'}): {c['text'][:400]}"
            )
        if dataset_metrics:
            evidence_lines.append(f"Tabular findings: {json.dumps(dataset_metrics)}")

        context = "\n".join(evidence_lines)
        prompt = (
            f"Clinical question: {query}\n"
            f"Decision criteria: {', '.join(criteria)}\n\n"
            "Build a structured decision report using ONLY the evidence above. "
            "Return JSON with keys: title, objective, executive_summary, key_findings (list), "
            "quantitative_metrics (object), alternatives (list of objects with name, description, "
            "pros, cons, feasibility_score 0-10, risk_level, estimated_impact), "
            "risks_and_limitations (list of objects with risk, severity, mitigation_strategy), "
            "assumptions (list), final_recommendation, actionable_next_steps (list). "
            f"Include this exact disclaimer: {DISCLAIMER}"
        )

        generated = await llm_service.generate_json(prompt, context=context) if context else None
        if generated:
            try:
                return self._coerce_report(generated, query, citations, dataset_metrics)
            except Exception as exc:
                logger.warning("Generated report failed validation (%s); using evidence fallback.", exc)

        return self._fallback_report(query, chunks, citations, dataset_metrics, criteria)

    # ------------------------------------------------------------------
    # Report shaping
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_report(
        data: Dict[str, Any],
        query: str,
        citations: List[Citation],
        metrics: Dict[str, Any],
    ) -> DecisionReportSchema:
        alternatives = []
        for item in data.get("alternatives", [])[:4]:
            alternatives.append(
                AlternativeOption(
                    name=str(item.get("name", "Alternative")),
                    description=str(item.get("description", "")),
                    pros=[str(x) for x in item.get("pros", [])],
                    cons=[str(x) for x in item.get("cons", [])],
                    feasibility_score=float(item.get("feasibility_score", 5.0)),
                    risk_level=str(item.get("risk_level", "Medium")),
                    estimated_impact=str(item.get("estimated_impact", "")),
                )
            )

        risks = []
        for item in data.get("risks_and_limitations", [])[:5]:
            risks.append(
                RiskFactor(
                    risk=str(item.get("risk", "Unspecified risk")),
                    severity=str(item.get("severity", "Medium")),
                    mitigation_strategy=str(item.get("mitigation_strategy", "")),
                )
            )

        summary = str(data.get("executive_summary", ""))
        recommendation = str(data.get("final_recommendation", ""))
        if DISCLAIMER not in summary:
            summary = f"{summary} {DISCLAIMER}".strip()
        if DISCLAIMER not in recommendation:
            recommendation = f"{recommendation} {DISCLAIMER}".strip()

        return DecisionReportSchema(
            title=str(data.get("title", f"Clinical Decision Brief: {query[:50]}")),
            objective=str(data.get("objective", query)),
            executive_summary=summary,
            key_findings=[str(x) for x in data.get("key_findings", [])] or [
                f"Retrieved {len(citations)} evidence sources relevant to the question."
            ],
            quantitative_metrics=data.get("quantitative_metrics") or metrics,
            evidence_sources=citations,
            alternatives=alternatives,
            risks_and_limitations=risks,
            assumptions=[str(x) for x in data.get("assumptions", [])],
            final_recommendation=recommendation,
            actionable_next_steps=[str(x) for x in data.get("actionable_next_steps", [])],
        )

    @staticmethod
    def _fallback_report(
        query: str,
        chunks: List[Dict[str, Any]],
        citations: List[Citation],
        metrics: Dict[str, Any],
        criteria: List[str],
    ) -> DecisionReportSchema:
        """Offline evidence inventory — explicitly not automated clinical advice."""
        has_evidence = bool(chunks or metrics)
        evidence_lines = [
            f"[E{i}] {c['filename']} "
            f"({c.get('source_ref') or c.get('modality', 'source')}): "
            f"{c['text'][:220].strip()}"
            for i, c in enumerate(chunks[:6], start=1)
        ]
        evidence_note = (
            f"{len(chunks)} evidence chunk(s) and {len(metrics)} tabular source(s) were retrieved."
            if has_evidence
            else "No uploaded evidence matched this question."
        )

        # Each "alternative" is a retrieved evidence path, not a fabricated
        # clinical recommendation. This keeps degraded mode honest and useful.
        alternatives = []
        for i, c in enumerate(chunks[:3], start=1):
            snippet = c["text"][:280].strip()
            if len(c["text"]) > 280:
                snippet += "..."
            alternatives.append(
                AlternativeOption(
                    name=f"Evidence path {i}: {c['filename']}",
                    description=snippet,
                    pros=[
                        f"Directly retrieved for this query [E{i}].",
                        f"Retrieval score: {float(c.get('score', 0)):.2f}.",
                    ],
                    cons=[
                        "Reflects a single evidence chunk; corroborate against the full source.",
                        "No provider synthesis was available in offline mode.",
                    ],
                    feasibility_score=round(
                        max(1.0, min(10.0, float(c.get("score", 0)) * 10)), 1
                    ),
                    risk_level="Medium",
                    estimated_impact="Evidence visibility only — no clinical effect inferred.",
                )
            )

        if len(alternatives) < 2:
            alternatives.append(
                AlternativeOption(
                    name="Evidence-gap review",
                    description=(
                        f"Only {len(chunks)} evidence chunk(s) matched this question. "
                        "Additional records are needed before any conclusion can be grounded."
                    ),
                    pros=["Makes uncertainty explicit", "Prevents unsupported conclusions"],
                    cons=["Requires additional records", "Does not resolve the question by itself"],
                    feasibility_score=7.0,
                    risk_level="Medium",
                    estimated_impact="Clarifies whether the question can be answered from evidence.",
                )
            )

        risks = [
            RiskFactor(
                risk="Offline mode: structured LLM generation was unavailable",
                severity="High",
                mitigation_strategy=(
                    "Set LLM_PROVIDER=groq or gemini with a free API key to enable "
                    "evidence-grounded synthesis."
                ),
            ),
            RiskFactor(
                risk="Evidence paths are retrieved snippets, not clinical recommendations",
                severity="High",
                mitigation_strategy="Verify each cited source and obtain qualified clinical interpretation.",
            ),
            RiskFactor(
                risk="Synthetic or de-identified demonstration data",
                severity="Medium",
                mitigation_strategy="Do not use these records or outputs for real patient care.",
            ),
        ]

        recommendation = (
            "No automated clinical recommendation was produced because structured generation was "
            "unavailable. Review the evidence paths above and obtain qualified interpretation. "
            f"{evidence_note} {DISCLAIMER}"
        )

        return DecisionReportSchema(
            title=f"Clinical Decision Brief: {query[:50]}",
            objective=query,
            executive_summary=(
                f"Offline evidence inventory for: '{query}'. {evidence_note} "
                f"Evaluation criteria: {', '.join(criteria)}. {DISCLAIMER}"
                + ("\n\n" + "\n".join(evidence_lines) if evidence_lines else "")
            ),
            key_findings=evidence_lines
            or ["No matching evidence chunks were available in the active index."],
            quantitative_metrics=metrics
            or {"Evidence chunks": len(citations), "Tabular sources": len(metrics)},
            evidence_sources=citations,
            alternatives=alternatives,
            risks_and_limitations=risks,
            assumptions=[
                "Uploaded records are synthetic or de-identified.",
                "Retrieved evidence is treated as source material only, not as clinical advice.",
                "A qualified human reviews all outputs before any use.",
            ],
            final_recommendation=recommendation,
            actionable_next_steps=[
                "Review each cited source against the original file.",
                "Confirm whether additional records are needed for this question.",
                "Configure a text provider for structured synthesis when API access is available.",
            ],
        )
