# quant-metrics-calculator

Paquete de análisis que procesa el historial de operaciones cerradas y la curva de equidad para calcular métricas estadísticas de rendimiento: **Sharpe Ratio**, **Sortino Ratio**, **Profit Factor**, **max drawdown** y **win rate**. Décimo módulo del ecosistema [quant-core-infra](https://github.com/juanmmm21/quant-core-infra).

Repositorio: [github.com/juanmmm21/quant-metrics-calculator](https://github.com/juanmmm21/quant-metrics-calculator)

---

## Qué es y qué problema resuelve

Evaluar una estrategia solo por PnL absoluto es insuficiente. Necesitas medir **riesgo ajustado** (Sharpe/Sortino), **consistencia** (profit factor, win rate) y **peor escenario** (max drawdown).

Este módulo transforma fills y equity curve en un informe unificado de rendimiento, compatible con la salida de `event-driven-backtester` y `market-condition-simulator`.

---

## Rol en quant-core-infra

```text
event-driven-backtester ──► fills + equity curve ──┐
market-condition-simulator ──► executions ─────────┤
                                                   ▼
                                      quant-metrics-calculator
                                                   │
                                                   ▼
                                      trade-audit-logger / quant-terminal-web
```

Cierra el ciclo de evaluación cuantitativa del backtest.

---

## Objetivo

Demuestra:

- Cálculo de retornos periódicos desde equity curve
- Sharpe y Sortino con tasa libre de riesgo anualizada
- Profit factor y win rate desde round-trips FIFO
- Max drawdown y retorno total
- Pipelines JSON/JSONL compatibles con el ecosistema

---

## Métricas calculadas

| Métrica | Fórmula / método |
|---------|------------------|
| **Sharpe** | `mean(excess_returns) / std(excess_returns) × √periods_per_year` |
| **Sortino** | `mean(excess_returns) / downside_std × √periods_per_year` |
| **Profit factor** | `gross_profit / gross_loss` |
| **Max drawdown** | `max((peak - equity) / peak)` sobre la curva |
| **Total return** | `(final_equity - initial_equity) / initial_equity` |
| **Win rate** | `winning_trades / trade_count` |

Los round-trips se reconstruyen con **FIFO long-only** a partir de fills buy/sell.

---

## Arquitectura

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

## Configuración: `MetricsConfig`

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `risk_free_rate_annual` | `0.02` | Tasa libre de riesgo anual (2%) |
| `periods_per_year` | `252` | Periodos de anualización (días de trading) |
| `min_observations` | `2` | Mínimo de retornos para ratios |

---

## Requisitos

- Python **3.11+**

---

## Instalación

```bash
cd quant-metrics-calculator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Uso CLI

```bash
quant-metrics-calculator compute \
  --fills samples/btcusdt_fills.jsonl \
  --equity samples/btcusdt_equity.json \
  --symbol BTCUSDT \
  --risk-free-rate 0.02 \
  --output metrics.json
```

### Salida esperada (extracto)

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

## Formatos de entrada

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

### Equity curve (JSON array o objeto con `equity_curve`)

```json
[
  {"event_time": "2024-01-01T12:00:00.000Z", "equity": "10000"},
  {"event_time": "2024-01-01T13:00:00.000Z", "equity": "10090"}
]
```

---

## Uso programático

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

## Desarrollo

```bash
pytest -q
ruff check src tests
mypy src
```

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `sell quantity exceeds open long position` | Fills desordenados o short implícito | Ordena cronológicamente; solo long FIFO |
| Sharpe/Sortino en 0 | Pocos puntos en equity curve | Añade más observaciones o baja `min_observations` |
| `equity_curve must not be empty` | Archivo equity vacío | Proporciona al menos un punto de equity |

---

## Roadmap

- [ ] Soporte short-selling en reconstructor FIFO
- [ ] Métricas rolling (Sharpe móvil 30d)
- [ ] Export HTML/PDF para `quant-terminal-web`
- [ ] Integración directa con salida JSON de `event-driven-backtester`

---

## Licencia

MIT
