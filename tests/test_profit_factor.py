from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from quant_metrics_calculator.models import FillSide, TradeFill
from quant_metrics_calculator.profit_factor import calculate_profit_factor
from quant_metrics_calculator.trade_reconstruction import FifoTradeReconstructor


def _fill(side: FillSide, price: str, order_id: str, hour: int) -> TradeFill:
    return TradeFill(
        order_id=order_id,
        symbol="BTCUSDT",
        side=side,
        quantity=Decimal("0.01"),
        price=Decimal(price),
        commission=Decimal("0.1"),
        filled_at=datetime(2024, 1, 1, hour, tzinfo=UTC),
    )


def test_fifo_reconstructor_builds_closed_trades() -> None:
    fills = [
        _fill(FillSide.BUY, "100", "b1", 12),
        _fill(FillSide.SELL, "110", "s1", 13),
    ]
    trades = FifoTradeReconstructor().reconstruct(fills)
    assert len(trades) == 1
    assert trades[0].gross_pnl == Decimal("0.1")
    assert trades[0].net_pnl == Decimal("-0.1")


def test_profit_factor_counts_winning_round_trip() -> None:
    fills = [
        _fill(FillSide.BUY, "100", "b1", 12),
        TradeFill(
            order_id="s1",
            symbol="BTCUSDT",
            side=FillSide.SELL,
            quantity=Decimal("0.01"),
            price=Decimal("200"),
            commission=Decimal("0.01"),
            filled_at=datetime(2024, 1, 1, 13, tzinfo=UTC),
        ),
    ]
    fills[0] = TradeFill(
        order_id="b1",
        symbol="BTCUSDT",
        side=FillSide.BUY,
        quantity=Decimal("0.01"),
        price=Decimal("100"),
        commission=Decimal("0.01"),
        filled_at=datetime(2024, 1, 1, 12, tzinfo=UTC),
    )
    trades = FifoTradeReconstructor().reconstruct(fills)
    gross_profit, gross_loss, factor = calculate_profit_factor(trades)
    assert gross_profit > Decimal("0")
    assert gross_loss == Decimal("0")
    assert factor == Decimal("999")
