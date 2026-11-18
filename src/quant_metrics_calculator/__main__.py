from __future__ import annotations

import argparse
import json
import logging
from decimal import Decimal

from quant_metrics_calculator.models import MetricsConfig
from quant_metrics_calculator.overfitting_pipeline import (
    load_returns_matrix,
    run_overfitting_pipeline,
)
from quant_metrics_calculator.pipeline import run_metrics_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calculadora de métricas de rendimiento para operaciones cerradas.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    compute = subparsers.add_parser("compute", help="Calcula métricas desde fills y equity curve.")
    compute.add_argument("--fills", required=True)
    compute.add_argument("--equity", required=True)
    compute.add_argument("--symbol", required=True)
    compute.add_argument("--risk-free-rate", default="0.02")
    compute.add_argument("--periods-per-year", type=int, default=252)
    compute.add_argument("--output", default=None)

    overfit = subparsers.add_parser(
        "overfit",
        help="Deflated Sharpe ratio and probability of backtest overfitting (CSCV).",
    )
    overfit.add_argument("--returns", required=True, help="JSON returns matrix (see README).")
    overfit.add_argument("--selected", default=None, help="Strategy that was chosen.")
    overfit.add_argument("--n-trials", type=int, default=None)
    overfit.add_argument("--periods-per-year", type=int, default=None)
    overfit.add_argument("--n-splits", type=int, default=16)
    overfit.add_argument("--max-combinations", type=int, default=None)
    overfit.add_argument("--output", default=None)

    return parser


def _emit(payload: object, output: str | None, what: str) -> None:
    rendered = json.dumps(payload, indent=2)
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.write("\n")
        logging.getLogger(__name__).info("wrote %s to %s", what, output)
        return
    print(rendered)


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    if args.command == "compute":
        config = MetricsConfig(
            risk_free_rate_annual=Decimal(args.risk_free_rate),
            periods_per_year=args.periods_per_year,
        )
        result = run_metrics_pipeline(
            fills_path=args.fills,
            equity_path=args.equity,
            symbol=args.symbol,
            config=config,
        )
        _emit(result, args.output, "metrics")
        return

    if args.command == "overfit":
        report = run_overfitting_pipeline(
            load_returns_matrix(args.returns),
            selected=args.selected,
            n_trials=args.n_trials,
            periods_per_year=args.periods_per_year,
            n_splits=args.n_splits,
            max_combinations=args.max_combinations,
        )
        _emit(report, args.output, "overfitting report")
        return

    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
