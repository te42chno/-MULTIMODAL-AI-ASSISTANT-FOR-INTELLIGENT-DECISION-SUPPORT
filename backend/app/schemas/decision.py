from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.chat import Citation


class AlternativeOption(BaseModel):
    name: str
    description: str
    pros: List[str]
    cons: List[str]
    feasibility_score: float = Field(ge=0.0, le=10.0)
    risk_level: str  # Low, Medium, High
    estimated_impact: str


class RiskFactor(BaseModel):
    risk: str
    severity: str  # Low, Medium, High, Critical
    mitigation_strategy: str


class DecisionReportSchema(BaseModel):
    title: str
    objective: str
    executive_summary: str
    key_findings: List[str]
    quantitative_metrics: Dict[str, Any] = Field(default_factory=dict)
    evidence_sources: List[Citation] = Field(default_factory=list)
    alternatives: List[AlternativeOption] = Field(default_factory=list)
    risks_and_limitations: List[RiskFactor] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    final_recommendation: str
    actionable_next_steps: List[str] = Field(default_factory=list)


class DecisionSupportRequest(BaseModel):
    conversation_id: Optional[str] = None
    query: str
    file_ids: Optional[List[str]] = Field(default_factory=list)
    criteria: Optional[List[str]] = Field(default_factory=list)


class DecisionSupportResponse(BaseModel):
    report_id: str
    conversation_id: str
    report: DecisionReportSchema
