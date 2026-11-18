from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union


class ColumnMetadata(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: List[Any] = Field(default_factory=list)


class ChartSpec(BaseModel):
    chart_type: str  # bar, line, scatter, pie, histogram
    title: str
    x_axis: str
    y_axis: str
    data: List[Dict[str, Any]]
    description: str


class DatasetSummaryResponse(BaseModel):
    file_id: str
    filename: str
    row_count: int
    column_count: int
    columns: List[ColumnMetadata]
    missing_value_count: int
    duplicate_row_count: int
    preview_rows: List[Dict[str, Any]]
    summary_statistics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    recommended_charts: List[ChartSpec] = Field(default_factory=list)
    correlations: Optional[Dict[str, Dict[str, float]]] = None


class DatasetQueryRequest(BaseModel):
    file_id: str
    question: str


class DatasetQueryResponse(BaseModel):
    file_id: str
    question: str
    answer: str
    calculation_summary: str
    chart: Optional[ChartSpec] = None
    data_table: Optional[List[Dict[str, Any]]] = None
