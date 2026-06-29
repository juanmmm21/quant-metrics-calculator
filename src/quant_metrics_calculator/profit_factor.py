from __future__ import annotations

from decimal import Decimal

from quant_metrics_calculator.models import ClosedTrade


def calculate_profit_factor(trades: list[ClosedTrade]) -> tuple[Decimal, Decimal, Decimal]:
    gross_profit = Decimal("0")
    gross_loss = Decimal("0")

    for trade in trades:
        if trade.net_pnl > Decimal("0"):
            gross_profit += trade.net_pnl
        elif trade.net_pnl < Decimal("0"):
            gross_loss += abs(trade.net_pnl)

    if gross_loss == Decimal("0"):
        if gross_profit > Decimal("0"):
            return gross_profit, gross_loss, Decimal("999")
        return gross_profit, gross_loss, Decimal("0")

    return gross_profit, gross_loss, gross_profit / gross_loss


def calculate_win_rate(trades: list[ClosedTrade]) -> tuple[Decimal, int, int]:
    if not trades:
        return Decimal("0"), 0, 0

    winners = sum(1 for trade in trades if trade.net_pnl > Decimal("0"))
    losers = sum(1 for trade in trades if trade.net_pnl < Decimal("0"))
    win_rate = Decimal(winners) / Decimal(len(trades))
    return win_rate, winners, losers
