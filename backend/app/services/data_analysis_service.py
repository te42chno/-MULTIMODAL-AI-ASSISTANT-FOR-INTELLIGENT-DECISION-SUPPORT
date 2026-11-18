"""Safe structured-data analytics.

Local development keeps the original pandas/numpy implementation exactly as
before, so every answer and chart is unchanged. The Vercel serverless bundle
excludes those heavy wheels, so a dependency-free CSV/Excel implementation is
used there instead. Both paths forbid eval()/exec().
"""

import csv
import logging
import math
import statistics
from collections import Counter, OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import pandas as pd

    _PANDAS_AVAILABLE = True
except ImportError:  # Vercel serverless runtime
    np = None
    pd = None
    _PANDAS_AVAILABLE = False


def _to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(round(value, 3))


class DataAnalysisService:
    """Dependency-free analytics fallback used when pandas is unavailable."""

    MAX_ROWS_PROCESS = 100_000
    MAX_COLS_PROCESS = 100

    def _read_csv(self, path: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
            reader = csv.reader(handle)
            try:
                columns = next(reader)
            except StopIteration:
                return [], []
            columns = [str(c).strip() or f"column_{i + 1}" for i, c in enumerate(columns)]
            columns = columns[: self.MAX_COLS_PROCESS]
            rows = []
            for raw in reader:
                if len(rows) >= self.MAX_ROWS_PROCESS:
                    break
                if not any(str(cell).strip() for cell in raw):
                    continue
                rows.append(
                    {
                        columns[i]: (raw[i] if i < len(raw) and raw[i] != "" else None)
                        for i in range(len(columns))
                    }
                )
        return columns, rows

    def _read_excel(self, path: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        try:
            header = next(iterator)
        except StopIteration:
            return [], []
        columns = [str(c).strip() if c is not None else f"column_{i + 1}" for i, c in enumerate(header)]
        columns = columns[: self.MAX_COLS_PROCESS]
        rows = []
        for raw in iterator:
            if len(rows) >= self.MAX_ROWS_PROCESS:
                break
            if not any(c is not None and str(c).strip() for c in raw):
                continue
            rows.append({columns[i]: (raw[i] if i < len(raw) else None) for i in range(len(columns))})
        workbook.close()
        return columns, rows

    def load_dataset(self, file_path: str, filename: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        file_path = storage_service.resolve(file_path)
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            return self._read_csv(file_path)
        if ext in {"xlsx", "xlsm"}:
            return self._read_excel(file_path)
        if ext == "xls":
            raise ValueError("Legacy .xls is not supported on Vercel; save as .xlsx or .csv")
        raise ValueError(f"Unsupported dataset format: {ext}")

    @staticmethod
    def _numeric_columns(columns: List[str], rows: List[Dict[str, Any]]) -> List[str]:
        result = []
        for column in columns:
            values = [_to_number(row.get(column)) for row in rows]
            present = [v for v in values if v is not None]
            if present and len(present) >= max(1, len(values) // 2):
                result.append(column)
        return result

    @staticmethod
    def _categorical_columns(columns: List[str], numeric: List[str]) -> List[str]:
        return [c for c in columns if c not in numeric]

    def analyze_dataset(self, file_path: str, filename: str) -> Dict[str, Any]:
        columns, rows = self.load_dataset(file_path, filename)
        numeric = self._numeric_columns(columns, rows)
        categorical = self._categorical_columns(columns, numeric)

        column_meta = []
        for column in columns:
            values = [row.get(column) for row in rows]
            present = [v for v in values if not _is_missing(v)]
            column_meta.append(
                {
                    "name": column,
                    "dtype": "number" if column in numeric else "object",
                    "non_null_count": len(present),
                    "null_count": len(values) - len(present),
                    "unique_count": len({str(v) for v in present}),
                    "sample_values": present[:3],
                }
            )

        missing_total = sum(meta["null_count"] for meta in column_meta)
        fingerprints = [tuple(str(row.get(c)) for c in columns) for row in rows]
        duplicate_rows = len(fingerprints) - len(set(fingerprints))

        summary_stats: Dict[str, Dict[str, Any]] = {}
        for column in numeric:
            present = sorted(v for v in (_to_number(r.get(column)) for r in rows) if v is not None)
            if not present:
                continue

            def percentile(fraction: float) -> float:
                index = min(len(present) - 1, max(0, int(fraction * (len(present) - 1))))
                return round(present[index], 3)

            summary_stats[column] = {
                "count": len(present),
                "mean": round(statistics.fmean(present), 3),
                "std": round(statistics.pstdev(present), 3) if len(present) > 1 else 0.0,
                "min": round(present[0], 3),
                "25%": percentile(0.25),
                "50%": percentile(0.50),
                "75%": percentile(0.75),
                "max": round(present[-1], 3),
            }

        correlations: Dict[str, Dict[str, float]] = {}
        if len(numeric) >= 2:
            for left in numeric:
                correlations[left] = {}
                for right in numeric:
                    pairs = [
                        (_to_number(row.get(left)), _to_number(row.get(right)))
                        for row in rows
                    ]
                    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
                    if len(pairs) < 2:
                        correlations[left][right] = 0.0
                        continue
                    xs = [p[0] for p in pairs]
                    ys = [p[1] for p in pairs]
                    mx, my = statistics.fmean(xs), statistics.fmean(ys)
                    numerator = sum((x - mx) * (y - my) for x, y in pairs)
                    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
                    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
                    correlations[left][right] = round(numerator / (dx * dy), 3) if dx and dy else 0.0

        return {
            "filename": filename,
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": column_meta,
            "missing_value_count": missing_total,
            "duplicate_row_count": duplicate_rows,
            "preview_rows": rows[:10],
            "summary_statistics": summary_stats,
            "recommended_charts": self._generate_chart_recommendations(columns, rows, numeric, categorical),
            "correlations": correlations,
        }

    def _generate_chart_recommendations(
        self,
        columns: List[str],
        rows: List[Dict[str, Any]],
        numeric: List[str],
        categorical: List[str],
    ) -> List[Dict[str, Any]]:
        charts: List[Dict[str, Any]] = []
        if categorical and numeric:
            cat_col, num_col = categorical[0], numeric[0]
            grouped: Dict[str, List[float]] = {}
            for row in rows:
                key = str(row.get(cat_col) or "Unknown")
                value = _to_number(row.get(num_col))
                if value is not None:
                    grouped.setdefault(key, []).append(value)
            chart_data = [
                {"name": name, "value": round(statistics.fmean(values), 2)}
                for name, values in list(grouped.items())[:8]
            ]
            if chart_data:
                charts.append(
                    {
                        "chart_type": "bar",
                        "title": f"Average {num_col} by {cat_col}",
                        "x_axis": cat_col,
                        "y_axis": num_col,
                        "data": chart_data,
                        "description": f"Mean {num_col} across distinct {cat_col} categories.",
                    }
                )

        if len(numeric) >= 2:
            x_col, y_col = numeric[0], numeric[1]
            points = []
            for row in rows[:20]:
                x, y = _to_number(row.get(x_col)), _to_number(row.get(y_col))
                if x is not None and y is not None:
                    points.append({"x": round(x, 2), "y": round(y, 2)})
            points.sort(key=lambda p: p["x"])
            if points:
                charts.append(
                    {
                        "chart_type": "line",
                        "title": f"{y_col} vs {x_col} Trend",
                        "x_axis": x_col,
                        "y_axis": y_col,
                        "data": points,
                        "description": f"Trend between {x_col} and {y_col}.",
                    }
                )

        if categorical:
            cat_col = categorical[0]
            counts = Counter(str(row.get(cat_col) or "Unknown") for row in rows)
            charts.append(
                {
                    "chart_type": "pie",
                    "title": f"{cat_col} Distribution",
                    "x_axis": cat_col,
                    "y_axis": "Count",
                    "data": [{"name": k, "value": v} for k, v in counts.most_common(5)],
                    "description": f"Top category frequencies for {cat_col}.",
                }
            )
        return charts

    def answer_question(self, file_path: str, filename: str, question: str) -> Dict[str, Any]:
        columns, rows = self.load_dataset(file_path, filename)
        q = question.lower()
        numeric = self._numeric_columns(columns, rows)
        matched_numeric = [c for c in numeric if c.lower() in q]

        if "how many rows" in q or "total rows" in q or "count of rows" in q:
            return {
                "answer": f"The dataset '{filename}' contains **{len(rows):,} total rows** and **{len(columns)} columns**.",
                "calculation_summary": f"Calculated: len(df) = {len(rows)}",
                "chart": None,
                "data_table": None,
            }

        if "highest" in q or "maximum" in q or "max" in q or "top" in q:
            col = matched_numeric[0] if matched_numeric else (numeric[0] if numeric else None)
            if col:
                pairs = [(i, _to_number(row.get(col))) for i, row in enumerate(rows)]
                pairs = [(i, v) for i, v in pairs if v is not None]
                if pairs:
                    best_index, max_val = max(pairs, key=lambda item: item[1])
                    return {
                        "answer": f"The maximum value for **{col}** is **{_fmt(max_val)}**.",
                        "calculation_summary": f"Calculated: df['{col}'].max() = {_fmt(max_val)}",
                        "chart": None,
                        "data_table": [{k: str(v) for k, v in rows[best_index].items()}][:1],
                    }

        if "lowest" in q or "minimum" in q or "min" in q:
            col = matched_numeric[0] if matched_numeric else (numeric[0] if numeric else None)
            if col:
                values = [v for v in (_to_number(row.get(col)) for row in rows) if v is not None]
                if values:
                    min_val = min(values)
                    return {
                        "answer": f"The minimum value for **{col}** is **{_fmt(min_val)}**.",
                        "calculation_summary": f"Calculated: df['{col}'].min() = {_fmt(min_val)}",
                        "chart": None,
                        "data_table": None,
                    }

        if "average" in q or "mean" in q:
            col = matched_numeric[0] if matched_numeric else (numeric[0] if numeric else None)
            if col:
                values = [v for v in (_to_number(row.get(col)) for row in rows) if v is not None]
                if values:
                    mean_val = round(statistics.fmean(values), 3)
                    return {
                        "answer": f"The average (mean) value for **{col}** across all records is **{mean_val}**.",
                        "calculation_summary": f"Calculated: df['{col}'].mean() = {mean_val}",
                        "chart": None,
                        "data_table": None,
                    }

        if "missing" in q or "null" in q or "empty" in q:
            missing_cols = OrderedDict()
            for column in columns:
                count = sum(1 for row in rows if _is_missing(row.get(column)))
                if count:
                    missing_cols[column] = count
            if missing_cols:
                details = ", ".join(f"{col}: {cnt} nulls" for col, cnt in missing_cols.items())
                return {
                    "answer": f"Missing values detected across the dataset: {details}.",
                    "calculation_summary": "Calculated: df.isna().sum()",
                    "chart": None,
                    "data_table": [{"Column": k, "MissingCount": v} for k, v in missing_cols.items()],
                }
            return {
                "answer": "There are **0 missing or null values** in this dataset; all records are complete.",
                "calculation_summary": "Calculated: df.isna().sum().sum() = 0",
                "chart": None,
                "data_table": None,
            }

        num_summary = ""
        if numeric:
            values = [v for v in (_to_number(row.get(numeric[0])) for row in rows) if v is not None]
            if values:
                num_summary = (
                    f" For column '{numeric[0]}', the mean is {round(statistics.fmean(values), 2)}, "
                    f"with a range from {_fmt(min(values))} to {_fmt(max(values))}."
                )
        return {
            "answer": (
                f"Statistical query analysis for '{filename}': The dataset consists of {len(rows):,} records "
                f"and {len(columns)} columns.{num_summary} You can ask specific questions about averages, "
                "maximums, minimums, category breakdowns, or missing values."
            ),
            "calculation_summary": f"Inspected columns: {', '.join(columns[:6])}",
            "chart": None,
            "data_table": rows[:5],
        }


class PandasDataAnalysisService(DataAnalysisService):
    """Original pandas/numpy implementation, used locally when those packages exist."""

    def load_dataset(self, file_path: str, filename: str):
        file_path = storage_service.resolve(file_path)
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext == "csv":
            df = pd.read_csv(file_path, nrows=self.MAX_ROWS_PROCESS)
        elif ext in {"xlsx", "xls"}:
            df = pd.read_excel(file_path, nrows=self.MAX_ROWS_PROCESS)
        else:
            raise ValueError(f"Unsupported dataset format: {ext}")
        if df.shape[1] > self.MAX_COLS_PROCESS:
            df = df.iloc[:, : self.MAX_COLS_PROCESS]
        return df

    def analyze_dataset(self, file_path: str, filename: str) -> Dict[str, Any]:
        df = self.load_dataset(file_path, filename)
        row_count, col_count = df.shape

        columns = []
        for col in df.columns:
            non_null = int(df[col].count())
            null_count = int(df[col].isna().sum())
            unique_count = int(df[col].nunique())
            dtype_str = str(df[col].dtype)
            sample_vals = df[col].dropna().head(3).tolist()
            sample_vals = [str(v) if not isinstance(v, (int, float, str, bool)) else v for v in sample_vals]
            columns.append(
                {
                    "name": str(col),
                    "dtype": dtype_str,
                    "non_null_count": non_null,
                    "null_count": null_count,
                    "unique_count": unique_count,
                    "sample_values": sample_vals,
                }
            )

        missing_total = int(df.isna().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        numeric_df = df.select_dtypes(include=[np.number])
        summary_stats = {}
        if not numeric_df.empty:
            desc = numeric_df.describe().to_dict()
            for col, stats in desc.items():
                summary_stats[col] = {
                    k: round(float(v), 3) if pd.notna(v) else None for k, v in stats.items()
                }

        correlations = None
        if numeric_df.shape[1] >= 2:
            correlations = numeric_df.corr().round(3).to_dict()

        charts = self._generate_chart_recommendations(df)
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
            "correlations": correlations,
        }

    def _generate_chart_recommendations(self, df) -> List[Dict[str, Any]]:
        charts = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        if categorical_cols and numeric_cols:
            cat_col, num_col = categorical_cols[0], numeric_cols[0]
            grouped = df.groupby(cat_col)[num_col].mean().dropna().head(8).reset_index()
            chart_data = [
                {"name": str(row[cat_col]), "value": round(float(row[num_col]), 2)}
                for _, row in grouped.iterrows()
            ]
            charts.append(
                {
                    "chart_type": "bar",
                    "title": f"Average {num_col} by {cat_col}",
                    "x_axis": cat_col,
                    "y_axis": num_col,
                    "data": chart_data,
                    "description": f"Displays the distribution of mean {num_col} across distinct {cat_col} categories.",
                }
            )

        if len(numeric_cols) >= 2:
            x_col, y_col = numeric_cols[0], numeric_cols[1]
            sample_df = df[[x_col, y_col]].dropna().head(20).sort_values(by=x_col)
            chart_data = [
                {"x": round(float(row[x_col]), 2), "y": round(float(row[y_col]), 2)}
                for _, row in sample_df.iterrows()
            ]
            charts.append(
                {
                    "chart_type": "line",
                    "title": f"{y_col} vs {x_col} Trend",
                    "x_axis": x_col,
                    "y_axis": y_col,
                    "data": chart_data,
                    "description": f"Visualizes the relationship and trend between {x_col} and {y_col}.",
                }
            )

        if categorical_cols:
            cat_col = categorical_cols[0]
            val_counts = df[cat_col].value_counts().head(5)
            chart_data = [{"name": str(k), "value": int(v)} for k, v in val_counts.items()]
            charts.append(
                {
                    "chart_type": "pie",
                    "title": f"{cat_col} Distribution",
                    "x_axis": cat_col,
                    "y_axis": "Count",
                    "data": chart_data,
                    "description": f"Top category frequencies for {cat_col}.",
                }
            )
        return charts

    def answer_question(self, file_path: str, filename: str, question: str) -> Dict[str, Any]:
        df = self.load_dataset(file_path, filename)
        q = question.lower()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        matched_numeric = [c for c in numeric_cols if c.lower() in q]
        matched_categorical = [c for c in categorical_cols if c.lower() in q]
        _ = matched_categorical  # preserved from original planner

        if "how many rows" in q or "total rows" in q or "count of rows" in q:
            return {
                "answer": f"The dataset '{filename}' contains **{len(df):,} total rows** and **{len(df.columns)} columns**.",
                "calculation_summary": f"Calculated: len(df) = {len(df)}",
                "chart": None,
                "data_table": None,
            }

        if "highest" in q or "maximum" in q or "max" in q or "top" in q:
            col = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
            if col:
                max_val = df[col].max()
                top_row = df.loc[df[col].idxmax()].to_dict()
                return {
                    "answer": f"The maximum value for **{col}** is **{max_val}**.",
                    "calculation_summary": f"Calculated: df['{col}'].max() = {max_val}",
                    "chart": None,
                    "data_table": [{k: str(v) for k, v in top_row.items()}][:1],
                }

        if "lowest" in q or "minimum" in q or "min" in q:
            col = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
            if col:
                min_val = df[col].min()
                return {
                    "answer": f"The minimum value for **{col}** is **{min_val}**.",
                    "calculation_summary": f"Calculated: df['{col}'].min() = {min_val}",
                    "chart": None,
                    "data_table": None,
                }

        if "average" in q or "mean" in q:
            col = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
            if col:
                mean_val = round(float(df[col].mean()), 3)
                return {
                    "answer": f"The average (mean) value for **{col}** across all records is **{mean_val}**.",
                    "calculation_summary": f"Calculated: df['{col}'].mean() = {mean_val}",
                    "chart": None,
                    "data_table": None,
                }

        if "missing" in q or "null" in q or "empty" in q:
            null_counts = df.isna().sum()
            missing_cols = null_counts[null_counts > 0].to_dict()
            if missing_cols:
                details = ", ".join([f"{col}: {cnt} nulls" for col, cnt in missing_cols.items()])
                return {
                    "answer": f"Missing values detected across the dataset: {details}.",
                    "calculation_summary": "Calculated: df.isna().sum()",
                    "chart": None,
                    "data_table": [{"Column": k, "MissingCount": v} for k, v in missing_cols.items()],
                }
            return {
                "answer": "There are **0 missing or null values** in this dataset; all records are complete.",
                "calculation_summary": "Calculated: df.isna().sum().sum() = 0",
                "chart": None,
                "data_table": None,
            }

        num_summary = ""
        if numeric_cols:
            primary_num = numeric_cols[0]
            num_summary = (
                f" For column '{primary_num}', the mean is {round(df[primary_num].mean(), 2)}, "
                f"with a range from {df[primary_num].min()} to {df[primary_num].max()}."
            )
        return {
            "answer": (
                f"Statistical query analysis for '{filename}': The dataset consists of {len(df):,} records "
                f"and {len(df.columns)} columns.{num_summary} You can ask specific questions about averages, "
                "maximums, minimums, category breakdowns, or missing values."
            ),
            "calculation_summary": f"Inspected columns: {', '.join(df.columns[:6])}",
            "chart": None,
            "data_table": df.head(5).replace({np.nan: None}).to_dict(orient="records"),
        }


# Global singleton: original behaviour locally, lightweight fallback on Vercel.
data_analysis_service = (
    PandasDataAnalysisService() if _PANDAS_AVAILABLE else DataAnalysisService()
)
