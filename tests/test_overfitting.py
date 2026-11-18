from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from quant_metrics_calculator.overfitting import (
    deflated_sharpe_ratio,
    expected_maximum_sharpe,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
    return_moments,
)
from quant_metrics_calculator.overfitting_pipeline import (
    load_returns_matrix,
    run_overfitting_pipeline,
)


def test_moments_of_symmetric_series() -> None:
    moments = return_moments([-1.0, 0.0, 1.0, -1.0, 0.0, 1.0])
    assert moments.mean == pytest.approx(0.0)
    assert moments.skewness == pytest.approx(0.0)
    assert moments.kurtosis == pytest.approx(1.5)


def test_paper_example_bailey_lopez_de_prado_2014() -> None:
    # Annualized SR 2.5 over 1250 daily observations, skew -3, kurtosis 10,
    # after 100 trials whose annualized SR variance is 0.5 -> DSR ~ 0.90 in the paper.
    sharpe = 2.5 / math.sqrt(250)
    benchmark = expected_maximum_sharpe(100, 0.5 / 250)
    assert benchmark == pytest.approx(0.1132, abs=1e-3)
    dsr = probabilistic_sharpe_ratio(sharpe, benchmark, 1250, -3.0, 10.0)
    assert dsr == pytest.approx(0.90, abs=0.01)


def test_more_trials_deflate_more() -> None:
    rng = random.Random(7)
    returns = [rng.gauss(0.001, 0.01) for _ in range(500)]
    trial_sharpes = [rng.gauss(0.0, 0.05) for _ in range(50)]
    few = deflated_sharpe_ratio(returns, n_trials=2, trial_sharpes=trial_sharpes)
    many = deflated_sharpe_ratio(returns, n_trials=1000, trial_sharpes=trial_sharpes)
    assert many.benchmark_sharpe_ratio > few.benchmark_sharpe_ratio
    assert many.deflated_sharpe_ratio < few.deflated_sharpe_ratio
    assert few.deflated_sharpe_ratio <= few.probabilistic_sharpe_ratio


def test_single_trial_dsr_equals_psr() -> None:
    rng = random.Random(1)
    returns = [rng.gauss(0.0005, 0.01) for _ in range(300)]
    result = deflated_sharpe_ratio(returns, n_trials=1, periods_per_year=365)
    assert result.benchmark_sharpe_ratio == 0.0
    assert result.deflated_sharpe_ratio == pytest.approx(result.probabilistic_sharpe_ratio)
    assert result.annualized_sharpe_ratio == pytest.approx(result.sharpe_ratio * math.sqrt(365))


def test_dsr_requires_trial_dispersion_when_many_trials() -> None:
    with pytest.raises(ValueError):
        deflated_sharpe_ratio([0.01, 0.02, -0.01], n_trials=5)


def _noise_matrix(rows: int, cols: int, seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 0.01) for _ in range(cols)] for _ in range(rows)]


def test_pbo_of_pure_noise_is_near_one_half() -> None:
    result = probability_of_backtest_overfitting(_noise_matrix(800, 10, 3), n_splits=10)
    assert result.n_combinations == math.comb(10, 5)
    assert 0.3 < result.probability_of_overfitting < 0.7


def test_pbo_with_genuine_edge_is_low() -> None:
    matrix = _noise_matrix(800, 10, 4)
    for row in matrix:
        row[0] += 0.004  # a real, persistent edge in strategy 0
    result = probability_of_backtest_overfitting(matrix, n_splits=10)
    assert result.probability_of_overfitting < 0.05
    assert result.mean_oos_sharpe > 0.0


def test_pbo_flags_regime_flip_as_overfit() -> None:
    # Strategy 0 is great in the first half and terrible in the second: picking it in-sample
    # means it lands at the bottom out-of-sample in most combinations.
    matrix = _noise_matrix(800, 6, 5)
    for index, row in enumerate(matrix):
        row[0] += 0.006 if index < 400 else -0.006
    result = probability_of_backtest_overfitting(matrix, n_splits=8)
    assert result.probability_of_overfitting > 0.5
    assert result.degradation_slope < 0.0


def test_pbo_validates_inputs() -> None:
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(_noise_matrix(100, 3, 1), n_splits=7)
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(_noise_matrix(10, 3, 1), n_splits=16)
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(_noise_matrix(100, 1, 1), n_splits=4)


def test_pbo_combination_sampling_is_deterministic() -> None:
    matrix = _noise_matrix(400, 4, 9)
    first = probability_of_backtest_overfitting(matrix, n_splits=16, max_combinations=200)
    second = probability_of_backtest_overfitting(matrix, n_splits=16, max_combinations=200)
    assert first.n_combinations == 200
    assert first.logits == second.logits


def test_overfit_pipeline_from_file(tmp_path: Path) -> None:
    matrix = _noise_matrix(320, 3, 11)
    path = tmp_path / "returns.json"
    path.write_text(
        json.dumps({"strategies": ["a", "b", "c"], "returns": matrix, "n_trials": 10}),
        encoding="utf-8",
    )
    report = run_overfitting_pipeline(load_returns_matrix(path), periods_per_year=8760, n_splits=8)
    assert report["selected_strategy"] in {"a", "b", "c"}
    assert report["deflated_sharpe"]["n_trials"] == 10
    assert 0.0 <= report["deflated_sharpe"]["deflated_sharpe_ratio"] <= 1.0
    assert report["pbo"]["n_combinations"] == math.comb(8, 4)
    json.dumps(report)


def test_overfit_pipeline_single_strategy_reports_pbo_error(tmp_path: Path) -> None:
    path = tmp_path / "returns.json"
    path.write_text(
        json.dumps({"strategies": ["only"], "returns": [[0.01], [-0.02], [0.005]]}),
        encoding="utf-8",
    )
    report = run_overfitting_pipeline(load_returns_matrix(path))
    assert report["pbo"] is None
    assert "two candidate" in report["pbo_error"]


def test_load_rejects_ragged_matrix(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"strategies": ["a", "b"], "returns": [[0.1]]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_returns_matrix(path)
