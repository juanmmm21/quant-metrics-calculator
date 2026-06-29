from __future__ import annotations

from decimal import Decimal

from quant_metrics_calculator.models import MetricsConfig
from quant_metrics_calculator.sharpe import calculate_sharpe_ratio


def test_sharpe_ratio_positive_for_upward_returns() -> None:
    returns = [Decimal("0.01"), Decimal("0.02"), Decimal("0.015")]
    sharpe = calculate_sharpe_ratio(returns, MetricsConfig(risk_free_rate_annual=Decimal("0")))
    assert sharpe > Decimal("0")
