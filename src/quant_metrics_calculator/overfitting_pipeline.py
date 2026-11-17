"""JSON in / JSON out wrapper around the overfitting diagnostics (used by the CLI)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from quant_metrics_calculator.overfitting import (
    deflated_sharpe_ratio,
    probability_of_backtest_overfitting,
    sharpe_ratio,
)


def load_returns_matrix(path: str | Path) -> dict[str, Any]:
    """Load ``{"strategies": [...], "returns": [[...], ...], ...}`` and validate its shape."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"returns file not found: {file_path}")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("returns file must contain a JSON object")
    strategies = payload.get("strategies")
    rows = payload.get("returns")
    if not isinstance(strategies, list) or not strategies:
        raise ValueError("'strategies' must be a non-empty list of names")
    if not isinstance(rows, list) or not rows:
        raise ValueError("'returns' must be a non-empty list of rows")
    width = len(strategies)
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != width:
            raise ValueError(f"row {index} must have {width} values")
        for value in row:
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"row {index} contains a non-finite value")
    return payload


def run_overfitting_pipeline(
    payload: dict[str, Any],
    *,
    selected: str | None = None,
    n_trials: int | None = None,
    periods_per_year: int | None = None,
    n_splits: int = 16,
    max_combinations: int | None = None,
) -> dict[str, Any]:
    strategies: list[str] = [str(name) for name in payload["strategies"]]
    rows: list[list[float]] = [[float(value) for value in row] for row in payload["returns"]]
    columns = [[row[col] for row in rows] for col in range(len(strategies))]
    sharpes = [sharpe_ratio(column) for column in columns]

    chosen = selected or payload.get("selected")
    if chosen is None:
        chosen = strategies[max(range(len(strategies)), key=lambda index: sharpes[index])]
    if chosen not in strategies:
        raise ValueError(f"selected strategy {chosen!r} is not in the matrix")

    trials = n_trials or int(payload.get("n_trials", len(strategies)))
    if trials < len(strategies):
        raise ValueError("n_trials cannot be smaller than the number of strategies in the matrix")
    extra_sharpes = payload.get("trial_sharpes")
    trial_sharpes = (
        [float(value) for value in extra_sharpes] if isinstance(extra_sharpes, list) else sharpes
    )
    ppy_raw = periods_per_year or payload.get("periods_per_year")
    ppy = int(ppy_raw) if ppy_raw else None

    dsr = deflated_sharpe_ratio(
        columns[strategies.index(chosen)],
        n_trials=trials,
        trial_sharpes=trial_sharpes,
        periods_per_year=ppy,
    )

    report: dict[str, Any] = {
        "selected_strategy": chosen,
        "n_observations": len(rows),
        "strategies": [
            {"name": name, "sharpe_ratio": sharpe}
            for name, sharpe in zip(strategies, sharpes, strict=True)
        ],
        "deflated_sharpe": {
            "sharpe_ratio": dsr.sharpe_ratio,
            "annualized_sharpe_ratio": dsr.annualized_sharpe_ratio,
            "benchmark_sharpe_ratio": dsr.benchmark_sharpe_ratio,
            "n_trials": dsr.n_trials,
            "trial_sharpe_variance": dsr.trial_sharpe_variance,
            "skewness": dsr.skewness,
            "kurtosis": dsr.kurtosis,
            "probabilistic_sharpe_ratio": dsr.probabilistic_sharpe_ratio,
            "deflated_sharpe_ratio": dsr.deflated_sharpe_ratio,
        },
        "pbo": None,
        "pbo_error": None,
    }
    if len(strategies) < 2:
        report["pbo_error"] = "PBO needs at least two candidate strategies"
        return report
    try:
        pbo = probability_of_backtest_overfitting(
            rows, n_splits=n_splits, max_combinations=max_combinations
        )
    except ValueError as exc:
        report["pbo_error"] = str(exc)
        return report
    report["pbo"] = {
        "probability_of_overfitting": pbo.probability_of_overfitting,
        "n_splits": pbo.n_splits,
        "n_combinations": pbo.n_combinations,
        "n_strategies": pbo.n_strategies,
        "probability_oos_loss": pbo.probability_oos_loss,
        "degradation_slope": pbo.degradation_slope,
        "degradation_intercept": pbo.degradation_intercept,
        "mean_is_sharpe": pbo.mean_is_sharpe,
        "mean_oos_sharpe": pbo.mean_oos_sharpe,
    }
    return report
