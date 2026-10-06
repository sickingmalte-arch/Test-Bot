"""Offline-Paper-Trading-Demo; dieses Modul sendet keine echten Orders."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite, sin
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if not all(isfinite(value) for value in values):
            raise ValueError("Kerzendaten müssen endlich sein.")
        if min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0:
            raise ValueError("Kurse müssen positiv und Volumen nicht-negativ sein.")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("Das Hoch/Tief muss Open und Close einschließen.")


class BinancePublicMarketData:
    BASE_URL = "https://api.binance.com/api/v3/klines"
    ALLOWED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}

    def fetch_closed_candles(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 200) -> list[Candle]:
        symbol = symbol.upper()
        if not re.fullmatch(r"[A-Z0-9]{5,20}", symbol):
            raise ValueError("Ungültiges Börsensymbol.")
        if interval not in self.ALLOWED_INTERVALS or not 1 <= limit <= 1000:
            raise ValueError("Intervall oder Anzahl der Kerzen ist ungültig.")

        query = urlencode({"symbol": symbol, "interval": interval, "limit": limit})
        request = Request(
            f"{self.BASE_URL}?{query}",
            headers={"User-Agent": "PaperTradingDashboard/1.0"},
        )
        try:
            with urlopen(request, timeout=8) as response:
                rows = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Öffentliche Binance-Kursdaten nicht verfügbar: {error}") from error

        if not isinstance(rows, list):
            raise RuntimeError(f"Unerwartete Antwort der Binance-API: {rows}")

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        candles = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 7 or int(row[6]) >= now_ms:
                continue
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )
        if not candles:
            raise RuntimeError("Die API lieferte keine abgeschlossenen Kerzen.")
        return candles


class Signal(Enum):
    BUY = "KAUFEN"
    SELL = "VERKAUFEN"


class SmaCrossoverStrategy:
    def __init__(self, fast_period: int = 5, slow_period: int = 12) -> None:
        if fast_period < 1 or slow_period <= fast_period:
            raise ValueError("Es muss gelten: 1 <= fast_period < slow_period.")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self._closes: list[float] = []

    def on_candle(self, candle: Candle) -> Optional[Signal]:
        self._closes.append(candle.close)
        if len(self._closes) > self.slow_period + 1:
            del self._closes[0]
        if len(self._closes) < self.slow_period + 1:
            return None

        previous_fast = sum(self._closes[-self.fast_period - 1 : -1]) / self.fast_period
        previous_slow = sum(self._closes[-self.slow_period - 1 : -1]) / self.slow_period
        current_fast = sum(self._closes[-self.fast_period :]) / self.fast_period
        current_slow = sum(self._closes[-self.slow_period :]) / self.slow_period

        if previous_fast <= previous_slow and current_fast > current_slow:
            return Signal.BUY
        if previous_fast >= previous_slow and current_fast < current_slow:
            return Signal.SELL
        return None


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade: float = 0.01
    max_position_fraction: float = 0.25
    stop_loss_fraction: float = 0.02
    take_profit_fraction: float = 0.04
    max_daily_loss_fraction: float = 0.03
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005

    def __post_init__(self) -> None:
        fractions = (
            self.risk_per_trade,
            self.max_position_fraction,
            self.stop_loss_fraction,
            self.take_profit_fraction,
            self.max_daily_loss_fraction,
        )
        if any(not isfinite(value) or not 0 < value <= 1 for value in fractions):
            raise ValueError("Risiko- und Positionslimits müssen zwischen 0 und 1 liegen.")
        if not isfinite(self.commission_rate) or self.commission_rate < 0:
            raise ValueError("Die Gebühren müssen endlich und nicht-negativ sein.")
        if not isfinite(self.slippage_rate) or not 0 <= self.slippage_rate < 1:
            raise ValueError("Slippage muss endlich und zwischen 0 und 1 liegen.")


@dataclass
class Position:
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_fee: float


@dataclass(frozen=True)
class Trade:
    timestamp: datetime
    side: str
    quantity: float
    price: float
    pnl: float
    reason: str


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def position_size(self, equity: float, cash: float, entry_price: float) -> float:
        risk_budget = equity * self.config.risk_per_trade
        stop_fill = entry_price * (1 - self.config.stop_loss_fraction) * (1 - self.config.slippage_rate)
        loss_per_unit = (
            entry_price
            - stop_fill
            + entry_price * self.config.commission_rate
            + stop_fill * self.config.commission_rate
        )
        quantity_by_risk = risk_budget / loss_per_unit
        quantity_by_exposure = equity * self.config.max_position_fraction / entry_price
        quantity_by_cash = cash / (entry_price * (1 + self.config.commission_rate))
        return max(0.0, min(quantity_by_risk, quantity_by_exposure, quantity_by_cash))


class PaperTradingEngine:
    def __init__(self, initial_cash: float = 10_000.0, config: Optional[RiskConfig] = None) -> None:
        if not isfinite(initial_cash) or initial_cash <= 0:
            raise ValueError("Das Startkapital muss positiv und endlich sein.")
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.config = config or RiskConfig()
        self.risk_manager = RiskManager(self.config)
        self.position: Optional[Position] = None
        self.trades: list[Trade] = []
        self._current_day = None
        self._day_start_equity = initial_cash
        self._daily_halted = False

    def equity(self, mark_price: float) -> float:
        position_value = self.position.quantity * mark_price if self.position else 0.0
        return self.cash + position_value

    def on_candle(self, candle: Candle, signal: Optional[Signal]) -> None:
        if self._current_day != candle.timestamp.date():
            self._current_day = candle.timestamp.date()
            self._day_start_equity = self.equity(candle.open)
            self._daily_halted = False

        if self.position:
            stop_hit = candle.low <= self.position.stop_loss
            target_hit = candle.high >= self.position.take_profit
            if stop_hit:
                raw_price = min(candle.open, self.position.stop_loss)
                self._close_position(candle, raw_price, "Stop-Loss")
            elif target_hit:
                raw_price = max(candle.open, self.position.take_profit)
                self._close_position(candle, raw_price, "Take-Profit")

        if self.equity(candle.close) <= self._day_start_equity * (1 - self.config.max_daily_loss_fraction):
            self._daily_halted = True
            if self.position:
                self._close_position(candle, candle.close, "Tagesverlustlimit")

        if signal is Signal.SELL and self.position:
            self._close_position(candle, candle.close, "Verkaufssignal")
        elif signal is Signal.BUY and not self.position and not self._daily_halted:
            self._open_position(candle)

    def _open_position(self, candle: Candle) -> None:
        entry_price = candle.close * (1 + self.config.slippage_rate)
        equity = self.equity(candle.close)
        quantity = self.risk_manager.position_size(equity, self.cash, entry_price)
        if quantity <= 0:
            return

        notional = quantity * entry_price
        fee = notional * self.config.commission_rate
        self.cash -= notional + fee
        self.position = Position(
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=entry_price * (1 - self.config.stop_loss_fraction),
            take_profit=entry_price * (1 + self.config.take_profit_fraction),
            entry_fee=fee,
        )
        self.trades.append(Trade(candle.timestamp, "KAUF", quantity, entry_price, 0.0, "SMA-Kreuzung"))

    def _close_position(self, candle: Candle, raw_price: float, reason: str) -> None:
        if not self.position:
            return
        position = self.position
        exit_price = raw_price * (1 - self.config.slippage_rate)
        exit_fee = position.quantity * exit_price * self.config.commission_rate
        self.cash += position.quantity * exit_price - exit_fee
        pnl = (exit_price - position.entry_price) * position.quantity - position.entry_fee - exit_fee
        self.trades.append(Trade(candle.timestamp, "VERKAUF", position.quantity, exit_price, pnl, reason))
        self.position = None


def generate_demo_candles(count: int) -> list[Candle]:
    if count < 1:
        raise ValueError("Die Anzahl der Demokerzen muss mindestens 1 sein.")

    candles = []
    previous_close = 100.0
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        phase = index % 90
        drift = 0.004 if phase < 35 else -0.004 if phase < 65 else 0.003
        open_price = previous_close
        close = max(1.0, open_price * (1 + drift + 0.0015 * sin(index * 0.8)))
        high = max(open_price, close) * 1.003
        low = min(open_price, close) * 0.997
        candles.append(
            Candle(
                timestamp=start + timedelta(minutes=15 * index),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=100 + index % 50,
            )
        )
        previous_close = close
    return candles


def run_demo(args: argparse.Namespace) -> None:
    config = RiskConfig(risk_per_trade=args.risk_percent / 100)
    strategy = SmaCrossoverStrategy(args.fast, args.slow)
    engine = PaperTradingEngine(args.cash, config)
    candles = generate_demo_candles(args.candles)

    print("Paper-Trading-Demo (synthetische Daten, keine echten Orders)")
    print(f"Startkapital: {args.cash:,.2f} USD | Risiko je Trade: {args.risk_percent:.2f}%")
    for candle in candles:
        signal = strategy.on_candle(candle)
        previous_trade_count = len(engine.trades)
        engine.on_candle(candle, signal)
        for trade in engine.trades[previous_trade_count:]:
            details = f"{trade.timestamp.isoformat()} {trade.side} {trade.quantity:.6f} zu {trade.price:.2f} USD"
            if trade.side == "VERKAUF":
                details += f" | P/L {trade.pnl:+.2f} USD | {trade.reason}"
            else:
                details += f" | {trade.reason}"
            print(details)

    last_price = candles[-1].close
    closed_trades = [trade for trade in engine.trades if trade.side == "VERKAUF"]
    realized_pnl = sum(trade.pnl for trade in closed_trades)
    winning_trades = sum(trade.pnl > 0 for trade in closed_trades)
    print("\n--- Übersicht ---")
    print(f"Endkapital inkl. offener Position: {engine.equity(last_price):,.2f} USD")
    print(f"Realisierter Gewinn/Verlust: {realized_pnl:+,.2f} USD")
    print(f"Geschlossene Trades: {len(closed_trades)} | Gewinner: {winning_trades}")
    if engine.position:
        print(
            f"Offene Position: {engine.position.quantity:.6f} Einheiten | "
            f"Stop {engine.position.stop_loss:.2f} | Ziel {engine.position.take_profit:.2f} USD"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline-Paper-Trading-Demo")
    parser.add_argument("--candles", type=int, default=180, help="Anzahl synthetischer Kerzen")
    parser.add_argument("--cash", type=float, default=10_000.0, help="Startkapital in USD")
    parser.add_argument("--fast", type=int, default=5, help="Kurze SMA-Periode")
    parser.add_argument("--slow", type=int, default=12, help="Lange SMA-Periode")
    parser.add_argument("--risk-percent", type=float, default=1.0, help="Risiko je Trade in Prozent")
    args = parser.parse_args()
    if args.candles < 1 or not isfinite(args.cash) or args.cash <= 0 or not 0 < args.risk_percent <= 100:
        parser.error("Kerzen und Kapital müssen positiv sein; Risiko muss zwischen 0 und 100 liegen.")
    run_demo(args)


if __name__ == "__main__":
    main()
