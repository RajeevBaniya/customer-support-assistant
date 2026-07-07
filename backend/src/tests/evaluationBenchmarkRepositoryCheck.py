import pytest

from src.evaluation.repositories.benchmarkDatasetRepository import BenchmarkDatasetRepository


def test_benchmark_rows_limit() -> None:
    rows = [{"query": "abc" * 2, "top_k": None, "document_ids": None, "prior_turns_text": None}]
    BenchmarkDatasetRepository.validate_rows(rows)


def test_benchmark_rows_over_limit() -> None:
    rows = [{"query": f"q{i:03d}" * 2, "top_k": None, "document_ids": None} for i in range(1001)]
    with pytest.raises(ValueError, match="benchmark_rows_over_limit"):
        BenchmarkDatasetRepository.validate_rows(rows)
