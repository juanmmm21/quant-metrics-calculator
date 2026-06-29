from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from quant_metrics_calculator.models import EquityPoint
from quant_metrics_calculator.returns import calculate_period_returns, mean_decimal


def test_calculate_period_returns() -> None:
    curve = [
        EquityPoint(datetime(2024, 1, 1, tzinfo=UTC), Decimal("100")),
        EquityPoint(datetime(2024, 1, 2, tzinfo=UTC), Decimal("110")),
        EquityPoint(datetime(2024, 1, 3, tzinfo=UTC), Decimal("99")),
    ]
    returns = calculate_period_returns(curve)
    assert returns[0] == Decimal("0.1")
    assert returns[1] == Decimal("-0.1")


def test_mean_decimal() -> None:
    assert mean_decimal([Decimal("1"), Decimal("3")]) == Decimal("2")
