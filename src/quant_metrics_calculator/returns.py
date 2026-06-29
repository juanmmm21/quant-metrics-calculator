from __future__ import annotations

from decimal import Decimal

from quant_metrics_calculator.models import EquityPoint


def calculate_period_returns(equity_curve: list[EquityPoint]) -> list[Decimal]:
    if len(equity_curve) < 2:
        return []

    returns: list[Decimal] = []
    previous = equity_curve[0].equity
    for point in equity_curve[1:]:
        if previous <= Decimal("0"):
            raise ValueError("equity must remain positive to compute returns")
        period_return = (point.equity - previous) / previous
        returns.append(period_return)
        previous = point.equity
    return returns


def mean_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


def sample_std_decimal(values: list[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal("0")
    avg = mean_decimal(values)
    variance = sum((value - avg) ** 2 for value in values) / Decimal(len(values) - 1)
    if variance <= Decimal("0"):
        return Decimal("0")
    return variance.sqrt()


def downside_std_decimal(values: list[Decimal], target: Decimal = Decimal("0")) -> Decimal:
    downside = [min(value - target, Decimal("0")) for value in values]
    squared = [value * value for value in downside]
    if len(squared) < 2:
        return Decimal("0")
    avg = sum(squared, start=Decimal("0")) / Decimal(len(squared))
    if avg <= Decimal("0"):
        return Decimal("0")
    return avg.sqrt()
