# quant-metrics-calculator

Analysis package that processes closed trade history and the equity curve to compute statistical performance metrics: **Sharpe Ratio**, **Sortino Ratio**, **Profit Factor**, **max drawdown**, and **win rate**. Tenth module of the [quant-core-infra](https://github.com/juanmmm21/quant-core-infra) ecosystem.

Repository: [github.com/juanmmm21/quant-metrics-calculator](https://github.com/juanmmm21/quant-metrics-calculator)

---

## What it is and what problem it solves

Evaluating a strategy by absolute PnL alone is insufficient. You need to measure **risk-adjusted return** (Sharpe/Sortino), **consistency** (profit factor, win rate), and **worst-case scenario** (max drawdown).

This module transforms fills and the equity curve into a unified performance report, compatible with the output of `event-driven-backtester` and `market-condition-simulator`.

---

## Role in quant-core-infra

```text
event-driven-backtester ──► fills + equity curve ──┐
market-condition-simulator ──► executions ─────────┤
                                                   ▼
                                      quant-metrics-calculator
                                                   │
                                                   ▼
                                      trade-audit-logger / quant-terminal-web
```

Closes the quantitative evaluation loop of the backtest.

---

## Purpose

Demonstrates:

- Periodic return calculation from the equity curve
- Sharpe and Sortino with an annualized risk-free rate
- Profit factor and win rate from FIFO round-trips
- Max drawdown and total return
- JSON/JSONL pipelines compatible with the ecosystem

---

## Computed metrics

| Metric | Formula / method |
|---------|------------------|
| **Sharpe** | `mean(excess_returns) / std(excess_returns) × √periods_per_year` |
| **Sortino** | `mean(excess_returns) / downside_std × √periods_per_year` |
| **Profit factor** | `gross_profit / gross_loss` |
| **Max drawdown** | `max((peak - equity) / peak)` over the curve |
| **Total return** | `(final_equity - initial_equity) / initial_equity` |
| **Win rate** | `winning_trades / trade_count` |

Round-trips are reconstructed using **long-only FIFO** from buy/sell fills.

---

## Overfitting diagnostics

A high backtest Sharpe means little if it is the best of many tries. Two estimates guard against
that (`overfitting.py`, stdlib only; they use `float` because they are statistics, not money):

| Metric | What it answers | Method |
|--------|-----------------|--------|
| **Probabilistic Sharpe (PSR)** | P[true SR > 0] given sample length, skew and kurtosis | Bailey & López de Prado (2012) |
| **Deflated Sharpe (DSR)** | P[true SR > the best SR expected from `n_trials` zero-skill tries] | Bailey & López de Prado (2014) |
| **PBO** | Probability that the in-sample winner ranks at or below the out-of-sample median | CSCV, Bailey, Borwein, López de Prado & Zhu (2017) |

- `n_trials` must count **every configuration you tried** before choosing one (strategies,
  parameters, timeframes). Under-counting inflates the DSR.
- PBO cuts the T × N return matrix into `n_splits` contiguous blocks (default 16 → 12,870
  combinations) and uses the conservative convention `logit <= 0`. Block sums are precomputed, so
  each combination costs O(splits × strategies).
- The report also gives the probability of an out-of-sample loss and the IS→OOS degradation
  slope (negative = the better it looked in-sample, the worse it did out-of-sample).

```bash
quant-metrics-calculator overfit \
  --returns returns_matrix.json \
  --n-trials 10 \
  --periods-per-year 8760 \
  --output overfitting.json
```

Input (`returns_matrix.json`, e.g. the `returns_matrix` emitted by `event-driven-backtester validate`):

```json
{
  "strategies": ["rsi_mean_reversion", "macd_crossover"],
  "returns": [[0.0012, -0.0004], [-0.0031, 0.0008]],
  "selected": "rsi_mean_reversion",
  "n_trials": 10
}
```

Output (excerpt):

```json
{
  "selected_strategy": "rsi_mean_reversion",
  "deflated_sharpe": {"sharpe_ratio": 0.012, "benchmark_sharpe_ratio": 0.018,
                      "probabilistic_sharpe_ratio": 0.81, "deflated_sharpe_ratio": 0.34},
  "pbo": {"probability_of_overfitting": 0.47, "n_combinations": 12870,
          "probability_oos_loss": 0.52, "degradation_slope": -0.6}
}
```

The numbers above illustrate the format; they are not results.

---

## Architecture

```text
fills JSONL + equity JSON
         │
         ▼
PerformanceCalculator
         │
    ┌────┼────┬──────────┬────────────┐
    ▼    ▼    ▼          ▼            ▼
Returns Sharpe Sortino Drawdown ProfitFactor
    │                              │
    └──────── FIFO reconstructor ──┘
                   │
                   ▼
          PerformanceMetrics
```

---

## Configuration: `MetricsConfig`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `risk_free_rate_annual` | `0.02` | Annual risk-free rate (2%) |
| `periods_per_year` | `252` | Annualization periods (trading days) |
| `min_observations` | `2` | Minimum returns required for ratios |

---

## Requirements

- Python **3.11+**

---

## Installation

```bash
cd quant-metrics-calculator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## CLI usage

```bash
quant-metrics-calculator compute \
  --fills samples/btcusdt_fills.jsonl \
  --equity samples/btcusdt_equity.json \
  --symbol BTCUSDT \
  --risk-free-rate 0.02 \
  --output metrics.json
```

### Expected output (excerpt)

```json
{
  "sharpe_ratio": "1.42",
  "sortino_ratio": "2.10",
  "profit_factor": "1.85",
  "max_drawdown_pct": "0.00594",
  "total_return_pct": "0.003",
  "win_rate": "0.5",
  "trade_count": 2
}
```

---

## Input formats

### Fills (JSONL)

```json
{
  "order_id": "ord-1",
  "symbol": "BTCUSDT",
  "side": "buy",
  "quantity": "0.01",
  "price": "100",
  "commission": "0.1",
  "filled_at": "2024-01-01T12:00:00.000Z"
}
```

### Equity curve (JSON array or object with `equity_curve`)

```json
[
  {"event_time": "2024-01-01T12:00:00.000Z", "equity": "10000"},
  {"event_time": "2024-01-01T13:00:00.000Z", "equity": "10090"}
]
```

---

## Programmatic usage

```python
from decimal import Decimal

from quant_metrics_calculator import MetricsConfig, run_metrics_pipeline

metrics = run_metrics_pipeline(
    fills_path="fills.jsonl",
    equity_path="equity.json",
    symbol="BTCUSDT",
    config=MetricsConfig(risk_free_rate_annual=Decimal("0.03")),
)
```

---

## Development

```bash
pytest -q
ruff check src tests
mypy src
```

---

## Troubleshooting

| Symptom | Likely cause | Solution |
|---------|----------------|----------|
| `sell quantity exceeds open long position` | Out-of-order fills or implicit short | Sort chronologically; long-only FIFO |
| Sharpe/Sortino at 0 | Too few points in the equity curve | Add more observations or lower `min_observations` |
| `equity_curve must not be empty` | Empty equity file | Provide at least one equity point |

---

## Roadmap

- [x] Deflated Sharpe ratio and probability of backtest overfitting (v0.2.0)
- [ ] Short-selling support in the FIFO reconstructor
- [ ] Rolling metrics (30d rolling Sharpe)
- [ ] HTML/PDF export for `quant-terminal-web`
- [ ] Direct integration with `event-driven-backtester`'s JSON output

---

## License

MIT
