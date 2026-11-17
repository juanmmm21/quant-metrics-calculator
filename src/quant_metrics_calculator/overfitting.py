"""Backtest overfitting diagnostics.

Implements the Deflated Sharpe Ratio (Bailey & López de Prado, 2014) and the Probability of
Backtest Overfitting estimated with Combinatorially Symmetric Cross-Validation (Bailey, Borwein,
López de Prado & Zhu, 2017).

These are statistical estimates, so they use ``float`` (like the ecosystem's TA math) instead of
``Decimal``, which stays reserved for money.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from statistics import NormalDist

EULER_MASCHERONI = 0.5772156649015329
_NORMAL = NormalDist()


@dataclass(frozen=True, slots=True)
class ReturnMoments:
    """Sample moments of a return series (kurtosis is Pearson's, so a normal gives 3)."""

    n_observations: int
    mean: float
    std: float
    skewness: float
    kurtosis: float


@dataclass(frozen=True, slots=True)
class DeflatedSharpeResult:
    sharpe_ratio: float
    annualized_sharpe_ratio: float | None
    benchmark_sharpe_ratio: float
    n_trials: int
    trial_sharpe_variance: float
    n_observations: int
    skewness: float
    kurtosis: float
    probabilistic_sharpe_ratio: float
    deflated_sharpe_ratio: float


@dataclass(frozen=True, slots=True)
class PboResult:
    probability_of_overfitting: float
    n_splits: int
    n_combinations: int
    n_strategies: int
    n_observations: int
    logits: tuple[float, ...]
    probability_oos_loss: float
    degradation_slope: float
    degradation_intercept: float
    mean_is_sharpe: float
    mean_oos_sharpe: float


def return_moments(returns: Sequence[float]) -> ReturnMoments:
    n = len(returns)
    if n < 2:
        raise ValueError("at least two returns are required")
    mean = math.fsum(returns) / n
    deviations = [value - mean for value in returns]
    m2 = math.fsum(d * d for d in deviations) / n
    sample_var = m2 * n / (n - 1)
    std = math.sqrt(sample_var)
    if m2 == 0.0:
        return ReturnMoments(n, mean, 0.0, 0.0, 3.0)
    m3 = math.fsum(d**3 for d in deviations) / n
    m4 = math.fsum(d**4 for d in deviations) / n
    return ReturnMoments(
        n_observations=n,
        mean=mean,
        std=std,
        skewness=m3 / m2**1.5,
        kurtosis=m4 / (m2 * m2),
    )


def sharpe_ratio(returns: Sequence[float]) -> float:
    """Per-period (non-annualized) Sharpe ratio of excess returns; 0 when volatility is 0."""
    moments = return_moments(returns)
    if moments.std == 0.0:
        return 0.0
    return moments.mean / moments.std


def probabilistic_sharpe_ratio(
    sharpe: float,
    benchmark_sharpe: float,
    n_observations: int,
    skewness: float,
    kurtosis: float,
) -> float:
    """P[true SR > benchmark] given the estimated per-period SR and the return moments."""
    if n_observations < 2:
        raise ValueError("n_observations must be at least 2")
    variance_term = 1.0 - skewness * sharpe + (kurtosis - 1.0) / 4.0 * sharpe * sharpe
    if variance_term <= 0.0:
        # Extreme moments make the asymptotic variance degenerate; fall back to the normal case.
        variance_term = 1.0 + 0.5 * sharpe * sharpe
    z = (sharpe - benchmark_sharpe) * math.sqrt(n_observations - 1) / math.sqrt(variance_term)
    return _NORMAL.cdf(z)


def expected_maximum_sharpe(n_trials: int, trial_sharpe_variance: float) -> float:
    """Expected maximum per-period SR among ``n_trials`` independent zero-skill trials."""
    if n_trials < 1:
        raise ValueError("n_trials must be at least 1")
    if trial_sharpe_variance < 0.0:
        raise ValueError("trial_sharpe_variance must be non-negative")
    if n_trials == 1 or trial_sharpe_variance == 0.0:
        return 0.0
    z_first = _NORMAL.inv_cdf(1.0 - 1.0 / n_trials)
    z_second = _NORMAL.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    expected_z = (1.0 - EULER_MASCHERONI) * z_first + EULER_MASCHERONI * z_second
    return math.sqrt(trial_sharpe_variance) * expected_z


def deflated_sharpe_ratio(
    returns: Sequence[float],
    *,
    n_trials: int,
    trial_sharpes: Sequence[float] | None = None,
    trial_sharpe_variance: float | None = None,
    periods_per_year: int | None = None,
) -> DeflatedSharpeResult:
    """Deflated Sharpe Ratio of the selected strategy's returns.

    ``n_trials`` is the number of configurations tried before choosing this one. The variance of
    their per-period Sharpe ratios is taken from ``trial_sharpes`` or given directly.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be at least 1")
    if trial_sharpe_variance is None:
        if trial_sharpes is None:
            if n_trials > 1:
                raise ValueError("trial_sharpes or trial_sharpe_variance is required")
            trial_sharpe_variance = 0.0
        elif len(trial_sharpes) < 2:
            trial_sharpe_variance = 0.0
        else:
            trial_sharpe_variance = return_moments(trial_sharpes).std ** 2

    moments = return_moments(returns)
    sharpe = 0.0 if moments.std == 0.0 else moments.mean / moments.std
    benchmark = expected_maximum_sharpe(n_trials, trial_sharpe_variance)
    psr = probabilistic_sharpe_ratio(
        sharpe, 0.0, moments.n_observations, moments.skewness, moments.kurtosis
    )
    dsr = probabilistic_sharpe_ratio(
        sharpe, benchmark, moments.n_observations, moments.skewness, moments.kurtosis
    )
    annualized = sharpe * math.sqrt(periods_per_year) if periods_per_year else None
    return DeflatedSharpeResult(
        sharpe_ratio=sharpe,
        annualized_sharpe_ratio=annualized,
        benchmark_sharpe_ratio=benchmark,
        n_trials=n_trials,
        trial_sharpe_variance=trial_sharpe_variance,
        n_observations=moments.n_observations,
        skewness=moments.skewness,
        kurtosis=moments.kurtosis,
        probabilistic_sharpe_ratio=psr,
        deflated_sharpe_ratio=dsr,
    )


def probability_of_backtest_overfitting(
    returns_matrix: Sequence[Sequence[float]],
    *,
    n_splits: int = 16,
    max_combinations: int | None = None,
    seed: int = 0,
) -> PboResult:
    """PBO via CSCV over a T x N matrix of per-period returns (rows: time, columns: strategies).

    Rows are cut into ``n_splits`` contiguous blocks. For every way of choosing half of the
    blocks as in-sample, the strategy with the best in-sample Sharpe is located in the
    out-of-sample ranking. PBO is the share of combinations where it ranks at or below the
    out-of-sample median (logit <= 0, the conservative convention).
    """
    if n_splits < 2 or n_splits % 2:
        raise ValueError("n_splits must be an even number >= 2")
    n_rows = len(returns_matrix)
    if n_rows < 2 * n_splits:
        raise ValueError("need at least two observations per split")
    n_strategies = len(returns_matrix[0])
    if n_strategies < 2:
        raise ValueError("PBO needs at least two strategies")
    if any(len(row) != n_strategies for row in returns_matrix):
        raise ValueError("returns_matrix must be rectangular")

    blocks = _block_statistics(returns_matrix, n_splits, n_strategies)
    all_blocks = frozenset(range(n_splits))
    combos: list[tuple[int, ...]] = list(combinations(range(n_splits), n_splits // 2))
    if max_combinations is not None and len(combos) > max_combinations:
        combos = random.Random(seed).sample(combos, max_combinations)

    logits: list[float] = []
    is_best: list[float] = []
    oos_of_best: list[float] = []
    for combo in combos:
        is_sharpes = _sharpes_for(blocks, combo, n_strategies)
        oos_sharpes = _sharpes_for(blocks, tuple(sorted(all_blocks - set(combo))), n_strategies)
        best = max(range(n_strategies), key=lambda index: (is_sharpes[index], -index))
        rank = _average_rank(oos_sharpes, best)
        omega = rank / (n_strategies + 1)
        logits.append(math.log(omega / (1.0 - omega)))
        is_best.append(is_sharpes[best])
        oos_of_best.append(oos_sharpes[best])

    total = len(logits)
    slope, intercept = _linear_fit(is_best, oos_of_best)
    return PboResult(
        probability_of_overfitting=sum(1 for value in logits if value <= 0.0) / total,
        n_splits=n_splits,
        n_combinations=total,
        n_strategies=n_strategies,
        n_observations=n_rows,
        logits=tuple(logits),
        probability_oos_loss=sum(1 for value in oos_of_best if value < 0.0) / total,
        degradation_slope=slope,
        degradation_intercept=intercept,
        mean_is_sharpe=math.fsum(is_best) / total,
        mean_oos_sharpe=math.fsum(oos_of_best) / total,
    )


@dataclass(frozen=True, slots=True)
class _Block:
    count: int
    sums: tuple[float, ...]
    squares: tuple[float, ...]


def _block_statistics(
    matrix: Sequence[Sequence[float]], n_splits: int, n_strategies: int
) -> list[_Block]:
    n_rows = len(matrix)
    base, extra = divmod(n_rows, n_splits)
    blocks: list[_Block] = []
    start = 0
    for index in range(n_splits):
        size = base + (1 if index < extra else 0)
        rows = matrix[start : start + size]
        start += size
        sums = tuple(math.fsum(row[col] for row in rows) for col in range(n_strategies))
        squares = tuple(math.fsum(row[col] ** 2 for row in rows) for col in range(n_strategies))
        blocks.append(_Block(size, sums, squares))
    return blocks


def _sharpes_for(blocks: list[_Block], chosen: tuple[int, ...], n_strategies: int) -> list[float]:
    count = sum(blocks[index].count for index in chosen)
    result: list[float] = []
    for col in range(n_strategies):
        total = math.fsum(blocks[index].sums[col] for index in chosen)
        squares = math.fsum(blocks[index].squares[col] for index in chosen)
        mean = total / count
        variance = max((squares - count * mean * mean) / (count - 1), 0.0)
        std = math.sqrt(variance)
        result.append(0.0 if std <= 1e-15 else mean / std)
    return result


def _average_rank(values: list[float], position: int) -> float:
    """1-based ascending rank of ``values[position]``; ties share their average rank."""
    target = values[position]
    below = sum(1 for value in values if value < target)
    equal = sum(1 for value in values if value == target)
    return below + (equal + 1) / 2.0


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mean_x = math.fsum(xs) / n
    mean_y = math.fsum(ys) / n
    var_x = math.fsum((x - mean_x) ** 2 for x in xs)
    if var_x == 0.0:
        return 0.0, mean_y
    cov = math.fsum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    slope = cov / var_x
    return slope, mean_y - slope * mean_x
