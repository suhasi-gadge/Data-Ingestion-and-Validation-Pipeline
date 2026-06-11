# Prototype Data Ingestion and Basic Validation Pipeline

This project implements a small, reusable data ingestion and validation pipeline for a raw tabular CSV dataset.

## Dataset

The demonstration uses a small CSV sample based on the public **Palmer Penguins** tabular dataset. It is suitable for validating common data-quality rules because it contains numeric measurements, categorical columns, and critical fields.

Included sample files:

- `data/sample_raw_penguins.csv` — valid sample data used for the successful validation scenario.
- `data/sample_invalid_penguins.csv` — intentionally invalid sample data for failure demonstration.

## Files

- `ingestion_validation_pipeline.py` — Python script for ingestion, validation, logging, cleaning, and validated output generation.
- `pipeline_demo.ipynb` — notebook demonstrating both successful and failed validation scenarios.
- `requirements.txt` — Python package requirements.
- `task_comment.txt` — copy/paste template for the task submission comment.

## Validation Checks Implemented

The pipeline performs more than three distinct validation checks:

1. Required column presence check
2. Missing values in critical columns
3. Numeric data type parse validation
4. Expected numeric range validation
5. Expected categorical value validation
6. Exact duplicate row detection

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run a successful validation scenario:

```bash
python ingestion_validation_pipeline.py \
  --input data/sample_raw_penguins.csv \
  --output output/validated_data.csv \
  --log-file output/validation_success.log
```

Run a simulated failure scenario:

```bash
python ingestion_validation_pipeline.py \
  --input data/sample_raw_penguins.csv \
  --output output/validated_data.csv \
  --log-file output/validation_failure.log \
  --simulate-failure
```

Run with the included invalid dataset:

```bash
python ingestion_validation_pipeline.py \
  --input data/sample_invalid_penguins.csv \
  --output output/validated_data.csv \
  --log-file output/validation_invalid_file.log
```

## Expected Output

When validation passes, the pipeline generates:

```text
output/validated_data.csv
```

When validation fails, the script logs the issues and does **not** generate a validated output file for that run.
