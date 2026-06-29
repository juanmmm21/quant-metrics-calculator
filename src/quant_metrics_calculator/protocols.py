from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from quant_metrics_calculator.models import (
    ClosedTrade,
    EquityPoint,
    MetricsConfig,
    PerformanceMetrics,
    TradeFill,
)


class MetricsCalculatorProtocol(Protocol):
    def compute(
        self,
        fills: list[TradeFill],
        equity_curve: list[EquityPoint],
        config: MetricsConfig,
    ) -> PerformanceMetrics:
        ...


class ReturnSeriesCalculator(Protocol):
    def calculate(self, equity_curve: list[EquityPoint]) -> list[Decimal]:
        ...


class ClosedTradeReconstructor(Protocol):
    def reconstruct(self, fills: list[TradeFill]) -> list[ClosedTrade]:
        ...
