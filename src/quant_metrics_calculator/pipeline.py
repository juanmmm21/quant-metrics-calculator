from __future__ import annotations

from typing import Any

from quant_metrics_calculator.calculator import PerformanceCalculator
from quant_metrics_calculator.ingest import load_equity_curve, load_fills
from quant_metrics_calculator.models import MetricsConfig, PerformanceMetrics


def serialize_metrics(metrics: PerformanceMetrics) -> dict[str, Any]:
    return {
        "sharpe_ratio": str(metrics.sharpe_ratio),
        "sortino_ratio": str(metrics.sortino_ratio),
        "profit_factor": str(metrics.profit_factor),
        "max_drawdown_pct": str(metrics.max_drawdown_pct),
        "total_return_pct": str(metrics.total_return_pct),
        "win_rate": str(metrics.win_rate),
        "trade_count": metrics.trade_count,
        "winning_trades": metrics.winning_trades,
        "losing_trades": metrics.losing_trades,
        "gross_profit": str(metrics.gross_profit),
        "gross_loss": str(metrics.gross_loss),
        "equity_curve": [
            {
                "event_time": point.event_time.isoformat(),
                "equity": str(point.equity),
            }
            for point in metrics.equity_curve
        ],
    }


def run_metrics_pipeline(
    fills_path: str,
    equity_path: str,
    symbol: str,
    config: MetricsConfig,
) -> dict[str, Any]:
    fills = load_fills(fills_path, default_symbol=symbol)
    equity_curve = load_equity_curve(equity_path)
    calculator = PerformanceCalculator()
    metrics = calculator.compute(fills, equity_curve, config)
    return serialize_metrics(metrics)
