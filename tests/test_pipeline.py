from __future__ import annotations

from pathlib import Path

from quant_metrics_calculator.models import MetricsConfig
from quant_metrics_calculator.pipeline import run_metrics_pipeline


def test_pipeline_runs_sample_files() -> None:
    root = Path(__file__).resolve().parents[1]
    result = run_metrics_pipeline(
        fills_path=str(root / "samples" / "btcusdt_fills.jsonl"),
        equity_path=str(root / "samples" / "btcusdt_equity.json"),
        symbol="BTCUSDT",
        config=MetricsConfig(),
    )
    assert result["trade_count"] == 2
    assert float(result["total_return_pct"]) == 0.003
    assert float(result["max_drawdown_pct"]) > 0
