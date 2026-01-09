"""Data processing and aggregation for BookSpring metrics."""
import pandas as pd
from datetime import datetime, date
from typing import Optional, Literal
from dateutil.relativedelta import relativedelta


TimeUnit = Literal["day", "week", "month", "quarter", "year", "fiscal_year"]


class DataProcessor:
    """Process and aggregate BookSpring activity data."""

    # BookSpring fiscal year starts July 1
    FISCAL_YEAR_START_MONTH = 7

    def __init__(self, records: list):
        self.df = self._records_to_dataframe(records)
        self._add_calculated_metrics()

    def _records_to_dataframe(self, records: list) -> pd.DataFrame:
        """Convert Fusioo records to a pandas DataFrame."""
        if not records:
            return pd.DataFrame()

        # Fusioo returns fields directly in the record, not nested under "fields"
        df = pd.DataFrame(records)

        # Rename 'id' to 'record_id' to avoid confusion
        if "id" in df.columns:
            df = df.rename(columns={"id": "record_id"})

        # Convert list columns to strings (Fusioo returns lists for single-select fields)
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, list)).any():
                df[col] = df[col].apply(
                    lambda x: x[0] if isinstance(x, list) and len(x) == 1
                    else ", ".join(str(i) for i in x) if isinstance(x, list)
                    else x
                )

        # Convert date columns
        date_columns = ["date_of_activity", "date", "created", "last_modified"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df

    def _add_calculated_metrics(self):
        """Add calculated metrics like books per child by age group."""
        if self.df.empty:
            return

        books_col = "_of_books_distributed"
        if books_col not in self.df.columns:
            return

        # Age group mapping: metric name -> list of possible source columns
        # Multiple source columns handle different schemas (legacy vs current)
        age_group_sources = {
            "books_per_child_0_2": ["children_035_months", "children_03_years"],
            "books_per_child_3_5": ["children_35_years", "children_34_years"],
            "books_per_child_6_8": ["children_68_years", "children_512_years"],
            "books_per_child_9_12": ["children_912_years"],
            "books_per_child_teens": ["teens"],
        }

        # Get all possible source columns that exist in the data
        all_source_cols = []
        for sources in age_group_sources.values():
            all_source_cols.extend([c for c in sources if c in self.df.columns])

        if not all_source_cols:
            return

        # Calculate total children by summing all available age columns per row
        # Use fillna(0) to handle missing columns gracefully
        self.df["_total_children_calc"] = self.df[all_source_cols].fillna(0).sum(axis=1)

        # Calculate books per child for each age group
        for metric_col, source_cols in age_group_sources.items():
            available_sources = [c for c in source_cols if c in self.df.columns]
            if available_sources:
                # Sum children from all available source columns for this age group
                # This handles cases where both legacy and current columns have data
                self.df[metric_col] = self.df.apply(
                    lambda row, cols=available_sources: (
                        row[books_col] / row["_total_children_calc"]
                        if row["_total_children_calc"] > 0 and sum(row[c] if pd.notna(row[c]) else 0 for c in cols) > 0
                        else 0
                    ),
                    axis=1
                )

        # Overall average books per child
        self.df["avg_books_per_child"] = self.df.apply(
            lambda row: row[books_col] / row["_total_children_calc"]
            if row["_total_children_calc"] > 0 else 0,
            axis=1
        )

        # Clean up temp column
        self.df.drop("_total_children_calc", axis=1, inplace=True)

    def get_date_column(self) -> Optional[str]:
        """Get the primary date column name."""
        date_columns = ["date_of_activity", "date", "created", "last_modified"]
        for col in date_columns:
            if col in self.df.columns:
                return col
        return None

    def filter_by_date_range(self, start_date: date, end_date: date) -> "DataProcessor":
        """Filter data by date range."""
        date_col = self.get_date_column()
        filtered = DataProcessor.__new__(DataProcessor)

        if date_col and date_col in self.df.columns:
            mask = (self.df[date_col] >= pd.Timestamp(start_date)) & \
                   (self.df[date_col] <= pd.Timestamp(end_date))
            filtered.df = self.df[mask].copy()
        else:
            filtered.df = self.df.copy()

        return filtered

    def _get_fiscal_year(self, dt: datetime) -> int:
        """Get fiscal year for a date (FY starts July 1)."""
        if dt.month >= self.FISCAL_YEAR_START_MONTH:
            return dt.year + 1
        return dt.year

    def _add_time_period_column(self, time_unit: TimeUnit) -> pd.DataFrame:
        """Add a time period column for grouping."""
        df = self.df.copy()
        date_col = self.get_date_column()

        if time_unit == "day":
            df["period"] = df[date_col].dt.date
        elif time_unit == "week":
            df["period"] = df[date_col].dt.to_period("W").dt.start_time
        elif time_unit == "month":
            df["period"] = df[date_col].dt.to_period("M").dt.start_time
        elif time_unit == "quarter":
            df["period"] = df[date_col].dt.to_period("Q").dt.start_time
        elif time_unit == "year":
            df["period"] = df[date_col].dt.year
        elif time_unit == "fiscal_year":
            df["period"] = df[date_col].apply(
                lambda x: f"FY{self._get_fiscal_year(x)}" if pd.notna(x) else None
            )

        return df

    # Metrics that should be averaged, not summed
    RATIO_METRICS = {
        "avg_books_per_child", "books_per_child_0_2", "books_per_child_3_5",
        "books_per_child_6_8", "books_per_child_9_12", "books_per_child_teens"
    }

    def aggregate_by_time(self, time_unit: TimeUnit,
                          metrics: Optional[list] = None) -> pd.DataFrame:
        """Aggregate metrics by time period."""
        df = self._add_time_period_column(time_unit)

        # Default metrics to aggregate
        if metrics is None:
            metrics = self._get_numeric_columns()

        # Aggregation config - use mean for ratio metrics, sum for counts
        agg_dict = {}
        for col in metrics:
            if col in df.columns:
                if col in self.RATIO_METRICS:
                    agg_dict[col] = "mean"
                else:
                    agg_dict[col] = "sum"

        if not agg_dict:
            return pd.DataFrame()

        result = df.groupby("period", dropna=True).agg(agg_dict).reset_index()
        result = result.sort_values("period")

        # Round ratio metrics to 2 decimal places
        for col in self.RATIO_METRICS:
            if col in result.columns:
                result[col] = result[col].round(2)

        return result

    def _get_numeric_columns(self) -> list:
        """Get numeric column names for aggregation."""
        numeric_cols = self.df.select_dtypes(include=["number"]).columns.tolist()
        # Exclude ID columns
        return [col for col in numeric_cols if not col.endswith("_id")]

    def aggregate_by_category(self, category_col: str,
                              metrics: Optional[list] = None) -> pd.DataFrame:
        """Aggregate metrics by a categorical column."""
        if category_col not in self.df.columns:
            return pd.DataFrame()

        if metrics is None:
            metrics = self._get_numeric_columns()

        agg_dict = {col: "sum" for col in metrics if col in self.df.columns}
        agg_dict["record_id"] = "count"

        result = self.df.groupby(category_col, dropna=True).agg(agg_dict).reset_index()
        result = result.rename(columns={"record_id": "activity_count"})

        return result

    def compare_periods(self, period1_start: date, period1_end: date,
                        period2_start: date, period2_end: date,
                        metrics: Optional[list] = None) -> pd.DataFrame:
        """Compare metrics between two time periods."""
        p1 = self.filter_by_date_range(period1_start, period1_end)
        p2 = self.filter_by_date_range(period2_start, period2_end)

        if metrics is None:
            metrics = self._get_numeric_columns()

        # Calculate totals for each period
        p1_totals = {}
        p2_totals = {}

        # Get total books and children for weighted average calculation
        p1_books = p1.df["_of_books_distributed"].sum() if "_of_books_distributed" in p1.df.columns else 0
        p1_children = p1.df["total_children"].sum() if "total_children" in p1.df.columns else 0
        p2_books = p2.df["_of_books_distributed"].sum() if "_of_books_distributed" in p2.df.columns else 0
        p2_children = p2.df["total_children"].sum() if "total_children" in p2.df.columns else 0

        for col in metrics:
            if col in p1.df.columns:
                if col == "avg_books_per_child":
                    # Calculate weighted average: total books / total children
                    p1_totals[col] = p1_books / p1_children if p1_children > 0 else 0
                elif col in self.RATIO_METRICS:
                    # For other ratio metrics, use weighted calculation too
                    p1_totals[col] = p1_books / p1_children if p1_children > 0 else 0
                else:
                    p1_totals[col] = p1.df[col].sum()

            if col in p2.df.columns:
                if col == "avg_books_per_child":
                    p2_totals[col] = p2_books / p2_children if p2_children > 0 else 0
                elif col in self.RATIO_METRICS:
                    p2_totals[col] = p2_books / p2_children if p2_children > 0 else 0
                else:
                    p2_totals[col] = p2.df[col].sum()

        comparison = []
        for metric in metrics:
            val1 = p1_totals.get(metric, 0)
            val2 = p2_totals.get(metric, 0)
            change = val2 - val1
            pct_change = (change / val1 * 100) if val1 != 0 else 0

            comparison.append({
                "metric": metric,
                "period_1": val1,
                "period_2": val2,
                "change": change,
                "percent_change": round(pct_change, 2)
            })

        return pd.DataFrame(comparison)

    def get_summary_stats(self) -> dict:
        """Get summary statistics for the dataset."""
        date_col = self.get_date_column()
        numeric_cols = self._get_numeric_columns()

        stats = {
            "total_records": len(self.df),
            "totals": {col: self.df[col].sum() for col in numeric_cols if col in self.df.columns}
        }

        if date_col and date_col in self.df.columns:
            stats["date_range"] = {
                "start": self.df[date_col].min(),
                "end": self.df[date_col].max()
            }
        else:
            stats["date_range"] = {"start": None, "end": None}

        return stats


# Mapping of field IDs to friendly names
FIELD_LABELS = {
    "_of_books_distributed": "Books Distributed",
    "total_children": "Total Children",
    "children_035_months": "Children 0-2 years",
    "children_03_years": "Children 0-35 months",
    "children_35_years": "Children 3-5 years",
    "children_34_years": "Children 3-5 years",
    "children_68_years": "Children 6-8 years",
    "children_512_years": "Children 6-8 years",
    "children_912_years": "Children 9-12 years",
    "teens": "Teens",
    "parents_or_caregivers": "Parents/Caregivers",
    "minutes_of_activity": "Minutes of Activity",
    "total_minutes_of_activity": "Total Activity Minutes",
    "total_people_not_staff": "Total People (not Staff)",
    # Calculated metrics
    "avg_books_per_child": "Avg Books per Child",
    "books_per_child_0_2": "Books/Child (0-2 yrs)",
    "books_per_child_3_5": "Books/Child (3-5 yrs)",
    "books_per_child_6_8": "Books/Child (6-8 yrs)",
    "books_per_child_9_12": "Books/Child (9-12 yrs)",
    "books_per_child_teens": "Books/Child (Teens)",
}


def get_friendly_name(field_id: str) -> str:
    """Get a friendly display name for a field ID."""
    return FIELD_LABELS.get(field_id, field_id.replace("_", " ").title())
