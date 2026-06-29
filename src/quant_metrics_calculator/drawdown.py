from __future__ import annotations

from decimal import Decimal

from quant_metrics_calculator.models import EquityPoint


def calculate_max_drawdown_pct(equity_curve: list[EquityPoint]) -> Decimal:
    if not equity_curve:
        return Decimal("0")

    peak = equity_curve[0].equity
    max_drawdown = Decimal("0")

    for point in equity_curve:
        if point.equity > peak:
            peak = point.equity
        if peak <= Decimal("0"):
            continue
        drawdown = (peak - point.equity) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return max_drawdown


def calculate_total_return_pct(equity_curve: list[EquityPoint]) -> Decimal:
    if len(equity_curve) < 2:
        return Decimal("0")

    initial = equity_curve[0].equity
    final = equity_curve[-1].equity
    if initial <= Decimal("0"):
        raise ValueError("initial equity must be positive")
    return (final - initial) / initial
