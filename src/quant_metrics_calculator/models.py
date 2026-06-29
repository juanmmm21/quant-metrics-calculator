from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class FillSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class TradeFill:
    order_id: str
    symbol: str
    side: FillSide
    quantity: Decimal
    price: Decimal
    commission: Decimal
    filled_at: datetime

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id must not be empty")
        if not self.symbol:
            raise ValueError("symbol must not be empty")
        if self.quantity <= Decimal("0"):
            raise ValueError("quantity must be positive")
        if self.price <= Decimal("0"):
            raise ValueError("price must be positive")
        if self.commission < Decimal("0"):
            raise ValueError("commission must be non-negative")
        if self.filled_at.tzinfo is None:
            raise ValueError("filled_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    trade_id: str
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    commission: Decimal
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not self.trade_id:
            raise ValueError("trade_id must not be empty")
        if self.quantity <= Decimal("0"):
            raise ValueError("quantity must be positive")
        if self.entry_price <= Decimal("0") or self.exit_price <= Decimal("0"):
            raise ValueError("prices must be positive")
        if self.commission < Decimal("0"):
            raise ValueError("commission must be non-negative")
        if self.opened_at.tzinfo is None or self.closed_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")


@dataclass(frozen=True, slots=True)
class EquityPoint:
    event_time: datetime
    equity: Decimal

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if self.equity <= Decimal("0"):
            raise ValueError("equity must be positive")


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    risk_free_rate_annual: Decimal = Decimal("0.02")
    periods_per_year: int = 252
    min_observations: int = 2

    def __post_init__(self) -> None:
        if self.periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")
        if self.min_observations < 2:
            raise ValueError("min_observations must be at least 2")


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    profit_factor: Decimal
    max_drawdown_pct: Decimal
    total_return_pct: Decimal
    win_rate: Decimal
    trade_count: int
    winning_trades: int
    losing_trades: int
    gross_profit: Decimal
    gross_loss: Decimal
    equity_curve: tuple[EquityPoint, ...]

    def __post_init__(self) -> None:
        if self.trade_count < 0:
            raise ValueError("trade_count must be non-negative")
        if self.winning_trades < 0 or self.losing_trades < 0:
            raise ValueError("trade win/loss counts must be non-negative")
        if self.gross_profit < Decimal("0") or self.gross_loss < Decimal("0"):
            raise ValueError("gross profit and loss must be non-negative")


def utc_from_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def decimal_from_value(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise ValueError(f"{field_name} must be numeric")


def parse_fill_side(value: str) -> FillSide:
    try:
        return FillSide(value)
    except ValueError as exc:
        raise ValueError(f"unsupported fill side: {value}") from exc
