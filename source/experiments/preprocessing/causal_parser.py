#!/usr/bin/env python3
"""Causal Data Parser for High-Frequency Crypto Tick Trade Streams.

Conforms strictly to docs/FEATURE_SPECIFICATION.md and plan.md §10.
Enforces past-only state dependencies (zero future-peeking), deterministic
1-to-1 sample ID mapping, and fail-closed validation for non-finite values,
negative prices/quantities, non-monotonic timestamps, and malformed rows.

Standard library only. No third-party dependencies.
"""
from __future__ import annotations

import csv
import math
from typing import NamedTuple, Optional, Sequence


class CausalParseError(ValueError):
    """Raised when raw trade data violates causality, finite bounds, or formatting rules."""
    pass


class ParsedTrade(NamedTuple):
    sample_id: str
    trade_id: int
    timestamp_ms: int
    price: float
    qty: float
    quote_qty: float
    is_buyer_maker: float
    interarrival_ms: float
    log_return: float
    trade_flow: float
    raw_ordinal: int

    def feature_vector(self) -> list[float]:
        """Returns the 7 canonical features defined in docs/FEATURE_SPECIFICATION.md."""
        return [
            self.price,
            self.qty,
            self.quote_qty,
            self.is_buyer_maker,
            self.interarrival_ms,
            self.log_return,
            self.trade_flow,
        ]


class CausalTradeParser:
    """Strictly causal streaming trade parser maintaining temporal past-only state."""

    def __init__(self):
        self.prev_timestamp_ms: Optional[int] = None
        self.prev_price: Optional[float] = None
        self.events_parsed: int = 0

    def reset(self) -> None:
        """Reset causal state between independent streams or sessions."""
        self.prev_timestamp_ms = None
        self.prev_price = None
        self.events_parsed = 0

    def parse_row(
        self,
        row: Sequence[str],
        ordinal: int = 0,
        date_str: str = "20170817",
    ) -> ParsedTrade:
        """Parse and validate a single raw trade row against the canonical Binance schema.

        Raw schema: [id, price, qty, quote_qty, time, is_buyer_maker, is_best_match]
        """
        if not row or len(row) < 6:
            raise CausalParseError(f"Row {ordinal}: Malformed column count (expected >= 6, got {len(row) if row else 0})")

        # 1. Parse Trade ID
        try:
            trade_id = int(row[0].strip())
            if trade_id < 0:
                raise ValueError("Trade ID must be non-negative")
        except (ValueError, TypeError) as ex:
            raise CausalParseError(f"Row {ordinal}: Invalid trade ID '{row[0]}': {ex}")

        # 2. Parse Price
        try:
            price = float(row[1])
            if not math.isfinite(price):
                raise ValueError(f"Non-finite price: {price}")
            if price <= 0.0:
                raise ValueError(f"Non-positive price: {price}")
        except (ValueError, TypeError) as ex:
            raise CausalParseError(f"Row {ordinal}: Invalid price '{row[1]}': {ex}")

        # 3. Parse Quantity
        try:
            qty = float(row[2])
            if not math.isfinite(qty):
                raise ValueError(f"Non-finite quantity: {qty}")
            if qty <= 0.0:
                raise ValueError(f"Non-positive quantity: {qty}")
        except (ValueError, TypeError) as ex:
            raise CausalParseError(f"Row {ordinal}: Invalid quantity '{row[2]}': {ex}")

        # 4. Parse Quote Quantity
        try:
            quote_qty = float(row[3])
            if not math.isfinite(quote_qty):
                raise ValueError(f"Non-finite quote quantity: {quote_qty}")
            if quote_qty < 0.0:
                raise ValueError(f"Negative quote quantity: {quote_qty}")
        except (ValueError, TypeError) as ex:
            raise CausalParseError(f"Row {ordinal}: Invalid quote quantity '{row[3]}': {ex}")

        # 5. Parse Exchange Timestamp
        try:
            timestamp_ms = int(row[4].strip())
            if timestamp_ms < 0:
                raise ValueError("Timestamp must be non-negative")
        except (ValueError, TypeError) as ex:
            raise CausalParseError(f"Row {ordinal}: Invalid timestamp '{row[4]}': {ex}")

        # 6. Parse Buyer Maker Flag
        val_maker_str = str(row[5]).strip().lower()
        if val_maker_str in ("true", "1", "1.0"):
            is_buyer_maker = 1.0
        elif val_maker_str in ("false", "0", "0.0"):
            is_buyer_maker = 0.0
        else:
            raise CausalParseError(f"Row {ordinal}: Invalid is_buyer_maker boolean flag '{row[5]}'")

        # 7. Validate Timestamp Monotonicity (Non-Decreasing Invariant)
        if self.prev_timestamp_ms is not None:
            if timestamp_ms < self.prev_timestamp_ms:
                raise CausalParseError(
                    f"Row {ordinal}: Non-monotonic exchange timestamp retrogression: "
                    f"current {timestamp_ms} < previous {self.prev_timestamp_ms}"
                )

        # 8. Compute Causal Incremental Features
        if self.prev_timestamp_ms is None:
            # Initial state initialization: delta_t_0 = 0.0 ms
            interarrival_ms = 0.0
        else:
            interarrival_ms = float(timestamp_ms - self.prev_timestamp_ms)

        if self.prev_price is None:
            # Initial state initialization: r_0 = ln(p_0 / p_0) = 0.0
            log_return = 0.0
        else:
            log_return = math.log(price / self.prev_price)

        # Signed order flow: +qty if buyer is taker (maker=0), -qty if seller is taker (maker=1)
        trade_flow = qty * (1.0 - 2.0 * is_buyer_maker)

        # Format deterministic 1-to-1 Sample ID: t_YYYYMMDD_XXXXXXX
        clean_date = date_str.replace("-", "")
        sample_id = f"t_{clean_date}_{trade_id:07d}"

        # 9. Update Causal State (Past only)
        self.prev_timestamp_ms = timestamp_ms
        self.prev_price = price
        self.events_parsed += 1

        return ParsedTrade(
            sample_id=sample_id,
            trade_id=trade_id,
            timestamp_ms=timestamp_ms,
            price=price,
            qty=qty,
            quote_qty=quote_qty,
            is_buyer_maker=is_buyer_maker,
            interarrival_ms=interarrival_ms,
            log_return=log_return,
            trade_flow=trade_flow,
            raw_ordinal=ordinal,
        )

    def parse_stream(
        self,
        rows: Sequence[Sequence[str]],
        date_str: str = "20170817",
    ) -> list[ParsedTrade]:
        """Sequentially parse a collection of raw trade rows, maintaining causal continuity."""
        parsed = []
        for ordinal, row in enumerate(rows):
            parsed.append(self.parse_row(row, ordinal=ordinal, date_str=date_str))
        return parsed
