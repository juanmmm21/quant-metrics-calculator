from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_metrics_calculator.models import (
    EquityPoint,
    TradeFill,
    decimal_from_value,
    parse_fill_side,
    utc_from_iso8601,
)


def load_fills(path: str | Path, default_symbol: str) -> list[TradeFill]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"fills file not found: {file_path}")

    fills: list[TradeFill] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid json on line {line_number}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"line {line_number} must contain a JSON object")
            fills.append(parse_trade_fill(payload, default_symbol))

    return fills


def load_equity_curve(path: str | Path) -> list[EquityPoint]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"equity file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError("equity file must contain valid json") from exc

    if isinstance(payload, dict) and "equity_curve" in payload:
        entries = payload["equity_curve"]
    elif isinstance(payload, list):
        entries = payload
    else:
        raise ValueError("equity file must be a list or object with equity_curve")

    if not isinstance(entries, list) or not entries:
        raise ValueError("equity_curve must be a non-empty list")

    curve: list[EquityPoint] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"equity point {index} must be an object")
        curve.append(parse_equity_point(entry))
    return curve


def parse_trade_fill(payload: dict[str, Any], default_symbol: str) -> TradeFill:
    order_id = payload.get("order_id") or payload.get("client_order_id")
    if not order_id:
        raise ValueError("missing order_id or client_order_id")

    required = ("side", "quantity", "price", "filled_at")
    for field in required:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")

    symbol = str(payload.get("symbol", default_symbol))
    commission_raw = payload.get("commission", "0")

    return TradeFill(
        order_id=str(order_id),
        symbol=symbol,
        side=parse_fill_side(str(payload["side"])),
        quantity=decimal_from_value(payload["quantity"], "quantity"),
        price=decimal_from_value(payload["price"], "price"),
        commission=decimal_from_value(commission_raw, "commission"),
        filled_at=utc_from_iso8601(str(payload["filled_at"])),
    )


def parse_equity_point(payload: dict[str, Any]) -> EquityPoint:
    if "equity" not in payload or "event_time" not in payload:
        raise ValueError("equity point requires equity and event_time")

    return EquityPoint(
        event_time=utc_from_iso8601(str(payload["event_time"])),
        equity=decimal_from_value(payload["equity"], "equity"),
    )
