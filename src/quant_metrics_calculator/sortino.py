from __future__ import annotations

from decimal import Decimal

from quant_metrics_calculator.models import MetricsConfig
from quant_metrics_calculator.returns import downside_std_decimal, mean_decimal


def calculate_sortino_ratio(returns: list[Decimal], config: MetricsConfig) -> Decimal:
    if len(returns) < config.min_observations:
        return Decimal("0")

    period_rf = config.risk_free_rate_annual / Decimal(config.periods_per_year)
    excess = [value - period_rf for value in returns]
    downside = downside_std_decimal(excess, target=Decimal("0"))
    if downside == Decimal("0"):
        return Decimal("0")

    mean_excess = mean_decimal(excess)
    annualization = Decimal(config.periods_per_year).sqrt()
    return (mean_excess / downside) * annualization
