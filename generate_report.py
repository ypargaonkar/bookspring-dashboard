#!/usr/bin/env python3
"""CLI tool to generate BookSpring Excel reports."""
import argparse
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from src.api.fusioo_client import FusiooClient, ACTIVITY_REPORT_APP_ID, PROGRAM_PARTNERS_APP_ID
from src.data.processor import DataProcessor
from src.reports.excel_generator import generate_standard_report


def parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format."""
    return date.fromisoformat(date_str)


def main():
    parser = argparse.ArgumentParser(description="Generate BookSpring Excel reports")

    parser.add_argument(
        "--source", "-s",
        choices=["activity", "partners"],
        default="activity",
        help="Data source (default: activity)"
    )
    parser.add_argument(
        "--start", "-S",
        type=parse_date,
        default=date.today() - relativedelta(years=1),
        help="Start date (YYYY-MM-DD, default: 1 year ago)"
    )
    parser.add_argument(
        "--end", "-E",
        type=parse_date,
        default=date.today(),
        help="End date (YYYY-MM-DD, default: today)"
    )
    parser.add_argument(
        "--time-unit", "-t",
        choices=["day", "week", "month", "quarter", "year", "fiscal_year"],
        default="month",
        help="Time aggregation unit (default: month)"
    )
    parser.add_argument(
        "--output", "-o",
        default=f"reports/bookspring_report_{date.today().isoformat()}.xlsx",
        help="Output file path"
    )

    args = parser.parse_args()

    # Select app ID
    app_id = ACTIVITY_REPORT_APP_ID if args.source == "activity" else PROGRAM_PARTNERS_APP_ID

    print(f"Loading data from Fusioo ({args.source})...")
    client = FusiooClient()
    records = client.get_all_records(app_id)
    print(f"Loaded {len(records)} records")

    # Process data
    processor = DataProcessor(records)
    processor = processor.filter_by_date_range(args.start, args.end)
    print(f"Filtered to {len(processor.df)} records in date range")

    # Generate report
    print(f"Generating report with {args.time_unit} aggregation...")
    output_path = generate_standard_report(processor, args.output, args.time_unit)
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
