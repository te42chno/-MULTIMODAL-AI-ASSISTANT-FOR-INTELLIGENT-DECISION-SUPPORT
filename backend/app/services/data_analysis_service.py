import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from app.schemas.dataset import DatasetSummaryResponse, ColumnMetadata, ChartSpec, DatasetQueryResponse

logger = logging.getLogger(__name__)


class DataAnalysisService:
    """Safe structured data analytics service for CSV and Excel files."""

    MAX_ROWS_PROCESS = 100_000
    MAX_COLS_PROCESS = 100

    def load_dataset(self, file_path: str, filename: str) -> pd.DataFrame:
        """Safely load CSV or Excel dataset with size guards."""
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            df = pd.read_csv(file_path, nrows=self.MAX_ROWS_PROCESS)
        elif ext in {"xlsx", "xls"}:
            df = pd.read_excel(file_path, nrows=self.MAX_ROWS_PROCESS)
        else:
            raise ValueError(f"Unsupported dataset format: {ext}")

        if df.shape[1] > self.MAX_COLS_PROCESS:
            df = df.iloc[:, :self.MAX_COLS_PROCESS]

        return df

    def analyze_dataset(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Compute full statistical summary and automated chart recommendations."""
        df = self.load_dataset(file_path, filename)
        row_count, col_count = df.shape

        # Column metadata
        columns = []
        for col in df.columns:
            non_null = int(df[col].count())
            null_count = int(df[col].isna().sum())
            unique_count = int(df[col].nunique())
            dtype_str = str(df[col].dtype)
            
            # Sample non-null values
            sample_vals = df[col].dropna().head(3).tolist()
            sample_vals = [str(v) if not isinstance(v, (int, float, str, bool)) else v for v in sample_vals]

            columns.append({
                "name": str(col),
                "dtype": dtype_str,
                "non_null_count": non_null,
                "null_count": null_count,
                "unique_count": unique_count,
                "sample_values": sample_vals
            })

        missing_total = int(df.isna().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        # Descriptive statistics for numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        summary_stats = {}
        if not numeric_df.empty:
            desc = numeric_df.describe().to_dict()
            for col, stats in desc.items():
                summary_stats[col] = {k: round(float(v), 3) if pd.notna(v) else None for k, v in stats.items()}

        # Correlation matrix
        correlations = None
        if numeric_df.shape[1] >= 2:
            corr_df = numeric_df.corr().round(3)
            correlations = corr_df.to_dict()

        # Generate automatic chart recommendations
        charts = self._generate_chart_recommendations(df)

        # Preview rows (convert NaN to None for JSON serialization)
        preview_data = df.head(10).replace({np.nan: None}).to_dict(orient="records")

        return {
            "filename": filename,
            "row_count": row_count,
            "column_count": col_count,
            "columns": columns,
            "missing_value_count": missing_total,
            "duplicate_row_count": duplicate_rows,
            "preview_rows": preview_data,
            "summary_statistics": summary_stats,
            "recommended_charts": charts,
            "correlations": correlations
        }

    def _generate_chart_recommendations(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        charts = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        # Recommendation 1: Categorical vs Numeric Bar Chart (e.g. sum or average)
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]
            grouped = df.groupby(cat_col)[num_col].mean().dropna().head(8).reset_index()
            chart_data = [
                {"name": str(row[cat_col]), "value": round(float(row[num_col]), 2)}
                for _, row in grouped.iterrows()
            ]
            charts.append({
                "chart_type": "bar",
                "title": f"Average {num_col} by {cat_col}",
                "x_axis": cat_col,
                "y_axis": num_col,
                "data": chart_data,
                "description": f"Displays the distribution of mean {num_col} across distinct {cat_col} categories."
            })

        # Recommendation 2: Two numeric columns Scatter / Line Chart
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            sample_df = df[[x_col, y_col]].dropna().head(20).sort_values(by=x_col)
            chart_data = [
                {"x": round(float(row[x_col]), 2), "y": round(float(row[y_col]), 2)}
                for _, row in sample_df.iterrows()
            ]
            charts.append({
                "chart_type": "line",
                "title": f"{y_col} vs {x_col} Trend",
                "x_axis": x_col,
                "y_axis": y_col,
                "data": chart_data,
                "description": f"Visualizes the relationship and trend between {x_col} and {y_col}."
            })

        # Recommendation 3: Distribution Pie Chart for categorical values
        if categorical_cols:
            cat_col = categorical_cols[0]
            val_counts = df[cat_col].value_counts().head(5)
            chart_data = [
                {"name": str(k), "value": int(v)}
                for k, v in val_counts.items()
            ]
            charts.append({
                "chart_type": "pie",
                "title": f"{cat_col} Distribution",
                "x_axis": cat_col,
                "y_axis": "Count",
                "data": chart_data,
                "description": f"Top category frequencies for {cat_col}."
            })

        return charts

    def answer_question(self, file_path: str, filename: str, question: str) -> Dict[str, Any]:
        """Safe deterministic query planner: translates questions into Pandas operations WITHOUT eval/exec."""
        df = self.load_dataset(file_path, filename)
        q = question.lower()

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        # Match columns in question
        matched_numeric = [c for c in numeric_cols if c.lower() in q]
        matched_categorical = [c for c in categorical_cols if c.lower() in q]

        # 1. Total rows / count query
        if "how many rows" in q or "total rows" in q or "count of rows" in q:
            return {
                "answer": f"The dataset '{filename}' contains **{len(df):,} total rows** and **{len(df.columns)} columns**.",
                "calculation_summary": f"Calculated: len(df) = {len(df)}",
                "chart": None,
                "data_table": None
            }

        # 2. Maximum / Highest value
        if "highest" in q or "maximum" in q or "max" in q or "top" in q:
            col = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
            if col:
                max_val = df[col].max()
                top_row = df.loc[df[col].idxmax()].to_dict()
                return {
                    "answer": f"The maximum value for **{col}** is **{max_val}**.",
                    "calculation_summary": f"Calculated: df['{col}'].max() = {max_val}",
                    "chart": None,
                    "data_table": [{k: str(v) for k, v in top_row.items()}][:1]
                }

        # 3. Minimum / Lowest value
        if "lowest" in q or "minimum" in q or "min" in q:
            col = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
            if col:
                min_val = df[col].min()
                return {
                    "answer": f"The minimum value for **{col}** is **{min_val}**.",
                    "calculation_summary": f"Calculated: df['{col}'].min() = {min_val}",
                    "chart": None,
                    "data_table": None
                }

        # 4. Average / Mean query
        if "average" in q or "mean" in q:
            col = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
            if col:
                mean_val = round(float(df[col].mean()), 3)
                return {
                    "answer": f"The average (mean) value for **{col}** across all records is **{mean_val}**.",
                    "calculation_summary": f"Calculated: df['{col}'].mean() = {mean_val}",
                    "chart": None,
                    "data_table": None
                }

        # 5. Missing values / nulls
        if "missing" in q or "null" in q or "empty" in q:
            null_counts = df.isna().sum()
            missing_cols = null_counts[null_counts > 0].to_dict()
            if missing_cols:
                details = ", ".join([f"{col}: {cnt} nulls" for col, cnt in missing_cols.items()])
                return {
                    "answer": f"Missing values detected across the dataset: {details}.",
                    "calculation_summary": f"Calculated: df.isna().sum()",
                    "chart": None,
                    "data_table": [{"Column": k, "MissingCount": v} for k, v in missing_cols.items()]
                }
            else:
                return {
                    "answer": "There are **0 missing or null values** in this dataset; all records are complete.",
                    "calculation_summary": "Calculated: df.isna().sum().sum() = 0",
                    "chart": None,
                    "data_table": None
                }

        # Default fallback: safe summary
        num_summary = ""
        if numeric_cols:
            primary_num = numeric_cols[0]
            num_summary = f" For column '{primary_num}', the mean is {round(df[primary_num].mean(), 2)}, with a range from {df[primary_num].min()} to {df[primary_num].max()}."

        return {
            "answer": (
                f"Statistical query analysis for '{filename}': The dataset consists of {len(df):,} records and {len(df.columns)} columns."
                f"{num_summary} You can ask specific questions about averages, maximums, minimums, category breakdowns, or missing values."
            ),
            "calculation_summary": f"Inspected columns: {', '.join(df.columns[:6])}",
            "chart": None,
            "data_table": df.head(5).replace({np.nan: None}).to_dict(orient="records")
        }


# Global singleton
data_analysis_service = DataAnalysisService()
