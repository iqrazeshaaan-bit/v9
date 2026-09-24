import os
import logging
from datetime import datetime, timezone
from data_engine import DataEngine
from micro_structure import MicroStructureAnalyzer
from discord_alert import DiscordNotifier
from state_manager import StateManager
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MainOrchestrator")


def run():
    if not config.WEBHOOK_URL:
        logger.error("⚠️ DISCORD_WEBHOOK_URL environment variable missing!")
        return

    analyzer = MicroStructureAnalyzer(
        delta_threshold=config.DELTA_THRESHOLD,
        oi_surge_pct=config.OI_SURGE_PCT
    )
    notifier = DiscordNotifier(webhook_url=config.WEBHOOK_URL)
    state_mgr = StateManager(config.STATE_FILE, config.TRADE_LOG_FILE)

    all_states = state_mgr.load_state()
    logger.info(f"Scanning {len(config.SYMBOLS_LIST)} symbols...")

    summary_results = []

    for symbol in config.SYMBOLS_LIST:
        logger.info(f"--- {symbol} ---")
        engine = DataEngine(symbol=symbol)

        market_data = engine.fetch_market_data()
        if market_data["price"] == 0.0:
            logger.warning(f"Empty price for {symbol}, skipping.")
            continue

        market_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        prev_state = all_states.get(symbol, {"price": 0.0, "oi": 0.0})
        analysis = analyzer.evaluate(market_data, prev_state)

        logger.info(
            f"{symbol} -> {analysis['status']} | "
            f"Price: ${market_data['price']:,.2f} | "
            f"Conf: {analysis['confidence']}%"
        )

        summary_results.append({
            "symbol": symbol,
            "status": analysis["status"],
            "price": market_data["price"]
        })

        if analysis["status"] != "NEUTRAL":
            notifier.send_signal(analysis)
            state_mgr.log_signal(analysis)
            logger.info(f"Signal dispatched: {analysis['status']}")

        all_states[symbol] = {
            "price": market_data["price"],
            "oi": market_data["open_interest"]
        }

    state_mgr.save_state(all_states)
    notifier.send_session_summary(summary_results)


if __name__ == "__main__":
    run()
