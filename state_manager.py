import os
import json
import logging

logger = logging.getLogger("StateManager")


class StateManager:
    def __init__(self, state_file: str, trade_log_file: str):
        self.state_file = state_file
        self.trade_log_file = trade_log_file

    def load_state(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"State load failed: {e}")
        return {}

    def save_state(self, states: dict):
        try:
            with open(self.state_file, "w") as f:
                json.dump(states, f, indent=2)
        except Exception as e:
            logger.error(f"State save failed: {e}")

    def log_signal(self, analysis: dict):
        """Har signal ko trade log mein record karo."""
        log_entry = {
            "timestamp": analysis["metrics"].get("timestamp", ""),
            "symbol": analysis["metrics"]["symbol"],
            "status": analysis["status"],
            "confidence": analysis["confidence"],
            "price": analysis["metrics"]["price"],
            "delta": analysis["metrics"]["delta"],
            "open_interest": analysis["metrics"]["open_interest"],
            "reason": analysis["reason"]
        }

        logs = []
        if os.path.exists(self.trade_log_file):
            try:
                with open(self.trade_log_file, "r") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append(log_entry)

        # Sirf last 500 signals rakho
        logs = logs[-500:]

        try:
            with open(self.trade_log_file, "w") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"Trade log save failed: {e}")
