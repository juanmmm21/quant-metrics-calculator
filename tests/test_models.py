from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from quant_metrics_calculator.models import EquityPoint, FillSide, MetricsConfig, TradeFill


def test_trade_fill_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="filled_at must be timezone-aware"):
        TradeFill(
            order_id="ord-1",
            symbol="BTCUSDT",
            side=FillSide.BUY,
            quantity=Decimal("0.01"),
            price=Decimal("100"),
            commission=Decimal("0"),
            filled_at=datetime(2024, 1, 1),
        )


def test_metrics_config_requires_positive_periods() -> None:
    with pytest.raises(ValueError, match="periods_per_year"):
        MetricsConfig(periods_per_year=0)


def test_equity_point_requires_positive_equity() -> None:
    with pytest.raises(ValueError, match="equity must be positive"):
        EquityPoint(
            event_time=datetime(2024, 1, 1, tzinfo=UTC),
            equity=Decimal("0"),
        )
