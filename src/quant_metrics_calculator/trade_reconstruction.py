from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from quant_metrics_calculator.models import ClosedTrade, FillSide, TradeFill


@dataclass(slots=True)
class _OpenLot:
    quantity: Decimal
    entry_price: Decimal
    commission: Decimal
    opened_at: datetime


class FifoTradeReconstructor:
    """Reconstruye round-trips long usando FIFO sobre fills."""

    def reconstruct(self, fills: list[TradeFill]) -> list[ClosedTrade]:
        sorted_fills = sorted(fills, key=lambda fill: fill.filled_at)
        open_lots: list[_OpenLot] = []
        closed: list[ClosedTrade] = []
        trade_counter = 0

        for fill in sorted_fills:
            if fill.side is FillSide.BUY:
                open_lots.append(
                    _OpenLot(
                        quantity=fill.quantity,
                        entry_price=fill.price,
                        commission=fill.commission,
                        opened_at=fill.filled_at,
                    )
                )
                continue

            remaining = fill.quantity
            exit_commission = fill.commission
            per_unit_exit_commission = (
                exit_commission / fill.quantity if fill.quantity > Decimal("0") else Decimal("0")
            )

            while remaining > Decimal("0") and open_lots:
                lot = open_lots[0]
                matched = min(remaining, lot.quantity)
                entry_commission_share = (
                    lot.commission * (matched / lot.quantity)
                    if lot.quantity > Decimal("0")
                    else Decimal("0")
                )
                exit_commission_share = per_unit_exit_commission * matched
                total_commission = entry_commission_share + exit_commission_share

                gross_pnl = (fill.price - lot.entry_price) * matched
                net_pnl = gross_pnl - total_commission
                trade_counter += 1
                closed.append(
                    ClosedTrade(
                        trade_id=f"trade-{trade_counter}",
                        symbol=fill.symbol,
                        quantity=matched,
                        entry_price=lot.entry_price,
                        exit_price=fill.price,
                        gross_pnl=gross_pnl,
                        net_pnl=net_pnl,
                        commission=total_commission,
                        opened_at=lot.opened_at,
                        closed_at=fill.filled_at,
                    )
                )

                lot.quantity -= matched
                lot.commission -= entry_commission_share
                remaining -= matched
                if lot.quantity == Decimal("0"):
                    open_lots.pop(0)

            if remaining > Decimal("0"):
                raise ValueError("sell quantity exceeds open long position")

        return closed
