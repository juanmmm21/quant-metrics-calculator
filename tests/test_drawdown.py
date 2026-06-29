from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from quant_metrics_calculator.drawdown import calculate_max_drawdown_pct, calculate_total_return_pct
from quant_metrics_calculator.models import EquityPoint


def test_max_drawdown_from_equity_curve() -> None:
    curve = [
        EquityPoint(datetime(2024, 1, 1, tzinfo=UTC), Decimal("100")),
        EquityPoint(datetime(2024, 1, 2, tzinfo=UTC), Decimal("120")),
        EquityPoint(datetime(2024, 1, 3, tzinfo=UTC), Decimal("90")),
    ]
    assert calculate_max_drawdown_pct(curve) == Decimal("0.25")


def test_total_return_pct() -> None:
    curve = [
        EquityPoint(datetime(2024, 1, 1, tzinfo=UTC), Decimal("100")),
        EquityPoint(datetime(2024, 1, 2, tzinfo=UTC), Decimal("110")),
    ]
    assert calculate_total_return_pct(curve) == Decimal("0.1")
