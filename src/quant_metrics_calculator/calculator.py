from __future__ import annotations

import logging

from quant_metrics_calculator.drawdown import calculate_max_drawdown_pct, calculate_total_return_pct
from quant_metrics_calculator.models import (
    EquityPoint,
    MetricsConfig,
    PerformanceMetrics,
    TradeFill,
)
from quant_metrics_calculator.profit_factor import calculate_profit_factor, calculate_win_rate
from quant_metrics_calculator.returns import calculate_period_returns
from quant_metrics_calculator.sharpe import calculate_sharpe_ratio
from quant_metrics_calculator.sortino import calculate_sortino_ratio
from quant_metrics_calculator.trade_reconstruction import FifoTradeReconstructor

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    def __init__(self, reconstructor: FifoTradeReconstructor | None = None) -> None:
        self._reconstructor = reconstructor or FifoTradeReconstructor()

    def compute(
        self,
        fills: list[TradeFill],
        equity_curve: list[EquityPoint],
        config: MetricsConfig,
    ) -> PerformanceMetrics:
        if not equity_curve:
            raise ValueError("equity_curve must not be empty")

        returns = calculate_period_returns(equity_curve)
        closed_trades = self._reconstructor.reconstruct(fills) if fills else []
        gross_profit, gross_loss, profit_factor = calculate_profit_factor(closed_trades)
        win_rate, winners, losers = calculate_win_rate(closed_trades)

        metrics = PerformanceMetrics(
            sharpe_ratio=calculate_sharpe_ratio(returns, config),
            sortino_ratio=calculate_sortino_ratio(returns, config),
            profit_factor=profit_factor,
            max_drawdown_pct=calculate_max_drawdown_pct(equity_curve),
            total_return_pct=calculate_total_return_pct(equity_curve),
            win_rate=win_rate,
            trade_count=len(closed_trades),
            winning_trades=winners,
            losing_trades=losers,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            equity_curve=tuple(equity_curve),
        )
        logger.info(
            "computed metrics trades=%s sharpe=%s profit_factor=%s",
            metrics.trade_count,
            metrics.sharpe_ratio,
            metrics.profit_factor,
        )
        return metrics
