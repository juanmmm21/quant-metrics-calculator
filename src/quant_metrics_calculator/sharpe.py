from __future__ import annotations

from decimal import Decimal

from quant_metrics_calculator.models import MetricsConfig
from quant_metrics_calculator.returns import mean_decimal, sample_std_decimal


def calculate_sharpe_ratio(returns: list[Decimal], config: MetricsConfig) -> Decimal:
    if len(returns) < config.min_observations:
        return Decimal("0")

    period_rf = config.risk_free_rate_annual / Decimal(config.periods_per_year)
    excess = [value - period_rf for value in returns]
    std_dev = sample_std_decimal(excess)
    if std_dev == Decimal("0"):
        return Decimal("0")

    mean_excess = mean_decimal(excess)
    annualization = Decimal(config.periods_per_year).sqrt()
    return (mean_excess / std_dev) * annualization
