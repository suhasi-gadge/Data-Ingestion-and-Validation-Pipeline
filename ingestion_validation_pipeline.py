"""
ingestion_validation_pipeline.py

Prototype data ingestion and basic validation pipeline for a raw tabular dataset.

Dataset used in the demo:
    Palmer Penguins tabular dataset, a public dataset commonly used for
    data science education and machine learning examples.

What the pipeline does:
    1. Ingests a CSV from a specified input path.
    2. Performs basic validation checks:
        - Required columns are present.
        - Critical columns do not contain missing values.
        - Numeric columns can be parsed to the correct data type.
        - Numeric columns fall within expected ranges.
        - Categorical columns contain only expected values.
        - Duplicate rows are identified.
    3. Logs all validation results to the console and to an optional log file.
    4. Writes a cleaned/validated CSV when validation passes.
    5. Can simulate a validation failure using --simulate-failure.

Example usage:
    python ingestion_validation_pipeline.py \
        --input data/sample_raw_penguins.csv \
        --output output/validated_data.csv \
        --log-file output/validation_report.log

    python ingestion_validation_pipeline.py \
        --input data/sample_raw_penguins.csv \
        --output output/validated_data.csv \
        --simulate-failure
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


REQUIRED_COLUMNS = [
    "species",
    "island",
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
    "sex",
    "year",
]

CRITICAL_COLUMNS = ["species", "island", "bill_length_mm", "body_mass_g", "sex", "year"]

NUMERIC_COLUMNS = [
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
    "year",
]

EXPECTED_RANGES: Dict[str, Tuple[float, float]] = {
    "bill_length_mm": (25, 70),
    "bill_depth_mm": (10, 30),
    "flipper_length_mm": (150, 250),
    "body_mass_g": (2500, 7000),
    "year": (2007, 2009),
}

EXPECTED_CATEGORIES: Dict[str, set] = {
    "species": {"Adelie", "Chinstrap", "Gentoo"},
    "island": {"Torgersen", "Biscoe", "Dream"},
    "sex": {"Male", "Female"},
}


class ValidationError(Exception):
    """Raised when one or more validation checks fail."""


def configure_logger(log_file: str | None = None) -> logging.Logger:
    """Configure console and optional file logging."""
    logger = logging.getLogger("ingestion_validation_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def ingest_data(input_path: str) -> pd.DataFrame:
    """Load raw CSV data from a specified file path."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    return pd.read_csv(path)


def simulate_validation_failure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intentionally introduce bad data to demonstrate validation failure handling.

    Introduced issues:
        - Missing critical species value
        - Invalid body_mass_g value outside expected range
        - Invalid bill_length_mm non-numeric value
        - Duplicate row
    """
    bad_df = df.copy()

    if bad_df.empty:
        return bad_df

    # Cast to object before injecting a string into a numeric-looking column,
    # keeping the simulation explicit and avoiding pandas dtype warnings.
    bad_df["bill_length_mm"] = bad_df["bill_length_mm"].astype("object")

    bad_df.loc[bad_df.index[0], "species"] = pd.NA
    bad_df.loc[bad_df.index[0], "body_mass_g"] = -100
    bad_df.loc[bad_df.index[0], "bill_length_mm"] = "not_a_number"
    bad_df = pd.concat([bad_df, bad_df.iloc[[0]]], ignore_index=True)

    return bad_df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply lightweight cleaning after validation passes.

    Cleaning steps:
        - Trim whitespace in string columns.
        - Cast numeric columns to numeric dtypes.
        - Drop exact duplicate rows.
    """
    cleaned = df.copy()

    for column in cleaned.select_dtypes(include="object").columns:
        cleaned[column] = cleaned[column].astype(str).str.strip()

    for column in NUMERIC_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    return cleaned


