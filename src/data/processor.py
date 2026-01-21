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

    # People count columns that should be zeroed for previously served (to avoid double counting)
    CHILDREN_COUNT_COLUMNS = [
        "total_children",
        "children_035_months",
        "children_03_years",
        "children_35_years",
        "children_34_years",
        "children_68_years",
        "children_512_years",
        "children_912_years",
        "teens",
        "parents_or_caregivers",
    ]

    def __init__(self, records: list):
        self.df = self._records_to_dataframe(records)
        self._exclude_previously_served_children()
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

        # Convert known numeric columns (handles legacy data that may come as strings)
        numeric_columns = [
            "_of_books_distributed",
            "total_children",
            "children_035_months",
            "children_03_years",
            "children_35_years",
            "children_34_years",
            "children_68_years",
            "children_512_years",
            "children_912_years",
            "teens",
            "parents_or_caregivers",
            "minutes_of_activity",
            "percentage_low_income",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    def _exclude_previously_served_children(self):
        """Zero out children AND books for rows where children were previously served this FY.

        This ensures that previously served children are not double-counted in metrics
        like total children served, average books per child, and age group breakdowns.
        Books are also zeroed to exclude them from trendline calculations.

        Original values are preserved in _all columns for reference if needed.
        """
        if self.df.empty:
            return

        # Check if the previously_served field exists
        if "previously_served_this_fy" not in self.df.columns:
            return

        # Create mask for rows where children were previously served
        # Handle boolean True/False or string "true"/"false"
        prev_served = self.df["previously_served_this_fy"].apply(
            lambda x: (x is True) or (pd.notna(x) and str(x).lower() in ("yes", "true", "1"))
        )

        # Store original values before zeroing (for trendline calculations that need all books/children)
        # Preserve original age columns
        for col in self.CHILDREN_COUNT_COLUMNS:
            if col in self.df.columns:
                self.df[f"{col}_all"] = self.df[col].copy()

        # Preserve original books
        if "_of_books_distributed" in self.df.columns:
            self.df["_books_distributed_all"] = self.df["_of_books_distributed"].copy()

        # Zero out children counts for previously served rows using .where()
        # This ensures unique children counts for totals
        for col in self.CHILDREN_COUNT_COLUMNS:
            if col in self.df.columns:
                # .where keeps values where condition is True, replaces with 0 where False
                # We want to keep values where NOT previously_served, so use ~prev_served
                self.df[col] = self.df[col].where(~prev_served, 0)

        # Zero out books for previously served rows (for non-trendline calculations)
        if "_of_books_distributed" in self.df.columns:
            self.df["_of_books_distributed"] = self.df["_of_books_distributed"].where(~prev_served, 0)

    def _add_calculated_metrics(self):
        """Add calculated metrics like books per child by age group."""
        if self.df.empty:
            return

        # Use _of_books_distributed to exclude books for previously served children
        books_col = "_of_books_distributed"
        if books_col not in self.df.columns:
            return

        # Age group mapping: metric name -> list of possible source columns
        # Multiple source columns handle different schemas (legacy vs current)
        # Use base columns (zeroed for previously served) to exclude previously served children
        age_group_sources_base = {
            "books_per_child_0_2": ["children_035_months", "children_03_years"],
            "books_per_child_3_5": ["children_35_years", "children_34_years"],
            "books_per_child_6_8": ["children_68_years", "children_512_years"],
            "books_per_child_9_12": ["children_912_years"],
            "books_per_child_teens": ["teens"],
        }

        # Build age_group_sources using base columns (zeroed for previously served)
        # This ensures both books AND children exclude previously served rows
        age_group_sources = {}
        for metric, base_cols in age_group_sources_base.items():
            existing_cols = [col for col in base_cols if col in self.df.columns]
            if existing_cols:
                age_group_sources[metric] = existing_cols

        # Get all possible source columns that exist in the data
        all_source_cols = []
        for sources in age_group_sources.values():
            all_source_cols.extend(sources)
        all_source_cols = list(set(all_source_cols))  # Remove duplicates

        if not all_source_cols:
            return

        # Calculate total children by summing all available age columns per row
        # Use fillna(0) to handle missing columns gracefully
        self.df["_total_children_calc"] = self.df[all_source_cols].fillna(0).sum(axis=1)

        # Calculate books per child for each age group
        for metric_col, source_cols in age_group_sources.items():
            # Sum children from all available source columns for this age group
            # This handles cases where both legacy and current columns have data
            age_children = self.df[source_cols].fillna(0).sum(axis=1)

            # Calculate: books / total_children, but only where this age group has children
            self.df[metric_col] = 0.0
            mask = (self.df["_total_children_calc"] > 0) & (age_children > 0)
            self.df.loc[mask, metric_col] = (
                self.df.loc[mask, books_col] / self.df.loc[mask, "_total_children_calc"]
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
                          metrics: Optional[list] = None,
                          debug: bool = False) -> pd.DataFrame:
        """Aggregate metrics by time period."""
        df = self._add_time_period_column(time_unit)

        if debug:
            print(f"\n=== DEBUG aggregate_by_time ===")
            print(f"Time unit: {time_unit}")
            print(f"Metrics requested: {metrics}")
            print(f"Total rows: {len(df)}")

        # Default metrics to aggregate
        if metrics is None:
            metrics = self._get_numeric_columns()

        # Separate ratio metrics from count metrics
        ratio_metrics_requested = [m for m in metrics if m in self.RATIO_METRICS and m in df.columns]
        count_metrics = [m for m in metrics if m not in self.RATIO_METRICS and m in df.columns]

        # For count metrics, use sum aggregation
        if count_metrics:
            agg_dict = {col: "sum" for col in count_metrics}
            result = df.groupby("period", dropna=True).agg(agg_dict).reset_index()
        else:
            result = df.groupby("period", dropna=True).size().reset_index(name="_count")
            result = result.drop("_count", axis=1)

        # For ratio metrics, calculate averages per period (books / children for that period)
        # Use _books_distributed_all and total_children_all to include previously served
        if ratio_metrics_requested:
            # Use _books_distributed_all to include all books (including previously served)
            # Fall back to _of_books_distributed if _all column doesn't exist
            if "_books_distributed_all" in df.columns:
                books_col = "_books_distributed_all"
            else:
                books_col = "_of_books_distributed"

            # Use total_children_all to include all children (including previously served)
            # Fall back to total_children if _all column doesn't exist
            if "total_children_all" in df.columns:
                children_col = "total_children_all"
            else:
                children_col = "total_children"

            # Age group column mapping for age-specific metrics
            age_group_sources_base = {
                "books_per_child_0_2": ["children_035_months", "children_03_years"],
                "books_per_child_3_5": ["children_35_years", "children_34_years"],
                "books_per_child_6_8": ["children_68_years", "children_512_years"],
                "books_per_child_9_12": ["children_912_years"],
                "books_per_child_teens": ["teens"],
            }

            # Build age_group_sources
            age_group_sources = {}
            for metric, base_cols in age_group_sources_base.items():
                existing_cols = [col for col in base_cols if col in df.columns]
                if existing_cols:
                    age_group_sources[metric] = existing_cols

            # Get all age columns that exist for calculating total children (for age group filtering)
            all_age_cols = []
            for sources in age_group_sources.values():
                all_age_cols.extend(sources)
            all_age_cols = list(set(all_age_cols))  # Remove duplicates

            if books_col in df.columns and children_col in df.columns:
                # Use total_children_all directly for children count
                df["_total_children_for_agg"] = df[children_col].fillna(0)

                if debug:
                    print(f"Age columns used: {all_age_cols}")
                    print(f"Total books ({books_col}): {df[books_col].sum():,.0f}")
                    print(f"Total children (from age cols): {df['_total_children_for_agg'].sum():,.0f}")

                # Aggregate books and children by period
                period_sums = df.groupby("period", dropna=True).agg({
                    books_col: "sum",
                    "_total_children_for_agg": "sum"
                }).reset_index()

                # Calculate avg_books_per_child: books / children for each period
                period_sums["avg_books_per_child"] = period_sums.apply(
                    lambda row: row[books_col] / row["_total_children_for_agg"]
                    if row["_total_children_for_agg"] > 0 else 0,
                    axis=1
                )

                if debug:
                    print(f"\nPeriod sums (first 5):")
                    print(period_sums.head().to_string())

                # Merge into result
                if "avg_books_per_child" in ratio_metrics_requested:
                    result = result.merge(
                        period_sums[["period", "avg_books_per_child"]],
                        on="period",
                        how="left"
                    )

                # For age group metrics, calculate average only for activities
                # where that age group was present
                for metric_col, source_cols in age_group_sources.items():
                    if metric_col in ratio_metrics_requested:
                        # Filter to rows where this age group has children
                        age_children = df[source_cols].fillna(0).sum(axis=1)
                        df_with_age = df[age_children > 0]

                        if not df_with_age.empty:
                            # Calculate average for this age group's activities
                            age_period_sums = df_with_age.groupby("period", dropna=True).agg({
                                books_col: "sum",
                                "_total_children_for_agg": "sum"
                            }).reset_index()

                            age_period_sums[metric_col] = age_period_sums.apply(
                                lambda row: row[books_col] / row["_total_children_for_agg"]
                                if row["_total_children_for_agg"] > 0 else 0,
                                axis=1
                            )

                            result = result.merge(
                                age_period_sums[["period", metric_col]],
                                on="period",
                                how="left"
                            )
                            result[metric_col] = result[metric_col].fillna(0)

                # Clean up temp column
                df.drop("_total_children_for_agg", axis=1, inplace=True)

        result = result.sort_values("period")

        # Round ratio metrics to 2 decimal places
        for col in self.RATIO_METRICS:
            if col in result.columns:
                result[col] = result[col].round(2)

        if debug:
            print(f"\n=== Final result ({len(result)} periods) ===")
            print(result.to_string())
            print("=== END DEBUG ===\n")

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
