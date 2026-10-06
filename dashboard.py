from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from Automatisches_trading_system import (
    BinancePublicMarketData,
    PaperTradingEngine,
    RiskConfig,
    Signal,
    SmaCrossoverStrategy,
)


st.set_page_config(page_title="Trading-System | Paper-Dashboard", layout="wide")
st.title("Automatisches Trading-System")
st.warning("Live-Marktdaten, aber ausschließlich Paper-Trading. Es werden keine echten Orders gesendet.")

with st.sidebar:
    st.header("Markt und Strategie")
    symbol = st.selectbox("Handelspaar (Binance Spot)", ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"])
    interval = st.selectbox("Kerzenintervall", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)
    fast_period = st.number_input("Kurzer SMA", min_value=1, max_value=100, value=5)
    slow_period = st.number_input("Langer SMA", min_value=2, max_value=200, value=12)
    initial_cash = st.number_input("Paper-Startkapital (USDT)", min_value=100.0, value=10_000.0, step=500.0)
    risk_percent = st.number_input("Risiko je Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    refresh_seconds = st.selectbox("Aktualisierung (Sekunden)", [5, 10, 30], index=1)
    strategy_enabled = st.toggle("Paper-Strategie aktiv", value=True)

if slow_period <= fast_period:
    st.error("Der lange SMA muss größer als der kurze SMA sein.")
    st.stop()

settings = (symbol, interval, fast_period, slow_period, initial_cash, risk_percent)
if st.session_state.get("settings") != settings:
    st.session_state.settings = settings
    st.session_state.strategy = SmaCrossoverStrategy(int(fast_period), int(slow_period))
    st.session_state.engine = PaperTradingEngine(
        float(initial_cash),
        RiskConfig(risk_per_trade=float(risk_percent) / 100),
    )
    st.session_state.last_processed = None
    st.session_state.market_candles = []
    st.session_state.last_signal = "Noch kein Signal"


@st.fragment(run_every=f"{refresh_seconds}s")
def live_panel() -> None:
    try:
        candles = BinancePublicMarketData().fetch_closed_candles(symbol, interval, limit=200)
    except (RuntimeError, ValueError) as error:
        st.error(f"Marktdaten konnten nicht geladen werden: {error}")
        st.caption("Bitte Verbindung prüfen oder Aktualisierung abwarten.")
        return

    engine = st.session_state.engine
    strategy = st.session_state.strategy
    last_processed = st.session_state.last_processed
    fresh_candles = [candle for candle in candles if last_processed is None or candle.timestamp > last_processed]

    for candle in fresh_candles:
        signal = strategy.on_candle(candle)
        if signal is not None:
            st.session_state.last_signal = signal.value
        engine.on_candle(candle, signal if strategy_enabled else None)
        st.session_state.last_processed = candle.timestamp
        st.session_state.market_candles.append(candle)

    st.session_state.market_candles = st.session_state.market_candles[-200:]
    latest = candles[-1]
    position = engine.position
    unrealized_pnl = (latest.close - position.entry_price) * position.quantity if position else 0.0
    closed_trades = [trade for trade in engine.trades if trade.side == "VERKAUF"]
    realized_pnl = sum(trade.pnl for trade in closed_trades)

    st.caption(
        f"Quelle: Binance Public API | Letzte abgeschlossene Kerze: "
        f"{latest.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"Abruf: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
    )
    metrics = st.columns(4)
    metrics[0].metric(f"{symbol} Schlusskurs", f"{latest.close:,.4f} USDT")
    metrics[1].metric("Paper-Eigenkapital", f"{engine.equity(latest.close):,.2f} USDT")
    metrics[2].metric("Realisierter Paper-P/L", f"{realized_pnl:+,.2f} USDT")
    metrics[3].metric("Letztes Signal", st.session_state.last_signal)

    if st.session_state.market_candles:
        st.subheader("Kursverlauf (abgeschlossene Kerzen)")
        st.line_chart({"Close (USDT)": [candle.close for candle in st.session_state.market_candles]})

    left, right = st.columns(2)
    with left:
        st.subheader("Paper-Position")
        if position:
            st.write(f"Menge: {position.quantity:.8f} {symbol.removesuffix('USDT')}")
            st.write(f"Einstieg: {position.entry_price:,.4f} USDT")
            st.write(f"Unrealisierter P/L: {unrealized_pnl:+,.2f} USDT")
            st.write(f"Stop-Loss: {position.stop_loss:,.4f} | Take-Profit: {position.take_profit:,.4f} USDT")
        else:
            st.write("Keine offene Paper-Position.")
        st.write(f"Paper-Cash: {engine.cash:,.2f} USDT")
        if engine._daily_halted:
            st.error("Tagesverlustlimit erreicht: neue Paper-Einstiege sind gesperrt.")
        if not strategy_enabled:
            st.info("Strategie pausiert. Bestehende Paper-Positionen werden weiter überwacht.")

    with right:
        st.subheader("Letzte Paper-Trades")
        if engine.trades:
            rows = [
                {
                    "Zeit (UTC)": trade.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Seite": trade.side,
                    "Menge": round(trade.quantity, 8),
                    "Preis (USDT)": round(trade.price, 4),
                    "P/L (USDT)": round(trade.pnl, 2),
                    "Grund": trade.reason,
                }
                for trade in reversed(engine.trades[-20:])
            ]
            st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.write("Noch keine Signale oder Paper-Trades.")

    st.caption(
        "Die ersten bis zu 200 abgeschlossenen Kerzen werden beim Start zur SMA-Aufwärmung "
        "und als Paper-Simulation verarbeitet. Gebühren/Slippage sind vereinfachte Modellwerte; "
        "dies ist keine echte Ausführung."
    )


live_panel()