def validate_data(df: pd.DataFrame, logger: logging.Logger) -> List[str]:
    """
    Run validation checks and return a list of validation failure messages.
    """
    failures: List[str] = []

    logger.info("Starting validation checks...")
    logger.info("Rows ingested: %s | Columns ingested: %s", df.shape[0], df.shape[1])

    # 1. Required columns check
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        failures.append(f"Missing required columns: {missing_columns}")
    else:
        logger.info("PASS: All required columns are present.")

    if missing_columns:
        return failures

    # 2. Missing values in critical columns
    missing_summary = df[CRITICAL_COLUMNS].isna().sum()
    missing_failures = missing_summary[missing_summary > 0]
    if not missing_failures.empty:
        failures.append(f"Missing values found in critical columns: {missing_failures.to_dict()}")
    else:
        logger.info("PASS: No missing values found in critical columns.")

    # 3. Data type parse checks for numeric columns
    for column in NUMERIC_COLUMNS:
        parsed = pd.to_numeric(df[column], errors="coerce")
        invalid_count = parsed.isna().sum() - df[column].isna().sum()
        if invalid_count > 0:
            failures.append(f"Column '{column}' has {int(invalid_count)} non-numeric value(s).")
        else:
            logger.info("PASS: Column '%s' can be parsed as numeric.", column)

    # 4. Range checks for numeric columns
    for column, (min_value, max_value) in EXPECTED_RANGES.items():
        parsed = pd.to_numeric(df[column], errors="coerce")
        out_of_range = parsed.notna() & ~parsed.between(min_value, max_value)
        count = int(out_of_range.sum())
        if count > 0:
            failures.append(
                f"Column '{column}' has {count} value(s) outside expected range "
                f"[{min_value}, {max_value}]."
            )
        else:
            logger.info(
                "PASS: Column '%s' values are within expected range [%s, %s].",
                column,
                min_value,
                max_value,
            )

    # 5. Categorical value checks
    for column, allowed_values in EXPECTED_CATEGORIES.items():
        invalid_values = set(df[column].dropna().unique()) - allowed_values
        if invalid_values:
            failures.append(f"Column '{column}' has invalid value(s): {sorted(invalid_values)}")
        else:
            logger.info("PASS: Column '%s' contains only expected categories.", column)

    # 6. Duplicate row checks
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count > 0:
        failures.append(f"Found {duplicate_count} exact duplicate row(s).")
    else:
        logger.info("PASS: No exact duplicate rows found.")

    return failures


def run_pipeline(
    input_path: str,
    output_path: str = "output/validated_data.csv",
    log_file: str | None = None,
    simulate_failure: bool = False,
) -> Dict[str, object]:
    """
    Execute the ingestion, validation, and output pipeline.

    Returns a summary dictionary useful for notebooks and automated tests.
    """
    logger = configure_logger(log_file)
    logger.info("Pipeline started.")
    logger.info("Input path: %s", input_path)

    df = ingest_data(input_path)

    if simulate_failure:
        logger.info("Simulating validation failure by injecting bad records.")
        df = simulate_validation_failure(df)

    failures = validate_data(df, logger)

    result = {
        "input_path": input_path,
        "output_path": output_path,
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "validation_passed": len(failures) == 0,
        "failures": failures,
    }

    if failures:
        logger.error("VALIDATION FAILED. Issues found:")
        for index, failure in enumerate(failures, start=1):
            logger.error("%s. %s", index, failure)
        logger.error("Validated output file was not generated.")
        return result

    cleaned = clean_data(df)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output, index=False)

    logger.info("VALIDATION PASSED.")
    logger.info("Cleaned/validated data written to: %s", output_path)
    logger.info("Final validated row count: %s", cleaned.shape[0])

    result["validated_row_count"] = int(cleaned.shape[0])
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a prototype data ingestion and validation pipeline."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to raw input CSV file.",
    )
    parser.add_argument(
        "--output",
        default="output/validated_data.csv",
        help="Path where validated CSV should be written when validation passes.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional path to write validation log output.",
    )
    parser.add_argument(
        "--simulate-failure",
        action="store_true",
        help="Inject intentionally bad records to demonstrate validation failure.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    run_pipeline(
        input_path=args.input,
        output_path=args.output,
        log_file=args.log_file,
        simulate_failure=args.simulate_failure,
    )


if __name__ == "__main__":
    main()
